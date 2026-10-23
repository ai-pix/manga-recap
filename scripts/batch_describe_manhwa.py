"""Batch describe script for manhwa chapters via Gemini Vision API.

Iterates through chapters of a series, invoking Stage 2 `describe` on each chapter,
verifying panel counts, and tracking completion.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def is_chapter_described(chapter_dir: Path) -> bool:
    """Check if chapter already has a complete 03_descriptions.json."""
    desc_path = chapter_dir / "03_descriptions.json"
    idx_path = chapter_dir / "02_panels" / "panel_index.json"

    if not desc_path.exists() or not idx_path.exists():
        return False

    try:
        desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
        idx_data = json.loads(idx_path.read_text(encoding="utf-8"))
        desc_count = len(desc_data.get("panels", []))
        idx_count = len(idx_data.get("panels", []))
        return desc_count >= idx_count and desc_count > 0
    except Exception:
        return False


def run_describe_chapter(chapter_id: str) -> bool:
    """Run `manga_recap describe <chapter_id>` via subprocess."""
    cmd = [sys.executable, "-m", "manga_recap", "describe", chapter_id]
    print(f"[{chapter_id}] Starting describe stage (Gemini Vision API)...", flush=True)
    t0 = time.time()
    res = subprocess.run(cmd, cwd=REPO_ROOT, text=True, capture_output=True)
    dur = time.time() - t0

    if res.returncode != 0:
        print(f"[{chapter_id}] Describe FAILED in {dur:.1f}s:", flush=True)
        if res.stderr:
            print(res.stderr.strip()[:1000], flush=True)
        if res.stdout:
            print(res.stdout.strip()[:1000], flush=True)
        return False

    print(f"[{chapter_id}] Describe COMPLETED in {dur:.1f}s!", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch describe manhwa chapters")
    parser.add_argument("--series", default="sss-class-revival-hunter", help="Series slug")
    parser.add_argument("--start", type=int, default=1, help="Start chapter number")
    parser.add_argument("--end", type=int, default=40, help="End chapter number")
    parser.add_argument("--force", action="store_true", help="Force re-describe")
    args = parser.parse_args()

    series_slug = args.series
    base_dir = REPO_ROOT / "data" / "chapters" / series_slug

    target_chapters = [n for n in range(args.start, args.end + 1)]
    print("=======================================================")
    print(f"BATCH VISION DESCRIBE: {series_slug}")
    print(f"Target Chapters: Ch {args.start:02d} to Ch {args.end:02d} ({len(target_chapters)} total)")
    print("=======================================================\n", flush=True)

    t_start = time.time()
    succeeded = []
    failed = []
    skipped = []

    for idx, num in enumerate(target_chapters, start=1):
        ch_id = f"{series_slug}/ch{num:02d}"
        ch_dir = base_dir / f"ch{num:02d}"

        if not ch_dir.exists():
            print(f"[{idx}/{len(target_chapters)}] Directory not found for {ch_id}. Skipping.")
            failed.append(ch_id)
            continue

        if not args.force and is_chapter_described(ch_dir):
            print(f"[{idx}/{len(target_chapters)}] {ch_id} already fully described. Skipping.", flush=True)
            skipped.append(ch_id)
            continue

        print(f"[{idx}/{len(target_chapters)}] Processing {ch_id}...", flush=True)
        ok = run_describe_chapter(ch_id)
        if ok:
            succeeded.append(ch_id)
        else:
            failed.append(ch_id)
            print(f"Halting batch describe due to error on {ch_id}.", flush=True)
            break

    elapsed = time.time() - t_start
    print("\n=======================================================")
    print(f"BATCH DESCRIBE RUN FINISHED in {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"Newly Succeeded: {len(succeeded)}")
    print(f"Already Completed (Skipped): {len(skipped)}")
    print(f"Failed / Halted: {len(failed)}")
    print("=======================================================")


if __name__ == "__main__":
    main()
