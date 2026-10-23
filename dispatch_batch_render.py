"""Batch rendering dispatcher for Manga Recap chapters on Kaggle GPU.

Stages and pushes rendering batches of 4-5 chapters to Kaggle Tesla T4 GPU,
running the verified PyNvVideoCodec NVENC engine at 355+ FPS.
"""

from __future__ import annotations

import argparse
import json
import shutil
import time
import zipfile
from pathlib import Path

from manga_recap.core import payload
from manga_recap.core.kaggle_io import KaggleClient
from manga_recap.core.paths import repo_path


def build_batch_zip(chapters: list[str], output_zip: Path) -> Path:
    """Pack multiple chapters into a structured payload for Kaggle batch render."""
    print(f"\n[batch_render] Packaging {len(chapters)} chapters into {output_zip.name}...", flush=True)
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    job_data = {
        "mode": "batch",
        "chapters": chapters,
        "render": {
            "engine": "pynv",
            "encoder": "h264_nvenc",
            "background_mode": "blurred",
            "pan_tall": True,
            "max_workers": 4,
            "fps": 30,
        },
    }

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as bundle:
        # 1. job.json at root
        bundle.writestr("job.json", json.dumps(job_data, indent=2))

        # 2. Package each chapter under chapters/<cid>/
        for cid in chapters:
            ch_root = repo_path(f"data/chapters/{cid}")
            print(f"  -> Adding {cid}...", flush=True)

            # script, timeline, narration
            bundle.write(ch_root / "04_script.json", f"chapters/{cid}/script.json")
            bundle.write(ch_root / "06_timeline.json", f"chapters/{cid}/timeline.json")
            bundle.write(ch_root / "05_narration.wav", f"chapters/{cid}/narration.wav")

            # panels
            panels_dir = ch_root / "02_panels"
            for p in panels_dir.glob("panel_*.png"):
                bundle.write(p, f"chapters/{cid}/panels/{p.name}")
            for p in panels_dir.glob("panel_*.jpg"):
                bundle.write(p, f"chapters/{cid}/panels/{p.name}")

        # 3. Bundle repo's src/ so manga_recap can be imported
        src_dir = repo_path("src")
        if src_dir.is_dir():
            for spath in src_dir.rglob("*.py"):
                bundle.write(spath, f"src/{spath.relative_to(src_dir)}")

        # 4. Bundle helper modules from kaggle/kernel_render into lib/
        kernel_dir = repo_path("kaggle/kernel_render")
        for module in kernel_dir.glob("*.py"):
            if module.name != "main.py":
                bundle.write(module, f"lib/{module.name}")

    size_mb = output_zip.stat().st_size / 1_000_000
    print(f"[batch_render] Packaged {output_zip.name} ({size_mb:.1f} MB)", flush=True)
    return output_zip


def render_batch(chapters: list[str], batch_name: str) -> bool:
    """Render a batch of chapters on Kaggle GPU."""
    print(f"\n========================================================")
    print(f"STARTING BATCH: {batch_name} ({len(chapters)} chapters: {chapters})")
    print(f"========================================================", flush=True)

    staging_dir = repo_path(f"data/chapters/_batch_staging/{batch_name}")
    staging_dir.mkdir(parents=True, exist_ok=True)
    zip_path = staging_dir / f"{batch_name}.zip"

    # Build zip
    build_batch_zip(chapters, zip_path)

    # Upload
    print(f"[batch_render] Uploading {zip_path.name} to filebin.net...", flush=True)
    payload_url = payload.upload(zip_path, host="https://filebin.net")
    print(f"[batch_render] Payload available at: {payload_url}", flush=True)

    # Stage kernel
    kernel_dir = repo_path("kaggle/kernel_render")
    client = KaggleClient()
    kernel_slug = "manga-recap-render"
    kernel_id = f"{client.username}/{kernel_slug}"
    work_dir = staging_dir / "kernel_push"

    print(f"[batch_render] Staging Kaggle kernel with render-bin dataset...", flush=True)
    staged = payload.stage_from_url(
        kernel_dir=kernel_dir,
        url=payload_url,
        work_dir=work_dir,
        metadata={
            "id": kernel_id,
            "title": kernel_slug,
            "enable_gpu": True,
            "dataset_sources": ["wampireai/manga-recap-render-bin"],
        },
    )

    print(f"[batch_render] Pushing kernel {kernel_id} to Kaggle Tesla T4 GPU...", flush=True)
    client.push_kernel(staged)

    print(f"[batch_render] Waiting for GPU execution to complete...", flush=True)
    run_info = client.wait_for_kernel(kernel_id, poll_interval=15, max_wait=2400)
    print(
        f"[batch_render] Kernel complete! Total: {run_info.total_seconds:.1f}s, "
        f"Queue: {run_info.queue_seconds:.1f}s",
        flush=True,
    )

    # Download outputs
    dl_dir = staging_dir / "outputs"
    print(f"[batch_render] Downloading rendered outputs...", flush=True)
    out_dir = client.download_kernel_output(kernel_id, dl_dir)

    # Place videos
    success_count = 0
    for cid in chapters:
        cand_vid = out_dir / f"{cid}_final.mp4"
        dest_vid = repo_path(f"data/chapters/{cid}/07_final.mp4")
        if cand_vid.exists() and cand_vid.stat().st_size > 1000:
            shutil.copy2(cand_vid, dest_vid)
            mb = dest_vid.stat().st_size / 1_000_000
            print(f"  -> [OK] Placed {cid} video: {dest_vid} ({mb:.1f} MB)", flush=True)
            success_count += 1
        else:
            print(f"  -> [FAIL] Missing video for {cid} in Kaggle outputs!", flush=True)

    return success_count == len(chapters)


def main():
    parser = argparse.ArgumentParser(description="Batch render chapters on Kaggle GPU.")
    parser.add_argument("--start", type=int, default=2, help="Start chapter")
    parser.add_argument("--end", type=int, default=20, help="End chapter")
    parser.add_argument("--batch-size", type=int, default=5, help="Chapters per Kaggle job")
    args = parser.parse_args()

    all_chapters = [f"barbarian_ch{c:02d}" for c in range(args.start, args.end + 1)]
    print(f"Batch Render Plan: {len(all_chapters)} chapters total ({all_chapters[0]} to {all_chapters[-1]})")

    for i in range(0, len(all_chapters), args.batch_size):
        chunk = all_chapters[i : i + args.batch_size]
        bname = f"batch_{chunk[0]}_to_{chunk[-1]}"
        ok = render_batch(chunk, bname)
        if not ok:
            print(f"WARNING: Some chapters failed in {bname}")

    print("\nAll batch rendering runs finished!")


if __name__ == "__main__":
    main()
