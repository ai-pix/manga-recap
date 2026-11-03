"""Quad Kaggle Kernel Batch Video Renderer for ORV.

Renders all 30 chapters concurrently across 4 Kaggle GPU instances spanning 2 accounts:
- Account 1 (ravidevai):
    - Worker 1: ravidevai/manga-recap-render     -> orv_ch01 .. orv_ch08 (8 chapters)
    - Worker 2: ravidevai/manga-recap-render-2   -> orv_ch09 .. orv_ch15 (7 chapters)
- Account 2 (fabricatevisuals):
    - Worker 3: fabricatevisuals/manga-recap-render   -> orv_ch16 .. orv_ch23 (8 chapters)
    - Worker 4: fabricatevisuals/manga-recap-render-2 -> orv_ch24 .. orv_ch30 (7 chapters)

All 4 kernels run the ultra-fast zero-copy PyNvVideoCodec DLPack GPU engine (355+ FPS)
on Tesla T4 GPU in pure hardware NVENC.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import httpx
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

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
        direct_url = raw_url.replace("https://tmpfiles.org/", "https://tmpfiles.org/dl/")
        print(f"[upload] SUCCESS via tmpfiles.org ({time.time() - t0:.1f}s): {direct_url}", flush=True)
        return direct_url
    except Exception as e:
        print(f"[upload] tmpfiles.org failed: {e}. Trying filebin.net...", flush=True)

    # 3. Fallback to filebin.net
    try:
        import uuid
        bin_id = f"mr-{uuid.uuid4().hex[:10]}"
        name = f"manga_batch_{archive.stem}_{int(time.time())}.zip"
        url_target = f"https://filebin.net/{bin_id}/{name}"
        with archive.open("rb") as f:
            resp = httpx.post(url_target, content=f.read(), timeout=timeout)
        resp.raise_for_status()
        print(f"[upload] SUCCESS via filebin.net ({time.time() - t0:.1f}s): {url_target}", flush=True)
        return url_target
    except Exception as e:
        raise RuntimeError(f"All payload upload hosts failed: {e}") from e


def stage_and_push(client: KaggleClient, slug: str, url: str) -> None:
    work_dir = repo_path(f"build/_staging_{client.username}_{slug}")
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
            "dataset_sources": [],
        },
    )
    print(f"[push] Pushing {kernel_id} to Kaggle...", flush=True)
    client.push_kernel(work_dir)
    print(f"[push] Pushed {kernel_id} successfully!", flush=True)


def monitor_quad_kernels(kernel_tasks: list[tuple[KaggleClient, str]], poll_interval: int = 20) -> dict[str, str]:
    print("[monitor] Waiting 25s for Kaggle job registration across all 4 kernels...", flush=True)
    time.sleep(25)

    all_kids = [f"{client.username}/{slug}" for client, slug in kernel_tasks]
    print(f"[monitor] Monitoring 4 kernels concurrently: {all_kids}", flush=True)

    start_times = {kid: time.time() for kid in all_kids}
    statuses = {kid: "pending" for kid in all_kids}
    seen_running = {kid: False for kid in all_kids}

    client_map = {f"{client.username}/{slug}": client for client, slug in kernel_tasks}

    while True:
        all_finished = True
        for kid in all_kids:
            if statuses[kid] in STATUS_DONE or statuses[kid] in STATUS_FAILED:
                continue

            client = client_map[kid]
            status = client.kernel_status(kid)
            elapsed = time.time() - start_times[kid]
            print(f"[monitor] [{format_duration(elapsed)}] {kid} -> {status}", flush=True)

            if status in STATUS_RUNNING:
                seen_running[kid] = True
                all_finished = False
            elif status in STATUS_DONE:
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
            print("[monitor] All 4 kernels have finished running!", flush=True)
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
    out_dir = repo_path(f"build/output_{client.username}_{slug}")
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
            manifest_data = json.loads(paths.render_manifest_file.read_text(encoding="utf-8"))
        else:
            manifest_data = {}

        # Locate sync report
        sync_file = _locate(out_dir, f"{ch}_sync_report.json")
        if sync_file:
            shutil.copy2(sync_file, paths.sync_report_file)

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


def main():
    env_vals = dotenv_values(REPO_ROOT / ".env")
    u1 = env_vals.get("KAGGLE_USERNAME", "ravidevai")
    k1 = env_vals.get("KAGGLE_KEY")
    u2 = env_vals.get("KAGGLE_USERNAME_2", "fabricatevisuals")
    k2 = env_vals.get("KAGGLE_KEY_2")

    c1 = KaggleClient(username=u1, key=k1)
    c2 = KaggleClient(username=u2, key=k2)

    # 4 Batches for all 30 chapters
    batches = [
        {
            "client": c1,
            "slug": "manga-recap-render",
            "name": "quad_batch_orv_ch01_ch08",
            "chapters": [f"orv_ch{i:02d}" for i in range(1, 9)],
        },
        {
            "client": c1,
            "slug": "manga-recap-render-2",
            "name": "quad_batch_orv_ch09_ch15",
            "chapters": [f"orv_ch{i:02d}" for i in range(9, 16)],
        },
        {
            "client": c2,
            "slug": "manga-recap-render",
            "name": "quad_batch_orv_ch16_ch23",
            "chapters": [f"orv_ch{i:02d}" for i in range(16, 24)],
        },
        {
            "client": c2,
            "slug": "manga-recap-render-2",
            "name": "quad_batch_orv_ch24_ch30",
            "chapters": [f"orv_ch{i:02d}" for i in range(24, 31)],
        },
    ]

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 70, flush=True)
    print("QUAD KAGGLE GPU BATCH RENDER: All 30 Chapters Across 4 Instances", flush=True)
    for b in batches:
        print(f"  [{b['client'].username}/{b['slug']}] -> {b['chapters']} ({len(b['chapters'])} chs)", flush=True)
    print("=" * 70, flush=True)

    # 1. Stage and upload all 4 archives
    for b in batches:
        arc = stage_batch(b["name"], b["chapters"], BUILD_DIR)
        url = upload_archive(arc)
        b["url"] = url
        # Remove local staging zip to save disk space
        if arc.exists():
            arc.unlink()

    # 2. Push all 4 kernels
    for b in batches:
        stage_and_push(b["client"], b["slug"], b["url"])

    # 3. Monitor all 4 concurrently
    kernel_tasks = [(b["client"], b["slug"]) for b in batches]
    statuses = monitor_quad_kernels(kernel_tasks, poll_interval=20)

    for b in batches:
        kid = f"{b['client'].username}/{b['slug']}"
        if statuses.get(kid) not in STATUS_DONE:
            print(f"[error] Kernel {kid} did not finish with done (status: {statuses.get(kid)})", flush=True)
            return 1

    # 4. Distribute outputs
    print("\n" + "=" * 70, flush=True)
    print("ALL 4 KERNELS COMPLETE! Distributing all 30 chapter videos...", flush=True)
    print("=" * 70, flush=True)
    for b in batches:
        distribute_outputs(b["client"], b["slug"], b["chapters"])

    print("\n[SUCCESS] All 30 chapters rendered and distributed successfully!", flush=True)

    # 5. Stitch Master Movies
    print("\n" + "=" * 70, flush=True)
    print("STITCHING MASTER MOVIES VIA LOCAL GPU NVENC (h264_nvenc, cq=28, +faststart)", flush=True)
    print("=" * 70, flush=True)

    # A. Hook Arc (Ch 01-05)
    hook_out = repo_path("data/movies/orv_hook_arc_ch01_ch05.mp4")
    subprocess.run(
        [
            sys.executable,
            str(repo_path("scripts/stitch_all_chapters.py")),
            "--prefix", "orv_ch",
            "--start", "1",
            "--end", "5",
            "--output", str(hook_out),
        ],
        check=True,
    )

    # B. Full Movie (Ch 01-30)
    full_out = repo_path("data/movies/orv_full_movie_ch01_ch30.mp4")
    subprocess.run(
        [
            sys.executable,
            str(repo_path("scripts/stitch_all_chapters.py")),
            "--prefix", "orv_ch",
            "--start", "1",
            "--end", "30",
            "--output", str(full_out),
        ],
        check=True,
    )

    print("\n[COMPLETE] ALL 30 CHAPTERS RENDERED AND STITCHED AT TEMPO 1.04!", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
