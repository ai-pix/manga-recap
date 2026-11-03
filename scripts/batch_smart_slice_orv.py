"""High-throughput multi-core Smart Manhwa Slicer for Omniscient Reader's Viewpoint (Chapters 0 - 30).

Uses upgraded manhwa_slicer:
- Continuous vertical canvas across image splits (zero decapitations)
- True semantic gutter detection (luminance + Canny edge/gradient density)
- Floating speech bubble auto-merging into adjacent scene panels
- Tight content ink bounding box trimming
- 100% WebP Standard (quality 90, method 3 for ultra-fast encoding)
- Multi-process parallel concurrency across all 31 chapters
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.stages.s1_crop.manhwa_slicer import slice_manhwa, ManhwaSliceConfig

ASURA_DIR = Path(r"D:\Python Projects\Hakuniku\cli\downloads\Asura")
ORV_RAW_DIR = next(d for d in ASURA_DIR.iterdir() if "Omniscient" in d.name)
HAKUNIKU_PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels\Omniscient Reader's Viewpoint")
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters"

def process_single_chapter(ch_num: int) -> tuple[int, bool, int, float, str]:
    t0 = time.time()
    raw_ch_dir = ORV_RAW_DIR / f"Chapter {ch_num}"
    if not raw_ch_dir.exists():
        # try without space or check actual name
        for cand in ORV_RAW_DIR.iterdir():
            if cand.is_dir() and cand.name.endswith(str(ch_num)):
                raw_ch_dir = cand
                break

    if not raw_ch_dir.exists():
        return ch_num, False, 0, 0.0, f"Raw chapter dir not found: {raw_ch_dir}"

    out_chapter_dir = HAKUNIKU_PANELS_ROOT / f"Chapter {ch_num}"
    out_panels_dir = out_chapter_dir / "02_panels"
    if out_chapter_dir.exists():
        shutil.rmtree(out_chapter_dir, ignore_errors=True)
    out_panels_dir.mkdir(parents=True, exist_ok=True)

    ch_id = f"orv_ch{ch_num:02d}"
    try:
        config = ManhwaSliceConfig(webp_quality=90)
        res = slice_manhwa(raw_ch_dir, out_panels_dir, chapter_id=ch_id, config=config, force=True)
        panel_count = res.panel_count

        # Also update / ensure chapter 02_panels junction in data/chapters
        data_ch_dir = CHAPTERS_ROOT / ch_id
        data_ch_dir.mkdir(parents=True, exist_ok=True)
        data_panels_dir = data_ch_dir / "02_panels"

        # If data_panels_dir is a junction or directory, unlink/remove
        if data_panels_dir.exists() or os.path.islink(data_panels_dir):
            import subprocess
            subprocess.run(["cmd", "/c", "rmdir", str(data_panels_dir)], capture_output=True)
            if data_panels_dir.exists():
                shutil.rmtree(data_panels_dir, ignore_errors=True)

        # Create fresh directory junction to Hakuniku panels/02_panels
        import subprocess
        subprocess.run(["cmd", "/c", "mklink", "/J", str(data_panels_dir), str(out_panels_dir)], capture_output=True)

        elapsed = time.time() - t0
        return ch_num, True, panel_count, elapsed, ""
    except Exception as e:
        elapsed = time.time() - t0
        return ch_num, False, 0, elapsed, str(e)


def main():
    print("=" * 70)
    print("STARTING SMART PARALLEL SLICER FOR ORV (CHAPTERS 0 - 30)")
    print("=" * 70)
    HAKUNIKU_PANELS_ROOT.mkdir(parents=True, exist_ok=True)

    chapters = list(range(0, 31))
    print(f"Total chapters to slice: {len(chapters)}")
    t_start = time.time()

    workers = min(7, os.cpu_count() or 4)
    print(f"Launching ProcessPoolExecutor with {workers} parallel workers...")

    results = []
    total_panels = 0

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as executor:
        future_map = {executor.submit(process_single_chapter, ch): ch for ch in chapters}
        for future in concurrent.futures.as_completed(future_map):
            ch_num, success, p_count, elap, err = future.result()
            if success:
                total_panels += p_count
                print(f"[SUCCESS] Chapter {ch_num:02d}: Sliced {p_count} panels in {elap:.1f}s (Total so far: {total_panels})", flush=True)
            else:
                print(f"[FAILED]  Chapter {ch_num:02d}: {err} in {elap:.1f}s", flush=True)
            results.append((ch_num, success, p_count, elap, err))

    results.sort(key=lambda r: r[0])
    total_time = time.time() - t_start

    print("=" * 70)
    print(f"ORV SLICING COMPLETE: {total_panels} panels across {len(results)} chapters in {total_time:.1f}s")
    print("=" * 70)

    # Save summary manifest
    summary = {
        "series": "Omniscient Reader's Viewpoint",
        "total_chapters": len(results),
        "total_panels": total_panels,
        "total_time_seconds": total_time,
        "chapters": [
            {"chapter": r[0], "success": r[1], "panel_count": r[2], "seconds": r[3], "error": r[4]}
            for r in results
        ]
    }
    summary_path = HAKUNIKU_PANELS_ROOT / "slicing_manifest.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Manifest written to {summary_path}")

if __name__ == "__main__":
    main()
