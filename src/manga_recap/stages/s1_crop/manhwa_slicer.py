"""Next-generation Smart Manhwa Panel Slicer.

Pipeline stage for vertical-scroll manhwa/webtoon chapters that:
1. Continuous Vertical Canvas:
   Stitches and tracks cumulative heights across multiple split image files
   (001.jpg, 002.jpg, etc.) so panel boundaries crossing image splits are
   never decapitated.
2. Robust Semantic Gutter Detection:
   Identifies horizontal separation bands by analyzing luminance (white >235,
   black <25, flat grey) AND Canny edge / gradient density (true gutters have
   zero art strokes/edges, distinguishing them from dark scenes with shadows
   or bright skies). Minimum gutter height: 25px.
3. Floating Speech Bubble & Void Panel Elimination:
   Detects isolated speech bubbles or text on plain backgrounds (>70% uniform area,
   high bubble density, zero character artwork) and merges them into the
   neighboring story panel based on proximity.
4. Clean Pruning:
   Skips tiny gutter slivers (height < 70px) and extreme aspect ratios (>15:1).
   Filters out obvious scanlation credits / title logo screens when isolated.
5. Tight Content Bounding Box:
   Trims excessive left/right empty side margins to the actual drawn ink bounding
   box with a configurable 10px safe margin.
6. 100% WebP Standard:
   Saves panels strictly as .webp (quality 90) and generates schema-compliant
   panel_index.json (PanelIndexFile).
"""

from __future__ import annotations

import argparse
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from ...core.logging import get_logger
from ...core.schema import BBox, PanelIndex, PanelIndexFile, save_model

_log = get_logger("stages.s1_crop.manhwa_slicer")


def natural_sort_key(s: Path | str) -> list[int | str]:
    """Sort filenames with embedded numbers naturally (001 before 010)."""
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", str(s))
    ]


@dataclass
class ManhwaSliceConfig:
    """Configuration tunables for the smart manhwa slicer."""

    # Gutter detection thresholds
    min_gutter_height: int = 25  # Minimum continuous rows to count as a gutter
    white_lum_thresh: float = 235.0  # Luminance threshold for white gutters
    black_lum_thresh: float = 25.0  # Luminance threshold for black gutters
    max_gutter_std: float = 8.0  # Max row luminance std for white/black gutters
    max_grey_std: float = 4.0  # Max row luminance std for solid grey gutters
    max_gutter_edge_density: float = 0.01  # Max Canny edge pixel ratio per row (zero art)
    canny_low: int = 50
    canny_high: int = 150

    # Speech bubble & void elimination
    floating_bubble_uniform_ratio: float = 0.70  # >70% uniform background
    bubble_conf_threshold: float = 0.35  # Confidence for ONNX bubble detector
    extract_text_crops: bool = True

    # Pruning parameters
    min_panel_height: int = 70  # Skip tiny slivers < 70px
    max_aspect_ratio: float = 15.0  # Skip extreme aspect ratios (>15:1)
    filter_credits: bool = True
    credit_patterns: list[str] = field(
        default_factory=lambda: [
            "discord",
            "patreon",
            "scanlation",
            "scans",
            "translated",
            "translation",
            "proofread",
            "typeset",
            "ko-fi",
            "paypal",
            "donat",
            "chapter end",
            "watermark",
        ]
    )

    # Content framing
    side_margin_px: int = 10  # 10px safe margin around ink content
    min_col_pixels: int = 3
    snap_edge_tolerance: int = 20

    # Storage standard
    webp_quality: int = 90  # 100% WebP standard quality


@dataclass
class RowMetrics:
    """Row-wise statistics calculated across the continuous canvas."""

    mean_lum: np.ndarray  # Shape: (total_height,)
    std_lum: np.ndarray  # Shape: (total_height,)
    color_std: np.ndarray  # Shape: (total_height,)
    edge_density: np.ndarray  # Shape: (total_height,)


@dataclass
class SliceMetadata:
    """Metadata for an individual slice of the continuous canvas."""

    index: int
    source: Path | Image.Image | np.ndarray
    width: int
    height: int
    y_start: int
    y_end: int


