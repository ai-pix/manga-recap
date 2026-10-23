"""Crop panel boxes out of page images and write the panel index.

Three crops can come out of a panel. The first is the panel itself, downscaled
for upload and for the video. The second is a tight, native-resolution crop of
the speech bubbles alone, which exists because panel text is usually only 8-12
pixels tall once the panel has been scaled down, and a vision model asked to
read 8 pixels of text returns `[illegible]` often enough that the recap loses the
reason anything happens. The third concern is content that is not a rectangle at
all: a bubble drawn across a border, a hand breaking the frame. Boxes are grown
to hold the ink that escapes them, measured from the pixels rather than assumed
from the box.

The panel box is also grown to contain its own speech bubbles before cropping.
A fixed padding of a few pixels is not enough: a bubble drawn across a panel
border is normal in manga, and clipping it mid-glyph destroys the one piece of
information the narrator cannot invent its way around.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

from ...core.logging import get_logger
from ...core.schema import (
    BBox,
    PanelIndex,
    PanelIndexFile,
    PanelSource,
)
from .inkmask import content_bounds, missing_panel_candidates, trace_outlines

_log = get_logger("stages.s1_crop")

PANEL_FILENAME = "panel_{reading_order:04d}"
TEXT_FILENAME = "panel_{reading_order:04d}_text"


def panel_id_for(reading_order: int) -> str:
    return PANEL_FILENAME.format(reading_order=reading_order)


@dataclass
class CropStats:
    page_count: int = 0
    panel_count: int = 0
    text_crop_count: int = 0
    grown_panels: int = 0
    recovered_panels: int = 0
    pages_with_no_panels: list[str] = field(default_factory=list)


def crop_chapter(
    page_images: list[Path],
    panels_dir: Path,
    *,
    detector,
    crop_config: dict,
    opencv_settings: dict | None = None,
    text_dir: Path | None = None,
    force: bool = False,
) -> PanelIndexFile:
    """Detect, order, crop and index every panel in the chapter.

    `detector` is a callable `detect(page_path) -> DetectionResult`, so this
    function does not care which detector is in use.
    """
    from .ordering import order_across_pages

    panels_dir.mkdir(parents=True, exist_ok=True)
    if text_dir is not None:
        text_dir.mkdir(parents=True, exist_ok=True)
    if force:
        for stale in panels_dir.glob("panel_*"):
            stale.unlink()
        if text_dir is not None:
            for stale in text_dir.glob("panel_*"):
                stale.unlink()

    union_text = bool(crop_config.get("union_text_boxes", True))
    text_min_overlap = float(crop_config.get("text_min_overlap", 0.15))
    write_text_crops = bool(crop_config.get("write_text_crops", True))
    ink = crop_config.get("ink", {}) or {}
    use_ink = bool(ink.get("enabled", True))
    max_growth = int(ink.get("max_growth_px", 40))
    band_px = int(ink.get("band_px", 8))
    min_coverage = float(ink.get("min_perimeter_coverage", 0.8))
    max_area_ratio = float(ink.get("max_contour_area_ratio", 2.5))
    auto_add = bool(ink.get("auto_add_candidates", False))
    min_candidate_ink = float(ink.get("min_candidate_ink_ratio", 0.02))
    mask_settings = {
        "paper_percentile": int(ink.get("paper_percentile", 85)),
        "paper_min_level": int(ink.get("paper_min_level", 180)),
        "paper_spread": int(ink.get("paper_spread", 20)),
        "barrier_level": int(ink.get("barrier_level", 100)),
        "barrier_spread": int(ink.get("barrier_spread", 40)),
    }
    tie_margin = int(ink.get("tie_margin_px", 8))
    erode_px = int(ink.get("candidate_erode_px", 12))
    trace_settings = {
        "band_px": band_px,
        "min_coverage": min_coverage,
        "max_area_ratio": max_area_ratio,
        "max_growth": max_growth,
        "tie_margin": tie_margin,
    }

    # Detect on every page first, then assign reading order across the whole
    # chapter. Per-page order would be fine, but doing it in one pass keeps the
    # numbering a single monotonic sequence.
    detections: list[list[BBox]] = []
    page_texts: list[list[BBox]] = []
    sources: list[PanelSource] = []
    page_heights: list[int] = []
    for page in page_images:
        result = detector(page)
        detections.append(result.boxes)
        page_texts.append(list(result.text_boxes))
        sources.append(result.source)
        with Image.open(page) as handle:
            page_heights.append(handle.size[1])
        _log.debug(
            "Detected %d panels and %d text regions on %s",
            len(result.boxes),
            len(result.text_boxes),
            page.name,
        )

    # Second opinion on the pages the detector walked past. Added to the
    # detection list before reading order is assigned, so a recovered panel is
    # numbered like any other rather than appended at the end of the chapter.
    if use_ink:
        detections, candidates = _recover_panels(
            page_images, detections, min_candidate_ink, erode_px,
            mask_settings, auto_add,
        )

    right_to_left = str(crop_config.get("reading_direction", "rtl")).lower() == "rtl"
    # Ordering runs on the raw detections, not the text-expanded boxes. Growing
    # a box by the width of a bubble that overhangs it must not be able to move
    # a panel into a different row.
    all_ranks = order_across_pages(
        detections,
        right_to_left=right_to_left,
        row_top_tolerance=float(crop_config.get("row_top_tolerance", 0.05)),
        page_heights=page_heights,
    )

    pad_floor = int(crop_config.get("padding_px", 6))
    pad_ratio = float(crop_config.get("padding_ratio", 0.02))
    pad_min = int(crop_config.get("padding_min_px", 8))
    pad_max = int(crop_config.get("padding_max_px", 40))
    max_edge = int(crop_config.get("max_panel_edge", 1400))
    text_max_edge = int(crop_config.get("text_crop_max_edge", 2000))

    entries: list[PanelIndex] = []
    content_boxes: dict[int, BBox] = {}
    stats = CropStats()
    cursor = 0

    for page_index, page_path in enumerate(page_images):
        with Image.open(page_path) as page_image:
            page_width, page_height = page_image.size
            boxes = detections[page_index]
            texts = page_texts[page_index]

            masks = _masks_for(page_image, mask_settings) if use_ink else None
            traced: dict[tuple[int, int, int, int], BBox] = {}
            if masks is not None:
                drawn = content_bounds(masks.content, page_width, page_height)
                if drawn is not None:
                    content_boxes[page_index + 1] = drawn
                # Every panel on the page is traced from one contour pass.
                traced = trace_outlines(
                    masks, boxes, page_width, page_height, **trace_settings
                )

            if not boxes:
                stats.pages_with_no_panels.append(page_path.name)
                _log.warning("No panels detected on %s", page_path.name)
                continue

            # Order within the page, by the ranks assigned above.
            page_ranks = all_ranks[cursor : cursor + len(boxes)]
            cursor += len(boxes)

            for box, rank in sorted(zip(boxes, page_ranks, strict=True), key=lambda pair: pair[1]):
                own_texts = (
                    _texts_for(box, texts, min_overlap=text_min_overlap) if union_text else []
                )
                # Text boxes first, so a bubble the detector found is already
                # inside and the trace only has to find what it missed.
                base = BBox.union_all([box, *own_texts]) or box
                grown = traced.get((base.x1, base.y1, base.x2, base.y2), base)
                if grown != base:
                    stats.grown_panels += 1
                    _log.debug(
                        "%s: %s traced out to %s",
                        page_path.name,
                        panel_id_for(rank),
                        grown.to_xywh(),
                    )

                index_on_page = sum(1 for e in entries if e.page_number == page_index + 1) + 1
                panel_id = PANEL_FILENAME.format(reading_order=rank)
                out_path = panels_dir / f"{panel_id}.png"

                padded = _pad(
                    grown,
                    page_width,
                    page_height,
                    floor_px=pad_floor,
                    ratio=pad_ratio,
                    min_px=pad_min,
                    max_px=pad_max,
                )
                crop_and_save(page_image, padded, out_path, max_edge)

                text_image_path = ""
                if own_texts and write_text_crops and text_dir is not None:
                    text_image_path = _write_text_crop(
                        page_image,
                        own_texts,
                        page_width,
                        page_height,
                        text_dir,
                        text_max_edge,
                        rank,
                        panels_dir.name,
                    )
                    stats.text_crop_count += 1

                entries.append(
                    PanelIndex(
                        panel_id=panel_id,
                        page_number=page_index + 1,
                        index_on_page=index_on_page,
                        reading_order=rank,
                        bbox=padded,
                        image_path=f"{panels_dir.name}/{out_path.name}",
                        source=sources[page_index],
                        page_width=page_width,
                        page_height=page_height,
                        text_boxes=own_texts,
                        text_image_path=text_image_path,
                    )
                )

    _mark_nested(entries)

    stats.page_count = len(page_images)
    stats.panel_count = len(entries)
    if stats.text_crop_count:
        _log.info(
            "Stage 1: wrote %d native-resolution text crop(s) for transcription",
            stats.text_crop_count,
        )
    if stats.grown_panels:
        _log.info(
            "Stage 1: traced %d panel outline(s) past their detected box",
            stats.grown_panels,
        )

    return PanelIndexFile(
        chapter_id="",  # filled in by the caller
        page_count=stats.page_count,
        panel_count=stats.panel_count,
        created_at=_now(),
        panels=entries,
        page_text_boxes={
            number: list(boxes)
            for number, boxes in enumerate(page_texts, start=1)
            if boxes
        },
        page_content_bbox=content_boxes,
        page_missing_candidates=candidates,
    )


def crop_and_save(page_image: Image.Image, box: BBox, out_path: Path, max_edge: int) -> None:
    """Crop one panel and save it as PNG, downscaled to fit `max_edge`."""
    panel = page_image.crop((box.x1, box.y1, box.x2, box.y2))

    longest = max(panel.size)
    if max_edge > 0 and longest > max_edge:
        scale = max_edge / longest
        panel = panel.resize(
            (max(1, int(panel.width * scale)), max(1, int(panel.height * scale))),
            Image.LANCZOS,
        )

    if panel.mode not in ("RGB", "L"):
        panel = panel.convert("RGB")
    panel.save(out_path, "PNG", optimize=True)


def _masks_for(page_image: Image.Image, settings: dict):
    """Paper/ink/content masks for one page, or None if it cannot be made."""
    from .inkmask import page_masks

    return page_masks(np.asarray(page_image.convert("RGB")), **settings)


def _recover_panels(
    page_images: list[Path],
    detections: list[list[BBox]],
    min_candidate_ink: float,
    erode_px: int,
    mask_settings: dict,
    auto_add: bool,
) -> tuple[list[list[BBox]], dict[int, list[BBox]]]:
    """Find panels the detector walked past, from ink no box accounts for.

    Always reports what it found, whether or not it also adds it. A panel
    bleeding off the edge of the page and artwork spilling between two bordered
    panels produce identical leftover ink, so the log and the contact sheet are
    the audit trail for a decision that a human may want to reverse.
    """

    candidates: dict[int, list[BBox]] = {}
    for position, page in enumerate(page_images):
        if not detections[position]:
            continue
        with Image.open(page) as image:
            masks = _masks_for(image, mask_settings)
            if masks is None:
                continue
            found = missing_panel_candidates(
                masks,
                detections[position],
                image.size[0],
                image.size[1],
                min_ink_ratio=min_candidate_ink,
                erode_px=erode_px,
            )
        if not found:
            continue

        number = position + 1
        candidates[number] = found
        _log.info(
            "%s: %d unaccounted ink region(s)%s: %s",
            page.name,
            len(found),
            " recovered as panels" if auto_add else " may be missed panels",
            [b.to_xywh() for b in found[:4]],
        )
        if auto_add:
            detections[position] = list(detections[position]) + found
    return detections, candidates


def _texts_for(panel: BBox, texts: list[BBox], *, min_overlap: float) -> list[BBox]:
    """Text regions that belong to this panel.

    Two tests, because a bubble can sit either wholly inside a panel or
    deliberately straddle a border and belong to both of its neighbours. A
    region centred inside the panel always counts; a region that only partly
    overlaps still counts once enough of it is inside, because the alternative
    is a crop that severs the sentence in half.
    """
    found: list[BBox] = []
    for text in texts:
        if text.center_inside(panel) or panel.contains_ratio(text) >= min_overlap:
            found.append(text)
    return found


def _write_text_crop(
    page_image: Image.Image,
    texts: list[BBox],
    page_width: int,
    page_height: int,
    text_dir: Path,
    max_edge: int,
    reading_order: int,
    panels_dir_name: str,
) -> str:
    """Save a native-resolution crop of a panel's text regions.

    No downscaling beyond `max_edge`, because legibility is the entire point.
    Padding is proportionally generous so the bubble outline survives: the text
    box came from inference on a downscaled page, so its edges are approximate.
    """
    tight = BBox.union_all(texts)
    if tight is None:
        return ""
    box = _pad(tight, page_width, page_height, floor_px=4, ratio=0.06, min_px=4, max_px=24)
    out_path = text_dir / f"{TEXT_FILENAME.format(reading_order=reading_order)}.png"
    crop_and_save(page_image, box, out_path, max_edge)
    return f"{panels_dir_name}/{text_dir.name}/{out_path.name}"


def _mark_nested(entries: list[PanelIndex], *, threshold: float = 0.9) -> None:
    """Flag panels that sit inside a larger panel on the same page.

    These are kept, not merged. A panel drawn inside another one is a real
    panel with its own content, and collapsing it would drop that content from
    the chapter.
    """
    by_page: dict[int, list[PanelIndex]] = {}
    for entry in entries:
        by_page.setdefault(entry.page_number, []).append(entry)

    for panels in by_page.values():
        for entry in panels:
            best_id, best_ratio = "", 0.0
            for other in panels:
                if other.panel_id == entry.panel_id:
                    continue
                if other.bbox.area <= entry.bbox.area:
                    continue
                ratio = other.bbox.contains_ratio(entry.bbox)
                if ratio > best_ratio:
                    best_id, best_ratio = other.panel_id, ratio
            if best_ratio >= threshold:
                entry.nested_in = best_id
                _log.info("%s is nested inside %s", entry.panel_id, best_id)


def _pad(
    box: BBox,
    page_width: int,
    page_height: int,
    *,
    floor_px: int,
    ratio: float,
    min_px: int,
    max_px: int,
) -> BBox:
    """Grow a box by a margin proportional to its own size, clamped to the page.

    A flat padding is wrong in both directions. Six pixels is generous on a
    100-pixel panel and negligible on a 700-pixel one, so a fixed value
    under-pads exactly the large panels where an overhanging bubble is most
    likely and the crop is most visible. `floor_px` is the configured absolute
    minimum, kept for backwards compatibility with a flat `crop.padding_px`.
    """
    pad = int(round(ratio * max(box.width, box.height)))
    pad = max(pad, min_px, floor_px)
    pad = min(pad, max_px)
    if pad <= 0:
        return box
    return BBox(
        x1=max(0, box.x1 - pad),
        y1=max(0, box.y1 - pad),
        x2=min(page_width, box.x2 + pad),
        y2=min(page_height, box.y2 + pad),
    )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
