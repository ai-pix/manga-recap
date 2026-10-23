"""Dual Kaggle Kernel Batch Video Renderer.

Renders batches of chapters across 2 concurrent Kaggle GPU kernels:
- Kernel 1 (wampireai/manga-recap-render): First half of chapters (e.g. 10 chapters)
- Kernel 2 (wampireai/manga-recap-render-2): Second half of chapters (e.g. 10 chapters)

Both kernels run the ultra-fast zero-copy PyNvVideoCodec DLPack GPU engine (355+ FPS)
on Tesla T4 GPU, rendering 20 chapters per run in ~10 minutes.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
import zipfile
from pathlib import Path

import httpx

from manga_recap.core import payload
from manga_recap.core.kaggle_io import (
    STATUS_DONE,
    STATUS_FAILED,
    STATUS_RUNNING,
    KaggleClient,
)
from manga_recap.core.logging import format_duration, write_stage_status
from manga_recap.core.paths import ChapterPaths, repo_path

KERNEL_DIR = repo_path("kaggle/kernel_render")
SRC_DIR = repo_path("src")
BUILD_DIR = repo_path("build/render_batches")


def build_job_json(chapters: list[str]) -> dict:
    return {
        "mode": "batch",
        "chapters": chapters,
        "render": {
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "crf": 20,
            "preset": "p1",
            "encoder": "auto",
            "engine": "pynv",  # Hardware zero-copy DLPack GPU engine
            "test_duration_seconds": 0.0,
            "audio_bitrate": "192k",
            "background_color": "0x0d0d12",
            "background_mode": "blurred",
            "blur_width": 128,
            "blur_radius": 12,
            "blur_darken": 0.12,
            "pan_tall": False,
            "subtle_motion": True,
            "min_shot_seconds": 0.7,
            "max_clip_seconds": 60.0,
            "max_words_per_beat": 14,
            "pan_cycle": "in,left,up,right",
            "max_workers": 0,
            "kenburns": {
                "enabled": True,
                "zoom_end": 1.06,
            },
        },
        "bgm": {
            "enabled": False,
        },
    }


def stage_batch(batch_name: str, chapters: list[str], output_dir: Path) -> Path:
    staging_dir = output_dir / f"staging_{batch_name}"
    if staging_dir.exists():
        shutil.rmtree(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{batch_name}] Writing job.json for {chapters}...", flush=True)
    (staging_dir / "job.json").write_text(
        json.dumps(build_job_json(chapters), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[{batch_name}] Copying src/...", flush=True)
    shutil.copytree(
        SRC_DIR,
        staging_dir / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        dirs_exist_ok=True,
    )

    print(f"[{batch_name}] Copying lib/...", flush=True)
    lib_dir = staging_dir / "lib"
    lib_dir.mkdir(exist_ok=True)
    for module in sorted(KERNEL_DIR.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)

    # Copy chapters
    for ch in chapters:
        print(f"[{batch_name}] Staging {ch}...", flush=True)
        paths = ChapterPaths.create(ch)
        ch_target = staging_dir / "chapters" / ch
        ch_target.mkdir(parents=True, exist_ok=True)

        script_src = paths.root / "04_script_fish.json"
        if not script_src.exists():
            script_src = paths.script_file
        shutil.copy2(script_src, ch_target / "script.json")
        shutil.copy2(paths.timeline_file, ch_target / "timeline.json")
        shutil.copy2(paths.narration_file, ch_target / "narration.wav")

        panels_target = ch_target / "panels"
        panels_target.mkdir(parents=True, exist_ok=True)
        for panel in paths.panel_images():
            shutil.copy2(panel, panels_target / panel.name)

    # Archive
    archive_path = output_dir / f"{batch_name}.zip"
    if archive_path.exists():
        archive_path.unlink()

    print(f"[{batch_name}] Creating archive {archive_path.name}...", flush=True)
    t0 = time.time()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for p in sorted(staging_dir.rglob("*")):
            if p.is_file():
                bundle.write(p, p.relative_to(staging_dir))
    elapsed = time.time() - t0
    size_mb = archive_path.stat().st_size / 1_000_000
    print(f"[{batch_name}] Created {archive_path.name} ({size_mb:.1f} MB in {elapsed:.1f}s)", flush=True)
    return archive_path


def upload_archive(archive: Path, timeout: float = 1200.0) -> str:
    print(f"[upload] Starting upload for {archive.name} ({archive.stat().st_size / 1e6:.1f} MB)...", flush=True)
    t0 = time.time()

    # 1. Try sendit.sh
    try:
        url_name = f"manga_batch_{archive.stem}_{int(time.time())}.zip"
        print(f"[upload] Trying sendit.sh for {url_name}...", flush=True)
        with archive.open("rb") as f:
            resp = httpx.put(f"https://sendit.sh/{url_name}", content=f.read(), timeout=timeout)
        resp.raise_for_status()
        match = re.search(r"https://sendit\.sh/[a-zA-Z0-9_\-]+/[^\s]+", resp.text)
        if match:
            url = match.group(0).strip()
            print(f"[upload] SUCCESS via sendit.sh ({time.time() - t0:.1f}s): {url}", flush=True)
            return url
    except Exception as e:
        print(f"[upload] sendit.sh failed: {e}. Trying tmpfiles.org...", flush=True)

    # 2. Fallback to tmpfiles.org
    try:
        name = f"manga_batch_{archive.stem}_{int(time.time())}.zip"
        with archive.open("rb") as f:
            resp = httpx.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": (name, f, "application/zip")},
                timeout=timeout,
            )
        resp.raise_for_status()
        res_json = resp.json()
        raw_url = res_json["data"]["url"]
        # Convert https://tmpfiles.org/<id>/<name> to direct download https://tmpfiles.org/dl/<id>/<name>
        direct_url = raw_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
        print(f"[upload] SUCCESS via tmpfiles.org ({time.time() - t0:.1f}s): {direct_url}", flush=True)
        return direct_url
    except Exception as e:
        raise RuntimeError(f"All payload upload hosts failed: {e}") from e


def stage_and_push(client: KaggleClient, slug: str, url: str) -> None:
    work_dir = repo_path(f"build/_staging_{slug}")
    kernel_id = f"{client.username}/{slug}"
    print(f"[push] Staging kernel {kernel_id} with payload {url}...", flush=True)

    payload.stage_from_url(
        kernel_dir=KERNEL_DIR,
        url=url,
        work_dir=work_dir,
        metadata={
            "id": kernel_id,
            "title": slug,
            "enable_gpu": True,
            "enable_internet": True,
            "dataset_sources": ["wampireai/manga-recap-render-bin"],
        },
    )
    print(f"[push] Pushing {kernel_id} to Kaggle...", flush=True)
    client.push_kernel(work_dir)
    print(f"[push] Pushed {kernel_id} successfully!", flush=True)


def monitor_dual_kernels(client: KaggleClient, kernel_ids: list[str], poll_interval: int = 20) -> dict[str, str]:
    print("[monitor] Waiting 25s for Kaggle job registration...", flush=True)
    time.sleep(25)

    print(f"[monitor] Monitoring {len(kernel_ids)} kernels concurrently: {kernel_ids}", flush=True)
    start_times = {kid: time.time() for kid in kernel_ids}
    statuses = {kid: "pending" for kid in kernel_ids}
    seen_running = {kid: False for kid in kernel_ids}

    while True:
        all_finished = True
        for kid in kernel_ids:
            if statuses[kid] in STATUS_DONE or statuses[kid] in STATUS_FAILED:
                continue

            status = client.kernel_status(kid)
            elapsed = time.time() - start_times[kid]
            print(f"[monitor] [{format_duration(elapsed)}] {kid} -> {status}", flush=True)

            if status in STATUS_RUNNING:
                seen_running[kid] = True
                all_finished = False
            elif status in STATUS_DONE:
                # Prevent false early exit if Kaggle reports stale complete before starting
                if not seen_running[kid] and elapsed < 45:
                    print(f"[monitor] {kid} reported complete very early ({elapsed:.0f}s), waiting for active run...", flush=True)
                    all_finished = False
                else:
                    statuses[kid] = status
            elif status in STATUS_FAILED:
                statuses[kid] = status
                print(f"[monitor] WARNING: Kernel {kid} failed with status: {status}", flush=True)
                client._dump_kernel_logs(kid)
            else:
                all_finished = False

        if all_finished:
            print("[monitor] All kernels have finished running!", flush=True)
            break

        time.sleep(poll_interval)

    return statuses


def _locate(directory: Path, filename: str) -> Path | None:
    if not directory.exists():
        return None
    direct = directory / filename
    if direct.exists():
        return direct
    candidates = [c for c in directory.rglob(filename) if c.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, str(p)))


def distribute_outputs(client: KaggleClient, slug: str, chapters: list[str]) -> None:
    kernel_id = f"{client.username}/{slug}"
    out_dir = repo_path(f"build/output_{slug}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[distribute] Downloading output of {kernel_id} to {out_dir}...", flush=True)
    client.download_kernel_output(kernel_id, out_dir)

    render_log = _locate(out_dir, "render_log.txt")

    for ch in chapters:
        print(f"[distribute] Processing {ch}...", flush=True)
        paths = ChapterPaths.create(ch)

        # Locate video
        video = _locate(out_dir, f"{ch}_final.mp4")
        if not video:
            raise FileNotFoundError(f"Missing {ch}_final.mp4 in {out_dir}")
        shutil.copy2(video, paths.final_file)
        v_size_mb = paths.final_file.stat().st_size / 1e6
        print(f"[distribute] [{ch}] Saved 07_final.mp4 ({v_size_mb:.1f} MB)", flush=True)

        # Locate manifest
        manifest_file = _locate(out_dir, f"{ch}_render_manifest.json")
        if manifest_file:
            shutil.copy2(manifest_file, paths.render_manifest_file)
            print(f"[distribute] [{ch}] Saved 07_render_manifest.json", flush=True)
            manifest_data = json.loads(paths.render_manifest_file.read_text(encoding="utf-8"))
        else:
            manifest_data = {}

        # Locate sync report
        sync_file = _locate(out_dir, f"{ch}_sync_report.json")
        if sync_file:
            shutil.copy2(sync_file, paths.sync_report_file)
            print(f"[distribute] [{ch}] Saved 07_sync_report.json", flush=True)

        # Copy log
        if render_log and render_log.exists():
            shutil.copy2(render_log, paths.root / "07_render_log.txt")

        # Mark stage completed
        write_stage_status(
            paths.chapter_id,
            "s5_render",
            "completed",
            {
                "clip_count": manifest_data.get("clip_count", 0),
                "duration": manifest_data.get("duration", 0),
                "output": str(paths.final_file),
            },
        )
        print(f"[distribute] [{ch}] Stage s5_render marked COMPLETED!", flush=True)


def run_super_batch(chapters: list[str]) -> int:
    if not chapters:
        print("No chapters specified.")
        return 1

    # Split into 2 kernels
    mid = (len(chapters) + 1) // 2
    c1 = chapters[:mid]
    c2 = chapters[mid:]

    batches = {
        "k1": {
            "slug": "manga-recap-render",
            "name": f"batch_{chapters[0]}_{c1[-1]}",
            "chapters": c1,
        },
        "k2": {
            "slug": "manga-recap-render-2",
            "name": f"batch_{c2[0]}_{c2[-1]}",
            "chapters": c2,
        },
    }

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    client = KaggleClient()

    print("=" * 70, flush=True)
    print(f"DUAL KAGGLE RENDER: {len(chapters)} Chapters across 2 GPU Kernels", flush=True)
    print(f"Kernel 1 ({batches['k1']['slug']}): {c1} ({len(c1)} chapters)", flush=True)
    print(f"Kernel 2 ({batches['k2']['slug']}): {c2} ({len(c2)} chapters)", flush=True)
    print("=" * 70, flush=True)

    # Check pre-uploaded cache
    preuploaded_file = BUILD_DIR / "preuploaded_urls.json"
    preuploaded = {}
    if preuploaded_file.exists():
        try:
            preuploaded = json.loads(preuploaded_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 1. Stage and zip archives / fetch URLs
    for _bkey, binfo in batches.items():
        if binfo["name"] in preuploaded:
            print(f"[{binfo['name']}] Using pre-uploaded URL: {preuploaded[binfo['name']]}", flush=True)
            binfo["url"] = preuploaded[binfo["name"]]
        else:
            arc = stage_batch(binfo["name"], binfo["chapters"], BUILD_DIR)
            binfo["archive"] = arc
            url = upload_archive(binfo["archive"])
            binfo["url"] = url

    # 3. Push both kernels
    for _bkey, binfo in batches.items():
        stage_and_push(client, binfo["slug"], binfo["url"])

    # 4. Monitor concurrently
    kernel_ids = [f"{client.username}/{binfo['slug']}" for binfo in batches.values()]
    statuses = monitor_dual_kernels(client, kernel_ids, poll_interval=20)

    for kid, st in statuses.items():
        if st not in STATUS_DONE:
            print(f"[error] Kernel {kid} did not succeed (ended with {st})", flush=True)
            return 1

    # 5. Distribute outputs
    print("\n" + "=" * 70, flush=True)
    print("ALL KERNELS COMPLETE! Distributing outputs...", flush=True)
    print("=" * 70, flush=True)
    for _bkey, binfo in batches.items():
        distribute_outputs(client, binfo["slug"], binfo["chapters"])

    print(f"\n[SUCCESS] Super-batch ({len(chapters)} chapters) rendered and verified!", flush=True)
    return 0


def render_all_remaining(batch_size: int = 20) -> int:
    chapters_dir = Path("data/chapters")
    all_chs = sorted([d.name for d in chapters_dir.iterdir() if d.is_dir() and d.name.startswith("ch")])
    remaining = [
        ch for ch in all_chs
        if not (chapters_dir / ch / "07_final.mp4").exists() and (chapters_dir / ch / "04_script.json").exists()
    ]

    print(f"Found {len(remaining)} total remaining chapters needing rendering.")
    if not remaining:
        print("All chapters are already rendered!")
        return 0

    chunk_idx = 1
    total_chunks = (len(remaining) + batch_size - 1) // batch_size

    while remaining:
        # Take up to batch_size chapters
        current_chunk = remaining[:batch_size]
        print(f"\n{'#' * 70}")
        print(f"SUPER-BATCH [{chunk_idx}/{total_chunks}]: Rendering {len(current_chunk)} chapters")
        print(f"Range: {current_chunk[0]} to {current_chunk[-1]}")
        print(f"{'#' * 70}\n", flush=True)

        res = run_super_batch(current_chunk)
        if res != 0:
            print(f"[FATAL] Super-batch {chunk_idx} failed! Halting pipeline.", flush=True)
            return res

        # Refresh remaining list
        remaining = [
            ch for ch in all_chs
            if not (chapters_dir / ch / "07_final.mp4").exists() and (chapters_dir / ch / "04_script.json").exists()
        ]
        chunk_idx += 1

    print("\n" + "=" * 70)
    print("ALL CHAPTERS IN THE SERIES HAVE BEEN SUCCESSFULLY RENDERED!")
    print("=" * 70, flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Dual Kaggle Batch Render")
    parser.add_argument("chapters", nargs="*", help="Chapters to render (optional)")
    parser.add_argument("--all", action="store_true", help="Render all remaining chapters in 20-chapter dual batches")
    parser.add_argument("--batch-size", type=int, default=20, help="Total chapters per dual-kernel run (default: 20)")
    args = parser.parse_args()

    if args.all or not args.chapters:
        sys.exit(render_all_remaining(args.batch_size))
    else:
        sys.exit(run_super_batch(args.chapters))


if __name__ == "__main__":
    main()