class ContinuousCanvas:
    """Represents a continuous vertical canvas assembled from multiple split images.

    Enables seamless cross-slice slicing with zero decapitation.
    """

    def __init__(
        self,
        sources: Sequence[Path | str] | Path | str | Sequence[Image.Image | np.ndarray],
    ):
        self.slices: list[SliceMetadata] = []
        raw_items: list[Path | Image.Image | np.ndarray] = []

        if isinstance(sources, (Path, str)):
            p = Path(sources)
            if p.is_dir():
                found = []
                for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                    found.extend(p.glob(ext))
                found.sort(key=natural_sort_key)
                raw_items = found
            elif p.is_file():
                raw_items = [p]
            else:
                raise FileNotFoundError(f"Source path {sources} does not exist.")
        elif isinstance(sources, Sequence):
            for item in sources:
                if isinstance(item, (str, Path)):
                    p = Path(item)
                    if p.is_file():
                        raw_items.append(p)
                elif isinstance(item, (Image.Image, np.ndarray)):
                    raw_items.append(item)
                else:
                    raise TypeError(f"Unsupported slice item type: {type(item)}")
        else:
            raise TypeError(f"Unsupported sources type: {type(sources)}")

        if not raw_items:
            raise ValueError("ContinuousCanvas initialized with no valid images.")

        cur_y = 0
        max_w = 0
        for idx, item in enumerate(raw_items):
            if isinstance(item, Path):
                with Image.open(item) as im:
                    w, h = im.size
            elif isinstance(item, Image.Image):
                w, h = item.size
            elif isinstance(item, np.ndarray):
                h, w = item.shape[:2]
            else:
                raise ValueError(f"Unknown item: {item}")

            max_w = max(max_w, w)
            self.slices.append(
                SliceMetadata(
                    index=idx,
                    source=item,
                    width=w,
                    height=h,
                    y_start=cur_y,
                    y_end=cur_y + h,
                )
            )
            cur_y += h

        self.width: int = max_w
        self.total_height: int = cur_y

    def __len__(self) -> int:
        return len(self.slices)

    def _load_slice_image(self, slice_meta: SliceMetadata) -> Image.Image:
        """Load a slice as a PIL RGB Image."""
        if isinstance(slice_meta.source, Path):
            with Image.open(slice_meta.source) as im:
                return im.convert("RGB")
        elif isinstance(slice_meta.source, Image.Image):
            return slice_meta.source.convert("RGB")
        elif isinstance(slice_meta.source, np.ndarray):
            arr = slice_meta.source
            if arr.ndim == 2:
                arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2RGB)
            elif arr.shape[2] == 4:
                arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2RGB)
            return Image.fromarray(arr)
        raise ValueError(f"Cannot load slice: {slice_meta.source}")

    def compute_row_metrics(
        self,
        canny_low: int = 50,
        canny_high: int = 150,
    ) -> RowMetrics:
        """Compute luminance mean, std, and Canny edge density row-by-row.

        Processes slice-by-slice to keep memory usage minimal.
        """
        mean_lums: list[np.ndarray] = []
        std_lums: list[np.ndarray] = []
        color_stds: list[np.ndarray] = []
        edge_densities: list[np.ndarray] = []

        for s in self.slices:
            im = self._load_slice_image(s)
            arr = np.asarray(im)
            h, w = arr.shape[:2]

            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
            m_lum = np.mean(gray, axis=1)
            s_lum = np.std(gray, axis=1)

            # Measure channel color divergence across RGB
            # In monochrome or solid gutters, color_std is ~0
            c_std = np.mean(np.std(arr.astype(np.float32), axis=-1), axis=1)

            # Canny edge density: true gutters have zero art strokes/edges
            edges = cv2.Canny(gray, canny_low, canny_high)
            e_density = np.count_nonzero(edges, axis=1) / float(w)

            mean_lums.append(m_lum.astype(np.float32))
            std_lums.append(s_lum.astype(np.float32))
            color_stds.append(c_std.astype(np.float32))
            edge_densities.append(e_density.astype(np.float32))

        return RowMetrics(
            mean_lum=np.concatenate(mean_lums) if mean_lums else np.empty(0, dtype=np.float32),
            std_lum=np.concatenate(std_lums) if std_lums else np.empty(0, dtype=np.float32),
            color_std=np.concatenate(color_stds) if color_stds else np.empty(0, dtype=np.float32),
            edge_density=np.concatenate(edge_densities) if edge_densities else np.empty(0, dtype=np.float32),
        )

    def crop_global(self, x1: int, y1: int, x2: int, y2: int) -> Image.Image:
        """Crop an arbitrary global rectangle [x1, y1, x2, y2] across slice splits.

        Zero decapitation: If [y1, y2] spans across 2 or more split image files,
        the parts are cleanly extracted and stitched into a single cohesive image.
        """
        y1 = max(0, min(y1, self.total_height))
        y2 = max(0, min(y2, self.total_height))
        x1 = max(0, min(x1, self.width))
        x2 = max(0, min(x2, self.width))

        target_h = y2 - y1
        target_w = x2 - x1
        if target_h <= 0 or target_w <= 0:
            return Image.new("RGB", (max(1, target_w), max(1, target_h)), (255, 255, 255))

        out_img = Image.new("RGB", (target_w, target_h), (255, 255, 255))
        cur_paste_y = 0

        for s in self.slices:
            if max(y1, s.y_start) < min(y2, s.y_end):
                overlap_start = max(y1, s.y_start)
                overlap_end = min(y2, s.y_end)
                local_y1 = overlap_start - s.y_start
                local_y2 = overlap_end - s.y_start

                slice_im = self._load_slice_image(s)
                slice_w = slice_im.width

                # Handle horizontal slice bounds gracefully if widths vary slightly
                crop_x1 = min(x1, slice_w)
                crop_x2 = min(x2, slice_w)
                if crop_x2 > crop_x1:
                    part = slice_im.crop((crop_x1, local_y1, crop_x2, local_y2))
                    out_img.paste(part, (0, cur_paste_y))

                cur_paste_y += (overlap_end - overlap_start)

        return out_img


