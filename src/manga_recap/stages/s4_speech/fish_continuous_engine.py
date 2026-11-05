"""Continuous Fish Audio narration with GPU forced alignment.

The old Fish path stitched one clip per block and estimated word positions from
character counts. This path keeps the cloud voice, but gives it the whole
narration at once and then measures the finished audio on Kaggle's GPU. The
renderer receives one word timing for every token in its beat list, so panel
cuts come from speech rather than arithmetic.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import numpy as np
import soundfile as sf

from ...core import env
from ...core.kaggle_io import KaggleClient, KaggleError
from ...core.logging import get_logger, write_stage_status
from ...core.paths import repo_path
from ...core.schema import ScriptFile, TimelineFile, load_model, save_model
from ...render.sync import alignment_tokens, beats_for_blocks, plan_shots
from .fish_tts_engine import _apply_tempo, apply_pronunciation_map

if TYPE_CHECKING:
    from ...core.config import Config
    from ...core.paths import ChapterPaths

_log = get_logger("stages.s4_speech.fish_continuous")

DEFAULT_MODEL = "s2.1-pro-free"
DEFAULT_VOICE_ID = "802e3bc2b27e49c2995d23ef70e6ac89"


def run_fish_continuous_tts(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> TimelineFile:
    """Synthesize one continuous narration, then align every script beat."""
    fish_script_file = paths.root / "04_script_fish.json"
    script_source = fish_script_file if fish_script_file.exists() else paths.script_file
    script = load_model(script_source, ScriptFile)
    if not script.blocks:
        raise ValueError("The storyboard has no blocks. Run `manga script` first.")
    _log.info("Stage 4 (Fish continuous): using %s", script_source.name)

    if paths.timeline_file.exists() and paths.narration_file.exists() and not force:
        _log.info("Stage 4: continuous narration and timeline already exist, skipping")
        return load_model(paths.timeline_file, TimelineFile)

    api_key = env.get("FISH_API_KEY") or str(config.get("tts.fish_api_key", "") or "")
    if not api_key:
        raise ValueError("FISH_API_KEY is not set in config/.env or the environment.")

    model_name = str(config.get("tts.fish_model", DEFAULT_MODEL) or DEFAULT_MODEL)
    voice_id = str(config.get("tts.fish_voice_id", DEFAULT_VOICE_ID) or DEFAULT_VOICE_ID)
    timeout = float(config.get("tts.fish_request_timeout_seconds", 300))
    max_chars = int(config.get("tts.fish_max_chars", 12_000))
    tempo = float(config.get("narration.tempo", config.get("tts.tempo", 1.0)) or 1.0)

    full_text = apply_pronunciation_map(
        "\n\n".join(block.narration.strip() for block in script.blocks if block.narration.strip())
    )
    if not full_text:
        raise ValueError("The storyboard has no narration text.")
    if len(full_text) > max_chars:
        raise ValueError(
            f"Continuous narration is {len(full_text)} characters, above "
            f"tts.fish_max_chars={max_chars}. Raise the limit or split the chapter."
        )

    cache_dir = paths.root / "_fish_continuous_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.md5(f"{voice_id}:{full_text}".encode()).hexdigest()
    cache_path = cache_dir / f"{digest}.wav"

    _log.info(
        "Stage 4 (Fish continuous): generating one %.1f kB narration request",
        len(full_text) / 1000,
    )
    audio, sample_rate = _synthesize_full_text(
        full_text,
        api_key=api_key,
        model_name=model_name,
        voice_id=voice_id,
        cache_path=cache_path,
        timeout=timeout,
    )
    if abs(tempo - 1.0) >= 0.005:
        audio = _apply_tempo(audio, sample_rate, tempo)

    duration = len(audio) / float(sample_rate)
    paths.narration_file.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(paths.narration_file), audio, sample_rate, subtype="PCM_16")
    _log.info(
        "Stage 4 (Fish continuous): generated %.1fs of continuous narration",
        duration,
    )

    timeline = _align_on_kaggle_gpu(paths, config, script, script_source=script_source)
    timeline = timeline.model_copy(
        update={
            "chapter_id": paths.chapter_id,
            "audio_file": paths.narration_file.name,
            "sample_rate": sample_rate,
            "duration": round(duration, 3),
            "tts_backend": f"fish-audio-continuous ({model_name} / {voice_id[:8]})",
            "whisper_model": str(config.get("align.whisper_model", "large-v3-turbo")),
        }
    )

    _validate_timeline(
        timeline,
        script,
        config,
        expected_sample_rate=sample_rate,
        expected_duration=duration,
    )
    save_model(timeline, paths.timeline_file)

    degraded = timeline.degraded_blocks()
    write_stage_status(
        paths.chapter_id,
        "s4_speech",
        "completed",
        {
            "duration": timeline.duration,
            "block_count": len(timeline.blocks),
            "fallback_blocks": len(degraded),
            "delivery": "continuous",
            "alignment": "forced-whisper",
        },
    )
    return timeline


def _synthesize_full_text(
    text: str,
    *,
    api_key: str,
    model_name: str,
    voice_id: str,
    cache_path: Path,
    timeout: float,
) -> tuple[np.ndarray, int]:
    if cache_path.exists():
        data, sr = sf.read(str(cache_path), dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        return data, sr

    payload = {
        "text": text,
        "reference_id": voice_id,
        "format": "wav",
        "temperature": 0.7,
        "model": model_name,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": model_name,
    }

    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout, connect=30.0)) as client:
                response = client.post("https://api.fish.audio/v1/tts", headers=headers, json=payload)
            if response.status_code == 200 and len(response.content) > 100:
                data, sr = sf.read(io.BytesIO(response.content), dtype="float32")
                if data.ndim > 1:
                    data = data[:, 0]
                sf.write(str(cache_path), data, sr, subtype="PCM_16")
                return data, sr
            last_error = RuntimeError(f"Fish Audio HTTP {response.status_code}: {response.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        if attempt < 3:
            time.sleep(5 * attempt)

    raise RuntimeError(f"Continuous Fish Audio synthesis failed: {last_error}")


def _align_on_kaggle_gpu(
    paths: ChapterPaths,
    config: Config,
    script: ScriptFile,
    *,
    script_source: Path | None = None,
) -> TimelineFile:
    from . import KERNEL_DIR, _build_job, _locate, _push_kernel

    if not KERNEL_DIR.exists():
        raise FileNotFoundError(f"Kaggle kernel directory missing: {KERNEL_DIR}")

    staging = paths.root / "_align_input"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    shutil.copy2(script_source or paths.script_file, staging / "script.json")
    shutil.copy2(paths.narration_file, staging / "narration.wav")

    lib_dir = staging / "lib"
    lib_dir.mkdir()
    for module in sorted(KERNEL_DIR.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)

    # The renderer owns beat derivation. Bundling the same module here prevents
    # Stage 4 and Stage 5 from disagreeing about how many words each beat owns.
    shutil.copy2(repo_path("src/manga_recap/render/sync.py"), lib_dir / "recap_sync.py")

    requirements = repo_path("kaggle/requirements-kaggle.txt")
    if requirements.exists():
        shutil.copy2(requirements, staging / requirements.name)

    job = _build_job(paths, config, staging, mode="align")
    (staging / "job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    client = KaggleClient()
    kernel_slug = str(config.require("tts.kernel_slug"))
    dataset_prefix = str(config.get("tts.align_dataset_prefix", "manga-recap-align"))
    safe_chapter = "".join(c.lower() if c.isalnum() else "-" for c in paths.chapter_id).strip("-")
    dataset_slug = f"{dataset_prefix}-{safe_chapter}"[:100]

    input_dataset = client.upload_dataset(
        staging,
        dataset_slug,
        private=True,
        description=f"Forced alignment input for {paths.chapter_id}",
        version_note="continuous narration and storyboard",
        required_files=("job.json",),
    )
    _push_kernel(client, kernel_slug, "", paths, input_dataset=input_dataset)

    kernel_id = f"{client.username}/{kernel_slug}"
    _log.info("Stage 4: waiting for GPU forced alignment on %s", kernel_id)
    run_info = client.wait_for_kernel(
        kernel_id,
        poll_interval=int(config.get("tts.poll_interval_seconds", 15)),
        max_wait=int(config.get("tts.max_wait_seconds", 21600)),
    )
    download_dir = client.download_kernel_output(kernel_id, paths.root / "_align_output")

    timeline_path = _locate(download_dir, "timeline.json") or _locate(
        download_dir, paths.timeline_file.name
    )
    if timeline_path is None:
        failure = _locate(download_dir, "failure.txt")
        detail = failure.read_text(encoding="utf-8")[:1000] if failure else "no timeline.json"
        raise KaggleError(f"GPU alignment finished without a timeline: {detail}")

    timeline = load_model(timeline_path, TimelineFile)
    debug_path = _locate(download_dir, "alignment_debug.json")
    if debug_path:
        shutil.copy2(debug_path, paths.alignment_debug_file)

    shutil.rmtree(download_dir, ignore_errors=True)
    _log.info(
        "Stage 4: GPU alignment completed in %.1fs (%d word timings)",
        run_info.total_seconds,
        len(timeline.words),
    )
    return timeline


def _validate_timeline(
    timeline: TimelineFile,
    script: ScriptFile,
    config: Config,
    *,
    expected_sample_rate: int,
    expected_duration: float,
) -> None:
    max_words = int(config.get("render.max_words_per_beat", 14))
    beats = beats_for_blocks(script.blocks, max_words=max_words)
    needed = sum(len(alignment_tokens(beat.text)) for beat in beats)

    if len(timeline.words) != needed:
        raise ValueError(
            f"Timeline has {len(timeline.words)} word timings, but the script needs "
            f"{needed}. Refusing to render estimated panel cuts."
        )

    min_ratio = float(config.get("align.min_match_ratio", 0.85))
    if bool(config.get("align.strict", True)):
        degraded = timeline.degraded_blocks()
        if degraded or any(block.match_ratio < min_ratio for block in timeline.blocks):
            raise ValueError(
                f"Forced alignment match ratio is below {min_ratio:.2f}. "
                "Re-run Stage 4 instead of rendering estimated word cuts."
            )

    if abs(timeline.sample_rate - expected_sample_rate) > 1:
        raise ValueError(
            f"Timeline sample rate {timeline.sample_rate} does not match narration "
            f"{expected_sample_rate}."
        )
    if abs(timeline.duration - expected_duration) > 0.25:
        raise ValueError(
            f"Timeline duration {timeline.duration}s does not match narration "
            f"{expected_duration:.3f}s."
        )

    report = plan_shots(
        script.blocks,
        timeline.words,
        audio_duration=timeline.duration,
        max_words_per_beat=max_words,
        min_shot_seconds=float(config.get("render.min_shot_seconds", 0.7)),
    )
    if report.problems:
        raise ValueError("Timeline failed renderer validation: " + "; ".join(report.problems))
    unanchored = [shot.beat_id for shot in report.shots if not shot.anchored]
    if unanchored:
        raise ValueError(
            f"{len(unanchored)} beat(s) were interpolated instead of word-anchored: "
            f"{unanchored[:10]}"
        )
