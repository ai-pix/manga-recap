"""Dual-Instance Kaggle GPU Batch Render Orchestrator.

Renders manga recap chapters in parallel across 2 simultaneous Kaggle Tesla T4 GPU instances:
- Instance 1: ravidevai/manga-recap-render
- Instance 2: ravidevai/manga-recap-render-2

Both instances encode using zero-copy PyNvVideoCodec NVENC at a compact, high-quality
bitrate (3.2 Mbps), cutting file sizes by ~70% (down to ~200-250MB for 10 min) for
lightning-fast downloading and storage efficiency.
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s5_render import run as run_render

sys.stdout.reconfigure(encoding="utf-8")
cfg = load_config()

start_ch = int(sys.argv[1]) if len(sys.argv) > 1 else 14
end_ch = int(sys.argv[2]) if len(sys.argv) > 2 else 40

print("=" * 70)
print(f"DUAL-INSTANCE KAGGLE GPU BATCH RENDER: Chapters {start_ch:02d} to {end_ch:02d}")
print("Instance 1: manga-recap-render   (Tesla T4 Pure GPU NVENC)")
print("Instance 2: manga-recap-render-2 (Tesla T4 Pure GPU NVENC)")
print("Target Bitrate: 3.2 Mbps (~200-250 MB per 10-min chapter)")
print("=" * 70)

print_lock = threading.Lock()


def log(msg: str) -> None:
    with print_lock:
        print(msg, flush=True)


ch_queue: queue.Queue[int | None] = queue.Queue()
for c in range(start_ch, end_ch + 1):
    ch_queue.put(c)

# Sentinel for each worker
ch_queue.put(None)
ch_queue.put(None)

completed_chapters = []
failed_chapters = []
stats_lock = threading.Lock()


def worker_loop(worker_id: int, kernel_slug: str) -> None:
    log(f"[Worker-{worker_id}] Started using Kaggle kernel: {kernel_slug}")
    while True:
        try:
            ch_num = ch_queue.get_nowait()
        except queue.Empty:
            break

        if ch_num is None:
            ch_queue.task_done()
            break

        ch_id = f"revival_hunter_ch{ch_num:02d}"
        paths = ChapterPaths.create(ch_id)

        if paths.final_file.exists():
            size_mb = paths.final_file.stat().st_size / (1024 * 1024)
            log(f"[Worker-{worker_id}] [{ch_num:02d}/{end_ch:02d}] {ch_id}: 07_final.mp4 already exists ({size_mb:.1f} MB) -> SKIPPING")
            with stats_lock:
                completed_chapters.append((ch_id, size_mb))
            ch_queue.task_done()
            continue

        log(f"\n[Worker-{worker_id}] [{ch_num:02d}/{end_ch:02d}] Launching Kaggle GPU render for {ch_id} on {kernel_slug}...")

        # Ensure kernel is completely idle before dispatching new job
        from manga_recap.core.kaggle_io import KaggleClient
        k_client = KaggleClient()
        while k_client.kernel_status(f"{k_client.username}/{kernel_slug}") in {"running", "pending", "queued"}:
            log(f"[Worker-{worker_id}] Waiting for {kernel_slug} to finish prior run...")
            time.sleep(10)

        # Wait for audio if needed
        wait_count = 0
        while not (paths.narration_file.exists() and paths.timeline_file.exists()):
            log(f"[Worker-{worker_id}] Waiting for {ch_id} audio files... ({wait_count * 10}s)")
            time.sleep(10)
            wait_count += 1
            if wait_count > 60:
                log(f"[Worker-{worker_id}] Error: timed out waiting for audio for {ch_id}")
                with stats_lock:
                    failed_chapters.append((ch_id, "Audio missing / timeout"))
                ch_queue.task_done()
                continue

        t0 = time.time()
        try:
            run_render(paths, cfg, force=True, kernel_slug=kernel_slug)
            render_elapsed = time.time() - t0

            # Verify streams
            probe_cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(paths.final_file)
            ]
            probe_res = subprocess.check_output(probe_cmd, text=True)
            data = json.loads(probe_res)
            v_dur = float(next(s["duration"] for s in data["streams"] if s["codec_type"] == "video"))
            a_dur = float(next(s["duration"] for s in data["streams"] if s["codec_type"] == "audio"))
            diff = abs(v_dur - a_dur)
            size_mb = paths.final_file.stat().st_size / (1024 * 1024)

            if diff > 1.0:
                log(f"[Worker-{worker_id}] [Auto-Sync] Audio/video diff {diff:.2f}s on {ch_id}, remuxing...")
                fixed_file = paths.root / "07_final_fixed.mp4"
                remux_cmd = [
                    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(paths.final_file),
                    "-i", str(paths.narration_file),
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    "-map", "0:v:0",
                    "-map", "1:a:0",
                    "-movflags", "+faststart",
                    str(fixed_file),
                ]
                subprocess.run(remux_cmd, check=True)
                os.replace(fixed_file, paths.final_file)
                size_mb = paths.final_file.stat().st_size / (1024 * 1024)

            log(
                f"[Worker-{worker_id}] -> SUCCESS: {ch_id} rendered in {render_elapsed:.1f}s | "
                f"Video: {v_dur:.1f}s, Audio: {a_dur:.1f}s (diff={diff:.3f}s), Size: {size_mb:.1f} MB!"
            )
            with stats_lock:
                completed_chapters.append((ch_id, size_mb))

        except Exception as exc:
            log(f"[Worker-{worker_id}] -> FAILED: {ch_id} on {kernel_slug}: {exc}")
            with stats_lock:
                failed_chapters.append((ch_id, str(exc)))

        ch_queue.task_done()

    log(f"[Worker-{worker_id}] All assigned chapters complete.")


t_start = time.time()
workers = [
    threading.Thread(target=worker_loop, args=(1, "manga-recap-render")),
    threading.Thread(target=worker_loop, args=(2, "manga-recap-render-2")),
]

for w in workers:
    w.start()

for w in workers:
    w.join()

t_tot = time.time() - t_start
print("\n" + "=" * 70)
print(f"DUAL-INSTANCE BATCH RENDER COMPLETE in {t_tot:.1f}s ({t_tot / 60:.1f} min)!")
print(f"Total Successful: {len(completed_chapters)}")
if completed_chapters:
    for cid, sz in completed_chapters:
        print(f"  {cid}: {sz:.1f} MB")
if failed_chapters:
    print(f"Failed ({len(failed_chapters)}):")
    for cid, err in failed_chapters:
        print(f"  {cid}: {err}")
print("=" * 70)