def _close_1d_gaps(mask: np.ndarray, max_gap: int = 3) -> np.ndarray:
    """Close small non-gutter noise gaps (e.g. compression noise) in a boolean mask."""
    out = mask.copy()
    n = len(out)
    in_gap = False
    gap_start = 0

    for i in range(n):
        if not out[i]:
            if not in_gap:
                in_gap = True
                gap_start = i
        else:
            if in_gap:
                in_gap = False
                if 0 < gap_start and (i - gap_start) <= max_gap:
                    out[gap_start:i] = True
    return out


def _filter_min_runs(mask: np.ndarray, min_length: int) -> np.ndarray:
    """Keep only contiguous True runs that have length >= min_length."""
    out = mask.copy()
    n = len(out)
    in_run = False
    run_start = 0

    for i in range(n):
        if out[i]:
            if not in_run:
                in_run = True
                run_start = i
        else:
            if in_run:
                in_run = False
                if (i - run_start) < min_length:
                    out[run_start:i] = False
    if in_run and (n - run_start) < min_length:
        out[run_start:n] = False
    return out


def _find_false_runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return (start, end) ranges for contiguous False runs (candidate panels)."""
    runs = []
    n = len(mask)
    in_run = False
    run_start = 0

    for i in range(n):
        if not mask[i]:
            if not in_run:
                in_run = True
                run_start = i
        else:
            if in_run:
                in_run = False
                runs.append((run_start, i))
    if in_run:
        runs.append((run_start, n))
    return runs


def detect_gutters(
    metrics: RowMetrics,
    config: ManhwaSliceConfig,
) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Detect semantic horizontal gutters separating manhwa panels.

    Returns:
        is_gutter: boolean array of length total_height.
        candidate_blocks: list of (y_start, y_end) tuples of non-gutter candidate panels.
    """
    if len(metrics.mean_lum) == 0:
        return np.empty(0, dtype=bool), []

    # 1. Detect candidate gutter rows
    # White gutter: high luminance, low std, zero/minimal edge density
    is_white = (
        (metrics.mean_lum >= config.white_lum_thresh)
        & (metrics.std_lum <= config.max_gutter_std)
        & (metrics.edge_density <= config.max_gutter_edge_density)
    )

    # Black gutter: low luminance, low std, zero/minimal edge density
    # (A dark scene with shadows has edge density > threshold, so it is NOT a gutter)
    is_black = (
        (metrics.mean_lum <= config.black_lum_thresh)
        & (metrics.std_lum <= config.max_gutter_std)
        & (metrics.edge_density <= config.max_gutter_edge_density)
    )

    # Grey gutter: flat, neutral grey with near-zero color variance and zero edges
    is_grey = (
        (metrics.std_lum <= config.max_grey_std)
        & (metrics.color_std <= 2.5)
        & (metrics.edge_density <= config.max_gutter_edge_density / 2.0)
    )

    is_gutter_raw = is_white | is_black | is_grey

    # 2. Close minor 1-3px noise gaps within gutters
    is_gutter_closed = _close_1d_gaps(is_gutter_raw, max_gap=3)

    # 3. Enforce minimum gutter height (25px)
    is_gutter = _filter_min_runs(is_gutter_closed, config.min_gutter_height)

    # 4. Extract candidate non-gutter segments
    blocks = _find_false_runs(is_gutter)

    return is_gutter, blocks


