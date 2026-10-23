"""Ink-based page geometry, for the content that is not a rectangle.

YOLO returns rectangles because most manga panels are rectangles. The pages that
break that convention are exactly the ones that lose content: a bubble drawn
across a border, a hand breaking the frame, a full-bleed panel with no border at
all. On those pages, box coordinates cannot tell you anything, so this module
measures the ink directly.

Two masks come out of a page, from two deliberately different thresholds.

`content` is everything that is not page background: ink, plus white enclosed by
ink. A speech bubble's white interior counts as content, because the bubble
outline encloses it. That makes the content extent the true drawn area of the
page, which is the only honest denominator for "did we detect enough panels".

`ink` is dark and unsaturated: strokes. Paper and line art are told apart by
channel spread as much as by brightness, because on a colour page a pale panel
background is bright but strongly tinted, and a dark coloured panel is dark but
strongly tinted. Neither is a stroke, and a pure luminance test confuses both for
one.

## Finding where a panel really ends

A panel's drawn border is a connected stroke, and the border is connected to
anything that broke through it. So the panel's true extent is found by tracing
the outline and reading off its bounding box, rather than by asking separately
whether a bubble or a limb is nearby. Nothing has to recognise a bubble: the
trace simply goes round it, because the ink is one piece.

The alternative, flooding the panel's interior and looking for what leaks out, was
tried and abandoned. It needs to know what is paper, and on this chapter 65-84% of
each sheet is not white, so the fill swept the page instead of being trapped.
Tracing needs to know only what is a stroke, which is the part that works.

The trace is only believed when it closes the loop. A contour that follows the
frame and returns covers nearly the whole box perimeter, and its bounding box is
then the panel's true extent. A contour that wanders off covers little of the
perimeter, and its bounding box means nothing, so nothing grows. That single test
is what keeps an arbitrary blob from stretching a crop across the page.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ...core.logging import get_logger
from ...core.schema import BBox

_log = get_logger("stages.s1_crop.inkmask")

DEFAULT_PAPER_PERCENTILE = 85
DEFAULT_PAPER_MIN_LEVEL = 180
# Paper is bright and neutral. Aged paper is still close to neutral; a coloured
# panel background is not, however pale it is.
DEFAULT_PAPER_SPREAD = 20
DEFAULT_BARRIER_LEVEL = 100
# Line art and panel borders are near-black and unsaturated. A coloured panel at
# the same luminance is artwork, not a border.
DEFAULT_BARRIER_SPREAD = 40
# How far either side of the box the border stroke is looked for.
DEFAULT_BAND_PX = 8
# The fraction of the box perimeter the traced outline has to account for before
# the trace is believed to be a frame at all.
DEFAULT_MIN_PERIMETER_COVERAGE = 0.8
# A real frame encloses roughly the panel, so its filled contour is about the
# panel's area. Something an order of magnitude larger is a blob that happens to
# span the box, not a border.
DEFAULT_MAX_AREA_RATIO = 2.5
# How much nearer to this panel an outline must reach than to the next panel over.
# A gutter is shared, and a stroke serving as the right edge of one panel is also
# the left edge of the next, so the trace has to be told whose it is.
DEFAULT_TIE_MARGIN = 8


@dataclass
class PageMasks:
    """The two views of a page's ink."""

    # Not page background: ink plus any white enclosed by ink.
    content: np.ndarray
    # Strokes: dark and unsaturated.
    ink: np.ndarray
    # Light, neutral pixels.
    paper: np.ndarray


