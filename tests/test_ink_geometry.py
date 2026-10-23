"""Tracing a panel's outline, for the content that is not a rectangle.

YOLO returns rectangles. These tests are about the pages where that assumption
breaks: a bubble drawn across a border, a hand breaking the frame, a full-bleed
panel with no border at all. The synthetic pages are drawn to contain exactly one
of those situations each, so a failure points at a specific behaviour rather
than at "detection got worse".
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image, ImageDraw

from manga_recap.core.schema import BBox
from manga_recap.stages.s1_crop.inkmask import (
    content_bounds,
    expand_box,
    missing_panel_candidates,
    page_masks,
    trace_outline,
    trace_outlines,
)

W, H = 400, 600
WHITE = (255, 255, 255)
INK = (0, 0, 0)


def _page() -> Image.Image:
    return Image.new("RGB", (W, H), WHITE)


def _masks(image: Image.Image, **kwargs):
    return page_masks(np.asarray(image.convert("RGB")), **kwargs)


# ---------------------------------------------------------------------------
# Splitting a page into paper, ink and content
# ---------------------------------------------------------------------------


def test_a_blank_page_has_no_content():
    masks = _masks(_page())

    assert not masks.ink.any()
    assert not masks.content.any()
    assert content_bounds(masks.content, W, H) is None


def test_drawn_ink_is_content_and_the_margin_is_not():
    image = _page()
    ImageDraw.Draw(image).rectangle([100, 100, 300, 500], outline=INK, width=3)

    bounds = content_bounds(_masks(image).content, W, H)

    assert bounds is not None
    # Margins excluded, and the stroke's own width included.
    assert bounds.x1 >= 97 and bounds.x2 <= 303
    assert bounds.y1 >= 97 and bounds.y2 <= 503


def test_white_enclosed_by_ink_counts_as_content():
    """A bubble's white interior is inside the drawing, not page background.

    This is what makes the content extent the true drawn area rather than a
    bounding box of the strokes, and it is why coverage can be measured against
    something meaningful.
    """
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 350, 550], outline=INK, width=3)
    draw.ellipse([150, 200, 300, 300], outline=INK, width=3)

    masks = _masks(image)

    assert not masks.ink[250, 200]  # it is white
    assert masks.content[250, 200]  # but it is inside the drawing


def test_a_grey_scan_still_resolves_paper_and_ink():
    """The paper threshold adapts, so a dark scan is not all paper."""
    image = Image.new("RGB", (W, H), (200, 200, 200))
    ImageDraw.Draw(image).rectangle([100, 100, 300, 500], outline=(20, 20, 20), width=3)

    masks = _masks(image)

    assert masks.ink.sum() > 0
    assert not masks.content[10, 10]


def test_a_tinted_background_is_not_paper():
    """Colour pages are the hard case, and the reason the channel spread exists.

    A pale coloured panel background is bright, so a pure luminance threshold
    counts it as paper and the page reads as empty margin. A tinted pixel is not
    paper however bright it is.
    """
    image = Image.new("RGB", (W, H), (250, 228, 232))
    ImageDraw.Draw(image).rectangle([100, 100, 300, 500], outline=(20, 20, 20), width=3)

    masks = _masks(image)

    assert not masks.paper[300, 200]
    assert masks.content[300, 200]


def test_aged_paper_is_still_paper():
    """The colour gate must not reject a yellowed scan.

    Narrow enough to exclude a pale panel tint, wide enough to survive a
    decade-old scan, and the test is what stops the two being confused.
    """
    image = Image.new("RGB", (W, H), (238, 234, 225))
    ImageDraw.Draw(image).rectangle([100, 100, 300, 500], outline=(20, 20, 20), width=3)

    masks = _masks(image)

    assert masks.paper[10, 10]
    assert not masks.content[10, 10]


# ---------------------------------------------------------------------------
# Closing the loop
# ---------------------------------------------------------------------------


def test_a_closed_frame_traces_to_its_own_border():
    """Nothing to find, because the frame closes on itself.

    A drawn stroke sits a pixel or two proud of the box the detector returned, so
    the trace legitimately reaches that far. The point is that it stops there:
    the growth is a stroke width, not a journey across the gutter.
    """
    image = _page()
    ImageDraw.Draw(image).rectangle([50, 50, 350, 550], outline=INK, width=3)
    box = BBox(x1=50, y1=50, x2=350, y2=550)

    grown, _ = trace_outline(_masks(image), box, W, H)

    assert grown is not None
    assert grown.x2 - box.x2 <= 3
    assert grown.y2 - box.y2 <= 3


def test_a_bubble_breaking_the_border_is_traced_around():
    """The idea, in one test.

    The border is a connected stroke, and a bubble drawn across it is connected
    to the border, so one contour encloses both. The trace goes round the bubble
    without ever having to recognise it as a bubble, and the bounding box of the
    trace is the panel's real extent.
    """
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 200, 550], outline=INK, width=3)
    # Drawn last so its outline sits over the border and the two are one stroke.
    draw.ellipse([180, 200, 300, 300], fill=WHITE, outline=INK, width=3)

    grown, _ = trace_outline(
        _masks(image), BBox(x1=50, y1=50, x2=200, y2=550), W, H, max_growth=120
    )

    assert grown is not None
    assert grown.x2 >= 290, "the trace should have gone round the far side of the bubble"


def test_a_hand_breaking_the_frame_is_traced_around():
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 200, 300], outline=INK, width=3)
    draw.ellipse([195, 150, 290, 240], fill=(40, 40, 40), outline=INK, width=3)

    grown, _ = trace_outline(
        _masks(image), BBox(x1=50, y1=50, x2=200, y2=300), W, H, max_growth=120
    )

    assert grown is not None
    assert grown.x2 > 200


def test_growth_is_capped_by_the_maximum():
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 200, 300], outline=INK, width=3)
    draw.ellipse([195, 150, 390, 240], fill=(40, 40, 40), outline=INK, width=3)

    grown, _ = trace_outline(
        _masks(image), BBox(x1=50, y1=50, x2=200, y2=300), W, H, max_growth=20
    )

    assert grown is not None
    assert grown.x2 <= 220


def test_growth_can_be_switched_off_entirely():
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 200, 550], outline=INK, width=3)
    draw.ellipse([180, 200, 300, 300], fill=WHITE, outline=INK, width=3)

    grown, reason = trace_outline(
        _masks(image), BBox(x1=50, y1=50, x2=200, y2=550), W, H, max_growth=0
    )

    assert grown is None
    assert "growth cap" in reason


# ---------------------------------------------------------------------------
# Deciding whether the trace is a frame at all
# ---------------------------------------------------------------------------


def test_a_stroke_that_is_not_a_frame_is_not_believed():
    """The loop has to close, or the bounding box means nothing.

    Without this test any blob near the box would stretch the crop to wherever
    the blob happened to end, which on a connected page is the whole page.
    """
    image = _page()
    draw = ImageDraw.Draw(image)
    # A short vertical stroke beside the box: ink, but no frame.
    draw.line([205, 100, 205, 200], fill=INK, width=4)

    grown, reason = trace_outline(
        _masks(image), BBox(x1=50, y1=50, x2=200, y2=550), W, H
    )

    assert grown is None
    assert "no outline closed" in reason


def test_a_blob_far_larger_than_the_panel_is_rejected():
    """A frame encloses about its own panel. A page-sized blob does not.

    A loop that genuinely wraps the box is ambiguous with a genuinely large
    panel, so the area guard is the only thing standing between a large frame and
    a blob. The test uses a ratio no real panel would reach.
    """
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.ellipse([5, 5, 395, 595], outline=INK, width=3)

    grown, _ = trace_outline(
        _masks(image), BBox(x1=150, y1=250, x2=250, y2=350), W, H
    )

    assert grown is None


def test_no_stroke_near_the_box_is_not_an_error():
    image = _page()
    ImageDraw.Draw(image).rectangle([300, 400, 380, 500], outline=INK, width=3)

    grown, reason = trace_outline(
        _masks(image), BBox(x1=50, y1=50, x2=200, y2=300), W, H
    )

    assert grown is None
    assert "loop" in reason


# ---------------------------------------------------------------------------
# Deciding whose outline it is
# ---------------------------------------------------------------------------


def test_a_shared_stroke_is_not_claimed_by_either_panel():
    """Manga often draws one line as the right edge of a panel and the left of
    the next, so a contour encloses both and growing to it would swallow the
    neighbour. The trace has to be shown to belong to one panel before it is
    allowed to move its box.
    """
    image = _page()
    draw = ImageDraw.Draw(image)
    # Abutting panels: the stroke at x=200 is drawn once and serves both.
    draw.rectangle([50, 50, 200, 550], outline=INK, width=3)
    draw.rectangle([200, 50, 380, 550], outline=INK, width=3)
    left = BBox(x1=50, y1=50, x2=200, y2=550)
    right = BBox(x1=200, y1=50, x2=380, y2=550)
    masks = _masks(image)

    # Tracing takes the whole page's boxes, and the tie-break uses them all as
    # siblings, which is why a shared stroke has to be judged against both.
    assert trace_outlines(masks, [left, right], W, H, max_growth=40) == {}


def test_an_outline_that_stops_short_of_the_neighbour_is_claimed():
    """The rejection rule must not throw away a real overhang.

    A rule that also discarded genuine overhangs would be worse than none, so
    the accepted case is pinned as firmly as the rejected one.
    """
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([50, 50, 200, 550], outline=INK, width=3)
    draw.rectangle([240, 50, 380, 550], outline=INK, width=3)
    # Breaks out of the left panel and ends well before the gutter does.
    draw.ellipse([190, 250, 222, 300], fill=(40, 40, 40), outline=INK, width=2)
    left = BBox(x1=50, y1=50, x2=200, y2=550)
    right = BBox(x1=240, y1=50, x2=380, y2=550)

    grown = trace_outlines(_masks(image), [left, right], W, H, max_growth=40)

    assert (left.x1, left.y1, left.x2, left.y2) in grown
    assert grown[(left.x1, left.y1, left.x2, left.y2)].x2 > 200


def test_expand_box_leaves_a_closed_panel_essentially_untouched():
    image = _page()
    ImageDraw.Draw(image).rectangle([50, 50, 350, 550], outline=INK, width=3)
    box = BBox(x1=50, y1=50, x2=350, y2=550)

    grown, _ = expand_box(_masks(image), box, W, H)

    # A stroke width of drift is correct; anything more means the trace ran off.
    assert grown.x2 - box.x2 <= 3
    assert grown.y2 - box.y2 <= 3


# ---------------------------------------------------------------------------
# Second opinion on missed panels
# ---------------------------------------------------------------------------


def test_leftover_ink_outside_every_panel_is_offered_as_a_candidate():
    """The page-10 case: one small panel found, a large one walked past."""
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 20, 380, 100], outline=INK, width=3)
    draw.rectangle([20, 150, 190, 580], outline=INK, width=3)
    draw.rectangle([210, 150, 380, 580], outline=INK, width=3)

    candidates = missing_panel_candidates(
        _masks(image), [BBox(x1=20, y1=20, x2=380, y2=100)], W, H, min_ink_ratio=0.01
    )

    assert len(candidates) == 2
    # Largest first, so the most likely missed panel is easy to spot.
    assert candidates[0].area >= candidates[1].area
    assert candidates[0].y1 > 100


def test_a_fully_detected_page_offers_no_candidates():
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 20, 190, 290], outline=INK, width=3)
    draw.rectangle([210, 20, 380, 290], outline=INK, width=3)
    draw.rectangle([20, 310, 380, 580], outline=INK, width=3)

    candidates = missing_panel_candidates(
        _masks(image),
        [
            BBox(x1=20, y1=20, x2=190, y2=290),
            BBox(x1=210, y1=20, x2=380, y2=290),
            BBox(x1=20, y1=310, x2=380, y2=580),
        ],
        W,
        H,
        min_ink_ratio=0.01,
    )

    assert candidates == []


def test_ink_smaller_than_the_threshold_is_not_offered():
    image = _page()
    draw = ImageDraw.Draw(image)
    draw.rectangle([20, 20, 380, 580], outline=INK, width=3)
    # A small stray mark in the gutter.
    draw.line([395, 300, 398, 303], fill=INK, width=1)

    candidates = missing_panel_candidates(
        _masks(image), [BBox(x1=20, y1=20, x2=380, y2=580)], W, H, min_ink_ratio=0.02
    )

    assert candidates == []


def test_a_page_with_no_panels_offers_nothing():
    """Nothing is subtracted, so the whole page would be reported as candidates."""
    image = _page()
    ImageDraw.Draw(image).rectangle([20, 20, 380, 580], outline=INK, width=3)

    assert missing_panel_candidates(_masks(image), [], W, H) == []


def test_a_white_page_offers_no_candidates():
    assert missing_panel_candidates(
        _masks(_page()), [BBox(x1=1, y1=1, x2=10, y2=10)], W, H
    ) == []


@pytest.mark.parametrize("size", [(1, 1), (8, 6), (W, H)])
def test_tiny_and_odd_page_sizes_do_not_crash(size):
    width, height = size
    image = Image.new("RGB", size, WHITE)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, width - 1, height - 1], outline=INK)
    box = BBox(x1=0, y1=0, x2=max(1, width - 1), y2=max(1, height - 1))

    trace_outline(_masks(image), box, width, height)
    missing_panel_candidates(_masks(image), [box], width, height)


def test_a_zero_sized_page_is_handled_rather_than_crashing():
    image = Image.new("RGB", (0, 0), WHITE)

    masks = _masks(image)

    assert not masks.ink.any()
    assert content_bounds(masks.content, 0, 0) is None