@dataclass
class PanelSegment:
    """Internal representation of a candidate or finalized panel segment."""

    y_start: int
    y_end: int
    segment_type: str = "STORY"  # "STORY", "FLOATING_BUBBLE", "VOID", "CREDIT"
    x1: int = 0
    x2: int = 0
    merged_bubbles: list[tuple[int, int]] = field(default_factory=list)


def detect_bubbles_in_image(
    sess: Any,
    img: Image.Image,
    conf_threshold: float = 0.35,
) -> list[tuple[int, int, int, int]]:
    """Detect speech bubbles in a panel using ONNX detector if available."""
    if sess is None:
        return []
    try:
        orig_w, orig_h = img.size
        im_resized = img.resize((640, 640), Image.BILINEAR)
        arr = np.array(im_resized, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, 0)
        orig_sizes = np.array([[orig_h, orig_w]], dtype=np.int64)

        outputs = sess.run(None, {"images": arr, "orig_target_sizes": orig_sizes})
        labels, boxes, scores = outputs[0][0], outputs[1][0], outputs[2][0]

        detections = []
        for lbl, box, score in zip(labels, boxes, scores, strict=False):
            if score >= conf_threshold and int(lbl) in (0, 1):
                ymin, xmin, ymax, xmax = [float(coord) for coord in box]
                detections.append((
                    max(0, int(round(xmin))),
                    max(0, int(round(ymin))),
                    min(orig_w, int(round(xmax))),
                    min(orig_h, int(round(ymax))),
                ))
        return detections
    except Exception as e:
        _log.debug("Speech bubble detection failed: %s", e)
        return []


