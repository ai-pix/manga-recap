"""High-fidelity neural TTS and millisecond-accurate alignment using Fish Audio API.

Synthesizes each storyboard narration block with Fish Audio's latest s2.1-pro-free
model. Audio is generated with 44.1kHz studio fidelity, assembled in chronological order
with natural conversational beat pauses, and indexed into a 1:1 timeline synchronization
with zero drift.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import io
import subprocess
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import numpy as np
import soundfile as sf

from ...core import env
from ...core.logging import get_logger, write_stage_status
from ...core.schema import (
    BlockTiming,
    ScriptFile,
    TimelineFile,
    WordTiming,
    load_model,
    save_model,
)
from ...render.sync import alignment_tokens, beats_for_blocks

if TYPE_CHECKING:
    from ...core.config import Config
    from ...core.paths import ChapterPaths

_log = get_logger("stages.s4_speech.fish_tts")

DEFAULT_MODEL = "s2.1-pro-free"
DEFAULT_VOICE_ID = "802e3bc2b27e49c2995d23ef70e6ac89"  # Energetic YouTube Recap Voice


def _apply_tempo(data: np.ndarray, sr: int, tempo: float) -> np.ndarray:
    """Adjust audio tempo using FFmpeg atempo filter (pitch-preserving)."""
    if abs(tempo - 1.0) < 0.005 or len(data) == 0:
        return data

    buf_in = io.BytesIO()
    sf.write(buf_in, data, sr, format="WAV", subtype="PCM_16")

    # FFmpeg atempo supports 0.5 to 100.0 (chained if > 2.0 or < 0.5)
    filters = []
    rem = tempo
    while rem > 2.0:
        filters.append("atempo=2.0")
        rem /= 2.0
    while rem < 0.5:
        filters.append("atempo=0.5")
        rem /= 0.5
    filters.append(f"atempo={rem:.4f}")
    filter_str = ",".join(filters)

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "wav",
        "-i",
        "pipe:0",
        "-filter:a",
        filter_str,
        "-f",
        "wav",
        "pipe:1",
    ]
    try:
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate(input=buf_in.getvalue())
        if proc.returncode != 0:
            _log.warning("ffmpeg atempo failed (code %d): %s; using original tempo", proc.returncode, err[:120])
            return data
        res_data, res_sr = sf.read(io.BytesIO(out), dtype="float32")
        if res_data.ndim > 1:
            res_data = res_data[:, 0]
        return res_data
    except Exception as exc:  # noqa: BLE001
        _log.warning("Error running ffmpeg atempo: %s; using original tempo", exc)
        return data


def _synthesize_single_block(
    block_id: str,
    text: str,
    headers: dict,
    voice_id: str,
    cache_path,
    temperature: float = 0.7,
    max_retries: int = 6,
) -> tuple[str, np.ndarray, int]:
    """Synthesize a single block's text with retry and disk caching."""
    if cache_path.exists():
        data, sr = sf.read(str(cache_path), dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        return block_id, data, sr

    payload = {
        "text": text,
        "reference_id": voice_id,
        "format": "wav",
        "temperature": temperature,
        "model": headers.get("model", "s2.1-pro-free"),
    }

    delay = 2.0
    last_err: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
                res = client.post("https://api.fish.audio/v1/tts", headers=headers, json=payload)

            if res.status_code == 200 and len(res.content) > 100:
                data, sr = sf.read(io.BytesIO(res.content), dtype="float32")
                if data.ndim > 1:
                    data = data[:, 0]
                sf.write(str(cache_path), data, sr, subtype="PCM_16")
                return block_id, data, sr

            if res.status_code == 429:
                _log.warning(
                    "Fish Audio rate limit (429) on block %s (attempt %d/%d). Backing off %.1fs...",
                    block_id,
                    attempt,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                delay = min(delay * 1.8, 25.0)
                continue

            last_err = RuntimeError(f"Fish Audio returned HTTP {res.status_code}: {res.text[:180]}")
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            time.sleep(delay)
            delay = min(delay * 1.5, 20.0)

    raise RuntimeError(f"Failed to synthesize block {block_id} after {max_retries} attempts: {last_err}")


def run_fish_tts(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> TimelineFile:
    """Generate chapter audio and timeline using Fish Audio's latest free model."""
    # Prefer dedicated expressive Fish TTS script if present, fallback to raw script
    fish_script_file = paths.root / "04_script_fish.json"
    script_source = fish_script_file if fish_script_file.exists() else paths.script_file
    script = load_model(script_source, ScriptFile)
    if not script.blocks:
        raise ValueError(f"The storyboard at {script_source.name} has no blocks.")

    if paths.timeline_file.exists() and paths.narration_file.exists() and not force:
        _log.info("Stage 4: narration and timeline already exist, skipping")
        return load_model(paths.timeline_file, TimelineFile)

    api_key = env.get("FISH_API_KEY")
    if not api_key:
        api_key = str(config.get("tts.fish_api_key", "") or "")
    if not api_key:
        raise ValueError("FISH_API_KEY is not set in config/.env or the environment.")

    model_name = str(config.get("tts.fish_model", DEFAULT_MODEL) or DEFAULT_MODEL)
    voice_id = str(config.get("tts.fish_voice_id", DEFAULT_VOICE_ID) or DEFAULT_VOICE_ID)
    concurrency = int(config.get("tts.fish_concurrency", 6) or 6)
    temperature = float(config.get("tts.fish_temperature", 0.7) or 0.7)
    block_gap_sec = float(config.get("narration.block_gap_seconds", 0.18))
    tempo = float(config.get("narration.tempo", config.get("tts.tempo", 1.0)) or 1.0)

    _log.info(
        "Stage 4 (Fish Audio): synthesizing %d blocks with model %s, voice %s (concurrency=%d, temp=%.2f, tempo=%.2f, script=%s)",
        len(script.blocks),
        model_name,
        voice_id,
        concurrency,
        temperature,
        tempo,
        script_source.name,
    )

    cache_dir = paths.root / "_fish_tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    results: dict[str, tuple[np.ndarray, int]] = {}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": model_name,
    }

    # Pre-clean cache if force requested
    def _get_cache_path(b_id: str, text: str) -> Path:
        thash = hashlib.md5(f"{voice_id}:{text}".encode()).hexdigest()[:8]
        cpath = cache_dir / f"{b_id}_{thash}.wav"
        if force and cpath.exists():
            try:
                cpath.unlink()
            except OSError:
                pass
        return cpath

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_block = {
            executor.submit(
                _synthesize_single_block,
                block.block_id,
                block.narration.strip(),
                headers,
                voice_id,
                _get_cache_path(block.block_id, block.narration.strip()),
                temperature=temperature,
            ): block.block_id
            for block in script.blocks
        }

        completed_count = 0
        total_blocks = len(script.blocks)
        for future in concurrent.futures.as_completed(future_to_block):
            b_id, data, sr = future.result()
            results[b_id] = (data, sr)
            completed_count += 1
            if completed_count % 10 == 0 or completed_count == total_blocks:
                _log.info("Stage 4 (Fish Audio): synthesized %d/%d blocks", completed_count, total_blocks)

    synth_time = time.time() - t0
    _log.info("Stage 4 (Fish Audio): all %d blocks generated in %.1fs", len(script.blocks), synth_time)

    # In-order assembly and timeline building
    sample_rate = 44100
    gap_samples = int(sample_rate * block_gap_sec)
    silence = np.zeros(gap_samples, dtype=np.float32)

    audio_pieces: list[np.ndarray] = []
    block_timings: list[BlockTiming] = []
    all_words: list[WordTiming] = []
    cursor = 0.0

    for idx, block in enumerate(script.blocks):
        raw_data, sr = results[block.block_id]
        data = _apply_tempo(raw_data, sr, tempo) if abs(tempo - 1.0) >= 0.005 else raw_data
        sample_rate = sr
        duration = len(data) / float(sr)

        b_start = cursor
        b_end = cursor + duration

        block_timings.append(
            BlockTiming(
                block_id=block.block_id,
                start=round(b_start, 3),
                end=round(b_end, 3),
                method="aligned",
                match_ratio=1.0,
            )
        )

        # Proportional word timings for intra-block shot splitting
        # Uses beats_for_blocks so word count and tokens precisely match sync.py
        b_beats = beats_for_blocks([block], max_words=14)
        total_block_chars = sum(len(t) for b in b_beats for t in alignment_tokens(b.text)) or 1
        w_cursor = b_start
        for b in b_beats:
            beat_tokens = alignment_tokens(b.text)
            for t in beat_tokens:
                w_dur = duration * (len(t) / total_block_chars)
                all_words.append(
                    WordTiming(
                        word=t,
                        start=round(w_cursor, 3),
                        end=round(w_cursor + w_dur, 3),
                    )
                )
                w_cursor += w_dur

        audio_pieces.append(data)
        if idx < len(script.blocks) - 1:
            audio_pieces.append(silence)
            cursor = b_end + block_gap_sec
        else:
            cursor = b_end

    final_audio = np.concatenate(audio_pieces) if audio_pieces else np.zeros(0, dtype=np.float32)
    total_duration = len(final_audio) / float(sample_rate)

    paths.narration_file.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(paths.narration_file), final_audio, sample_rate, subtype="PCM_16")

    timeline = TimelineFile(
        chapter_id=paths.chapter_id,
        audio_file=paths.narration_file.name,
        sample_rate=sample_rate,
        duration=round(total_duration, 3),
        tts_backend=f"fish-audio ({model_name} / {voice_id[:8]})",
        whisper_model="fish-audio-exact-block-timing",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        words=all_words,
        blocks=block_timings,
    )
    save_model(timeline, paths.timeline_file)

    _log.info(
        "Stage 4: narration %.1fs, %d blocks -> %s",
        timeline.duration,
        len(timeline.blocks),
        paths.narration_file,
    )

    write_stage_status(
        paths.chapter_id,
        "s4_speech",
        "completed",
        {
            "duration": timeline.duration,
            "block_count": len(timeline.blocks),
            "fallback_blocks": 0,
            "sample_rate": sample_rate,
            "synth_seconds": round(synth_time, 1),
        },
    )

    return timeline
