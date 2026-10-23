"""Filesystem layout for a chapter run.

Every stage reads and writes inside exactly one chapter directory, and the
numbered prefixes keep the pipeline auditable at a glance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Repo root: src/manga_recap/core/paths.py -> parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]

# Directory names inside a chapter, in pipeline order.
INPUT_DIR = "00_input"
PAGES_DIR = "01_pages"
PANELS_DIR = "02_panels"
DESCRIPTIONS_FILE = "03_descriptions.json"
SCRIPT_FILE = "04_script.json"
NARRATION_FILE = "05_narration.wav"
TIMELINE_FILE = "06_timeline.json"
FINAL_FILE = "07_final.mp4"

# Sidecar artifacts, written by Kaggle kernels and downloaded alongside the
# primary outputs.
ALIGNMENT_DEBUG_FILE = "06_alignment_debug.json"
RENDER_MANIFEST_FILE = "07_render_manifest.json"
# Which panel was on screen while each clause was spoken, with the measured
# drift between the video and the narration.
SYNC_REPORT_FILE = "07_sync_report.json"

DEBUG_DIRNAME = "_debug"
# Native-resolution speech-bubble crops. Kept in their own subdirectory so
# they never leak into the panel list that later stages iterate over.
TEXT_DIRNAME = "_text"


@dataclass(frozen=True)
class ChapterPaths:
    """All resolved paths for one chapter.

    Stages take this object rather than juggling string paths, which keeps the
    on-disk contract in a single place.
    """

    chapter_id: str
    data_dir: Path

    @classmethod
    def create(cls, chapter_id: str, data_dir: Path | str | None = None) -> ChapterPaths:
        base = Path(data_dir) if data_dir else REPO_ROOT / "data" / "chapters"
        return cls(chapter_id=chapter_id, data_dir=Path(base).resolve())

    @property
    def root(self) -> Path:
        return self.data_dir / self.chapter_id

    @property
    def input_dir(self) -> Path:
        return self.root / INPUT_DIR

    @property
    def pages_dir(self) -> Path:
        return self.root / PAGES_DIR

    @property
    def panels_dir(self) -> Path:
        return self.root / PANELS_DIR

    @property
    def panel_debug_dir(self) -> Path:
        return self.panels_dir / DEBUG_DIRNAME

    @property
    def panel_text_dir(self) -> Path:
        return self.panels_dir / TEXT_DIRNAME

    @property
    def descriptions_file(self) -> Path:
        return self.root / DESCRIPTIONS_FILE

    @property
    def script_file(self) -> Path:
        return self.root / SCRIPT_FILE

    @property
    def narration_file(self) -> Path:
        return self.root / NARRATION_FILE

    @property
    def timeline_file(self) -> Path:
        return self.root / TIMELINE_FILE

    @property
    def alignment_debug_file(self) -> Path:
        return self.root / ALIGNMENT_DEBUG_FILE

    @property
    def final_file(self) -> Path:
        return self.root / FINAL_FILE

    @property
    def render_manifest_file(self) -> Path:
        return self.root / RENDER_MANIFEST_FILE

    @property
    def sync_report_file(self) -> Path:
        return self.root / SYNC_REPORT_FILE

    def page_images(self) -> list[Path]:
        """Page images in natural filename order (page_2 before page_10)."""
        return sorted_pages(self.pages_dir)

    def panel_images(self) -> list[Path]:
        """Panel crops in reading order (panel_001 before panel_002).

        The `_debug` and `_text` subdirectories are excluded. This matters for
        `_text` specifically: its files are named `panel_0001_text.png`, so
        without the exclusion a bubble crop would be mistaken for a second
        panel and narrated as one.
        """
        return sorted_pages(
            self.panels_dir, exclude_dirs={DEBUG_DIRNAME, TEXT_DIRNAME}
        )

    def panel_text_images(self) -> list[Path]:
        """Native-resolution speech-bubble crops, in reading order."""
        return sorted_pages(self.panel_text_dir)

    def ensure_dirs(self) -> None:
        for directory in (self.input_dir, self.pages_dir, self.panels_dir):
            directory.mkdir(parents=True, exist_ok=True)


def _natural_key(path: Path) -> list:
    """Sort key that compares embedded integers numerically.

    Plain string sorting puts page_10 before page_2, which silently reorders a
    chapter and corrupts reading order.
    """
    import re

    parts = re.split(r"(\d+)", path.name.lower())
    return [int(part) if part.isdigit() else part for part in parts]


def sorted_pages(directory: Path, exclude_dirs: set[str] | None = None) -> list[Path]:
    """List image files in `directory` using natural ordering.

    Debug subdirectories and non-image files are skipped.
    """
    if not directory.exists():
        return []
    exclude = exclude_dirs or set()
    suffix_map = {
        ".png": ".png",
        ".jpg": ".jpg",
        ".jpeg": ".jpg",
        ".webp": ".webp",
    }
    found: dict[str, Path] = {}
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if exclude & set(path.relative_to(directory).parts[:-1]):
            continue
        suffix = suffix_map.get(path.suffix.lower())
        if suffix is None:
            continue
        # Deduplicate on the normalised suffix so page.png and page.jpg of the
        # same base name cannot both land in the list.
        found.setdefault(path.stem, path)
    return sorted(found.values(), key=_natural_key)


def repo_path(relative: str) -> Path:
    """Resolve a repo-relative path, allowing config overrides."""
    candidate = Path(relative)
    return candidate if candidate.is_absolute() else (REPO_ROOT / candidate)