def classify_segment(
    canvas: ContinuousCanvas,
    y_start: int,
    y_end: int,
    config: ManhwaSliceConfig,
    detector_session: Any = None,
    is_boundary: bool = False,
) -> tuple[str, dict[str, Any]]:
    """Classify a segment as STORY, FLOATING_BUBBLE, VOID, or CREDIT."""
    h = y_end - y_start
    w = canvas.width
    if h <= 0 or w <= 0:
        return "VOID", {}

    # Check for tiny sliver
    if h < config.min_panel_height and (w / max(1, h) > config.max_aspect_ratio):
        return "VOID", {"reason": "sliver"}

    img = canvas.crop_global(0, y_start, w, y_end)
    arr = np.asarray(img)

    # 1. Determine dominant background color from perimeter edges
    border_pixels = np.vstack([
        arr[:min(4, h), :].reshape(-1, 3),
        arr[max(0, h - 4):, :].reshape(-1, 3),
        arr[:, :min(4, w)].reshape(-1, 3),
        arr[:, max(0, w - 4):].reshape(-1, 3),
    ])
    bg_color = np.median(border_pixels, axis=0)

    # Background distance map
    dist = np.max(np.abs(arr.astype(np.float32) - bg_color), axis=2)
    is_bg = dist <= 25.0
    uniform_ratio = np.count_nonzero(is_bg) / float(arr.shape[0] * arr.shape[1])

    # 2. Pure void / empty canvas check
    if uniform_ratio >= 0.985:
        return "VOID", {"uniform_ratio": uniform_ratio}

    fg_mask = ~is_bg
    fg_pixels = np.count_nonzero(fg_mask)
    if fg_pixels == 0:
        return "VOID", {"uniform_ratio": uniform_ratio}

    # Measure color saturation of foreground:
    # Manhwa artwork has rich color saturation (skin, hair, clothing, effects).
    # Speech bubbles and scanlation text are monochrome.
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    sat = hsv[..., 1]
    fg_sat = sat[fg_mask]
    high_sat_ratio = np.count_nonzero(fg_sat > 40) / float(fg_pixels)

    # If significant colored artwork is present, it is definitely STORY
    if high_sat_ratio > 0.12 or uniform_ratio < 0.60:
        return "STORY", {"uniform_ratio": uniform_ratio, "high_sat_ratio": high_sat_ratio}

    # 3. Check for scanlation credit screens (isolated at chapter boundaries with no color art)
    if is_boundary and config.filter_credits:
        if (h < 140 and (w / max(1, h) >= 3.5)) or (uniform_ratio >= 0.88 and h < 220):
            return "CREDIT", {"uniform_ratio": uniform_ratio, "reason": "boundary_credit"}

    # 4. Floating Speech Bubble vs Story Artwork check
    if uniform_ratio >= config.floating_bubble_uniform_ratio:

        # If ONNX bubble detector is available, check if bubbles cover the foreground
        if detector_session is not None:
            bubbles = detect_bubbles_in_image(detector_session, img, config.bubble_conf_threshold)
            if bubbles:
                # Check coverage of foreground by detected bubbles
                bubble_mask = np.zeros((h, w), dtype=bool)
                for bx1, by1, bx2, by2 in bubbles:
                    bubble_mask[by1:by2, bx1:bx2] = True
                fg_in_bubble = np.count_nonzero(fg_mask & bubble_mask)
                if fg_in_bubble / float(fg_pixels) >= 0.70:
                    return "FLOATING_BUBBLE", {"uniform_ratio": uniform_ratio, "bubbles": len(bubbles)}

        # Contour geometry check for floating bubble:
        # A bubble is a compact shape in a sea of background
        ys, xs = np.where(fg_mask)
        fg_h = int(np.max(ys) - np.min(ys) + 1)
        fg_w = int(np.max(xs) - np.min(xs) + 1)
        fg_area_ratio = (fg_h * fg_w) / float(w * h)

        # In a floating bubble, the ink extent is localized (< 55% of panel area)
        # and non-background pixels are a small fraction (< 22%)
        if fg_area_ratio < 0.55 and (fg_pixels / float(w * h)) < 0.22:
            return "FLOATING_BUBBLE", {
                "uniform_ratio": uniform_ratio,
                "fg_area_ratio": fg_area_ratio,
            }

    return "STORY", {"uniform_ratio": uniform_ratio}