def page_masks(
    image: np.ndarray,
    *,
    paper_percentile: int = DEFAULT_PAPER_PERCENTILE,
    paper_min_level: int = DEFAULT_PAPER_MIN_LEVEL,
    paper_spread: int = DEFAULT_PAPER_SPREAD,
    barrier_level: int = DEFAULT_BARRIER_LEVEL,
    barrier_spread: int = DEFAULT_BARRIER_SPREAD,
) -> PageMasks:
    """Split a page into paper, ink and content.

    Accepts either a greyscale array or an RGB one. RGB is what the pipeline has,
    and the colour channel matters.

    `paper_percentile` adapts the paper threshold to the page, so a grey scan and
    a clean digital page both work. `paper_min_level` stops that adaptation from
    declaring a dark page to be all paper, which would make the content mask
    empty and quietly turn every downstream check into a no-op. A page dark
    enough to hit that floor degrades to treating the whole page as content,
    which is the old behaviour rather than a wrong answer.
    """
    if image.ndim == 3:
        channels = image.astype(np.int16)
        grey = channels.mean(axis=2)
        spread = channels.max(axis=2) - channels.min(axis=2)
    else:
        grey = image.astype(np.float64)
        spread = np.zeros(grey.shape, dtype=np.float64)

    if grey.size == 0:
        empty = np.zeros(grey.shape, dtype=bool)
        return PageMasks(content=empty, ink=empty, paper=~empty)

    paper_level = max(paper_min_level, float(np.percentile(grey, paper_percentile)))
    paper = (grey >= paper_level) & (spread <= paper_spread)
    ink = (grey <= barrier_level) & (spread <= barrier_spread)

    # Background is the paper reachable from the edge of the page. Anything the
    # ink encloses is content even though it is white, which is what pulls a
    # bubble's interior and a panel's white sky into the content mask.
    background = _border_connected(paper.astype(np.uint8))
    return PageMasks(content=~background, ink=ink, paper=paper)


def content_bounds(content: np.ndarray, page_width: int, page_height: int) -> BBox | None:
    """Bounding box of everything drawn on the page, margins excluded."""
    return _mask_bounds(content, page_width, page_height)


def trace_outlines(
    masks: PageMasks,
    boxes: list[BBox],
    page_width: int,
    page_height: int,
    *,
    band_px: int = DEFAULT_BAND_PX,
    min_coverage: float = DEFAULT_MIN_PERIMETER_COVERAGE,
    max_area_ratio: float = DEFAULT_MAX_AREA_RATIO,
    max_growth: int = 40,
    tie_margin: int = DEFAULT_TIE_MARGIN,
) -> dict[tuple[int, int, int, int], BBox]:
    """Trace every panel's outline on one page.

    The contours are found once and shared. Tracing a page per panel instead
    costs one full-page contour pass per panel, which on a busy colour page is
    the whole runtime of the stage for no extra information.

    Returns only the boxes that actually moved, keyed by their coordinates
    because a pydantic model is not hashable. An empty result is the normal
    outcome for a page of well-bordered panels.
    """
    import cv2

    grown: dict[tuple[int, int, int, int], BBox] = {}
    if max_growth <= 0 or not boxes:
        return grown

    ink = masks.ink.astype(np.uint8)
    if not ink.any():
        return grown

    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return grown

    # One bounding rect per contour, and nothing else, until a box actually
    # claims it. A page of line art has thousands of contours and filling each
    # one in costs far more than the answer is worth.
    prepared: list[tuple[np.ndarray, BBox]] = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        prepared.append((contour, BBox(x1=x, y1=y, x2=x + w, y2=y + h)))

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    filled = np.zeros(ink.shape, dtype=np.uint8)

    for box in boxes:
        band = _grown(box, page_width, page_height, band_px)
        samples = _perimeter_samples(box)
        cap = box.area * max_area_ratio
        limit = _grown(box, page_width, page_height, max_growth)

        best: BBox | None = None
        for contour, rough in prepared:
            if _intersect(rough, band) is None:
                continue
            # A frame is roughly the panel's own size, so the cheap test is
            # whether the rect and the box are of a piece. This rejects the
            # overwhelming majority of contours before any of them is filled.
            if rough.area > cap or rough.area < box.area * 0.4:
                continue
            overlap = _intersect(rough, box)
            if overlap is None or overlap.area < box.area * 0.4:
                continue

            filled.fill(0)
            cv2.drawContours(filled, [contour], -1, 1, thickness=cv2.FILLED)
            if _coverage(filled, samples, kernel) < min_coverage:
                continue

            clipped = _intersect(rough, limit)
            if clipped is None:
                continue
            best = BBox.union_all([b for b in (best, clipped) if b is not None])

        if best is None:
            continue
        if not _claims(box, best, boxes, tie_margin):
            continue
        moved = BBox.union_all([box, best]) or box
        if moved != box:
            grown[_key(box)] = moved

    return grown


