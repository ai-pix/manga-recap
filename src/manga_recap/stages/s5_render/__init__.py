"""Stage 5: render the final video on Kaggle.

Drives Kaggle kernel B. Two datasets go in: the chapter's panels and script, and
the speech outputs from stage 4. One video comes out.

Keeping this a separate kernel from stage 4 is deliberate. Re-rendering after a
visual tweak is common, and audio synthesis is the expensive half. Splitting them
means tweaking the look costs a CPU render instead of a full TTS pass.
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
from ...core.schema import (
    RenderManifest,
    ScriptFile,
    TimelineFile,
    load_model,
    save_model,
)

_log = get_logger("stages.s5_render")

# Resolved from the repo root, not by counting parents off this file. The stage
# package sits four levels down, so `parents[3]` is `src/` and silently points at
# a directory that does not exist.
KERNEL_DIR = repo_path("kaggle/kernel_render")


def run(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
    kernel_slug: str | None = None,
) -> RenderManifest:
    """Render the chapter and place the final video."""
    if not paths.timeline_file.exists() or not paths.narration_file.exists():
        raise FileNotFoundError(
            "Narration and timeline are missing. Run `manga speak` first."
        )
    timeline = load_model(paths.timeline_file, TimelineFile)

    if paths.final_file.exists() and not force:
        _log.info("Stage 5: final video already exists, skipping")
        return load_model(paths.render_manifest_file, RenderManifest)

    if not KERNEL_DIR.exists():
        raise FileNotFoundError(f"Kaggle kernel directory missing: {KERNEL_DIR}")

    if kernel_slug is None:
        kernel_slug = str(config.require("render.kernel_slug"))
    client = KaggleClient()

    with timed(f"stage 5 render (Kaggle {kernel_slug})"):
        payload_url = _build_payload(paths, config)
        enable_gpu = bool(config.get("render.enable_gpu", True))
        _log.info("Stage 5: Kaggle kernel GPU acceleration: %s", enable_gpu)
        work_dir = payload.stage_from_url(
            kernel_dir=KERNEL_DIR,
            url=payload_url,
            work_dir=paths.root / "_kaggle_kernel",
            metadata={
                "id": f"{client.username}/{kernel_slug}",
                "title": kernel_slug,
                "enable_gpu": enable_gpu,
                "dataset_sources": ["wampireai/manga-recap-render-bin"],
            },
        )
        client.push_kernel(work_dir)

        kernel_id = f"{client.username}/{kernel_slug}"
        _log.info("Stage 5: waiting for %s", kernel_id)
        run_info = client.wait_for_kernel(
            kernel_id,
            poll_interval=int(config.get("render.poll_interval_seconds", 30)),
            max_wait=int(config.get("render.max_wait_seconds", 21600)),
        )
        download_dir = client.download_kernel_output(kernel_id, paths.root / "_kaggle_output")

    video = _locate(download_dir, paths.final_file.name) or _locate(download_dir, "final.mp4")
    if video is None:
        failure_txt = _locate(download_dir, "failure.txt")
        details = ""
        if failure_txt and failure_txt.exists():
            details = f"\nKernel failure trace:\n{failure_txt.read_text(encoding='utf-8')}"
        raise KaggleError(
            f"Kernel finished but produced no {paths.final_file.name}. Check "
            f"{paths.root / '_kaggle_output'} and the kernel log.{details}"
        )

    # Invariant: verify that the output belongs to this chapter and is not a stale prior run
    render_log = _locate(download_dir, "render_log.txt")
    if render_log and render_log.exists():
        log_text = render_log.read_text(encoding="utf-8", errors="ignore")
        if f"render job for {paths.chapter_id}:" not in log_text:
            raise KaggleError(
                f"Stale output detected! Downloaded log does not belong to {paths.chapter_id}."
            )

    shutil.copy2(video, paths.final_file)

    manifest_path = _locate(download_dir, paths.render_manifest_file.name) or _locate(download_dir, "render_manifest.json")
    if manifest_path is None:
        manifest = _fallback_manifest(paths, timeline)
        _log.warning("Stage 5: kernel produced no manifest; recording a local one")
    else:
        manifest = load_model(manifest_path, RenderManifest)
    manifest = manifest.model_copy(update={"chapter_id": paths.chapter_id})
    save_model(manifest, paths.render_manifest_file)

    # The sync report is the only artefact that says which panel was on screen
    # while each clause was spoken. Without it, "is this cut in the right place?"
    # can only be answered by watching ten minutes of video.
    sync_report = _locate(download_dir, "07_sync_report.json")
    if sync_report is not None:
        shutil.copy2(sync_report, paths.sync_report_file)
        _log.info("Stage 5: sync report saved to %s", paths.sync_report_file)

    render_log = _locate(download_dir, "render_log.txt")
    if render_log and render_log.exists():
        shutil.copy2(render_log, paths.root / "07_render_log.txt")
        _log.info("Stage 5: Kaggle execution log saved to %s", paths.root / "07_render_log.txt")

    shutil.rmtree(download_dir, ignore_errors=True)

    _report(paths, manifest)
    write_stage_status(
        paths.chapter_id,
        "s5_render",
        "completed",
        {
            "clip_count": manifest.clip_count,
            "duration": manifest.duration,
            "queue_seconds": round(run_info.queue_seconds, 1),
            "total_seconds": round(run_info.total_seconds, 1),
            "output": str(paths.final_file),
        },
    )
    return manifest


# ---------------------------------------------------------------------------
# Kaggle plumbing
# ---------------------------------------------------------------------------


def _build_payload(paths: ChapterPaths, config: Config) -> str:
    """Bundle everything the render kernel needs into one archive and host it.

    Panels, script, narration audio and timeline all go into a single zip. The
    old design split them across two Kaggle Datasets and then had the kernel
    search both mounts for each file, which meant guessing which mount a given
    file lived in.
    """
    staging = paths.root / "_kaggle_input"
    if staging.exists():
        shutil.rmtree(staging)
    (staging / "panels").mkdir(parents=True, exist_ok=True)

    for panel in paths.panel_images():
        shutil.copy2(panel, staging / "panels" / panel.name)
    shutil.copy2(paths.script_file, staging / "script.json")
    shutil.copy2(paths.narration_file, staging / paths.narration_file.name)
    shutil.copy2(paths.timeline_file, staging / paths.timeline_file.name)
    shutil.copy2(paths.narration_file, staging / "narration.wav")
    shutil.copy2(paths.timeline_file, staging / "timeline.json")
    (staging / "job.json").write_text(
        json.dumps(_build_job(paths, config), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Bundle repo's src/ so that manga_recap.render.ffmpeg and kenburns are importable
    src_dir = repo_path("src")
    if src_dir.is_dir():
        shutil.copytree(
            src_dir,
            staging / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )

    # Helper modules travel in the payload rather than beside main.py. Kaggle
    # does not put files that sat beside main.py on sys.path, so a module that
    # was uploaded is still unimportable.
    lib_dir = staging / "lib"
    lib_dir.mkdir(exist_ok=True)
    for module in sorted(KERNEL_DIR.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)

    archive = payload.build_archive(staging, paths.root / "_kaggle_payload.zip")
    override = str(config.get("render.payload_url", "") or "")
    if override:
        _log.info("Stage 5: using configured payload URL instead of uploading")
        return override
    return payload.upload(
        archive,
        host=str(config.get("render.payload_host", payload.DEFAULT_HOST)),
        filename=f"{paths.chapter_id}-render.zip",
    )


def _build_job(paths: ChapterPaths, config: Config) -> dict:
    """Resolve render settings for the kernel."""
    return {
        "chapter_id": paths.chapter_id,
        "render": {
            "width": config.get("render.width", 1920),
            "height": config.get("render.height", 1080),
            "fps": config.get("render.fps", 30),
            "crf": config.get("render.crf", 20),
            "preset": config.get("render.preset", "p1"),
            "encoder": config.get("render.encoder", "auto"),
            "engine": config.get("render.engine", "direct_stream"),
            "test_duration_seconds": config.get("render.test_duration_seconds", 0.0),
            "audio_bitrate": config.get("render.audio_bitrate", "192k"),
            "background_color": config.get("render.background_color", "0x0d0d12"),
            "background_mode": config.get("render.background_mode", "blurred"),
            "blur_width": config.get("render.blur_width", 512),
            "blur_radius": config.get("render.blur_radius", 16),
            "blur_darken": config.get("render.blur_darken", 0.12),
            "pan_tall": config.get("render.pan_tall", True),
            "subtle_motion": config.get("render.subtle_motion", True),
            "min_shot_seconds": config.get("render.min_shot_seconds", 0.7),
            "max_clip_seconds": config.get("render.max_clip_seconds", 60.0),
            "max_words_per_beat": config.get("render.max_words_per_beat", 14),
            "pan_cycle": config.get("render.pan_cycle", "in,left,up,right"),
            "max_workers": config.get("render.max_workers", 0),
            "kenburns": {
                "enabled": config.get("render.kenburns.enabled", True),
                "zoom_end": config.get("render.kenburns.zoom_end", 1.06),
            },
        },
        "bgm": {
            "enabled": config.get("bgm.enabled", False),
            "directory": config.get("bgm.directory", "assets/bgm"),
            "mode": config.get("bgm.mode", "random"),
            "fixed_file": config.get("bgm.fixed_file", ""),
            "music_db": config.get("bgm.music_db", -22.0),
            "fade_seconds": config.get("bgm.fade_seconds", 2.0),
        },
    }


def set_kernel_datasets(
    kernel_slug: str, input_slug: str, speech_slug: str, username: str
) -> None:
    """Point the render kernel at this chapter's two datasets."""
    metadata_path = KERNEL_DIR / "kernel-metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["title"] = kernel_slug
    metadata["dataset_sources"] = [f"{username}/{input_slug}", f"{username}/{speech_slug}"]
    # Written here for the same reason as the dataset sources: the checked-in
    # metadata carries no `id` so it never embeds a Kaggle username, and the
    # push path parses whatever `id` it finds as a slug string.
    metadata["id"] = f"{username}/{kernel_slug}"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _report(paths: ChapterPaths, manifest: RenderManifest) -> None:
    """Log the render, and check every panel actually made it into the video.

    A panel that is in the script but missing from the video is the failure this
    catches, and it is invisible until you scrub through twenty minutes of
    footage.
    """
    size_mb = paths.final_file.stat().st_size / 1_000_000
    _log.info(
        "Stage 5: %d clips, %.1fs, %.1f MB -> %s",
        manifest.clip_count,
        manifest.duration,
        size_mb,
        paths.final_file,
    )

    script = load_model(paths.script_file, ScriptFile)
    expected = set(script.referenced_panels())
    shown = manifest.panels_shown

    if not shown:
        _log.warning("Stage 5: render manifest lists no clips; cannot verify coverage")
        return

    missing = expected - shown
    if missing:
        _log.warning(
            "Stage 5: %d panel(s) in the script never appeared in the video: %s. "
            "Check for missing panel images in 02_panels/.",
            len(missing),
            sorted(missing)[:8],
        )
    else:
        _log.info("Stage 5: all %d scripted panels appear in the video", len(shown))


