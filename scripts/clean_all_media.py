"""Script to safely remove all media files (videos, audio, images, archives) to reclaim disk space.

Preserves:
- All source code, configs, schemas, tests, documentation
- All JSON/text metadata (03_descriptions.json, 04_script.json, 06_timeline.json,
  panel_index.json, manifests, summaries, series bibles, prompts)
- Directory scaffolding (.gitkeep)
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MEDIA_EXTENSIONS = {
    # Video
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".flv",
    ".webm",
    # Audio
    ".wav",
    ".mp3",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
    ".gif",
    ".tiff",
    # Archives
    ".zip",
    ".tar",
    ".gz",
    ".tgz",
    ".rar",
    ".7z",
    # Codec bitstreams
    ".h264",
    ".hevc",
}

TARGET_DIRS = [
    REPO_ROOT / "data",
    REPO_ROOT / "build",
    REPO_ROOT / "zips",
    REPO_ROOT / "app/data",
]


def clean_media(dry_run: bool = False) -> tuple[int, int]:
    total_freed = 0
    total_files = 0

    for target_dir in TARGET_DIRS:
        if not target_dir.exists():
            continue

        for root, dirs, files in os.walk(target_dir, topdown=False):
            root_path = Path(root)

            # Delete media files
            for fname in files:
                fpath = root_path / fname
                ext = fpath.suffix.lower()

                if ext in MEDIA_EXTENSIONS and fname != ".gitkeep":
                    try:
                        sz = fpath.stat().st_size
                        total_freed += sz
                        total_files += 1
                        if not dry_run:
                            fpath.unlink()
                    except OSError as e:
                        print(f"Error removing {fpath}: {e}")

            # Remove empty directory if not a scaffolded root
            if not dry_run and root_path not in TARGET_DIRS:
                try:
                    remaining = list(root_path.iterdir())
                    if not remaining:
                        root_path.rmdir()
                except OSError:
                    pass

    return total_files, total_freed


def main():
    parser = argparse.ArgumentParser(description="Purge all media files across workspace.")
    parser.add_argument("--dry-run", action="store_true", help="Report without deleting.")
    args = parser.parse_args()

    total, used, free_before = shutil.disk_usage(REPO_ROOT)
    print("=" * 70)
    print("MANGA RECAP: MEDIA PURGE & DISK SPACE RECLAMATION")
    print(f"Drive Free Space Before: {free_before / (1024**3):.2f} GB")
    print("=" * 70)

    count, bytes_freed = clean_media(dry_run=args.dry_run)

    print(f"\nFiles {'identified' if args.dry_run else 'deleted'}: {count:,}")
    print(f"Space {'reclaimable' if args.dry_run else 'reclaimed'}: {bytes_freed / (1024**3):.2f} GB ({bytes_freed / (1024**2):.2f} MB)")

    if not args.dry_run:
        _, _, free_after = shutil.disk_usage(REPO_ROOT)
        print(f"Drive Free Space After:  {free_after / (1024**3):.2f} GB (+{(free_after - free_before) / (1024**3):.2f} GB)")
    print("=" * 70)


if __name__ == "__main__":
    main()