def trace_outline(
    masks: PageMasks,
    box: BBox,
    page_width: int,
    page_height: int,
    **kwargs,
) -> tuple[BBox | None, str]:
    """Trace a single panel's outline.

    The page-level form is what the cropper uses; this is the same code with the
    result unpacked for a one-off, so a caller that has one box does not have to
    know the tracing is really done a page at a time.
    """
    grown = trace_outlines(masks, [box], page_width, page_height, **kwargs)
    moved = grown.get(_key(box))
    if moved is None:
        return None, "no outline closed the loop within the growth cap"
    return moved, f"traced outline to {moved.to_xywh()}"


def expand_box(
    masks: PageMasks,
    box: BBox,
    page_width: int,
    page_height: int,
    **kwargs,
) -> tuple[BBox, str]:
    """Grow a box to the extent of its own drawn outline."""
    grown, reason = trace_outline(masks, box, page_width, page_height, **kwargs)
    if grown is None:
        return box, reason
    return grown, reason


def missing_panel_candidates(
    masks: PageMasks,
    boxes: list[BBox],
    page_width: int,
    page_height: int,
    *,
    min_ink_ratio: float = 0.02,
    slack_px: int = 4,
    erode_px: int = 12,
) -> list[BBox]:
    """Drawn area on the page that no detected panel accounts for.

    This is a second opinion. Subtracting the detected panels from the page's
    drawn area leaves whatever the detector walked past, and on a colour page with
    full-bleed artwork that is usually a real panel. It cannot tell a panel that
    bleeds off the page from artwork spilling between two bordered panels, so the
    result is logged and drawn on the contact sheet for a human to confirm, and
    only added when `crop.ink.auto_add_candidates` is set.

    The mask used is `content` rather than `ink`. Ink is deliberately strict, so
    it works for finding strokes, but most of a panel is white and using ink here
    would report the page margins and every pale panel background as unaccounted
    for.

    The leftover is eroded before it is measured. On a colour page the gutters
    are not white, so every panel is surrounded by a connected web of drawn
    gutters that no box accounts for. Undifferentiated, that web is one component
    spanning the sheet and is reported as a single whole-page candidate, which
    says nothing. A missed panel is a solid block, a gutter is a thin strip, so
    eroding by more than a gutter's width removes one and keeps the other.
    """
    import cv2

    if masks.content.size == 0 or not boxes:
        return []

    accounted = np.zeros(masks.content.shape, dtype=bool)
    for box in boxes:
        grown = _grown(box, page_width, page_height, slack_px)
        accounted[_slice(grown, accounted.shape)] = True

    leftover = (masks.content & ~accounted).astype(np.uint8)
    if not leftover.any():
        return []

    # Thin line art fragments a region into hundreds of specks. Closing the mask
    # first merges each drawing back into one blob.
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    leftover = cv2.morphologyEx(leftover, cv2.MORPH_CLOSE, close_kernel)

    if erode_px > 0:
        erode_kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (erode_px * 2 + 1, erode_px * 2 + 1)
        )
        leftover = cv2.erode(leftover, erode_kernel)
        if not leftover.any():
            return []

    count, _, stats, _ = cv2.connectedComponentsWithStats(leftover, connectivity=8)
    page_area = float(page_width * page_height)
    candidates: list[BBox] = []
    for label in range(1, count):
        area = float(stats[label, cv2.CC_STAT_AREA])
        if area < page_area * min_ink_ratio:
            continue
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        # Grow back over the panel border the close trimmed off and over the
        # erosion, so the candidate is the region rather than its skeleton.
        grown = _grown(
            BBox(x1=x, y1=y, x2=x + w, y2=y + h),
            page_width,
            page_height,
            erode_px + slack_px,
        )
        candidates.append(grown)

    candidates.sort(key=lambda b: b.area, reverse=True)
    return candidates


# ---------------------------------------------------------------------------
# Tracing helpers
# ---------------------------------------------------------------------------


def _perimeter_samples(box: BBox, per_side: int = 40) -> np.ndarray:
    """Points spaced evenly around the box border, as (x, y) rows."""
    xs = box.x1 + (box.x2 - box.x1) * (np.arange(per_side) / per_side)
    ys = box.y1 + (box.y2 - box.y1) * (np.arange(per_side) / per_side)
    points = []
    for x in xs:
        points.append((x, box.y1))
        points.append((x, box.y2))
    for y in ys:
        points.append((box.x1, y))
        points.append((box.x2, y))
    return np.round(np.asarray(points)).astype(int)


