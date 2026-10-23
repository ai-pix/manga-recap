"""Orchestrate multi-kernel batch rendering on Kaggle.

Renders batches of up to 10 chapters simultaneously across two Kaggle kernels
(manga-recap-render and manga-recap-render-2), downloads outputs, and installs
07_final.mp4, 07_render_manifest.json, and 07_sync_report.json into each chapter directory.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys

from manga_recap.core import payload
from manga_recap.core.config import Config, load_config
from manga_recap.core.kaggle_io import KaggleClient
from manga_recap.core.logging import get_logger
from manga_recap.core.paths import ChapterPaths, repo_path

_log = get_logger("batch_render")
KERNEL_DIR = repo_path("kaggle/kernel_render")


def build_batch_payload(batch_id: str, chapters: list[str], config: Config) -> str:
    """Bundle up to 10 chapters into one archive and upload to sendit.sh."""
    staging = repo_path(f"data/staging_{batch_id}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)

    chapters_dir = staging / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    for ch in chapters:
        paths = ChapterPaths.create(ch)
        ch_target = chapters_dir / ch
        ch_target.mkdir(parents=True, exist_ok=True)
        panels_target = ch_target / "panels"
        panels_target.mkdir(parents=True, exist_ok=True)

        for p in paths.panel_images():
            shutil.copy2(p, panels_target / p.name)

        shutil.copy2(paths.script_file, ch_target / "script.json")
        shutil.copy2(paths.timeline_file, ch_target / "timeline.json")
        shutil.copy2(paths.narration_file, ch_target / "narration.wav")

    # Render settings from first chapter config
    dummy_paths = ChapterPaths.create(chapters[0])
    from manga_recap.stages.s5_render import _build_job
    job_data = _build_job(dummy_paths, config)
    job_data["mode"] = "batch"
    job_data["chapters"] = chapters
    (staging / "job.json").write_text(
        json.dumps(job_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Repo src/
    src_dir = repo_path("src")
    if src_dir.is_dir():
        shutil.copytree(
            src_dir,
            staging / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )

    # Lib modules from kernel dir
    lib_dir = staging / "lib"
    lib_dir.mkdir(exist_ok=True)
    for module in sorted(KERNEL_DIR.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)

    archive_path = repo_path(f"data/{batch_id}_payload.zip")
    if archive_path.exists():
        archive_path.unlink()

    print(f"[{batch_id}] Zipping {len(chapters)} chapters payload...", flush=True)
    payload.build_archive(staging, archive_path)
    shutil.rmtree(staging, ignore_errors=True)

    size_mb = archive_path.stat().st_size / 1e6
    print(f"[{batch_id}] Uploading payload ({size_mb:.1f} MB) to sendit.sh...", flush=True)
    url = payload.upload(
        archive_path,
        host=str(config.get("render.payload_host", "https://sendit.sh")),
        filename=f"{batch_id}-render.zip",
    )
    print(f"[{batch_id}] Upload complete: {url}", flush=True)
    archive_path.unlink(missing_ok=True)
    return url


def run_batch(
    batch_id: str,
    chapters: list[str],
    kernel_slug: str,
    config: Config,
    payload_url: str | None = None,
) -> bool:
    """Build payload, push to Kaggle kernel, wait, and install results."""
    client = KaggleClient()
    kernel_id = f"{client.username}/{kernel_slug}"
    print("\n==========================================", flush=True)
    print(f"[{batch_id}] Starting batch on {kernel_id} ({len(chapters)} chapters)", flush=True)
    print(f"[{batch_id}] Chapters: {chapters}", flush=True)
    print("==========================================", flush=True)

    if payload_url:
        print(f"[{batch_id}] Using pre-uploaded payload URL: {payload_url}", flush=True)
        url = payload_url
    else:
        url = build_batch_payload(batch_id, chapters, config)

    work_dir = repo_path(f"data/_kaggle_kernel_{batch_id}")
    payload.stage_from_url(
        kernel_dir=KERNEL_DIR,
        url=url,
        work_dir=work_dir,
        metadata={
            "id": kernel_id,
            "title": kernel_slug,
            "enable_gpu": True,
            "dataset_sources": ["wampireai/manga-recap-render-bin"],
        },
    )

    print(f"[{batch_id}] Pushing kernel to Kaggle...", flush=True)
    client.push_kernel(work_dir)
    shutil.rmtree(work_dir, ignore_errors=True)

    print(f"[{batch_id}] Waiting for kernel {kernel_id} to finish...", flush=True)
    client.wait_for_kernel(
        kernel_id,
        poll_interval=int(config.get("render.poll_interval_seconds", 30)),
        max_wait=int(config.get("render.max_wait_seconds", 21600)),
    )

    output_dir = repo_path(f"data/_kaggle_output_{batch_id}")
    client.download_kernel_output(kernel_id, output_dir)

    print(f"[{batch_id}] Processing downloaded outputs from {output_dir}...", flush=True)
    success_count = 0
    for ch in chapters:
        paths = ChapterPaths.create(ch)
        video_name = f"{ch}_final.mp4"
        manifest_name = f"{ch}_render_manifest.json"
        sync_name = f"{ch}_sync_report.json"

        # Search downloaded directory
        video_files = list(output_dir.rglob(video_name))
        manifest_files = list(output_dir.rglob(manifest_name))
        sync_files = list(output_dir.rglob(sync_name))

        if video_files and video_files[0].is_file():
            shutil.copy2(video_files[0], paths.final_file)
            size_mb = paths.final_file.stat().st_size / 1e6
            print(f"[{batch_id}] [OK] Installed {ch} video ({size_mb:.1f} MB)", flush=True)
            success_count += 1
        else:
            print(f"[{batch_id}] [FAIL] Missing video for {ch}!", flush=True)

        if manifest_files and manifest_files[0].is_file():
            shutil.copy2(manifest_files[0], paths.render_manifest_file)
        if sync_files and sync_files[0].is_file():
            shutil.copy2(sync_files[0], paths.sync_report_file)

    render_logs = list(output_dir.rglob("render_log.txt"))
    if render_logs:
        shutil.copy2(render_logs[0], repo_path(f"data/{batch_id}_render_log.txt"))

    shutil.rmtree(output_dir, ignore_errors=True)
    print(f"[{batch_id}] Batch finished: {success_count}/{len(chapters)} chapters installed.", flush=True)
    return success_count == len(chapters)


def main():
    parser = argparse.ArgumentParser(description="Run a batch of chapters on Kaggle")
    parser.add_argument("--batch-id", required=True, help="Unique identifier, e.g. batch1")
    parser.add_argument("--chapters", nargs="+", required=True, help="List of chapter IDs")
    parser.add_argument("--kernel-slug", required=True, help="Kaggle kernel slug")
    args = parser.parse_args()

    config = load_config()
    ok = run_batch(args.batch_id, args.chapters, args.kernel_slug, config)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
