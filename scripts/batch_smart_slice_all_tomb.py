"""Batch Smart Manhwa Slicer for Tomb Raider King (Chapters 01 - 30).

Features:
- Reads pristine uncropped raw slices from:
  `D:\\Python Projects\\Hakuniku\\cli\\downloads\\Comix\\Tomb Raider King\\Chapter {c}`
- Safely unlinks legacy Hakuniku junctions in `data/chapters/series3_ch{c:02d}/02_panels`.
- Runs ManhwaSlicer:
  1. Continuous vertical canvas across all split files (zero decapitations).
  2. Gutter detection (white >235, black <25, flat grey, Canny edge density).
  3. Floating speech bubble auto-merging into adjacent scene panels.
  4. Content ink bounding box trimming.
  5. Strict WebP format (quality 90).
  6. High-res bubble text crops in `_text/`.
  7. Schema-compliant `panel_index.json`.
- Concurrent worker execution across chapters.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.stages.s1_crop.manhwa_slicer import get_detector_session, slice_manhwa

RAWS_DIR = Path(r"D:\Python Projects\Hakuniku\cli\downloads\Comix\Tomb Raider King")
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters"


def unlink_junction_if_present(p: Path) -> None:
    """Safely unlink a Windows directory junction if present."""
    if not p.exists():
        return
    # Check if reparse point / junction
    try:
        import stat
        s = os.lstat(str(p))
        if s.st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            subprocess.run(["cmd", "/c", "rmdir", str(p)], check=True, capture_output=True)
            return
    except Exception:
        pass

    # If it is a real directory with old contents
    if p.is_dir():
        import shutil
        shutil.rmtree(p, ignore_errors=True)


def process_chapter(ch_num: int, force: bool = False) -> tuple[int, bool, int, float, str]:
    t0 = time.time()
    ch_name = f"series3_ch{ch_num:02d}"
    raw_chapter_dir = RAWS_DIR / f"Chapter {ch_num}"
    dest_chapter_dir = CHAPTERS_ROOT / ch_name
    dest_panels_dir = dest_chapter_dir / "02_panels"

    if not raw_chapter_dir.exists():
        return ch_num, False, 0, 0.0, f"Raw directory missing: {raw_chapter_dir}"

    dest_chapter_dir.mkdir(parents=True, exist_ok=True)

    # Check if already sliced with smart slicer (has WebP panels and panel_index.json)
    idx_file = dest_panels_dir / "panel_index.json"
    if not force and idx_file.exists():
        try:
            data = json.loads(idx_file.read_text(encoding="utf-8"))
            count = len(data.get("panels", []))
            webp_files = list(dest_panels_dir.glob("*.webp"))
            if count > 0 and len(webp_files) >= count:
                return ch_num, True, count, time.time() - t0, "Already sliced"
        except Exception:
            pass

    # Clean old junction or directory
    unlink_junction_if_present(dest_panels_dir)
    dest_panels_dir.mkdir(parents=True, exist_ok=True)

    try:
        detector_sess = get_detector_session()
        res = slice_manhwa(
            input_source=raw_chapter_dir,
            output_dir=dest_chapter_dir,
            chapter_id=f"ch{ch_num:02d}",
            detector_session=detector_sess,
            force=True,
        )
        elapsed = time.time() - t0
        return ch_num, True, res.panel_count, elapsed, "Success"
    except Exception as e:
        elapsed = time.time() - t0
        return ch_num, False, 0, elapsed, str(e)


def main():
    parser = argparse.ArgumentParser(description="Batch Smart Manhwa Slicer for Tomb Raider King")
    parser.add_argument("--start", type=int, default=1, help="Start chapter (default 1)")
    parser.add_argument("--end", type=int, default=30, help="End chapter (default 30)")
    parser.add_argument("--chapter", type=int, help="Single chapter to slice")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent worker threads (default 4)")
    parser.add_argument("--force", action="store_true", help="Force re-slicing even if already done")
    args = parser.parse_args()

    if args.chapter:
        target_chapters = [args.chapter]
    else:
        target_chapters = list(range(args.start, args.end + 1))

    print("=" * 70)
    print("🚀 BATCH SMART MANHWA SLICER (TOMB RAIDER KING)")
    print(f"Chapters: {target_chapters[0]} to {target_chapters[-1]} ({len(target_chapters)} total)")
    print(f"Workers: {args.workers} concurrent | Output: WebP Q90 | Force: {args.force}")
    print("=" * 70, flush=True)

    t_global = time.time()
    succeeded = []
    failed = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_ch = {
            executor.submit(process_chapter, ch, args.force): ch
            for ch in target_chapters
        }
        for future in concurrent.futures.as_completed(future_to_ch):
            ch_num, ok, count, dur, msg = future.result()
            ch_tag = f"series3_ch{ch_num:02d}"
            if ok:
                succeeded.append(ch_num)
                print(f"  ✅ [{ch_tag}] Sliced {count} clean panels in {dur:.1f}s ({msg})", flush=True)
            else:
                failed.append((ch_num, msg))
                print(f"  ❌ [{ch_tag}] FAILED in {dur:.1f}s: {msg}", flush=True)

    total_time = time.time() - t_global
    print("\n" + "=" * 70)
    print(f"🎉 BATCH SLICING COMPLETE in {total_time:.1f}s ({total_time/60:.2f} min)")
    print(f"Success: {len(succeeded)}/{len(target_chapters)}")
    if failed:
        print(f"Failed: {failed}")
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
