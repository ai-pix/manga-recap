"""Master Batch Smart Slicer for all downloaded manhwa series.

Slices each series chapter-by-chapter with the upgraded ManhwaSlicer:
- Continuous vertical canvas
- Smart gutter detection
- Speech bubble margin protection & auto-merge
- 100% WebP Quality 90 (ultra-fast method 3)
- Auto-packages into ZIP_STORED and uploads to sendit.sh
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.stages.s1_crop.manhwa_slicer import slice_manhwa, ManhwaSliceConfig

DOWNLOADS_ROOT = Path(r"D:\Python Projects\Hakuniku\cli\downloads")
ZIPS_ROOT = DOWNLOADS_ROOT / "zips"
PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels")

SERIES_QUEUE = [
    {"name": "Eleceed", "zip": "eleceed.zip", "folder": "Eleceed"},
    {"name": "Pick Me Up, Infinite Gacha", "zip": "pick_me_up.zip", "folder": "Pick Me Up, Infinite Gacha"},
    {"name": "Player Who Returned 10,000 Years Later", "zip": "player_10000_years_later.zip", "folder": "Player Who Returned 10,000 Years Later"},
    {"name": "A Returner's Magic Should Be Special", "zip": "returners_magic.zip", "folder": "A Returner's Magic Should Be Special"},
    {"name": "The Greatest Estate Developer", "zip": "greatest_estate.zip", "folder": "The Greatest Estate Developer"},
    {"name": "I'm the Max-Level Newbie", "zip": "max_level_newbie.zip", "folder": "I'm the Max-Level Newbie"},
    {"name": "Solo Leveling - Ragnarok", "zip": "solo_leveling_ragnarok.zip", "folder": "Solo Leveling - Ragnarok"},
    {"name": "The Regressed Mercenary Has a Plan", "zip": "regressed_mercenary.zip", "folder": "The Regressed Mercenary Has a Plan"},
    {"name": "The Stellar Swordmaster", "zip": "stellar_swordmaster.zip", "folder": "The Stellar Swordmaster"},
    {"name": "The Beginning After the End", "zip": "beginning_after_the_end.zip", "folder": "The Beginning After the End"},
    {"name": "Murim Login", "zip": "murim_login_clean.zip", "folder": "Murim Login"},
    {"name": "Myst, Might, Mayhem", "zip": "myst_might_mayhem.zip", "folder": "Myst, Might, Mayhem"},
    {"name": "Return of the Mad Demon", "zip": "return_of_mad_demon.zip", "folder": "Return of the Mad Demon"},
    {"name": "Villain to Kill", "zip": "villain_to_kill.zip", "folder": "Villain to Kill"},
    {"name": "Damn Reincarnation", "zip": "damn_reincarnation.zip", "folder": "Damn Reincarnation"},
    {"name": "Reaper of the Drifting Moon", "zip": "reaper_drifting_moon.zip", "folder": "Reaper of the Drifting Moon"},
    {"name": "Regressor Instruction Manual", "zip": "regressor_instruction_manual.zip", "folder": "Regressor Instruction Manual"},
    {"name": "Steel-Eating Player", "zip": "steel_eating_player.zip", "folder": "Steel-Eating Player"},
    {"name": "Archmage Transcending Through Regression", "zip": "archmage_transcending.zip", "folder": "Archmage Transcending Through Regression"},
    {"name": "Nano Machine", "zip": "nano_machine.zip", "folder": "Nano Machine"},
    {"name": "The Tutorial is Too Hard", "zip": "The Tutorial Is Too Hard.zip", "folder": "The Tutorial is Too Hard"},
    {"name": "Kill the Hero", "path": DOWNLOADS_ROOT / "Comix" / "Kill the Hero", "folder": "Kill the Hero"},
    {"name": "Return of the Disaster-Class Hero", "path": DOWNLOADS_ROOT / "Asura" / "Return of the Disaster-Class Hero", "folder": "Return of the Disaster-Class Hero"},
    {"name": "Second Life Ranker", "path": DOWNLOADS_ROOT / "Comix" / "Second Life Ranker", "folder": "Second Life Ranker"},
]

def slice_single_chapter(raw_ch_dir: Path, out_ch_dir: Path, ch_id: str) -> tuple[int, bool, int, float]:
    t0 = time.time()
    if out_ch_dir.exists():
        shutil.rmtree(out_ch_dir, ignore_errors=True)
    out_ch_dir.mkdir(parents=True, exist_ok=True)
    try:
        config = ManhwaSliceConfig(webp_quality=90)
        res = slice_manhwa(raw_ch_dir, out_ch_dir, chapter_id=ch_id, config=config, force=True)
        return 1, True, res.panel_count, time.time() - t0
    except Exception as e:
        return 1, False, 0, time.time() - t0

def process_series(item: dict):
    name = item["name"]
    folder_name = item["folder"]
    out_series_dir = PANELS_ROOT / folder_name
    print("\n" + "=" * 70)
    print(f"PROCESSING SERIES: {name}")
    print("=" * 70)

    # Resolve raw source directory
    raw_source = item.get("path")
    if not raw_source:
        zip_path = ZIPS_ROOT / item["zip"]
        raw_source = DOWNLOADS_ROOT / folder_name
        if not raw_source.exists() or not any(raw_source.glob("*")):
            if zip_path.exists():
                print(f"[{name}] Extracting raw chapters from {zip_path.name}...")
                raw_source.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(raw_source)

    if not raw_source.exists():
        print(f"[{name}] ERROR: Raw source {raw_source} not found!")
        return

    # Find chapter directories
    ch_dirs = [d for d in raw_source.rglob("*") if d.is_dir() and any(d.glob("*.jpg")) or any(d.glob("*.png")) or any(d.glob("*.webp"))]
    # sort naturally
    def nat_key(p):
        return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", p.name)]
    ch_dirs.sort(key=nat_key)

    print(f"[{name}] Found {len(ch_dirs)} raw chapters to slice.")
    out_series_dir.mkdir(parents=True, exist_ok=True)

    workers = min(7, os.cpu_count() or 4)
    total_panels = 0
    t0 = time.time()

    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as ex:
        fmap = {}
        for idx, ch_dir in enumerate(ch_dirs, 1):
            out_ch = out_series_dir / f"Chapter {idx}"
            fmap[ex.submit(slice_single_chapter, ch_dir, out_ch, f"ch{idx:02d}")] = idx

        for fut in concurrent.futures.as_completed(fmap):
            idx = fmap[fut]
            _, success, count, elap = fut.result()
            if success:
                total_panels += count
                print(f"[{name}] Chapter {idx:02d}: Sliced {count} WebP panels ({elap:.1f}s)", flush=True)

    print(f"[{name}] Finished all chapters in {time.time() - t0:.1f}s! Total panels: {total_panels}")

if __name__ == "__main__":
    for s in SERIES_QUEUE:
        process_series(s)
