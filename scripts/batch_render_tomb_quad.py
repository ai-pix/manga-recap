"""Quad-Instance Kaggle GPU Batch Render Orchestrator for Tomb Raider King.

Renders remaining 20 chapters across 4 concurrent Kaggle Tesla T4 GPU instances
divided cleanly into 4 batches (5 chapters per instance):

Batch 1 (Ch08, Ch09, Ch11, Ch12, Ch13) -> fabricatevisuals/manga-recap-render
Batch 2 (Ch14, Ch15, Ch18, Ch19, Ch20) -> fabricatevisuals/manga-recap-render-2
Batch 3 (Ch21, Ch22, Ch23, Ch24, Ch25) -> ravidevai/manga-recap-render
Batch 4 (Ch26, Ch27, Ch28, Ch29, Ch30) -> ravidevai/manga-recap-render-2

100% Pure GPU NVENC via PyNvVideoCodec at 355+ FPS.
"""

from __future__ import annotations

import concurrent.futures
import json
import shutil
import sys
import threading
import time
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core import payload  # noqa: E402
from manga_recap.core.config import load_config  # noqa: E402
from manga_recap.core.kaggle_io import KaggleClient  # noqa: E402
from manga_recap.core.paths import repo_path  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")

KERNEL_DIR = repo_path("kaggle/kernel_render")
cfg = load_config()
env_vals = dotenv_values(REPO_ROOT / ".env")

KEY_RAVIDEVAI = env_vals.get("KAGGLE_KEY", "")
KEY_FABRICATE = env_vals.get("KAGGLE_KEY_2", "KGAT_fd644b78e8b62fc80d015b1ffa98ea0e")

CONFIG_DIR_RAVIDEVAI = Path.home() / ".kaggle"
CONFIG_DIR_FABRICATE = Path.home() / ".kaggle_fabricatevisuals"

# 4 Batches x ~7-8 Chapters = 30 Chapters (8 + 7 + 8 + 7)
BATCH_CONFIGS = [
    {
        "batch_id": "tomb_batch_1",
        "username": "fabricatevisuals",
        "key": KEY_FABRICATE,
        "config_dir": CONFIG_DIR_FABRICATE,
        "kernel_slug": "manga-recap-render",
        "chapters": [1, 2, 3, 4, 5, 6, 7, 8],
    },
    {
        "batch_id": "tomb_batch_2",
        "username": "fabricatevisuals",
        "key": KEY_FABRICATE,
        "config_dir": CONFIG_DIR_FABRICATE,
        "kernel_slug": "manga-recap-render-2",
        "chapters": [9, 10, 11, 12, 13, 14, 15],
    },
    {
        "batch_id": "tomb_batch_3",
        "username": "ravidevai",
        "key": KEY_RAVIDEVAI,
        "config_dir": CONFIG_DIR_RAVIDEVAI,
        "kernel_slug": "manga-recap-render",
        "chapters": [16, 17, 18, 19, 20, 21, 22, 23],
    },
    {
        "batch_id": "tomb_batch_4",
        "username": "ravidevai",
        "key": KEY_RAVIDEVAI,
        "config_dir": CONFIG_DIR_RAVIDEVAI,
        "kernel_slug": "manga-recap-render-2",
        "chapters": [24, 25, 26, 27, 28, 29, 30],
    },
]

log_lock = threading.Lock()


