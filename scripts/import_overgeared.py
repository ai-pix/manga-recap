"""Import Overgeared (Chapters 01-30) from Cocomic directory into pipeline data."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s0_ingest import run as run_ingest

SOURCE_DIR = Path("C:/Users/ravih/OneDrive/Pictures/Cocomic/Overgeared")


def get_chapter_number(name: str) -> int | None:
    match = re.search(r"\d+", name)
    return int(match.group()) if match else None


def main():
    if not SOURCE_DIR.is_dir():
        print(f"Source directory not found: {SOURCE_DIR}")
        return 1

    source_chapters = [d for d in SOURCE_DIR.iterdir() if d.is_dir()]
    # Sort numerically
    source_chapters.sort(key=lambda d: get_chapter_number(d.name) or 0)

    print("=" * 70)
    print(f"IMPORTING OVERGEARED: Found {len(source_chapters)} Chapters")
    print(f"Source: {SOURCE_DIR}")
    print("=" * 70)

    imported = []

    for src_ch in source_chapters:
        num = get_chapter_number(src_ch.name)
        if num is None:
            continue

        ch_id = f"ch{num:02d}"
        full_ch_id = f"overgeared/{ch_id}"
        paths = ChapterPaths.create(full_ch_id)
        paths.ensure_dirs()

        # Gather source images in natural order
        imgs = [
            f
            for f in src_ch.iterdir()
            if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        ]
        imgs.sort(key=lambda x: int("".join(c for c in x.stem if c.isdigit()) or 0))

        # Copy to 00_input
        for idx, img in enumerate(imgs, start=1):
            target = paths.input_dir / f"page_{idx:03d}{img.suffix.lower()}"
            if not target.exists() or target.stat().st_size != img.stat().st_size:
                shutil.copy2(img, target)

        # Run s0_ingest to populate 01_pages
        page_count = run_ingest(paths, force=True)
        print(f"  [{ch_id}] {src_ch.name} -> {page_count} pages ingested in {paths.pages_dir.name}")

        # Also create junction link at data/chapters/overgeared_chXX -> overgeared/chXX
        alias_dir = REPO_ROOT / "data" / "chapters" / f"overgeared_ch{num:02d}"
        if not alias_dir.exists():
            target_rel = paths.root.resolve()
            try:
                subprocess.run(
                    ["cmd", "/c", "mklink", "/J", str(alias_dir), str(target_rel)],
                    capture_output=True,
                    check=True,
                )
            except Exception:
                pass

        imported.append((ch_id, page_count))

    print("\n" + "=" * 70)
    print(f"SUCCESS: Imported {len(imported)} Overgeared Chapters!")
    print(f"Total Pages: {sum(cnt for _, cnt in imported)}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
