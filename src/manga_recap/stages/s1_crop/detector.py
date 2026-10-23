"""Panel detection: YOLO when weights exist, recursive XY-cut otherwise.

The OpenCV path is a first-class fallback, not a stub. It handles clean digital
pages with white gutters, which is the majority of modern raws, and it means the
pipeline is runnable before any model weights are set up.

The manual override is the escape hatch for pages where both fail: drop
`02_panels/manual_boxes.json` in place and re-run the stage.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

from ...core.logging import get_logger
from ...core.schema import BBox, PanelSource

_log = get_logger("stages.s1_crop.detector")

MANUAL_BOXES_FILENAME = "manual_boxes.json"


class DetectionResult:
    """Boxes found on one page, with the detector that produced them.

    `text_boxes` are the speech and text regions. They are deliberately kept:
    they are the evidence that a bubble stayed inside its panel crop, and the
    cropper uses them to grow each box and to produce a high-resolution crop
    for transcription.
    """

    def __init__(
        self,
        boxes: list[BBox],
        source: PanelSource,
        text_boxes: list[BBox] | None = None,
    ) -> None:
        self.boxes = boxes
        self.source = source
        self.text_boxes = text_boxes or []


def detect(
    image_path: Path,
    *,
    detector: str,
    weights_path: Path | None,
    confidence: float,
    iou_threshold: float,
    min_area_ratio: float,
    opencv_settings: dict | None = None,
    manual_dir: Path | None = None,
    yolo_settings: dict | None = None,
    text_class_ids: tuple[int, ...] | None = (1,),
    text_min_area_ratio: float = 0.0002,
) -> DetectionResult:
    """Find panel boxes and text regions on a single page image."""
    if manual_dir is not None:
        manual = _load_manual_boxes(manual_dir, image_path)
        if manual is not None:
            _log.info("Using manual boxes for %s", image_path.name)
            return DetectionResult(manual, "manual")

    with Image.open(image_path) as image:
        width, height = image.size
        grayscale = np.asarray(image.convert("L"))

    text_boxes: list[BBox] = []

    if detector == "yolo":
        settings = yolo_settings or {}
        boxes, text_boxes = _detect_yolo(
            image_path,
            weights_path,
            confidence=confidence,
            iou_threshold=iou_threshold,
            imgsz=int(settings.get("imgsz", 1024)),
            class_ids=_parse_class_ids(settings.get("class_ids")),
            text_class_ids=text_class_ids,
        )
        source: PanelSource = "yolo"
    else:
        boxes = _detect_opencv(grayscale, **(opencv_settings or {}))
        source = "opencv"

    boxes = [b for b in boxes if _area_ratio(b, width, height) >= min_area_ratio]
    boxes = dedupe(boxes, iou_threshold=0.5)

    # Text regions get their own, far smaller, floor: a single speech bubble can
    # be a rounding error against page area, and dropping it is exactly the
    # failure this whole stage exists to prevent.
    text_boxes = [b for b in text_boxes if _area_ratio(b, width, height) >= text_min_area_ratio]
    text_boxes = dedupe(text_boxes, iou_threshold=0.4)

    return DetectionResult(boxes, source, text_boxes)


# ---------------------------------------------------------------------------
# YOLO
# ---------------------------------------------------------------------------

# YOLO weights load in a second or two, which is invisible once and very
# visible across a thirty-page chapter if it happens per page.
_MODEL_CACHE: dict[tuple[str, int], object] = {}
_DML_SESSION_CACHE: dict[str, object] = {}
_DML_CHECKED: bool | None = None


def _is_dml_available() -> bool:
    global _DML_CHECKED
    if _DML_CHECKED is not None:
        return _DML_CHECKED
    try:
        import onnxruntime as ort

        _DML_CHECKED = "DmlExecutionProvider" in ort.get_available_providers()
    except Exception:
        _DML_CHECKED = False
    return _DML_CHECKED


def _get_dml_session(onnx_path: Path):
    key = str(onnx_path)
    if key not in _DML_SESSION_CACHE:
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess = ort.InferenceSession(
            str(onnx_path), opts, providers=["DmlExecutionProvider", "CPUExecutionProvider"]
        )
        _DML_SESSION_CACHE[key] = sess
    return _DML_SESSION_CACHE[key]


def _detect_dml(
    image_path: Path,
    onnx_path: Path,
    *,
    confidence: float,
    iou_threshold: float,
    imgsz: int = 1024,
    class_ids: tuple[int, ...] | None = (0,),
    text_class_ids: tuple[int, ...] | None = (1,),
) -> tuple[list[BBox], list[BBox]]:
    """Fast DirectML GPU inference on Windows DirectX 12 hardware (e.g. GTX 1650)."""
    import torch
    from ultralytics.utils.nms import non_max_suppression

    sess = _get_dml_session(onnx_path)

    with Image.open(image_path) as img:
        img_rgb = img.convert("RGB")
        orig_w, orig_h = img_rgb.size

        scale = min(imgsz / orig_w, imgsz / orig_h)
        nw, nh = int(round(orig_w * scale)), int(round(orig_h * scale))
        resized = img_rgb.resize((nw, nh), Image.BILINEAR)

        pad_w = imgsz - nw
        pad_h = imgsz - nh
        pad_x = pad_w // 2
        pad_y = pad_h // 2
        padded = Image.new("RGB", (imgsz, imgsz), (114, 114, 114))
        padded.paste(resized, (pad_x, pad_y))

        arr = np.asarray(padded, dtype=np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))
        arr = np.expand_dims(arr, 0)

    input_name = sess.get_inputs()[0].name
    outputs = sess.run(None, {input_name: arr})
    preds = torch.from_numpy(outputs[0])

    results = non_max_suppression(preds, conf_thres=confidence, iou_thres=iou_threshold)

    panels: list[BBox] = []
    texts: list[BBox] = []
    if results and len(results[0]) > 0:
        for det in results[0]:
            x1, y1, x2, y2, conf, cls_id = det.tolist()
            cls_id = int(cls_id)
            is_panel = class_ids is None or cls_id in class_ids
            is_text = text_class_ids is not None and cls_id in text_class_ids
            if not is_panel and not is_text:
                continue

            x1 = max(0, min(orig_w, (x1 - pad_x) / scale))
            y1 = max(0, min(orig_h, (y1 - pad_y) / scale))
            x2 = max(0, min(orig_w, (x2 - pad_x) / scale))
            y2 = max(0, min(orig_h, (y2 - pad_y) / scale))
            x1, y1, x2, y2 = (int(round(v)) for v in (x1, y1, x2, y2))
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(orig_w, x2), min(orig_h, y2)
            if x2 <= x1 or y2 <= y1:
                continue

            box = BBox(x1=x1, y1=y1, x2=x2, y2=y2)
            if is_panel:
                panels.append(box)
            if is_text:
                texts.append(box)

    return panels, texts


def _load_model(weights_path: Path, imgsz: int):
    """Load and cache the detector. Keyed by path and input size."""
    key = (str(weights_path), imgsz)
    if key in _MODEL_CACHE:
        return _MODEL_CACHE[key]

    try:
        from ultralytics import YOLO
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ImportError(
            "ultralytics is required for crop.detector: yolo. "
            "Install it with `pip install ultralytics`, or set crop.detector: opencv."
        ) from exc

    model = YOLO(str(weights_path))
    _MODEL_CACHE[key] = model
    return model


def _detect_yolo(
    image_path: Path,
    weights_path: Path | None,
    *,
    confidence: float,
    iou_threshold: float,
    imgsz: int = 1024,
    class_ids: tuple[int, ...] | None = (0,),
    text_class_ids: tuple[int, ...] | None = (1,),
) -> tuple[list[BBox], list[BBox]]:
    """Detect panels and text regions with a YOLO model.

    Returns `(panel_boxes, text_boxes)`.

    `imgsz` matters more than it looks. A manga page is tall and a full page
    squeezed into 640px loses the thin panels down the side of a busy layout.
    1024 keeps them.

    `class_ids` selects what counts as a panel and `text_class_ids` what counts
    as text. The model in use detects speech and text regions as well, and
    splitting them here is what lets the cropper guarantee a bubble is never
    sliced in half. Classes matching neither are ignored.
    """
    if weights_path:
        onnx_candidate = Path(weights_path).with_suffix(".onnx")
        if onnx_candidate.exists() and _is_dml_available():
            return _detect_dml(
                image_path,
                onnx_candidate,
                confidence=confidence,
                iou_threshold=iou_threshold,
                imgsz=imgsz,
                class_ids=class_ids,
                text_class_ids=text_class_ids,
            )

    if not weights_path or not Path(weights_path).exists():
        raise FileNotFoundError(
            f"YOLO weights not found at {weights_path}.\n"
            "Either place your panel detector weights there and set "
            "crop.weights_path in config.yaml, or set crop.detector: opencv to "
            "use the built-in XY-cut detector."
        )

    model = _load_model(Path(weights_path), imgsz)
    results = model.predict(
        source=str(image_path),
        imgsz=imgsz,
        conf=confidence,
        iou=iou_threshold,
        verbose=False,
    )
    if not results:
        return [], []

    result = results[0]
    boxes_object = getattr(result, "boxes", None)
    if boxes_object is None or boxes_object.xyxy is None or len(boxes_object.xyxy) == 0:
        return [], []

    height, width = result.orig_shape
    classes = (
        boxes_object.cls.tolist()
        if boxes_object.cls is not None
        else [0] * len(boxes_object.xyxy)
    )

    panels: list[BBox] = []
    texts: list[BBox] = []
    for coordinates, class_id in zip(boxes_object.xyxy.tolist(), classes, strict=True):
        class_id = int(class_id)
        is_panel = class_ids is None or class_id in class_ids
        is_text = text_class_ids is not None and class_id in text_class_ids
        # A detector with a single class reports everything as class 0, so the
        # panel branch has to win rather than the text branch claiming it.
        if not is_panel and not is_text:
            continue

        x1, y1, x2, y2 = (int(round(v)) for v in coordinates)
        # Clamp to the page: detectors occasionally overshoot the border.
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(width, x2), min(height, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        box = BBox(x1=x1, y1=y1, x2=x2, y2=y2)
        if is_panel:
            panels.append(box)
        if is_text:
            texts.append(box)

    return panels, texts


# ---------------------------------------------------------------------------
# Recursive XY-cut
# ---------------------------------------------------------------------------


def _detect_opencv(
    grayscale: np.ndarray,
    *,
    gutter_white_ratio: float = 0.97,
    min_gutter_px: int = 12,
    depth_limit: int = 6,
    min_panel_share: float = 0.05,
    ink_close_px: int = 2,
    trim_margin_px: int = 3,
    border_ink_ratio: float = 0.5,
) -> list[BBox]:
    """Recursive XY-cut over the page's white gutters.

    At each step, look for a near-white band spanning the region. A horizontal
    band splits the region top/bottom; a vertical band splits it left/right. Stop
    when no gutter qualifies or the depth limit is hit.
    """
    if grayscale.size == 0:
        return []

    binary = _binarize(grayscale, ink_close_px=ink_close_px)

    # Cut on the content area, not the whole page. A panel border is solid ink
    # along its own length but covers only a fraction of a full page, so
    # evaluating a cut against the raw page dilutes that evidence and the border
    # test rejects real gutters. Trimming to the ink first keeps the test
    # meaningful, and also ignores page margins and blank areas.
    content = _content_box(binary, margin=trim_margin_px)
    if content is None:
        return []
    x0, y0, x1, y1 = content
    working = binary[y0:y1, x0:x1]

    regions = _xy_cut(
        working,
        depth=depth_limit,
        gutter_white_ratio=gutter_white_ratio,
        min_gutter_px=min_gutter_px,
        min_panel_share=min_panel_share,
        border_ink_ratio=border_ink_ratio,
    )

    # A cut region's bounds are set by the gutters around it, so each one still
    # carries a strip of white margin. Trimming to the ink inside lands the crop
    # on the panel border, which is what the viewer should see. Trim in working
    # coordinates against the working image, then shift back to page space once.
    boxes: list[BBox] = []
    for x, y, width, height in regions:
        tx, ty, tw, th = _trim_to_ink(working, (x, y, width, height), margin=trim_margin_px)
        x, y = tx + x0, ty + y0
        if tw > 2 and th > 2:
            boxes.append(BBox(x1=x, y1=y, x2=x + tw, y2=y + th))
    return boxes


def _content_box(binary: np.ndarray, *, margin: int) -> tuple[int, int, int, int] | None:
    """Bounding box of all ink on the page, expanded by `margin`."""
    ink = binary > 128
    if not ink.any():
        return None
    rows = np.flatnonzero(ink.any(axis=1))
    cols = np.flatnonzero(ink.any(axis=0))
    height, width = binary.shape
    y1 = max(0, int(rows[0]) - margin)
    y2 = min(height, int(rows[-1]) + 1 + margin)
    x1 = max(0, int(cols[0]) - margin)
    x2 = min(width, int(cols[-1]) + 1 + margin)
    return (x1, y1, x2, y2)


def _trim_to_ink(
    binary: np.ndarray, region: tuple[int, int, int, int], *, margin: int
) -> tuple[int, int, int, int]:
    """Shrink a region to the bounding box of its ink, plus a small margin."""
    x, y, width, height = region
    sub = binary[y : y + height, x : x + width]
    ink = sub > 128
    if not ink.any():
        return region

    rows = np.flatnonzero(ink.any(axis=1))
    cols = np.flatnonzero(ink.any(axis=0))
    y1 = y + max(0, int(rows[0]) - margin)
    y2 = y + min(height, int(rows[-1]) + 1 + margin)
    x1 = x + max(0, int(cols[0]) - margin)
    x2 = x + min(width, int(cols[-1]) + 1 + margin)
    return (x1, y1, x2 - x1, y2 - y1)


def _binarize(grayscale: np.ndarray, *, ink_close_px: int = 5) -> np.ndarray:
    """Threshold to ink-on-white, then thicken the ink into solid blocks.

    Thickening matters more than it looks. Line art is thin, sparse strokes, so
    a column running down the middle of a panel can average only a few percent
    ink and read as an empty gutter. Dilating the ink closes those gaps and makes
    panel interiors solid, while a genuine gutter stays empty because it is
    wider than the kernel.
    """
    import cv2

    blurred = cv2.GaussianBlur(grayscale, (3, 3), 0)
    _, ink = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if ink_close_px > 0:
        size = ink_close_px | 1  # force an odd kernel
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (size, size))
        ink = cv2.dilate(ink, kernel, iterations=1)
    return ink


def _xy_cut(
    binary: np.ndarray,
    *,
    depth: int,
    gutter_white_ratio: float,
    min_gutter_px: int,
    min_panel_share: float,
    border_ink_ratio: float,
    origin: tuple[int, int] = (0, 0),
) -> list[tuple[int, int, int, int]]:
    """Recursively split a region on its white gutters.

    `origin` is the region this array was cut from, in page coordinates. It is
    threaded through the recursion so the returned boxes are in page space
    rather than local space.

    A cut is chosen by balance, not by width. Panel interiors are full of small
    empty gaps, so the widest white band inside a panel is often a false
    positive. A real gutter sits between two pieces of content and therefore
    splits the region into two reasonably large halves, so candidates are ranked
    by how close the cut is to the region's midpoint, with width as tiebreak.
    """
    height, width = binary.shape
    origin_x, origin_y = origin

    if width < min_gutter_px * 2 or height < min_gutter_px * 2 or depth <= 0:
        return [(origin_x, origin_y, width, height)]

    shared = {
        "gutter_white_ratio": gutter_white_ratio,
        "min_gutter_px": min_gutter_px,
        "min_panel_share": min_panel_share,
        "border_ink_ratio": border_ink_ratio,
    }

    def split(
        region: np.ndarray,
        axis: int,
        total: int,
        new_origin: tuple[int, int],
    ) -> list[tuple[int, int, int, int]] | None:
        band = _best_band(
            region,
            axis=axis,
            ratio=gutter_white_ratio,
            min_size=min_gutter_px,
            total=total,
            min_panel_share=min_panel_share,
            border_ink_ratio=border_ink_ratio,
        )
        if band is None:
            return None
        start, stop = band
        if axis == 0:
            first, second = region[:start, :], region[stop:, :]
            second_origin = (new_origin[0], new_origin[1] + stop)
        else:
            first, second = region[:, :start], region[:, stop:]
            second_origin = (new_origin[0] + stop, new_origin[1])
        return _xy_cut(
            first, depth=depth - 1, origin=new_origin, **shared
        ) + _xy_cut(second, depth=depth - 1, origin=second_origin, **shared)

    # Horizontal gutters first: manga pages divide top/bottom before left/right,
    # and that is the grain of the layout.
    horizontal = split(binary, axis=0, total=height, new_origin=(origin_x, origin_y))
    if horizontal is not None:
        return horizontal

    vertical = split(binary, axis=1, total=width, new_origin=(origin_x, origin_y))
    if vertical is not None:
        return vertical

    return [(origin_x, origin_y, width, height)]


def _best_band(
    binary: np.ndarray,
    *,
    axis: int,
    ratio: float,
    min_size: int,
    total: int,
    min_panel_share: float,
    border_ink_ratio: float,
) -> tuple[int, int] | None:
    """Pick the best gutter band on one axis, or None if the region is atomic.

    A candidate must satisfy three tests, and all three are needed:

    1. Every line in the band is nearly empty, judged per line rather than on
       the band average, so a panel's white sky cannot read as a gutter.
    2. Both sides of the cut keep a real share of the region, so a page margin
       cannot masquerade as a divider.
    3. The lines immediately outside the band are ink-heavy, meaning a panel
       border sits on each side. This is the test that actually separates a
       real gutter from a low-ink column of artwork inside a panel.
    """
    ink = binary > 128
    line_ink = ink.mean(axis=1) if axis == 0 else ink.mean(axis=0)
    clean = line_ink <= (1.0 - ratio)

    bands: list[tuple[int, int]] = []
    start: int | None = None
    for index, is_clean in enumerate(clean):
        if is_clean and start is None:
            start = index
        elif not is_clean and start is not None:
            bands.append((start, index))
            start = None
    if start is not None:
        bands.append((start, len(clean)))

    candidates = [b for b in bands if b[1] - b[0] >= min_size]
    if not candidates:
        return None

    floor = max(total * min_panel_share, 1.0)

    def usable(band: tuple[int, int]) -> bool:
        first, second = band[0], total - band[1]
        return first >= floor and second >= floor and _has_borders(
            line_ink, band[0], band[1], border_ink_ratio
        )

    usable_bands = [b for b in candidates if usable(b)]
    if not usable_bands:
        return None

    # Rank by distance from the region midpoint, then by width.
    midpoint = total / 2.0
    return min(
        usable_bands,
        key=lambda b: (abs((b[0] + b[1]) / 2.0 - midpoint), -(b[1] - b[0])),
    )


def _has_borders(
    line_ink: np.ndarray, start: int, stop: int, border_ink_ratio: float, *, probe_px: int = 3
) -> bool:
    """True when a panel border sits on both sides of a gutter band.

    A real gutter is the white gap between two panel borders, so the lines
    immediately outside it are nearly solid ink. Artwork inside a panel can be
    sparse enough to read as a gutter, but it is never a solid line, so this
    check rejects it. It also assumes the page has drawn panel borders, which
    is why a YOLO detector is the default and this is the fallback.
    """
    before = line_ink[max(0, start - probe_px) : start]
    after = line_ink[stop : stop + probe_px]
    if before.size == 0 or after.size == 0:
        # A band flush against the region edge has no border to lean on.
        return False
    return bool(before.mean() >= border_ink_ratio and after.mean() >= border_ink_ratio)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def dedupe(
    boxes: list[BBox], *, iou_threshold: float = 0.5, max_growth: float = 1.15
) -> list[BBox]:
    """Collapse duplicate detections by merging them, not by discarding one.

    The old behaviour kept the larger box and threw the other away. That is
    correct for a jittered re-detection of the same panel, and wrong for
    anything else: whenever two genuinely different panels overlapped, one of
    them vanished from the chapter entirely, taking its artwork and its
    dialogue with it. Nothing downstream can detect the loss, because a shorter
    chapter looks exactly like a correct one.

    So the two cases are separated. A union that grows the box by no more than
    `max_growth` is the same panel seen twice, so it is merged. A union that
    grows it further is two real panels that overlap, and both are kept.
    """
    if not boxes:
        return []

    kept: list[BBox] = []
    # Largest first, so a loose box is available to absorb a tight one.
    for box in sorted(boxes, key=lambda b: b.area, reverse=True):
        merged = box
        survivors: list[BBox] = []
        for other in kept:
            if merged.iou(other) < iou_threshold:
                survivors.append(other)
                continue

            union = merged.union(other)
            budget = max(merged.area, other.area) * max_growth
            if union.area <= budget:
                merged = union
                continue

            # A real overlap rather than a duplicate. Keeping both costs a
            # little airtime; keeping one would silently lose a panel.
            survivors.append(other)
            _log.debug(
                "Keeping overlapping detections %s and %s: union area %d exceeds "
                "%d, so these look like two panels rather than one",
                other.to_xywh(),
                merged.to_xywh(),
                union.area,
                int(budget),
            )
        survivors.append(merged)
        kept = survivors
    return kept


def _parse_class_ids(value) -> tuple[int, ...] | None:
    """Read the accepted class ids from config.

    `null` or an empty list means accept every class, which is right for a
    single-class panel detector and wrong for one that also finds text.
    """
    if value is None:
        return None
    if isinstance(value, int):
        return (value,)
    parsed = tuple(int(v) for v in value)
    return parsed or None

def _area_ratio(box: BBox, page_width: int, page_height: int) -> float:
    total = page_width * page_height
    return box.area / total if total else 0.0


def _load_manual_boxes(manual_dir: Path, image_path: Path) -> list[BBox] | None:
    """Read hand-authored boxes for one page, if the user supplied any.

    Format: {"005.png": [[x1, y1, x2, y2], ...]} in reading order.
    """
    manual_path = manual_dir / MANUAL_BOXES_FILENAME
    if not manual_path.exists():
        return None
    try:
        data = json.loads(manual_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _log.warning("Ignoring malformed %s: %s", manual_path, exc)
        return None

    entry = data.get(image_path.name)
    if not entry:
        return None
    return [BBox(x1=c[0], y1=c[1], x2=c[2], y2=c[3]) for c in entry]
