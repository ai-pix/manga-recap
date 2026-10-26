"""Two-Batch Kaggle GPU Movie Render & Local Assembly for Overgeared (Ch01 to Ch30).

Executes the user's unified 2-inference movie pipeline:
1. Batch 1 (Ch01–15): Renders on Kaggle GPU NVENC, stitches into `overgeared_part1.mp4` on Kaggle, and downloads.
2. Batch 2 (Ch16–30): Renders on Kaggle GPU NVENC, stitches into `overgeared_part2.mp4` on Kaggle, and downloads.
3. Final Stitch: Concat stream-copy combines both half-movies into `data/movies/overgeared_full_movie_ch01_ch30.mp4`.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from manga_recap.core import payload
from manga_recap.core.config import Config, load_config
from manga_recap.core.kaggle_io import KaggleClient
from manga_recap.core.paths import repo_path

sys.stdout.reconfigure(encoding="utf-8")
KERNEL_DIR = repo_path("kaggle/kernel_render")
MOVIES_DIR = repo_path("data/movies")
MOVIES_DIR.mkdir(parents=True, exist_ok=True)


def build_movie_batch_payload(
    batch_id: str,
    chapter_nums: list[int],
    movie_filename: str,
    config: Config,
) -> tuple[Path, str]:
    """Bundle 15 chapters and render configuration into a single cloud payload."""
    staging = repo_path(f"data/staging_{batch_id}")
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    chapters_dir = staging / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{batch_id}] Staging {len(chapter_nums)} chapters for {movie_filename}...")
    for n in chapter_nums:
        ch_name = f"ch{n:02d}"
        ch_src = repo_path(f"data/chapters/overgeared/{ch_name}")
        ch_dst = chapters_dir / ch_name
        ch_dst.mkdir(parents=True, exist_ok=True)

        panels_src = ch_src / "02_panels"
        panels_dst = ch_dst / "panels"
        panels_dst.mkdir(parents=True, exist_ok=True)

        # Copy panel webp images
        webp_count = 0
        for p in panels_src.glob("*.webp"):
            shutil.copy2(p, panels_dst / p.name)
            webp_count += 1

        # Copy script, timeline, narration
        shutil.copy2(ch_src / "04_script.json", ch_dst / "script.json")
        shutil.copy2(ch_src / "06_timeline.json", ch_dst / "timeline.json")
        shutil.copy2(ch_src / "05_narration.wav", ch_dst / "narration.wav")
        print(f"  -> Staged {ch_name}: {webp_count} panels, script, timeline, audio")

    # Build job.json with batch stitching configuration
    job_data = {
        "mode": "batch",
        "chapters": [f"ch{n:02d}" for n in chapter_nums],
        "stitch_movie": True,
        "movie_filename": movie_filename,
        "keep_individual": False,
        "engine": str(config.get("render.engine", "pynv")),
        "resolution": list(config.get("render.resolution", [1920, 1080])),
        "fps": int(config.get("render.fps", 24)),
        "video_bitrate": str(config.get("render.video_bitrate", "3200k")),
        "background_mode": str(config.get("render.background_mode", "blurred")),
        "blur_width": int(config.get("render.blur_width", 64)),
        "pan_tall": bool(config.get("render.pan_tall", True)),
        "subtle_motion": bool(config.get("render.subtle_motion", True)),
        "kenburns": {
            "enabled": bool(config.get("render.kenburns.enabled", True)),
            "zoom_min": float(config.get("render.kenburns.zoom_min", 1.0)),
            "zoom_max": float(config.get("render.kenburns.zoom_max", 1.08)),
        },
    }
    (staging / "job.json").write_text(
        json.dumps(job_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Package repo src/
    src_dir = repo_path("src")
    if src_dir.is_dir():
        shutil.copytree(
            src_dir,
            staging / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )

    # Package kernel helper modules
    lib_dir = staging / "lib"
    lib_dir.mkdir(exist_ok=True)
    for module in sorted(KERNEL_DIR.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)

    # Compress archive
    archive_path = repo_path(f"data/{batch_id}_payload.zip")
    if archive_path.exists():
        archive_path.unlink()

    print(f"[{batch_id}] Zipping payload archive to {archive_path.name}...", flush=True)
    payload.build_archive(staging, archive_path)
    shutil.rmtree(staging, ignore_errors=True)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"[{batch_id}] Uploading payload ({size_mb:.1f} MB)...", flush=True)

    host = str(config.get("render.payload_host", "https://sendit.sh"))
    url = payload.upload(archive_path, host=host)
    print(f"[{batch_id}] Payload available at: {url}", flush=True)
    return archive_path, url


def run_batch_render_pipeline(
    batch_id: str,
    kernel_slug: str,
    chapter_nums: list[int],
    movie_filename: str,
    config: Config,
) -> Path:
    """End-to-end execution of a single batch on Kaggle GPU NVENC."""
    t0 = time.time()
    client = KaggleClient()
    kernel_id = f"{client.username}/{kernel_slug}"

    archive_path, payload_url = build_movie_batch_payload(
        batch_id, chapter_nums, movie_filename, config
    )

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

    print(f"\n[{batch_id}] Pushing kernel to Kaggle ({kernel_id})...", flush=True)
    client.push_kernel(work_dir)
    shutil.rmtree(work_dir, ignore_errors=True)

    print(f"[{batch_id}] Waiting for Kaggle GPU execution ({kernel_id})...", flush=True)
    client.wait_for_kernel(
        kernel_id,
        poll_interval=int(config.get("render.poll_interval_seconds", 30)),
        max_wait=int(config.get("render.max_wait_seconds", 21600)),
    )

    output_dir = repo_path(f"data/_kaggle_output_{batch_id}")
    if output_dir.exists():
        shutil.rmtree(output_dir, ignore_errors=True)
    print(f"[{batch_id}] Downloading kernel outputs from {kernel_id}...", flush=True)
    client.download_kernel_output(kernel_id, output_dir)

    movie_path = output_dir / movie_filename
    if not movie_path.exists():
        candidates = list(output_dir.glob("*.mp4"))
        if candidates:
            movie_path = candidates[0]
        else:
            raise RuntimeError(f"[{batch_id}] No video output produced in {output_dir}")

    dest_movie = MOVIES_DIR / movie_filename
    shutil.copy2(movie_path, dest_movie)
    size_mb = dest_movie.stat().st_size / (1024 * 1024)
    elapsed = time.time() - t0
    print(
        f"\n[{batch_id}] [SUCCESS] Downloaded {movie_filename} ({size_mb:.1f} MB) in {elapsed:.1f}s ({elapsed/60:.2f} min)!"
    )

    # Save execution log
    log_file = output_dir / "render_log.txt"
    if log_file.exists():
        shutil.copy2(log_file, MOVIES_DIR / f"{batch_id}_render_log.txt")

    shutil.rmtree(output_dir, ignore_errors=True)
    archive_path.unlink(missing_ok=True)
    return dest_movie


def stitch_full_movie(part1: Path, part2: Path, final_dest: Path) -> Path:
    """Concatenate Part 1 and Part 2 into the complete 30-chapter movie."""
    print("=" * 70)
    print(f"STITCHING FULL 30-CHAPTER MOVIE: {part1.name} + {part2.name}")
    print("=" * 70)

    concat_file = MOVIES_DIR / "concat_full_movie.txt"
    with concat_file.open("w", encoding="utf-8") as f:
        f.write(f"file '{part1.resolve().as_posix()}'\n")
        f.write(f"file '{part2.resolve().as_posix()}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-c", "copy",
        str(final_dest),
    ]
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    concat_file.unlink(missing_ok=True)

    size_mb = final_dest.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Final 30-chapter movie generated: {final_dest} ({size_mb:.1f} MB)!")
    return final_dest


def main():
    parser = argparse.ArgumentParser(description="Two-batch movie render for Overgeared")
    parser.add_argument("--batch", type=int, choices=[1, 2], help="Run single batch (1 or 2)")
    parser.add_argument("--dual", action="store_true", help="Run both batches in parallel on Kaggle")
    parser.add_argument("--stitch-only", action="store_true", help="Only stitch existing part1 and part2")
    args = parser.parse_args()

    cfg = load_config()

    part1_dest = MOVIES_DIR / "overgeared_part1.mp4"
    part2_dest = MOVIES_DIR / "overgeared_part2.mp4"
    full_dest = MOVIES_DIR / "overgeared_full_movie_ch01_ch30.mp4"

    if args.stitch_only:
        if not part1_dest.exists() or not part2_dest.exists():
            print("ERROR: Both part1 and part2 must exist in data/movies to stitch!")
            sys.exit(1)
        stitch_full_movie(part1_dest, part2_dest, full_dest)
        return

    if args.dual:
        print("=" * 70)
        print("LAUNCHING DUAL PARALLEL KAGGLE GPU BATCHES (Ch01–15 and Ch16–30)")
        print("Instance 1: ravidevai/manga-recap-render   -> overgeared_part1.mp4")
        print("Instance 2: ravidevai/manga-recap-render-2 -> overgeared_part2.mp4")
        print("=" * 70)

        results = {}

        def _run_b1():
            try:
                results["part1"] = run_batch_render_pipeline(
                    "overgeared_batch1",
                    "manga-recap-render",
                    list(range(1, 16)),
                    "overgeared_part1.mp4",
                    cfg,
                )
            except Exception as exc:
                print(f"[ERROR in Batch 1]: {exc}")
                results["part1_err"] = exc

        def _run_b2():
            try:
                results["part2"] = run_batch_render_pipeline(
                    "overgeared_batch2",
                    "manga-recap-render-2",
                    list(range(16, 31)),
                    "overgeared_part2.mp4",
                    cfg,
                )
            except Exception as exc:
                print(f"[ERROR in Batch 2]: {exc}")
                results["part2_err"] = exc

        t1 = threading.Thread(target=_run_b1, name="Batch1-Worker")
        t2 = threading.Thread(target=_run_b2, name="Batch2-Worker")

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        if "part1" in results and "part2" in results:
            stitch_full_movie(results["part1"], results["part2"], full_dest)
        else:
            print("[ERROR] One or both batches failed, cannot stitch full movie.")
            if "part1_err" in results:
                print(f"Batch 1 error: {results['part1_err']}")
            if "part2_err" in results:
                print(f"Batch 2 error: {results['part2_err']}")
        return

    # Single batch execution
    batch_num = args.batch or 1
    if batch_num == 1:
        run_batch_render_pipeline(
            "overgeared_batch1",
            "manga-recap-render",
            list(range(1, 16)),
            "overgeared_part1.mp4",
            cfg,
        )
    else:
        run_batch_render_pipeline(
            "overgeared_batch2",
            "manga-recap-render-2",
            list(range(16, 31)),
            "overgeared_part2.mp4",
            cfg,
        )


if __name__ == "__main__":
    main()