def merge_floating_bubbles(
    segments: list[PanelSegment],
) -> list[PanelSegment]:
    """Merge floating speech bubbles into neighboring story panels based on proximity.

    Zero isolated floating bubbles: Bounding boxes of story panels are expanded
    vertically to incorporate their adjacent speech bubbles.
    """
    story_indices = [i for i, s in enumerate(segments) if s.segment_type == "STORY"]
    if not story_indices:
        # If no story panels detected at all, promote all non-void segments to STORY
        for s in segments:
            if s.segment_type != "VOID":
                s.segment_type = "STORY"
        return [s for s in segments if s.segment_type == "STORY"]

    bubble_indices = [i for i, s in enumerate(segments) if s.segment_type == "FLOATING_BUBBLE"]

    for b_idx in bubble_indices:
        bubble = segments[b_idx]

        # Find closest story panel above
        prev_story = None
        for s_idx in reversed(story_indices):
            s = segments[s_idx]
            if s.y_end <= bubble.y_start:
                prev_story = s
                break

        # Find closest story panel below
        next_story = None
        for s_idx in story_indices:
            s = segments[s_idx]
            if s.y_start >= bubble.y_end:
                next_story = s
                break

        if prev_story is not None and next_story is not None:
            gap_pre = bubble.y_start - prev_story.y_end
            gap_post = next_story.y_start - bubble.y_end
            if gap_pre <= gap_post:
                prev_story.y_end = max(prev_story.y_end, bubble.y_end)
                prev_story.merged_bubbles.append((bubble.y_start, bubble.y_end))
            else:
                next_story.y_start = min(next_story.y_start, bubble.y_start)
                next_story.merged_bubbles.append((bubble.y_start, bubble.y_end))
        elif prev_story is not None:
            prev_story.y_end = max(prev_story.y_end, bubble.y_end)
            prev_story.merged_bubbles.append((bubble.y_start, bubble.y_end))
        elif next_story is not None:
            next_story.y_start = min(next_story.y_start, bubble.y_start)
            next_story.merged_bubbles.append((bubble.y_start, bubble.y_end))
        else:
            bubble.segment_type = "STORY"

    # Return only story segments
    return [segments[i] for i in story_indices]


def prune_segments(
    segments: list[PanelSegment],
    canvas_width: int,
    config: ManhwaSliceConfig,
) -> list[PanelSegment]:
    """Prune tiny slivers, extreme aspect ratios, and credit screens."""
    kept: list[PanelSegment] = []
    for seg in segments:
        h = seg.y_end - seg.y_start
        w = (seg.x2 - seg.x1) if (seg.x2 > seg.x1) else canvas_width

        # 1. Skip tiny slivers < min_panel_height (70px)
        if h < config.min_panel_height:
            continue

        # 2. Skip extreme aspect ratios (>15:1)
        aspect = max(w / max(1, h), h / max(1, w))
        if aspect > config.max_aspect_ratio:
            continue

        # 3. Filter credit / void segments
        if seg.segment_type in ("CREDIT", "VOID"):
            continue

        kept.append(seg)
    return kept


def find_tight_horizontal_bounds(
    panel_img: Image.Image | np.ndarray,
    config: ManhwaSliceConfig,
) -> tuple[int, int]:
    """Trim excessive empty side margins to the actual drawn ink bounding box.

    Applies a configurable safe margin (default: 10px). Snaps to full canvas
    width if the art bleeds close to the border.
    """
    if isinstance(panel_img, Image.Image):
        arr = np.asarray(panel_img.convert("RGB"))
    else:
        arr = panel_img

    h, w = arr.shape[:2]
    if w <= 0 or h <= 0:
        return 0, w

    # Determine background color from outer side edges
    left_sample = arr[:, :min(10, w)]
    right_sample = arr[:, max(0, w - 10):]
    edge_pixels = np.vstack([left_sample.reshape(-1, 3), right_sample.reshape(-1, 3)])
    bg_color = np.median(edge_pixels, axis=0)

    # Color difference and Canny edge map
    diff = np.max(np.abs(arr.astype(np.float32) - bg_color), axis=2)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 40, 120)

    col_has_ink = (
        (np.count_nonzero(diff > 18.0, axis=0) >= config.min_col_pixels)
        | (np.count_nonzero(edges, axis=0) >= 2)
    )

    ink_indices = np.where(col_has_ink)[0]
    if len(ink_indices) == 0:
        return 0, w

    x_min = int(ink_indices[0])
    x_max = int(ink_indices[-1]) + 1

    # Apply safe margin
    x1 = max(0, x_min - config.side_margin_px)
    x2 = min(w, x_max + config.side_margin_px)

    # Snap to full width if artwork is near edges
    if x1 <= config.snap_edge_tolerance and x2 >= (w - config.snap_edge_tolerance):
        return 0, w

    # Ensure minimum usable width (80px)
    if (x2 - x1) < 80 and w >= 80:
        center = (x1 + x2) // 2
        x1 = max(0, center - 40)
        x2 = min(w, x1 + 80)
        x1 = max(0, x2 - 80)

    return x1, x2


