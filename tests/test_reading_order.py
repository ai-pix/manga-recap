"""Reading order: manga reads right-to-left, top-to-bottom."""

from __future__ import annotations

from manga_recap.core.schema import BBox
from manga_recap.stages.s1_crop.ordering import (
    assign_reading_order,
    order_across_pages,
)


def boxes_from(spec):
    return [BBox(x1=x1, y1=y1, x2=x2, y2=y2) for _, x1, y1, x2, y2 in spec]


def ordered_labels(spec, boxes, ranks):
    """Labels of the boxes, in reading order."""
    return [spec[i][0] for i in sorted(range(len(boxes)), key=lambda i: ranks[i])]


# label, x1, y1, x2, y2
THREE_ROWS = [
    ("top_left", 20, 20, 320, 260),
    ("top_mid", 340, 20, 640, 260),
    ("top_right", 660, 20, 980, 260),
    ("mid_left", 20, 280, 490, 560),
    ("mid_right", 510, 280, 980, 560),
    ("bottom_full", 20, 580, 980, 780),
]


def test_right_to_left_within_a_row():
    boxes = boxes_from(THREE_ROWS)
    ranks = assign_reading_order(boxes, right_to_left=True)
    got = ordered_labels(THREE_ROWS, boxes, ranks)

    assert got == [
        "top_right",
        "top_mid",
        "top_left",
        "mid_right",
        "mid_left",
        "bottom_full",
    ]


def test_left_to_right_when_configured():
    boxes = boxes_from(THREE_ROWS)
    ranks = assign_reading_order(boxes, right_to_left=False)
    got = ordered_labels(THREE_ROWS, boxes, ranks)

    assert got[0] == "top_left"
    assert got[-1] == "bottom_full"


def test_rows_are_top_to_bottom():
    boxes = boxes_from(THREE_ROWS)
    ranks = assign_reading_order(boxes, right_to_left=True)
    by_label = {entry[0]: ranks[i] for i, entry in enumerate(THREE_ROWS)}

    assert by_label["top_right"] < by_label["mid_right"] < by_label["bottom_full"]


def test_single_panel_gets_rank_one():
    boxes = [BBox(x1=0, y1=0, x2=100, y2=100)]
    assert assign_reading_order(boxes) == [1]


def test_empty_input_is_empty_output():
    assert assign_reading_order([]) == []


def test_ranks_are_a_contiguous_sequence():
    boxes = boxes_from(THREE_ROWS)
    ranks = assign_reading_order(boxes, right_to_left=True)
    assert sorted(ranks) == list(range(1, len(boxes) + 1))


def test_staggered_layout_still_groups_rows():
    # A row whose panels are offset vertically must still read as one row.
    spec = [
        ("right", 700, 20, 980, 250),
        ("left", 20, 40, 660, 270),
    ]
    boxes = boxes_from(spec)
    ranks = assign_reading_order(boxes, right_to_left=True, page_height=300)
    got = ordered_labels(spec, boxes, ranks)
    assert got == ["right", "left"]


def test_tall_side_panel_with_stacked_panels_beside_it():
    """A regression case, and a very common manga layout.

    A tall panel down the left with two panels stacked to its right. Grouping on
    vertical overlap merges all three into one row and then reads them by x,
    which puts the bottom-right panel first. Grouping on top edges keeps the
    stacked pair in separate rows.
    """
    spec = [
        ("tall_left", 20, 20, 320, 980),
        ("right_top", 340, 20, 980, 480),
        ("right_bottom", 340, 500, 980, 980),
    ]
    boxes = boxes_from(spec)
    ranks = assign_reading_order(boxes, right_to_left=True, page_height=1000)
    got = ordered_labels(spec, boxes, ranks)

    # Row 1 is the top pair, read right to left; row 2 is the bottom panel.
    assert got == ["right_top", "tall_left", "right_bottom"]


def test_mirror_image_tall_panel_on_the_right():
    spec = [
        ("left_top", 20, 20, 660, 480),
        ("left_bottom", 20, 500, 660, 980),
        ("tall_right", 700, 20, 980, 980),
    ]
    boxes = boxes_from(spec)
    ranks = assign_reading_order(boxes, right_to_left=True, page_height=1000)
    got = ordered_labels(spec, boxes, ranks)

    assert got == ["tall_right", "left_top", "left_bottom"]


def test_full_width_panel_below_a_row():
    spec = [
        ("row_right", 520, 20, 980, 400),
        ("row_left", 20, 20, 500, 400),
        ("bottom_full", 20, 420, 980, 980),
    ]
    boxes = boxes_from(spec)
    ranks = assign_reading_order(boxes, right_to_left=True, page_height=1000)
    got = ordered_labels(spec, boxes, ranks)

    assert got == ["row_right", "row_left", "bottom_full"]


def test_top_tolerance_is_respected():
    # Panels 60px apart on a 1000px page must land in different rows.
    spec = [
        ("upper", 20, 100, 480, 400),
        ("lower", 20, 200, 480, 500),
    ]
    boxes = boxes_from(spec)
    ranks = assign_reading_order(
        boxes, right_to_left=True, row_top_tolerance=0.05, page_height=1000
    )
    got = ordered_labels(spec, boxes, ranks)
    assert got == ["upper", "lower"]


def test_reading_order_continues_across_pages():
    page1 = boxes_from(THREE_ROWS[:3])
    page2 = boxes_from(THREE_ROWS[3:5])
    ranks = order_across_pages([page1, page2], right_to_left=True)

    assert sorted(ranks) == list(range(1, 6))
    # Page 2 starts after everything on page 1.
    assert min(ranks[3:]) > max(ranks[:3])


def test_input_list_is_not_mutated():
    boxes = boxes_from(THREE_ROWS)
    before = [(b.x1, b.y1, b.x2, b.y2) for b in boxes]
    assign_reading_order(boxes, right_to_left=True)
    assert [(b.x1, b.y1, b.x2, b.y2) for b in boxes] == before
