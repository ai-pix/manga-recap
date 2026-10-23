"""Panel detection: the OpenCV XY-cut fallback and box deduplication."""

from __future__ import annotations

import numpy as np
import pytest
from conftest import LAYOUTS, iou, make_page

from manga_recap.core.schema import BBox
from manga_recap.stages.s1_crop.detector import _detect_opencv, dedupe


def detect_page(layout, seed=11, **kwargs):
    grayscale = np.asarray(make_page(layout, seed).convert("L"))
    settings = {"gutter_white_ratio": 0.97, "min_gutter_px": 12}
    settings.update(kwargs)
    return _detect_opencv(grayscale, **settings)


def expected_boxes(layout):
    return [BBox(x1=a, y1=b, x2=c, y2=d) for a, b, c, d in layout]


def match_all(detected, expected, threshold=0.75):
    """Greedily match detections to expected panels; return unmatched both sides."""
    unmatched_expected = list(expected)
    unmatched_detected = []
    for box in detected:
        best, best_iou = None, 0.0
        for candidate in unmatched_expected:
            score = iou(box, candidate)
            if score > best_iou:
                best, best_iou = candidate, score
        if best is not None and best_iou >= threshold:
            unmatched_expected.remove(best)
        else:
            unmatched_detected.append(box)
    return unmatched_expected, unmatched_detected


@pytest.mark.parametrize("page_index", range(len(LAYOUTS)))
def test_finds_every_panel_on_a_conventional_page(page_index):
    layout = LAYOUTS[page_index]
    detected = detect_page(layout, seed=page_index + 1)

    missed, spurious = match_all(detected, expected_boxes(layout))
    assert not missed, f"missed {len(missed)} panel(s) on page {page_index + 1}"
    assert not spurious, f"{len(spurious)} spurious box(es) on page {page_index + 1}"


def test_crops_land_on_the_panel_border_not_the_gutter():
    """Trimming to ink is what keeps a panel from carrying white margin."""
    detected = detect_page(LAYOUTS[0], seed=1)
    x1, y1, x2, y2 = LAYOUTS[0][0]

    box = min(detected, key=lambda b: abs(b.x1 - x1) + abs(b.y1 - y1))
    # Within a few pixels of the true border, not the ~24px page margin.
    assert abs(box.x1 - x1) <= 8
    assert abs(box.y1 - y1) <= 8
    assert abs(box.x2 - x2) <= 8


def test_page_margins_do_not_become_panels():
    detected = detect_page(LAYOUTS[0], seed=1)
    for box in detected:
        assert box.x1 >= 10, "a box starting in the left margin is suspicious"
        assert box.y1 >= 10, "a box starting in the top margin is suspicious"


def test_white_page_yields_nothing():
    from PIL import Image

    blank = np.asarray(Image.new("RGB", (800, 600), (255, 255, 255)).convert("L"))
    assert _detect_opencv(blank) == []


def test_empty_array_is_handled():
    assert _detect_opencv(np.zeros((0, 0), dtype=np.uint8)) == []


# -- deduplication ----------------------------------------------------------


def test_dedupe_collapses_near_identical_boxes():
    original = BBox(x1=10, y1=10, x2=110, y2=110)
    jitter = BBox(x1=12, y1=11, x2=109, y2=112)
    far = BBox(x1=400, y1=400, x2=500, y2=500)

    result = dedupe([original, jitter, far], iou_threshold=0.5)

    assert len(result) == 2
    assert any(b.iou(original) > 0.9 for b in result)
    assert any(b.iou(far) > 0.9 for b in result)


def test_dedupe_keeps_distinct_panels():
    a = BBox(x1=0, y1=0, x2=100, y2=100)
    b = BBox(x1=200, y1=0, x2=300, y2=100)
    assert len(dedupe([a, b], iou_threshold=0.5)) == 2


def test_dedupe_prefers_the_larger_box():
    tight = BBox(x1=10, y1=10, x2=90, y2=90)
    loose = BBox(x1=0, y1=0, x2=100, y2=100)

    result = dedupe([tight, loose], iou_threshold=0.5)

    assert len(result) == 1
    assert result[0].area == loose.area


def test_dedupe_on_empty_input():
    assert dedupe([], iou_threshold=0.5) == []