class ManhwaSlicer:
    """Smart Manhwa panel slicing engine."""

    def __init__(
        self,
        config: ManhwaSliceConfig | None = None,
        detector_session: Any = None,
    ):
        self.config = config or ManhwaSliceConfig()
        self.detector_session = detector_session

    def slice_canvas(
        self,
        canvas: ContinuousCanvas,
        output_dir: Path,
        chapter_id: str = "ch01",
        force: bool = False,
    ) -> PanelIndexFile:
        """Run the full slicer pipeline on a ContinuousCanvas."""
        output_dir = Path(output_dir)
        panels_dir = output_dir if output_dir.name == "02_panels" else output_dir / "02_panels"
        text_dir = panels_dir / "_text"
        index_file = panels_dir / "panel_index.json"

        if not force and index_file.exists() and any(panels_dir.glob("panel_*.webp")):
            try:
                from ...core.schema import load_model

                existing_idx = load_model(index_file, PanelIndexFile)
                _log.info("ManhwaSlicer: using existing panel_index.json (%d panels)", existing_idx.panel_count)
                return existing_idx
            except Exception:
                pass

        panels_dir.mkdir(parents=True, exist_ok=True)
        if self.config.extract_text_crops:
            text_dir.mkdir(parents=True, exist_ok=True)

        if force:
            for stale in panels_dir.glob("panel_*.webp"):
                stale.unlink()
            for stale in text_dir.glob("panel_*.webp"):
                stale.unlink()

        # Step 1: Compute row metrics & detect gutters
        metrics = canvas.compute_row_metrics(self.config.canny_low, self.config.canny_high)
        _, candidate_blocks = detect_gutters(metrics, self.config)

        _log.info(
            "ManhwaSlicer: found %d candidate blocks across %d slices (%dpx total height)",
            len(candidate_blocks),
            len(canvas),
            canvas.total_height,
        )

        # Step 2: Classify candidate segments
        classified_segments: list[PanelSegment] = []
        total_cand = len(candidate_blocks)
        for i, (sy, ey) in enumerate(candidate_blocks):
            is_bound = (i == 0 or i == total_cand - 1)
            seg_type, _ = classify_segment(
                canvas,
                sy,
                ey,
                self.config,
                detector_session=self.detector_session,
                is_boundary=is_bound,
            )
            classified_segments.append(
                PanelSegment(y_start=sy, y_end=ey, segment_type=seg_type)
            )

        # Step 3: Merge floating speech bubbles into neighboring story panels
        merged_segments = merge_floating_bubbles(classified_segments)

        # Step 4: Prune slivers, extreme aspect ratios, credits
        story_segments = prune_segments(merged_segments, canvas.width, self.config)

        # Step 5: Compute tight horizontal content bounding boxes & crop
        panel_entries: list[PanelIndex] = []
        all_chapter_text_boxes: list[BBox] = []

        for rank, seg in enumerate(story_segments, start=1):
            panel_id = f"panel_{rank:04d}"
            panel_filename = f"{panel_id}.webp"
            panel_path = panels_dir / panel_filename

            # Extract full-width segment to find tight horizontal bounds
            seg_img = canvas.crop_global(0, seg.y_start, canvas.width, seg.y_end)
            x1, x2 = find_tight_horizontal_bounds(seg_img, self.config)
            seg.x1, seg.x2 = x1, x2

            # Crop finalized tight panel
            final_panel_img = canvas.crop_global(x1, seg.y_start, x2, seg.y_end)

            # 100% WebP Standard: Save strictly as .webp (quality 90, method 3 for ultra-fast encoding)
            final_panel_img.save(panel_path, format="WEBP", quality=self.config.webp_quality, method=3)

            # Bubble detection on the final cropped panel
            panel_text_boxes: list[BBox] = []
            text_rel_path = ""
            if self.detector_session is not None and self.config.extract_text_crops:
                bubbles = detect_bubbles_in_image(
                    self.detector_session, final_panel_img, self.config.bubble_conf_threshold
                )
                if bubbles:
                    for b_idx, (bx1, by1, bx2, by2) in enumerate(bubbles):
                        if bx2 > bx1 and by2 > by1:
                            t_crop = final_panel_img.crop((bx1, by1, bx2, by2))
                            t_name = (
                                f"{panel_id}_text_{b_idx:02d}.webp"
                                if len(bubbles) > 1
                                else f"{panel_id}_text.webp"
                            )
                            t_path = text_dir / t_name
                            t_crop.save(t_path, format="WEBP", quality=self.config.webp_quality, method=3)

                            # Global coordinates relative to canvas
                            global_tbox = BBox(
                                x1=x1 + bx1,
                                y1=seg.y_start + by1,
                                x2=x1 + bx2,
                                y2=seg.y_start + by2,
                            )
                            panel_text_boxes.append(global_tbox)
                            all_chapter_text_boxes.append(global_tbox)

                    text_rel_path = f"02_panels/_text/{panel_id}_text.webp"

            panel_entries.append(
                PanelIndex(
                    panel_id=panel_id,
                    page_number=1,
                    index_on_page=rank,
                    reading_order=rank,
                    bbox=BBox(x1=x1, y1=seg.y_start, x2=x2, y2=seg.y_end),
                    image_path=f"02_panels/{panel_filename}",
                    source="manhwa",
                    page_width=canvas.width,
                    page_height=canvas.total_height,
                    text_boxes=panel_text_boxes,
                    text_image_path=text_rel_path,
                    nested_in="",
                )
            )

        # Step 6: Write schema-compliant panel_index.json
        index_file_doc = PanelIndexFile(
            chapter_id=chapter_id,
            page_count=1,
            panel_count=len(panel_entries),
            created_at=datetime.now(timezone.utc).isoformat(),
            panels=panel_entries,
            page_text_boxes={1: all_chapter_text_boxes} if all_chapter_text_boxes else {},
            page_content_bbox={1: BBox(x1=0, y1=0, x2=canvas.width, y2=canvas.total_height)},
            page_missing_candidates={},
        )
        save_model(index_file_doc, index_file)
        _log.info(
            "ManhwaSlicer: completed %d panels -> %s",
            len(panel_entries),
            index_file,
        )
        return index_file_doc