def _coverage(filled: np.ndarray, samples: np.ndarray, kernel: np.ndarray) -> float:
    """Share of the sampled perimeter lying inside a traced contour.

    The contour is dilated first so a border drawn a pixel proud of the box still
    counts, which matters because a detector's box and the drawn stroke never
    agree exactly.
    """
    import cv2

    grown = cv2.dilate(filled, kernel)
    height, width = grown.shape
    xs = np.clip(samples[:, 0], 0, width - 1)
    ys = np.clip(samples[:, 1], 0, height - 1)
    return float(grown[ys, xs].mean())


def _key(box: BBox) -> tuple[int, int, int, int]:
    """Hashable identity for a box, for use as a dictionary key."""
    return (box.x1, box.y1, box.x2, box.y2)


def _claims(box: BBox, escape: BBox, siblings: list[BBox] | None, tie_margin: int) -> bool:
    """Is the traced extent nearer to `box` than to every other panel on the page?

    Manga often draws one stroke as the right edge of a panel and the left edge
    of its neighbour, so a contour can enclose both. Growing to it would swallow
    the neighbour, so the trace has to be shown to belong to this panel.
    """
    if not siblings:
        return True
    own_gap = _gap(box, escape)
    for other in siblings:
        if other == box or other.iou(box) > 0.5:
            continue
        if _gap(other, escape) < own_gap + tie_margin:
            return False
    return True


def _gap(a: BBox, b: BBox) -> int:
    """Shortest distance between two boxes, zero when they overlap or touch."""
    dx = max(0, max(a.x1 - b.x2, b.x1 - a.x2))
    dy = max(0, max(a.y1 - b.y2, b.y1 - a.y2))
    return max(dx, dy)


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _border_connected(mask: np.ndarray) -> np.ndarray:
    """The parts of `mask` reachable from the edge of the image.

    Connectivity 4 rather than 8 on purpose: a single anti-aliased pixel
    bridging a gutter would otherwise connect the page margin to the inside of
    the artwork under 8-connectivity, and the whole page would read as
    background.
    """
    import cv2

    count, labels = cv2.connectedComponents(mask, connectivity=4)
    if count <= 1:
        return np.zeros(mask.shape, dtype=bool)

    edge_labels = np.unique(
        np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    )
    # Label 0 is the label function's own background, not a paper component.
    edge_labels = edge_labels[edge_labels != 0]
    if edge_labels.size == 0:
        return np.zeros(mask.shape, dtype=bool)
    return np.isin(labels, edge_labels)


def _mask_bounds(mask: np.ndarray, page_width: int, page_height: int) -> BBox | None:
    rows = np.flatnonzero(mask.any(axis=1))
    if rows.size == 0:
        return None
    cols = np.flatnonzero(mask.any(axis=0))
    return BBox(
        x1=max(0, int(cols[0])),
        y1=max(0, int(rows[0])),
        x2=min(page_width, int(cols[-1]) + 1),
        y2=min(page_height, int(rows[-1]) + 1),
    )


def _grown(box: BBox, page_width: int, page_height: int, amount: int) -> BBox:
    if amount <= 0:
        return box
    return BBox(
        x1=max(0, box.x1 - amount),
        y1=max(0, box.y1 - amount),
        x2=min(page_width, box.x2 + amount),
        y2=min(page_height, box.y2 + amount),
    )


def _intersect(a: BBox, b: BBox) -> BBox | None:
    """Overlap of two boxes, or None where they do not meet."""
    x1, y1 = max(a.x1, b.x1), max(a.y1, b.y1)
    x2, y2 = min(a.x2, b.x2), min(a.y2, b.y2)
    if x2 <= x1 or y2 <= y1:
        return None
    return BBox(x1=x1, y1=y1, x2=x2, y2=y2)


def _slice(box: BBox, shape: tuple[int, int]):
    """`box` as a numpy slice, clipped to the array."""
    height, width = shape
    return (
        slice(max(0, min(box.y1, height)), max(0, min(box.y2, height))),
        slice(max(0, min(box.x1, width)), max(0, min(box.x2, width))),
    )
