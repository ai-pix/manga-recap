"""Batch crop Overgeared chapters (ch02 to ch30) with progress tracking."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s1_crop import run as run_crop


def main():
    cfg = load_config()
    start_ch = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    end_ch = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    print("=" * 70)
    print(f"BATCH CROPPING OVERGEARED: Chapters {start_ch:02d} to {end_ch:02d}")
    print("=" * 70)

    summary = []

    for ch_num in range(start_ch, end_ch + 1):
        ch_id = f"overgeared/ch{ch_num:02d}"
        paths = ChapterPaths.create(ch_id)

        if not paths.pages_dir.is_dir() or not paths.page_images():
            print(f"[{ch_id}] Missing 01_pages/, skipping.")
            continue

        index_file = paths.panels_dir / "panel_index.json"
        if index_file.exists() and "--force" not in sys.argv:
            print(f"[{ch_id}] Already cropped, skipping.")
            continue

        print(f"\n>>> [{ch_num}/{end_ch}] Cropping {ch_id} ({len(paths.page_images())} pages)...", flush=True)
        t0 = time.time()
        try:
            index = run_crop(paths, cfg, force=True)
            elapsed = time.time() - t0
            print(f"  [OK] {ch_id}: {index.panel_count} panels in {elapsed:.1f}s")
            summary.append((ch_id, index.panel_count, elapsed))
        except Exception as exc:
            print(f"  [ERROR] {ch_id} failed: {exc}")

    print("\n" + "=" * 70)
    print(f"BATCH CROP FINISHED: {len(summary)} chapters processed")
    print(f"Total Panels: {sum(cnt for _, cnt, _ in summary)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