def slice_manhwa(
    input_source: Sequence[Path | str] | Path | str | Sequence[Image.Image | np.ndarray],
    output_dir: Path | str,
    chapter_id: str = "ch01",
    config: ManhwaSliceConfig | None = None,
    detector_session: Any = None,
    force: bool = False,
) -> PanelIndexFile:
    """Convenience function to run the smart manhwa slicer."""
    canvas = ContinuousCanvas(input_source)
    slicer = ManhwaSlicer(config=config, detector_session=detector_session)
    return slicer.slice_canvas(canvas, Path(output_dir), chapter_id=chapter_id, force=force)


def get_detector_session() -> Any:
    """Attempt to load the ONNX detector session via DirectML or CPU."""
    try:
        import onnxruntime as ort

        repo_root = Path(__file__).resolve().parents[4]
        model_path = repo_root / "models" / "detector.onnx"
        if not model_path.exists():
            return None
        providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
        return ort.InferenceSession(str(model_path), providers=providers)
    except Exception as e:
        _log.debug("Could not load detector.onnx session: %s", e)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Manhwa Panel Slicer")
    parser.add_argument("input_source", help="Path to manhwa images directory or files")
    parser.add_argument("output_dir", help="Path to output directory (e.g. data/chapters/ch01)")
    parser.add_argument("--chapter-id", default="ch01", help="Chapter identifier")
    parser.add_argument("--force", action="store_true", help="Force re-slicing")
    args = parser.parse_args()

    sess = get_detector_session()
    result = slice_manhwa(
        args.input_source,
        args.output_dir,
        chapter_id=args.chapter_id,
        detector_session=sess,
        force=args.force,
    )
    print(f"Successfully sliced {result.panel_count} panels into {args.output_dir}")


if __name__ == "__main__":
    main()
