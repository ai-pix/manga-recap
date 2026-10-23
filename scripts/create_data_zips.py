"""Package chapter pages, panels, and series data into 10-chapter zip bundles.

Output directory: ./zips/
Archive structure inside each zip:
  data/chapters/<chapter_id>/01_pages/...
  data/chapters/<chapter_id>/02_panels/...
Standalone series zip:
  zips/series.zip -> data/series/...
"""

from __future__ import annotations

import re
import sys
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
CHAPTERS_DIR = DATA_DIR / "chapters"
SERIES_DIR = DATA_DIR / "series"
OUTPUT_DIR = REPO_ROOT / "zips"

BATCH_SIZE = 10


def chapter_sort_key(name: str) -> tuple[int, int, str]:
    """Parse chapter names like 'ch01', 'ch005_5', 'ch103' for natural ordering."""
    m = re.match(r"^ch0*(\d+)(?:_(\d+))?$", name)
    if m:
        main_num = int(m.group(1))
        sub_num = int(m.group(2)) if m.group(2) else 0
        return (main_num, sub_num, name)
    return (9999, 0, name)


def get_all_chapters() -> list[str]:
    """Return all sorted chapter directory names."""
    if not CHAPTERS_DIR.exists():
        raise FileNotFoundError(f"Chapters directory not found: {CHAPTERS_DIR}")
    chapters = [
        d.name
        for d in CHAPTERS_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and not d.name.startswith(".")
    ]
    chapters.sort(key=chapter_sort_key)
    return chapters


def zip_series() -> Path:
    """Zip data/series into zips/series.zip."""
    print("--> Packaging series folder...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = OUTPUT_DIR / "series.zip"

    t0 = time.time()
    file_count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for f in sorted(SERIES_DIR.rglob("*")):
            if f.is_file():
                arcname = str(f.relative_to(REPO_ROOT)).replace("\\", "/")
                zf.write(f, arcname)
                file_count += 1

    # Verify integrity
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"Corrupt file in {zip_path}: {bad}")

    elapsed = time.time() - t0
    size_kb = zip_path.stat().st_size / 1024
    print(f"    [OK] {zip_path.name}: {file_count} files, {size_kb:.1f} KB in {elapsed:.2f}s\n")
    return zip_path


def zip_chapter_batch(batch_num: int, chapters: list[str]) -> Path:
    """Package a batch of chapters into a single zip file."""
    first_ch = chapters[0]
    last_ch = chapters[-1]
    zip_name = f"batch_{batch_num:02d}_{first_ch}-{last_ch}.zip"
    zip_path = OUTPUT_DIR / zip_name

    print(f"--> [{batch_num:02d}] Packaging {zip_name} ({len(chapters)} chapters: {first_ch} -> {last_ch})...")
    t0 = time.time()
    file_count = 0
    total_uncompressed_bytes = 0

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for ch in chapters:
            ch_dir = CHAPTERS_DIR / ch
            pages_dir = ch_dir / "01_pages"
            panels_dir = ch_dir / "02_panels"

            ch_files = 0
            if pages_dir.exists():
                for f in sorted(pages_dir.rglob("*")):
                    if f.is_file():
                        arcname = str(f.relative_to(REPO_ROOT)).replace("\\", "/")
                        zf.write(f, arcname)
                        file_count += 1
                        ch_files += 1
                        total_uncompressed_bytes += f.stat().st_size

            if panels_dir.exists():
                for f in sorted(panels_dir.rglob("*")):
                    if f.is_file():
                        arcname = str(f.relative_to(REPO_ROOT)).replace("\\", "/")
                        zf.write(f, arcname)
                        file_count += 1
                        ch_files += 1
                        total_uncompressed_bytes += f.stat().st_size

            print(f"      + {ch}: {ch_files} files added")

    # Quick integrity check
    with zipfile.ZipFile(zip_path, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"Corrupt file in {zip_path}: {bad}")

    elapsed = time.time() - t0
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"    [OK] {zip_name}: {file_count} files, {size_mb:.1f} MB in {elapsed:.2f}s\n")
    return zip_path


def main() -> int:
    start_time = time.time()
    chapters = get_all_chapters()
    total_chapters = len(chapters)
    print(f"Found {total_chapters} chapters in {CHAPTERS_DIR}")
    print(f"Output folder: {OUTPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Series zip
    series_zip = zip_series()

    # 2. Chapter batches
    batches: list[list[str]] = [
        chapters[i : i + BATCH_SIZE] for i in range(0, total_chapters, BATCH_SIZE)
    ]
    print(f"Created plan: {len(batches)} batches of up to {BATCH_SIZE} chapters each.\n")

    created_zips: list[Path] = [series_zip]
    for idx, batch in enumerate(batches, start=1):
        zip_path = zip_chapter_batch(idx, batch)
        created_zips.append(zip_path)

    total_time = time.time() - start_time
    total_size_mb = sum(p.stat().st_size for p in created_zips) / (1024 * 1024)

    print("=" * 70)
    print("ALL ZIPS COMPLETED SUCCESSFULLY")
    print("=" * 70)
    for z in created_zips:
        size_mb = z.stat().st_size / (1024 * 1024)
        print(f"  {z.name:<35s}  {size_mb:8.2f} MB")
    print("-" * 70)
    print(f"Total: {len(created_zips)} archives, {total_size_mb:.2f} MB in {total_time:.1f}s")
    print(f"Saved to: {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
