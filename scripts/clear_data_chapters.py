"""Script to safely clear completed chapter data, exports, and movies while preserving scaffolding."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def is_junction_or_symlink(path: Path) -> bool:
    if path.is_symlink():
        return True
    if hasattr(path, "is_junction") and path.is_junction():
        return True
    return False


def clear_chapters_dir() -> int:
    ch_dir = DATA_DIR / "chapters"
    if not ch_dir.exists():
        ch_dir.mkdir(parents=True, exist_ok=True)
        return 0

    removed = 0

    # Pass 1: Remove junctions first to avoid traversing targets
    for item in list(ch_dir.iterdir()):
        if item.name == ".gitkeep":
            continue
        if is_junction_or_symlink(item):
            try:
                os.rmdir(item)
                removed += 1
            except OSError:
                try:
                    os.unlink(item)
                    removed += 1
                except OSError as e:
                    print(f"Warning: Failed to unlink junction {item}: {e}")

    # Pass 2: Remove real directories and remaining files
    for item in list(ch_dir.iterdir()):
        if item.name == ".gitkeep":
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
                removed += 1
            else:
                item.unlink(missing_ok=True)
                removed += 1
        except Exception as e:
            print(f"Warning: Failed to delete {item}: {e}")

    # Ensure .gitkeep exists
    (ch_dir / ".gitkeep").touch(exist_ok=True)
    return removed


def clear_subfolder(folder_name: str) -> int:
    folder = DATA_DIR / folder_name
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
        (folder / ".gitkeep").touch(exist_ok=True)
        return 0

    removed = 0
    for item in list(folder.iterdir()):
        if item.name == ".gitkeep":
            continue
        try:
            if is_junction_or_symlink(item):
                os.rmdir(item)
            elif item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
            removed += 1
        except Exception as e:
            print(f"Warning: Failed to delete {item}: {e}")

    (folder / ".gitkeep").touch(exist_ok=True)
    return removed


def clear_root_files() -> int:
    removed = 0
    for item in list(DATA_DIR.iterdir()):
        if item.is_file() and item.name != ".gitkeep":
            try:
                item.unlink(missing_ok=True)
                removed += 1
            except Exception as e:
                print(f"Warning: Failed to delete {item}: {e}")
    (DATA_DIR / ".gitkeep").touch(exist_ok=True)
    return removed


def main():
    print("=" * 70)
    print("MANGA RECAP: CLEARING COMPLETED CHAPTER DATA")
    print("=" * 70)

    total_total, total_used, free_before = shutil.disk_usage(REPO_ROOT)
    print(f"Drive Free Space Before: {free_before / (1024**3):.2f} GB")

    ch_removed = clear_chapters_dir()
    print(f"  - Cleared data/chapters/ ({ch_removed} entries/junctions removed)")

    export_removed = clear_subfolder("export")
    print(f"  - Cleared data/export/ ({export_removed} entries removed)")

    movies_removed = clear_subfolder("movies")
    print(f"  - Cleared data/movies/ ({movies_removed} entries removed)")

    hooks_removed = clear_subfolder("hooks")
    thumbs_removed = clear_subfolder("thumbnails")
    files_removed = clear_root_files()
    print(f"  - Cleared temporary root logs/json files ({files_removed} files removed)")

    # Ensure all scaffolded directories exist with .gitkeep
    for sub in ["chapters", "series", "hooks", "thumbnails"]:
        d = DATA_DIR / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / ".gitkeep").touch(exist_ok=True)

    _, _, free_after = shutil.disk_usage(REPO_ROOT)
    print("\n" + "=" * 70)
    print(f"DATA FOLDER CLEANED SUCCESSFULLY!")
    print(f"Scaffolding preserved: data/chapters, data/series, data/hooks, data/thumbnails")
    print(f"Drive Free Space: {free_after / (1024**3):.2f} GB")
    print("=" * 70)


if __name__ == "__main__":
    main()
