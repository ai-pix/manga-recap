"""Download and extract panels for the 5 incoming manhwas from Foxy (chat #404).

Titles:
1. I'm the Max-Level Newbie
2. Solo Leveling: Ragnarok
3. The Regressed Mercenary Has a Plan
4. The Stellar Swordmaster
5. The Beginning After the End
"""

from __future__ import annotations

import concurrent.futures
import shutil
import sys
import time
import zipfile
from pathlib import Path
import cv2
import numpy as np
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from batch_extract_all_manhwa import detect_gutters, natural_sort_key, safe_imread, safe_imwrite

DOWNLOADS_DIR = Path(r"D:\Python Projects\Hakuniku\cli\downloads")
PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels")

TASKS = [
    {
        "name": "I'm the Max-Level Newbie",
        "url": "https://sendit.sh/B1PpK/6kScd.zip",
        "zip_name": "max_level_newbie.zip",
    },
    {
        "name": "Solo Leveling - Ragnarok",
        "url": "https://sendit.sh/fHOJZ/JI3z9.zip",
        "zip_name": "solo_leveling_ragnarok.zip",
    },
    {
        "name": "The Regressed Mercenary Has a Plan",
        "url": "https://sendit.sh/o6PCW/TVhn4.zip",
        "zip_name": "regressed_mercenary.zip",
    },
    {
        "name": "The Stellar Swordmaster",
        "url": "https://sendit.sh/xi6A9/tNDph.zip",
        "zip_name": "stellar_swordmaster.zip",
    },
    {
        "name": "The Beginning After the End",
        "url": "https://sendit.sh/mUtSK/dozBl.zip",
        "zip_name": "beginning_after_the_end.zip",
    },
]


def download_file(url: str, dest_path: Path) -> bool:
    if dest_path.exists() and dest_path.stat().st_size > 1024 * 1024:
        print(f"[Download] {dest_path.name} already exists ({dest_path.stat().st_size / (1024*1024):.1f} MB), skipping.")
        return True
    print(f"[Download] Fetching {dest_path.name} from {url}...", flush=True)
    t0 = time.time()
    try:
        with requests.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total_size = int(r.headers.get("content-length", 0))
            downloaded = 0
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=2 * 1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
        elapsed = time.time() - t0
        mb = dest_path.stat().st_size / (1024 * 1024)
        print(f"[Download] Complete {dest_path.name}: {mb:.1f} MB in {elapsed:.1f}s ({mb/max(elapsed, 0.001):.2f} MB/s)", flush=True)
        return True
    except Exception as e:
        print(f"[Download Error] {dest_path.name}: {e}", flush=True)
        return False


def extract_zip(zip_path: Path, target_dir: Path) -> None:
    print(f"[Unzip] Extracting {zip_path.name} -> {target_dir.name}...", flush=True)
    t0 = time.time()
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(target_dir)
    print(f"[Unzip] Extracted {zip_path.name} in {time.time() - t0:.1f}s.", flush=True)


def extract_chapter_panels(ch_dir: Path, out_ch_dir: Path, min_panel_h: int = 50) -> tuple[int, int]:
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    image_files = []
    for ext in extensions:
        image_files.extend(ch_dir.glob(ext))
    image_files.sort(key=lambda p: natural_sort_key(p.name))

    if not image_files:
        return 0, 0

    panel_idx = 1
    for img_p in image_files:
        img = safe_imread(img_p)
        if img is None:
            continue
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gutters = detect_gutters(gray)

        segments = []
        cur_y = 0
        for gs, ge in gutters:
            if gs - cur_y >= min_panel_h:
                segments.append((cur_y, gs))
            cur_y = ge
        if h - cur_y >= min_panel_h:
            segments.append((cur_y, h))

        if not segments:
            segments = [(0, h)]

        for sy, ey in segments:
            seg_img = img[sy:ey, :]
            if np.std(seg_img) < 5.0 and (ey - sy) < 100:
                continue
            out_name = f"panel_{panel_idx:04d}.png"
            safe_imwrite(out_ch_dir / out_name, seg_img)
            panel_idx += 1

    return len(image_files), panel_idx - 1


def process_series(item: dict) -> tuple[str, int, int]:
    name = item["name"]
    url = item["url"]
    zips_dir = DOWNLOADS_DIR / "zips"
    zip_path = zips_dir / item["zip_name"]
    series_download_dir = DOWNLOADS_DIR / name
    series_panel_dir = PANELS_ROOT / name

    print(f"\n{'='*65}\nSTARTING SERIES: {name}\n{'='*65}", flush=True)
    ok = download_file(url, zip_path)
    if not ok:
        return name, 0, 0

    extract_zip(zip_path, series_download_dir)

    # Locate chapter folders
    all_dirs = [d for d in series_download_dir.rglob("*") if d.is_dir() and any(d.glob("*.webp"))]
    if not all_dirs:
        all_dirs = [d for d in series_download_dir.iterdir() if d.is_dir()]

    all_dirs.sort(key=lambda d: natural_sort_key(d.name))
    print(f"[{name}] Slicing panels across {len(all_dirs)} chapter directories...", flush=True)

    total_pages = 0
    total_panels = 0
    t0 = time.time()
    for idx, ch_dir in enumerate(all_dirs, start=1):
        out_ch = series_panel_dir / f"Chapter {idx}"
        out_ch.mkdir(parents=True, exist_ok=True)
        pages, panels = extract_chapter_panels(ch_dir, out_ch)
        total_pages += pages
        total_panels += panels

    elapsed = time.time() - t0
    print(f"[{name}] COMPLETE: {total_panels} panels, {total_pages} pages in {elapsed:.1f}s!", flush=True)
    return name, total_pages, total_panels


def main():
    print("=" * 70)
    print("BATCH EXTRACTION PIPELINE: 5 INCOMING MANHWAS (Foxy #404)")
    print("Target: D:\\Python Projects\\Hakuniku\\panels")
    print("=" * 70, flush=True)

    t_all = time.time()
    results = []

    # Process each series
    for task in TASKS:
        res = process_series(task)
        results.append(res)

    print("\n" + "=" * 70)
    print("ALL 5 MANHWAS EXTRACTED SUCCESSFULLY!")
    for name, pages, panels in results:
        print(f"  - {name}: {panels} panels across {pages} source pages")
    total_panels = sum(r[2] for r in results)
    print(f"Grand Total: {total_panels} panels extracted in {time.time() - t_all:.1f}s!")
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
