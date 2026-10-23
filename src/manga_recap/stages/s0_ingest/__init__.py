"""Stage 0: ingest raw chapter source into normalised page images.

Accepts a folder of images or a PDF and writes one PNG per page into
`01_pages/`, named so that natural sort matches reading order. Getting this
wrong reorders the whole chapter, so the naming is deliberate and the sort is
natural, not lexicographic.
"""

from __future__ import annotations

from pathlib import Path

from ...core.logging import get_logger
from ...core.paths import ChapterPaths

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
PDF_SUFFIXES = {".pdf"}

_log = get_logger("stages.s0_ingest")


def run(paths: ChapterPaths, *, force: bool = False) -> int:
    """Populate `01_pages/`. Returns the page count.

    Idempotent: existing pages are kept unless `force` is set.
    """
    paths.ensure_dirs()

    existing = paths.page_images()
    if existing and not force:
        _log.info("Stage 0: %d pages already ingested, skipping", len(existing))
        return len(existing)

    if force and paths.pages_dir.exists():
        for stale in paths.pages_dir.iterdir():
            if stale.is_file():
                stale.unlink()

    sources = _collect_sources(paths.input_dir)
    if not sources:
        raise FileNotFoundError(
            f"No source pages found in {paths.input_dir}. Put images or a PDF there, "
            "or pass --input to `manga ingest` to point at a folder."
        )

    if len(sources) == 1 and sources[0].suffix.lower() in PDF_SUFFIXES:
        count = _render_pdf(sources[0], paths.pages_dir)
    else:
        count = _copy_images(sources, paths.pages_dir)

    _log.info("Stage 0: ingested %d pages", count)
    return count


def _collect_sources(input_dir: Path) -> list[Path]:
    """Find every usable source file, PDFs included, in natural order."""
    if not input_dir.exists():
        return []
    found: list[Path] = []
    for path in input_dir.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES or suffix in PDF_SUFFIXES:
            found.append(path)
    from ...core.paths import _natural_key

    return sorted(found, key=_natural_key)


def _copy_images(sources: list[Path], pages_dir: Path) -> int:
    """Normalise image sources to page_001.png, page_002.png, ..."""
    from PIL import Image

    count = 0
    for index, source in enumerate(sources, start=1):
        target = pages_dir / f"page_{index:03d}.png"
        try:
            with Image.open(source) as image:
                # Flatten transparency onto white: manga pages are line art and
                # a transparent background would break panel detection later.
                if image.mode in ("RGBA", "LA", "P"):
                    image = image.convert("RGBA")
                    canvas = Image.new("RGB", image.size, (255, 255, 255))
                    canvas.paste(image, mask=image.split()[-1])
                    image = canvas
                else:
                    image = image.convert("RGB")
                image.save(target, "PNG", optimize=True)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Could not read image {source}: {exc}") from exc
        count += 1
    return count


def _render_pdf(pdf_path: Path, pages_dir: Path) -> int:
    """Rasterise a PDF into one PNG per page."""
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ImportError(
            "PyMuPDF is required to read PDFs. Install it with `pip install pymupdf`."
        ) from exc

    count = 0
    with fitz.open(pdf_path) as document:
        for index, page in enumerate(document, start=1):
            # 200 dpi suits manga line art and keeps files a sane size.
            pixmap = page.get_pixmap(dpi=200, alpha=False)
            pixmap.save(pages_dir / f"page_{index:03d}.png")
            count += 1
    return count