def _fallback_manifest(paths: ChapterPaths, timeline: TimelineFile) -> RenderManifest:
    """Build a manifest locally when the kernel did not emit one.

    Clip details are unknown in this case, so it records what is knowable: the
    narration length. Stage 5's coverage check will decline to verify panel
    coverage rather than report a false pass.
    """
    return RenderManifest(
        chapter_id=paths.chapter_id,
        created_at=_now(),
        width=1920,
        height=1080,
        fps=30,
        duration=timeline.duration,
        clip_count=0,
        bgm_track=None,
        output_file=paths.final_file.name,
        clips=[],
    )


def _locate(directory: Path, filename: str) -> Path | None:
    """Find a kernel output, newest first.

    `kaggle kernels output` can hand back a directory holding artifacts from more
    than one run, and a plain `rglob` walks in name order, so an older copy of a
    file could be picked up and copied over a newer one. The manifest from the
    previous render was being preferred that way, and the chapter was left with
    a manifest describing a video that no longer existed.
    """
    if not directory.exists():
        return None
    direct = directory / filename
    if direct.exists():
        return direct
    candidates = [c for c in directory.rglob(filename) if c.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, str(p)))


def _dataset_slug(config: Config, chapter_id: str, kind: str) -> str:
    project = str(config.get("project.slug", "manga-recap"))
    safe_chapter = "".join(c.lower() if c.isalnum() else "-" for c in chapter_id)
    while "--" in safe_chapter:
        safe_chapter = safe_chapter.replace("--", "-")
    return f"{project}-{kind}-{safe_chapter.strip('-')}"[:100]


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%S")
