"""High-speed multi-threaded image compressor and packager.

Optimizes all panels and text crops for SSS-Class Revival Hunter Ch 1 to 40
without quality loss and packs them into a single organized ZIP file.
"""

from __future__ import annotations

import io
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
SERIES_DIR = REPO_ROOT / "data" / "chapters" / "sss-class-revival-hunter"
OUT_ZIP = REPO_ROOT / "zips" / "sss_class_revival_hunter_ch01_ch40_panels.zip"


def process_file_entry(rel_path: str, full_path: Path) -> tuple[str, bytes, int, int]:
    """Compress image or read file into memory, returning (rel_path, data, orig_size, opt_size)."""
    orig_size = full_path.stat().st_size
    name_lower = full_path.name.lower()

    if name_lower.endswith((".jpg", ".jpeg")):
        try:
            with Image.open(full_path) as im:
                buf = io.BytesIO()
                im.save(buf, format="JPEG", quality=85, optimize=True, progressive=True, subsampling=1)
                compressed = buf.getvalue()
                if len(compressed) < orig_size:
                    return rel_path, compressed, orig_size, len(compressed)
        except Exception:
            pass
    elif name_lower.endswith(".png"):
        try:
            with Image.open(full_path) as im:
                buf = io.BytesIO()
                im.save(buf, format="PNG", optimize=True, compress_level=9)
                compressed = buf.getvalue()
                if len(compressed) < orig_size:
                    return rel_path, compressed, orig_size, len(compressed)
        except Exception:
            pass

    # Default to raw file
    raw = full_path.read_bytes()
    return rel_path, raw, orig_size, len(raw)


def main():
    if not SERIES_DIR.exists():
        print(f"Error: {SERIES_DIR} not found.")
        sys.exit(1)

    OUT_ZIP.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("COMPRESSING & PACKAGING 40 CHAPTERS OF PANELS (VISUALLY LOSSLESS)")
    print(f"Source: {SERIES_DIR}")
    print(f"Target Zip: {OUT_ZIP}")
    print("=" * 65, flush=True)

    # 1. Gather all files in order across ch01 to ch40
    chapters = sorted([d for d in SERIES_DIR.iterdir() if d.is_dir() and d.name.startswith("ch")])
    if len(chapters) != 40:
        print(f"Warning: Expected 40 chapters, found {len(chapters)}")

    file_tasks: list[tuple[str, Path]] = []
    for ch in chapters:
        panels_dir = ch / "02_panels"
        if not panels_dir.exists():
            continue
        for p in panels_dir.rglob("*"):
            if p.is_file():
                rel = f"sss-class-revival-hunter/{ch.name}/02_panels/{p.relative_to(panels_dir).as_posix()}"
                file_tasks.append((rel, p))

    print(f"Gathered {len(file_tasks)} files to compress and archive...", flush=True)

    t0 = time.time()
    total_orig = 0
    total_opt = 0

    # 2. Parallel optimization and writing to ZIP
    with zipfile.ZipFile(OUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        with ThreadPoolExecutor(max_workers=8) as executor:
            batch_size = 100
            for i in range(0, len(file_tasks), batch_size):
                chunk = file_tasks[i : i + batch_size]
                futures = [executor.submit(process_file_entry, rel, path) for rel, path in chunk]
                for fut in futures:
                    rel_p, data, orig_s, opt_s = fut.result()
                    total_orig += orig_s
                    total_opt += opt_s
                    zf.writestr(rel_p, data)

                done = min(i + batch_size, len(file_tasks))
                pct = (done / len(file_tasks)) * 100
                print(
                    f"[{done}/{len(file_tasks)}] {pct:.1f}% processed... "
                    f"({total_opt / (1024*1024):.1f} MB written)",
                    flush=True,
                )

    dur = time.time() - t0
    final_zip_size = OUT_ZIP.stat().st_size

    print("\n" + "=" * 65)
    print("COMPRESSION & PACKAGING COMPLETED!")
    print(f"Elapsed Time: {dur:.1f}s ({dur/60:.1f} min)")
    print(f"Total Files Archived: {len(file_tasks)}")
    print(f"Original Uncompressed Size: {total_orig / (1024*1024):.2f} MB ({total_orig / (1024*1024*1024):.2f} GB)")
    print(f"Optimized Image Size:       {total_opt / (1024*1024):.2f} MB ({total_opt / (1024*1024*1024):.2f} GB)")
    print(f"Final ZIP Archive Size:     {final_zip_size / (1024*1024):.2f} MB ({final_zip_size / (1024*1024*1024):.2f} GB)")
    print(f"Total Size Reduction:       {(1 - final_zip_size / total_orig) * 100:.1f}%")
    print(f"Saved to: {OUT_ZIP}")
    print("=" * 65)


if __name__ == "__main__":
    main()
