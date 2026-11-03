"""Extract panels for the 10 successfully downloaded new manhwa series into Hakuniku/panels."""

import concurrent.futures
import sys
import time
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from batch_extract_all_manhwa import natural_sort_key
from batch_extract_five_incoming import extract_chapter_panels

ZIPS_DIR = Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips")
DOWNLOADS_DIR = Path(r"D:\Python Projects\Hakuniku\cli\downloads")
PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels")

TASKS_10 = [
    {"name": "Villain to Kill", "zip": "villain_to_kill.zip"},
    {"name": "Return of the Mad Demon", "zip": "return_of_mad_demon.zip"},
    {"name": "Damn Reincarnation", "zip": "damn_reincarnation.zip"},
    {"name": "Regressor Instruction Manual", "zip": "regressor_instruction_manual.zip"},
    {"name": "Myst, Might, Mayhem", "zip": "myst_might_mayhem.zip"},
    {"name": "Nano Machine", "zip": "nano_machine.zip"},
    {"name": "Reaper of the Drifting Moon", "zip": "reaper_drifting_moon.zip"},
    {"name": "Murim Login", "zip": "murim_login_clean.zip"},
    {"name": "Steel-Eating Player", "zip": "steel_eating_player.zip"},
    {"name": "Archmage Transcending Through Regression", "zip": "archmage_transcending.zip"}
]

def extract_one_series(task):
    name = task["name"]
    zip_path = ZIPS_DIR / task["zip"]
    if not zip_path.exists():
        print(f"[{name}] Zip not found: {zip_path.name}")
        return name, 0, 0
        
    extract_dir = DOWNLOADS_DIR / name
    out_panels_dir = PANELS_ROOT / name
    
    print(f"\n[{name}] Unzipping {zip_path.name}...", flush=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
        
    dirs = [d for d in extract_dir.rglob("*") if d.is_dir() and any(d.glob("*.webp"))]
    if not dirs:
        dirs = [d for d in extract_dir.iterdir() if d.is_dir()]
    dirs.sort(key=lambda d: natural_sort_key(d.name))
    
    print(f"[{name}] Extracting panels across {len(dirs)} chapters...", flush=True)
    t0 = time.time()
    total_pages = 0
    total_panels = 0
    
    for idx, ch_dir in enumerate(dirs, start=1):
        out_ch = out_panels_dir / f"Chapter {idx}"
        out_ch.mkdir(parents=True, exist_ok=True)
        pages, panels = extract_chapter_panels(ch_dir, out_ch)
        total_pages += pages
        total_panels += panels
        
    print(f"[{name}] DONE: {total_panels} panels across {total_pages} pages in {time.time() - t0:.1f}s!", flush=True)
    return name, total_pages, total_panels

def main():
    print("=" * 70)
    print("BATCH EXTRACTION: 10 NEW DOWNLOADED MANHWAS")
    print("=" * 70, flush=True)
    
    t_start = time.time()
    results = []
    for t in TASKS_10:
        res = extract_one_series(t)
        results.append(res)
        
    print("\n" + "=" * 70)
    print(f"FINISHED ALL 10 EXTRACTIONS IN {time.time() - t_start:.1f}s!")
    for name, pages, panels in results:
        print(f"  - {name}: {panels} panels across {pages} source pages")
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
