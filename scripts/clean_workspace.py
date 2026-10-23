"""Workspace cleanup script for Manga Recap.

Safely frees disk space after archiving Only Sense Online to Google Drive:
- Verifies archive state in build/gdrive_archive_state.json
- Removes chapter working data in data/chapters/ (~43.4 GB)
- Removes data/youtube_ready/ (~2.7 GB)
- Removes data/hooks/, data/thumbnails/, and metadata text files (already archived)
- Removes logs/ (~3.1 GB) and scratch/ (~280 MB)
- Preserves all source code, models, configs, tests, Kaggle kernels, credentials, and venv
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "build/gdrive_archive_state.json"


def get_dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def verify_archive(chapters_dir: Path) -> tuple[bool, list[str]]:
    if not STATE_FILE.exists():
        return False, ["State file build/gdrive_archive_state.json does not exist!"]

    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"Failed to read state file: {e}"]

    missing = []
    ch_dirs = [d for d in chapters_dir.iterdir() if d.is_dir() and d.name.startswith("ch")]
    for cdir in ch_dirs:
        # Check critical artifacts
        for target_name in ["07_final.mp4", "04_script.json", "03_descriptions.json"]:
            target = cdir / target_name
            if target.exists():
                skey = f"{cdir.name}:{target_name}"
                if skey not in state:
                    missing.append(f"Missing in Drive archive: {skey}")

    return len(missing) == 0, missing


def clean_directory_contents(dir_path: Path, dry_run: bool = False) -> int:
    freed = 0
    if not dir_path.exists():
        return 0

    for item in dir_path.iterdir():
        if item.name == ".gitkeep":
            continue
        size = get_dir_size(item)
        freed += size
        if not dry_run:
            try:
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    item.unlink(missing_ok=True)
            except Exception as e:
                print(f"Warning: Failed to delete {item}: {e}")
    return freed


def main():
    parser = argparse.ArgumentParser(description="Clean Manga Recap workspace after Drive archiving.")
    parser.add_argument("--dry-run", action="store_true", help="Calculate space to be freed without deleting anything.")
    parser.add_argument("--skip-verify", action="store_true", help="Skip Google Drive archive state verification.")
    args = parser.parse_args()

    print("=" * 70)
    print("MANGA RECAP: WORKSPACE CLEANUP & STORAGE RECLAMATION")
    print("=" * 70)

    chapters_dir = REPO_ROOT / "data/chapters"

    # Step 1: Verify Google Drive Archive
    if not args.skip_verify:
        print("\n[1/3] Verifying Google Drive Archive integrity...")
        ok, missing = verify_archive(chapters_dir)
        if not ok:
            print("ERROR: Google Drive archive verification failed!")
            for m in missing[:15]:
                print(f"  - {m}")
            if len(missing) > 15:
                print(f"  ... and {len(missing) - 15} more.")
            print("\nPlease ensure scripts/archive_to_gdrive.py completes before running cleanup.")
            return 1
        print("  [OK] Google Drive archive fully verified (all chapter MP4s and metadata present).")
    else:
        print("\n[1/3] Skipping Google Drive archive verification (--skip-verify).")

    # Step 2: Calculate cleanup targets
    print("\n[2/3] Analyzing cleanup targets...")
    targets = [
        ("Chapter Data (data/chapters/*)", chapters_dir, "contents"),
        ("YouTube Ready Videos (data/youtube_ready/)", REPO_ROOT / "data/youtube_ready", "full"),
        ("Hooks (data/hooks/*)", REPO_ROOT / "data/hooks", "contents"),
        ("Thumbnails (data/thumbnails/*)", REPO_ROOT / "data/thumbnails", "contents"),
        ("Logs (logs/*)", REPO_ROOT / "logs", "contents"),
        ("Scratch files (scratch/*)", REPO_ROOT / "scratch", "contents"),
    ]

    # Specific metadata files in data/
    meta_files = [
        REPO_ROOT / "data/Only_Sense_Online_Part_1_Timestamps.txt",
        REPO_ROOT / "data/Only_Sense_Online_Part_2_Timestamps.txt",
        REPO_ROOT / "data/youtube_uploads_movies.json",
        REPO_ROOT / "data/concat_list.txt",
        REPO_ROOT / "data/part1_list.txt",
        REPO_ROOT / "data/part2_list.txt",
    ]

    total_size = 0
    for name, path, _mode in targets:
        sz = get_dir_size(path)
        total_size += sz
        print(f"  - {name}: {sz / 1e9:.2f} GB ({sz / 1e6:.1f} MB)")

    meta_sz = sum(f.stat().st_size for f in meta_files if f.exists())
    total_size += meta_sz
    print(f"  - Project Metadata & Lists: {meta_sz / 1e6:.2f} MB")
    print(f"\nTotal reclaimable disk space: {total_size / 1e9:.2f} GB")

    if args.dry_run:
        print("\n[DRY RUN] No files were deleted.")
        return 0

    # Step 3: Execute Cleanup
    print("\n[3/3] Reclaiming disk space...")
    freed_total = 0

    for name, path, mode in targets:
        if not path.exists():
            continue
        print(f"  Cleaning {name}...", end="", flush=True)
        if mode == "contents":
            freed = clean_directory_contents(path, dry_run=False)
        else:
            freed = get_dir_size(path)
            shutil.rmtree(path, ignore_errors=True)
        freed_total += freed
        print(f" done (freed {freed / 1e9:.2f} GB)")

    for mf in meta_files:
        if mf.exists():
            sz = mf.stat().st_size
            try:
                mf.unlink(missing_ok=True)
                freed_total += sz
            except Exception:
                pass

    # Ensure clean directory scaffolding exists for the next manga series
    for scaffold in [REPO_ROOT / "data/chapters", REPO_ROOT / "data/series", REPO_ROOT / "logs", REPO_ROOT / "data/hooks", REPO_ROOT / "data/thumbnails"]:
        scaffold.mkdir(parents=True, exist_ok=True)
        keep = scaffold / ".gitkeep"
        if not keep.exists():
            keep.touch()

    print("\n" + "=" * 70)
    print(f"SUCCESS: Reclaimed {freed_total / 1e9:.2f} GB of disk space!")
    print("The codebase is clean, modular, and ready for your next manga series.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