def log(msg: str) -> None:
    with log_lock:
        print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_batch_payload(batch: dict) -> tuple[Path, str]:
    batch_id = batch["batch_id"]
    chapter_nums = batch["chapters"]
    staging = repo_path(f"data/staging_{batch_id}")
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    chapters_dir = staging / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    log(f"[{batch_id}] Staging {len(chapter_nums)} chapters: {[f'ch{n:02d}' for n in chapter_nums]}")
    for n in chapter_nums:
        ch_name = f"series3_ch{n:02d}"
        ch_src = repo_path(f"data/chapters/{ch_name}")
        ch_dst = chapters_dir / ch_name
        ch_dst.mkdir(parents=True, exist_ok=True)

        panels_src = ch_src / "02_panels"
        panels_dst = ch_dst / "panels"
        panels_dst.mkdir(parents=True, exist_ok=True)

        for p in panels_src.glob("*.png"):
            shutil.copy2(p, panels_dst / p.name)
        for p in panels_src.glob("*.webp"):
            shutil.copy2(p, panels_dst / p.name)

        shutil.copy2(ch_src / "04_script.json", ch_dst / "script.json")
        shutil.copy2(ch_src / "06_timeline.json", ch_dst / "timeline.json")
        shutil.copy2(ch_src / "05_narration.wav", ch_dst / "narration.wav")

    job_data = {
        "mode": "batch",
        "chapters": [f"series3_ch{n:02d}" for n in chapter_nums],
        "stitch_movie": False,
        "keep_individual": True,
        "engine": "pynv",
        "resolution": [1920, 1080],
        "fps": 24,
        "video_bitrate": 3200000,
        "background_mode": "blurred",
        "blur_width": 64,
        "pan_tall": True,
        "subtle_motion": True,
        "kenburns": {
            "enabled": True,
            "zoom_min": 1.0,
            "zoom_max": 1.08,
        },
    }
    (staging / "job.json").write_text(
        json.dumps(job_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    src_dir = repo_path("src")
    if src_dir.is_dir():
        shutil.copytree(
            src_dir,
            staging / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )

    lib_dir = staging / "lib"
    lib_dir.mkdir(exist_ok=True)
    for module in sorted(KERNEL_DIR.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)

    archive_path = repo_path(f"data/{batch_id}_payload.zip")
    if archive_path.exists():
        archive_path.unlink()

    log(f"[{batch_id}] Zipping payload archive...")
    payload.build_archive(staging, archive_path)
    shutil.rmtree(staging, ignore_errors=True)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    log(f"[{batch_id}] Uploading payload ({size_mb:.1f} MB) to sendit.sh...")
    host = str(cfg.get("render.payload_host", "https://sendit.sh"))
    url = payload.upload(archive_path, host=host)
    log(f"[{batch_id}] Uploaded: {url}")
    return archive_path, url


def run_batch_worker(batch: dict) -> None:
    batch_id = batch["batch_id"]
    username = batch["username"]
    key = batch["key"]
    config_dir = batch.get("config_dir")
    kernel_slug = batch["kernel_slug"]
    chapter_nums = batch["chapters"]
    kernel_id = f"{username}/{kernel_slug}"

    log(f"[{batch_id}] >>> Preparing worker for {kernel_id}...")
    client = KaggleClient(username=username, key=key, config_dir=config_dir)

    archive_path, payload_url = build_batch_payload(batch)

    work_dir = repo_path(f"data/_kaggle_kernel_{batch_id}")
    if work_dir.exists():
        shutil.rmtree(work_dir, ignore_errors=True)

    payload.stage_from_url(
        kernel_dir=KERNEL_DIR,
        url=payload_url,
        work_dir=work_dir,
        metadata={
            "id": kernel_id,
            "title": kernel_slug,
            "enable_gpu": True,
            "dataset_sources": [],
        },
    )

    log(f"[{batch_id}] Pushing kernel {kernel_id}...")
    client.push_kernel(work_dir)
    shutil.rmtree(work_dir, ignore_errors=True)

    log(f"[{batch_id}] Kernel pushed! Waiting for GPU execution...")
    t0 = time.time()
    client.wait_for_kernel(
        kernel_id,
        poll_interval=15,
        max_wait=14400,
    )
    duration = time.time() - t0
    log(f"[{batch_id}] GPU execution complete in {duration:.1f}s ({duration/60:.2f} min)!")

    output_dir = repo_path(f"data/_kaggle_output_{batch_id}")
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)

    log(f"[{batch_id}] Downloading outputs from {kernel_id}...")
    client.download_kernel_output(kernel_id, output_dir)

    # Distribute outputs to each chapter folder
    saved_count = 0
    for n in chapter_nums:
        ch_name = f"series3_ch{n:02d}"
        cand_vid = output_dir / f"{ch_name}_final.mp4"
        if not cand_vid.exists():
            # Check for alternative naming
            matches = list(output_dir.glob(f"*{ch_name}*final*.mp4"))
            if matches:
                cand_vid = matches[0]

        if cand_vid.exists():
            dst = repo_path(f"data/chapters/{ch_name}/07_final.mp4")
            shutil.copy2(cand_vid, dst)
            size_mb = dst.stat().st_size / (1024 * 1024)
            log(f"[{batch_id}] -> Saved {ch_name} video: {size_mb:.1f} MB")
            saved_count += 1
        else:
            log(f"[{batch_id}] WARNING: Video missing for {ch_name} in output!")
            r_log = output_dir / "render_log.txt"
            if r_log.exists():
                tail = r_log.read_text(encoding="utf-8", errors="ignore")[-800:]
                log(f"[{batch_id}] Kernel log snippet:\n{tail}")

        # Sync reports & manifests
        for cand in output_dir.glob(f"{ch_name}*sync*.json"):
            shutil.copy2(cand, repo_path(f"data/chapters/{ch_name}/07_sync_report.json"))
        for cand in output_dir.glob(f"{ch_name}*manifest*.json"):
            shutil.copy2(cand, repo_path(f"data/chapters/{ch_name}/07_render_manifest.json"))

    log(f"[{batch_id}] [ALL DONE] Successfully processed {saved_count}/{len(chapter_nums)} chapters!")
    shutil.rmtree(output_dir, ignore_errors=True)
    archive_path.unlink(missing_ok=True)


def main():
    print("=" * 80)
    print("QUAD-INSTANCE KAGGLE GPU BATCH RENDER: TOMB RAIDER KING (30 CHAPTERS)")
    print("  - Instance 1 (fabricatevisuals): Ch01 - Ch08 (8 chapters) -> manga-recap-render")
    print("  - Instance 2 (fabricatevisuals): Ch09 - Ch15 (7 chapters) -> manga-recap-render-2")
    print("  - Instance 3 (ravidevai):        Ch16 - Ch23 (8 chapters) -> manga-recap-render")
    print("  - Instance 4 (ravidevai):        Ch24 - Ch30 (7 chapters) -> manga-recap-render-2")
    print("Engine: PyNvVideoCodec DLPack Zero-Copy (355+ FPS on Tesla T4)")
    print("=" * 80, flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_batch_worker, b): b["batch_id"] for b in BATCH_CONFIGS}
        for fut in concurrent.futures.as_completed(futures):
            b_id = futures[fut]
            try:
                fut.result()
                log(f"[MAIN] Batch {b_id} finished successfully!")
            except Exception as e:
                log(f"[MAIN] ERROR in {b_id}: {e}")
                import traceback
                traceback.print_exc()

    print("\n" + "=" * 80)
    print("ALL 4 BATCH RUNS COMPLETE!")
    print("=" * 80, flush=True)


if __name__ == "__main__":
    main()
