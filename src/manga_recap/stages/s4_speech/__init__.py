"""Stage 4: narrate the chapter on Kaggle, and time every narration block.

Drives Kaggle kernel A end to end:

    stage files -> input dataset -> kernel push -> poll -> download outputs

The kernel is uploaded once and reused. Each run only uploads the chapter's
panels and script, so the expensive part, a multi-minute TTS pass, is the only
thing that repeats.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ...core import payload
from ...core.config import Config
from ...core.kaggle_io import KaggleClient, KaggleError
from ...core.logging import get_logger, timed, write_stage_status
from ...core.paths import ChapterPaths, repo_path
from ...core.schema import ScriptFile, TimelineFile, load_model, save_model

_log = get_logger("stages.s4_speech")

# Resolved from the repo root, not by counting parents off this file. The stage
# package sits four levels down, so `parents[3]` is `src/` and silently points at
# a directory that does not exist. `repo_path` is the one way to spell this, and
# preflight.py checks the same location, so the two cannot drift apart.
KERNEL_DIR = repo_path("kaggle/kernel_tts_align")


def run(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> TimelineFile:
    """Run TTS and alignment, then place the audio and timeline."""
    script = load_model(paths.script_file, ScriptFile)
    if not script.blocks:
        raise ValueError("The storyboard has no blocks. Run `manga script` first.")
    if paths.timeline_file.exists() and paths.narration_file.exists() and not force:
        _log.info("Stage 4: narration and timeline already exist, skipping")
        return load_model(paths.timeline_file, TimelineFile)

    backend = str(config.get("tts.backend", "fish-tts") or "fish-tts").lower()
    if backend in ("fish-tts", "fish", "fish_audio", "fish-audio"):
        from .fish_tts_engine import run_fish_tts

        return run_fish_tts(paths, config, force=force)

    if backend in ("gemini-tts", "gemini"):
        from .gemini_tts_engine import run_gemini_tts

        return run_gemini_tts(paths, config, force=force)

    if backend == "edge-tts":
        from .edge_tts_engine import run_edge_tts

        return run_edge_tts(paths, config, force=force)

    if not KERNEL_DIR.exists():
        raise FileNotFoundError(f"Kaggle kernel directory missing: {KERNEL_DIR}")

    kernel_slug = str(config.require("tts.kernel_slug"))
    client = KaggleClient()

    with timed(f"stage 4 speech (Kaggle {kernel_slug})"):
        payload_url = _prepare_payload(paths, config)
        _push_kernel(client, kernel_slug, payload_url, paths)
        kernel_id = f"{client.username}/{kernel_slug}"
        _log.info("Stage 4: waiting for %s", kernel_id)
        run_info = client.wait_for_kernel(
            kernel_id,
            poll_interval=int(config.get("tts.poll_interval_seconds", 30)),
            max_wait=int(config.get("tts.max_wait_seconds", 21600)),
        )
        download_dir = client.download_kernel_output(kernel_id, paths.root / "_kaggle_output")

    narration = _locate(download_dir, "narration.wav") or _locate(download_dir, paths.narration_file.name)
    if narration is None:
        raise KaggleError(
            f"Kernel finished but produced no {paths.narration_file.name} or narration.wav. "
            f"Check {paths.root / '_kaggle_output'} for what it did produce."
        )
    shutil.copy2(narration, paths.narration_file)

    timeline_path = _locate(download_dir, "timeline.json") or _locate(download_dir, paths.timeline_file.name)
    if timeline_path is None:
        raise KaggleError(
            f"Kernel finished but produced no {paths.timeline_file.name} or timeline.json. The "
            "alignment step did not complete."
        )
    timeline = load_model(timeline_path, TimelineFile)
    timeline = timeline.model_copy(update={"chapter_id": paths.chapter_id})
    save_model(timeline, paths.timeline_file)

    debug = _locate(download_dir, "alignment_debug.json") or _locate(download_dir, paths.alignment_debug_file.name)
    if debug is not None:
        shutil.copy2(debug, paths.alignment_debug_file)

    shutil.rmtree(download_dir, ignore_errors=True)

    _log.info(
        "Stage 4: narration %.1fs, %d blocks -> %s",
        timeline.duration,
        len(timeline.blocks),
        paths.narration_file,
    )
    degraded = timeline.degraded_blocks()
    if degraded:
        _log.warning(
            "Stage 4: %d of %d blocks used fallback timing, which is an estimate. "
            "Panels over these may drift from the narration.",
            len(degraded),
            len(timeline.blocks),
        )

    write_stage_status(
        paths.chapter_id,
        "s4_speech",
        "completed",
        {
            "duration": timeline.duration,
            "block_count": len(timeline.blocks),
            "fallback_blocks": len(degraded),
            "queue_seconds": round(run_info.queue_seconds, 1),
            "total_seconds": round(run_info.total_seconds, 1),
        },
    )
    return timeline


# ---------------------------------------------------------------------------
# Kaggle plumbing
# ---------------------------------------------------------------------------


def _prepare_payload(paths: ChapterPaths, config: Config) -> str:
    """Stage the kernel inputs, zip them, upload, and return the fetch URL.

    One archive rather than a Kaggle Dataset: one request instead of a dataset
    per chapter, and the kernel does not depend on where Kaggle chose to mount
    the files.
    """
    staging = paths.root / "_kaggle_input"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "panels").mkdir(parents=True, exist_ok=True)

    shutil.copy2(paths.script_file, staging / "script.json")

    # Speech synthesis only needs the script, voice reference, and runtime helpers.
    # Panel images are used in render stage (stage 5), not in speech stage.
    (staging / "panels").mkdir(parents=True, exist_ok=True)

    # Voice cloning needs its reference clip uploaded too.
    voice = config.get("tts.voice", {}) or {}
    if str(voice.get("mode", "builtin")) == "clone":
        reference = voice.get("reference_wav")
        if reference:
            reference_path = Path(reference)
            if not reference_path.is_absolute():
                reference_path = repo_path(str(reference))
            if not reference_path.exists():
                raise FileNotFoundError(
                    f"tts.voice.mode is 'clone' but the reference wav is missing: "
                    f"{reference_path}"
                )
            shutil.copy2(reference_path, staging / Path(reference).name)

    (staging / "job.json").write_text(
        json.dumps(_build_job(paths, config, staging), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # The kernel's helper modules travel in the payload rather than beside
    # main.py. Kaggle runs a script kernel as /kaggle/src/script.py and does not
    # put sibling files on sys.path, so `from tts_engine import TTSEngine` fails
    # with ModuleNotFoundError even though the file was uploaded. Carrying them
    # inside the archive the kernel already unpacks removes the question.
    lib_dir = staging / "lib"
    lib_dir.mkdir(exist_ok=True)
    for module in sorted(KERNEL_DIR.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)
            _log.debug("Bundled helper module %s into the payload", module.name)

    # The dependency list rides along so the kernel installs exactly what this
    # repo pins, rather than duplicating it in two places that can drift.
    requirements = repo_path("kaggle/requirements-kaggle.txt")
    if requirements.exists():
        shutil.copy2(requirements, staging / requirements.name)

    _log.info("Stage 4: bundled script and voice payload")
    archive = payload.build_archive(staging, paths.root / "_kaggle_payload.zip")
    override = str(config.get("tts.payload_url", "") or "")
    if override:
        # Useful when the file host is unreachable from this machine but the
        # kernel has better connectivity, and for testing without an upload.
        _log.info("Stage 4: using configured payload URL instead of uploading")
        return override
    return payload.upload(
        archive,
        host=str(config.get("tts.payload_host", payload.DEFAULT_HOST)),
        filename=f"{paths.chapter_id}-speak.zip",
    )


def _build_job(paths: ChapterPaths, config: Config, staging: Path) -> dict:
    """Resolve every setting the kernel needs into one file.

    The kernel has no access to config.yaml, and shipping config parsing to
    Kaggle would tie it to the repo layout. Resolving here keeps one source of
    truth and makes each kernel run self-describing.
    """
    voice = dict(config.get("tts.voice", {}) or {})
    reference = voice.get("reference_wav")
    if voice.get("mode") == "clone" and reference:
        voice["reference_wav"] = Path(reference).name

    return {
        "chapter_id": paths.chapter_id,
        "panel_count": len(paths.panel_images()),
        "tts": {
            "voice": voice,
            "language_id": config.get("tts.language_id", "en"),
            "max_chars_per_chunk": config.get("tts.max_chars_per_chunk", 400),
            "duration_words_per_minute": config.get("tts.duration_words_per_minute", 150),
            "duration_tolerance": config.get("tts.duration_tolerance", 0.6),
            "workers_per_gpu": config.get("tts.workers_per_gpu", 2),
        },
        "align": {
            "whisper_model": config.get("align.whisper_model", "large-v3"),
            "device": config.get("align.device", "cuda"),
            "compute_type": config.get("align.compute_type", "float16"),
            "beam_size": config.get("align.beam_size", 5),
            "min_match_ratio": config.get("align.min_match_ratio", 0.55),
        },
        "narration": {
            "block_gap_seconds": config.get("narration.block_gap_seconds", 0.18),
            "target_lufs": config.get("narration.target_lufs", -16.0),
        },
    }


def _push_kernel(
    client: KaggleClient, kernel_slug: str, payload_url: str, paths: ChapterPaths
) -> None:
    """Push a copy of the kernel, pointed at this run's payload URL.

    The copy matters: the payload URL and the kernel slug are both per-run, and
    writing them into the checked-in `kernel-metadata.json` would leave a Kaggle
    username in a file that is meant to be safe to commit.
    """
    metadata = {
        "id": f"{client.username}/{kernel_slug}",
        "title": kernel_slug,
        "dataset_sources": [f"{client.username}/manga-recap-voice-orus"],
    }
    work_dir = payload.stage_from_url(
        kernel_dir=KERNEL_DIR,
        url=payload_url,
        work_dir=paths.root / "_kaggle_kernel",
        metadata=metadata,
    )
    client.push_kernel(work_dir)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _locate(directory: Path, filename: str) -> Path | None:
    """Find a kernel output, wherever it landed in the download tree."""
    if not directory.exists():
        return None
    direct = directory / filename
    if direct.exists():
        return direct
    for candidate in directory.rglob(filename):
        if candidate.is_file():
            return candidate
    return None


def _dataset_slug(config: Config, chapter_id: str, kind: str) -> str:
    """Kaggle dataset slug for a chapter's inputs or speech outputs."""
    project = str(config.get("project.slug", "manga-recap"))
    safe_chapter = _slugify(chapter_id)
    return f"{project}-{kind}-{safe_chapter}"[:100]


def _slugify(value: str) -> str:
    cleaned = "".join(c.lower() if c.isalnum() else "-" for c in value)
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-")
