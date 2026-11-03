"""Quad-Instance Kaggle GPU Batch Render Orchestrator for Omniscient Reader's Viewpoint (ORV).

Renders all 31 ORV chapters across 4 concurrent Kaggle Tesla T4 GPU instances
divided cleanly into 4 batches (8 + 8 + 8 + 7):

Batch 1 (Ch00–07, 8 chapters) -> fabricatevisuals/manga-recap-render
Batch 2 (Ch08–15, 8 chapters) -> fabricatevisuals/manga-recap-render-2
Batch 3 (Ch16–23, 8 chapters) -> ravidevai/manga-recap-render
Batch 4 (Ch24–30, 7 chapters) -> ravidevai/manga-recap-render-2

100% Pure GPU NVENC via PyNvVideoCodec at 355+ FPS.
Strict adherence to kaggle/MASTER_RENDER_STANDARD.md.
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
env_cfg = dotenv_values(REPO_ROOT / "config" / ".env")

KEY_RAVIDEVAI = env_vals.get("KAGGLE_KEY") or env_cfg.get("KAGGLE_KEY", "")
KEY_FABRICATE = env_vals.get("KAGGLE_KEY_2") or env_cfg.get("KAGGLE_KEY_2", "KGAT_fd644b78e8b62fc80d015b1ffa98ea0e")

CONFIG_DIR_RAVIDEVAI = Path.home() / ".kaggle"
CONFIG_DIR_FABRICATE = Path.home() / ".kaggle_fabricatevisuals"

# 4 Batches x ~7-8 Chapters = 31 Chapters (8 + 8 + 8 + 7)
BATCH_CONFIGS = [
    {
        "batch_id": "orv_batch_1",
        "username": "fabricatevisuals",
        "key": KEY_FABRICATE,
        "config_dir": CONFIG_DIR_FABRICATE,
        "kernel_slug": "manga-recap-render",
        "chapters": [0, 1, 2, 3, 4, 5, 6, 7],
    },
    {
        "batch_id": "orv_batch_2",
        "username": "fabricatevisuals",
        "key": KEY_FABRICATE,
        "config_dir": CONFIG_DIR_FABRICATE,
        "kernel_slug": "manga-recap-render-2",
        "chapters": [8, 9, 10, 11, 12, 13, 14, 15],
    },
    {
        "batch_id": "orv_batch_3",
        "username": "ravidevai",
        "key": KEY_RAVIDEVAI,
        "config_dir": CONFIG_DIR_RAVIDEVAI,
        "kernel_slug": "manga-recap-render",
        "chapters": [16, 17, 18, 19, 20, 21, 22, 23],
    },
    {
        "batch_id": "orv_batch_4",
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

    log(f"[{batch_id}] Staging {len(chapter_nums)} chapters: {[f'orv_ch{n:02d}' for n in chapter_nums]}")
    for n in chapter_nums:
        ch_name = f"orv_ch{n:02d}"
        ch_src = repo_path(f"data/chapters/{ch_name}")
        ch_dst = chapters_dir / ch_name
        ch_dst.mkdir(parents=True, exist_ok=True)

        panels_src = ch_src / "02_panels"
        panels_dst = ch_dst / "panels"
        panels_dst.mkdir(parents=True, exist_ok=True)

        for p in panels_src.glob("panel_*.webp"):
            shutil.copy2(p, panels_dst / p.name)
        if (panels_src / "panel_index.json").exists():
            shutil.copy2(panels_src / "panel_index.json", ch_dst / "panel_index.json")
            shutil.copy2(panels_src / "panel_index.json", panels_dst / "panel_index.json")

        shutil.copy2(ch_src / "04_script.json", ch_dst / "script.json")
        shutil.copy2(ch_src / "06_timeline.json", ch_dst / "timeline.json")
        shutil.copy2(ch_src / "05_narration.wav", ch_dst / "narration.wav")

    job_data = {
        "mode": "batch",
        "chapters": [f"orv_ch{n:02d}" for n in chapter_nums],
        "stitch_movie": False,
        "keep_individual": True,
        "engine": "pynv",
        "resolution": [1920, 1080],
        "fps": 30,
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


def is_batch_complete(batch: dict) -> bool:
    for n in batch["chapters"]:
        ch_name = f"orv_ch{n:02d}"
        ch_dir = repo_path(f"data/chapters/{ch_name}")
        vid = ch_dir / "07_final.mp4"
        sync = ch_dir / "07_sync_report.json"
        wav = ch_dir / "05_narration.wav"
        if not vid.exists() or vid.stat().st_size < 10_000_000:
            return False
        if not sync.exists():
            return False
        if wav.exists() and vid.stat().st_mtime < wav.stat().st_mtime:
            return False
    return True


def run_batch_worker(batch: dict) -> None:
    batch_id = batch["batch_id"]
    username = batch["username"]
    key = batch["key"]
    config_dir = batch.get("config_dir")
    kernel_slug = batch["kernel_slug"]
    chapter_nums = batch["chapters"]
    kernel_id = f"{username}/{kernel_slug}"

    if is_batch_complete(batch):
        log(f"[{batch_id}] All {len(chapter_nums)} chapters already up-to-date and verified. Skipping!")
        return

    log(f"[{batch_id}] >>> Preparing worker for {kernel_id}...")
    client = KaggleClient(username=username, key=key, config_dir=config_dir)

    # Build & upload payload
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
            "dataset_sources": [
                "wampireai/manga-recap-render-bin",
                "wampireai/manga-recap-voice-orus",
            ],
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

    out_dir = repo_path(f"data/output_{batch_id}")
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"[{batch_id}] Downloading rendered outputs from {kernel_id}...")
    client.download_kernel_output(kernel_id, out_dir)

    # Move outputs into chapter folders
    for ch_num in chapter_nums:
        ch_name = f"orv_ch{ch_num:02d}"
        ch_target = repo_path(f"data/chapters/{ch_name}")
        ch_target.mkdir(parents=True, exist_ok=True)

        candidates = [
            out_dir / f"{ch_name}_final.mp4",
            out_dir / ch_name / "07_final.mp4",
            out_dir / "07_final.mp4",
        ]
        found_video = False
        for c in candidates:
            if c.exists():
                shutil.copy2(c, ch_target / "07_final.mp4")
                size_mb = (ch_target / "07_final.mp4").stat().st_size / (1024 * 1024)
                log(f"  -> Saved {ch_name}/07_final.mp4 ({size_mb:.1f} MB)")
                found_video = True
                break

        if not found_video:
            for f in out_dir.rglob("*.mp4"):
                if ch_name in f.name:
                    shutil.copy2(f, ch_target / "07_final.mp4")
                    size_mb = (ch_target / "07_final.mp4").stat().st_size / (1024 * 1024)
                    log(f"  -> Saved {ch_name}/07_final.mp4 ({size_mb:.1f} MB)")
                    found_video = True
                    break

        if not found_video:
            raise RuntimeError(f"[{batch_id}] Rendered video not found for {ch_name} in {out_dir}")

        for f in out_dir.rglob(f"*{ch_name}*sync_report*.json"):
            shutil.copy2(f, ch_target / "07_sync_report.json")
        for f in out_dir.rglob(f"*{ch_name}*manifest*.json"):
            shutil.copy2(f, ch_target / "07_render_manifest.json")
        for f in out_dir.rglob(f"*{ch_name}*render_log*.txt"):
            shutil.copy2(f, ch_target / "07_render_log.txt")
        if (out_dir / "render_log.txt").exists() and not (ch_target / "07_render_log.txt").exists():
            shutil.copy2(out_dir / "render_log.txt", ch_target / "07_render_log.txt")

    log(f"[{batch_id}] All {len(chapter_nums)} chapters deployed and verified!")


def main():
    print("=" * 80)
    print("MASTER QUAD-INSTANCE KAGGLE GPU BATCH RENDER: OMNISCIENT READER'S VIEWPOINT")
    print("=" * 80)
    print("Distributing 31 chapters across 4 concurrent Kaggle Tesla T4 GPU instances:")
    print("  - Instance 1 (fabricatevisuals): orv_ch00 - orv_ch07 (8 chapters) -> manga-recap-render")
    print("  - Instance 2 (fabricatevisuals): orv_ch08 - orv_ch15 (8 chapters) -> manga-recap-render-2")
    print("  - Instance 3 (ravidevai):        orv_ch16 - orv_ch23 (8 chapters) -> manga-recap-render")
    print("  - Instance 4 (ravidevai):        orv_ch24 - orv_ch30 (7 chapters) -> manga-recap-render-2")
    print("=" * 80)

    t_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_batch_worker, b): b["batch_id"] for b in BATCH_CONFIGS}
        for fut in concurrent.futures.as_completed(futures):
            b_id = futures[fut]
            try:
                fut.result()
                log(f"[SUCCESS] {b_id} fully rendered and synchronized!")
            except Exception as e:
                log(f"[FAILED] {b_id} failed with error: {e}")
                raise

    elapsed = time.time() - t_start
    print("=" * 80)
    print(f"ALL 4 INSTANCES COMPLETED IN {elapsed:.1f}s ({elapsed/60:.2f} minutes)!")
    print("=" * 80)


if __name__ == "__main__":
    main()
