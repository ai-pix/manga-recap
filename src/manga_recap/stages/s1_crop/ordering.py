"""Reading-order assignment for panels on a page.

Manga reads right-to-left, top-to-bottom. The tricky part is not the direction
but the grouping: a page is a grid of rows, and within a row panels are ordered
right to left, while tall panels and full-width panels have to interrupt the
row structure without derailing it.

The algorithm groups boxes into rows by how close their top edges are, sorts
rows top to bottom, then sorts each row right to left. Grouping on tops rather
than on vertical overlap is what makes the common "tall panel down one side,
stacked panels beside it" layout come out right.
"""

from __future__ import annotations

from ...core.schema import BBox


def assign_reading_order(
    boxes: list[BBox],
    *,
    right_to_left: bool = True,
    row_top_tolerance: float = 0.05,
    page_height: int | None = None,
) -> list[int]:
    """Return a reading-order rank for each box, parallel to `boxes`.

    Rank 1 comes first. The input list is not modified.

    `row_top_tolerance` is the fraction of page height within which two panel
    tops count as the same row. `page_height` is needed to turn that into
    pixels; it is inferred from the boxes when not supplied.
    """
    if not boxes:
        return []

    if page_height is None:
        page_height = max(b.y2 for b in boxes)

    rows = _group_into_rows(boxes, row_top_tolerance, page_height)
    ordered: list[tuple[int, int]] = []
    rank = 1
    for row in rows:
        # Within a row, right-to-left means descending x.
        row_sorted = sorted(row, key=lambda i: boxes[i].x1, reverse=right_to_left)
        for index in row_sorted:
            ordered.append((rank, index))
            rank += 1

    result = [0] * len(boxes)
    for rank, index in ordered:
        result[index] = rank
    return result


def _group_into_rows(boxes: list[BBox], tolerance_ratio: float, page_height: int) -> list[list[int]]:
    """Cluster box indices into rows by how close their tops are.

    Grouping on top edges rather than vertical overlap is what makes the common
    manga layout work. Consider a tall panel down the left side with two panels
    stacked to its right: the tall panel vertically overlaps both of them, so an
    overlap-based rule collapses all three into a single row and then reads them
    in x order, which puts a panel from the bottom of the page first.

    Panels in the same visual row start at the same height. That is the signal
    to use, and a stacked panel fails it because its top is far lower.
    """
    tolerance = max(4, int(page_height * tolerance_ratio))
    remaining = sorted(range(len(boxes)), key=lambda i: (boxes[i].y1, boxes[i].x1))

    rows: list[list[int]] = []
    while remaining:
        row_top = boxes[remaining[0]].y1
        row = []
        leftovers = []
        for index in remaining:
            if abs(boxes[index].y1 - row_top) <= tolerance:
                row.append(index)
            else:
                leftovers.append(index)
        rows.append(row)
        remaining = leftovers

    # Top to bottom, ties broken on the leftmost edge so the result is stable.
    return sorted(rows, key=lambda r: (min(boxes[i].y1 for i in r), min(boxes[i].x1 for i in r)))


def order_across_pages(
    per_page_boxes: list[list[BBox]],
    *,
    right_to_left: bool = True,
    row_top_tolerance: float = 0.05,
    page_heights: list[int] | None = None,
) -> list[int]:
    """Assign continuous reading order across every page of a chapter.

    Reading order restarts each page but keeps increasing, so the result is a
    single 1..N sequence over the whole chapter.
    """
    orders: list[int] = []
    offset = 0
    for position, boxes in enumerate(per_page_boxes):
        height = page_heights[position] if page_heights else None
        page_orders = assign_reading_order(
            boxes,
            right_to_left=right_to_left,
            row_top_tolerance=row_top_tolerance,
            page_height=height,
        )
        for rank in page_orders:
            orders.append(offset + rank)
        offset += len(boxes)
    return orders


def describe_order(boxes: list[BBox], ranks: list[int]) -> str:
    """Human-readable order, for logs and contact-sheet captions."""
    pairs = sorted(zip(ranks, range(len(boxes)), strict=True), key=lambda p: p[0])
    parts = []
    for rank, index in pairs:
        box = boxes[index]
        parts.append(f"{rank}. ({box.x1},{box.y1})-({box.x2},{box.y2})")
    return " | ".join(parts)
