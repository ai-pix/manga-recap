"""Stage 1 sanity checks and a per-page contact sheet.

Cropping is the one stage whose failures are silent: a missed panel looks
exactly like a shorter chapter, and a speech bubble sliced in half looks exactly
like a panel with no dialogue. The contact sheet exists so both failures are
visible without writing code, and the checks catch the obvious cases.

The text-coverage check is the one that matters most. Once the detector's text
boxes are retained, "is any dialogue being cut?" becomes pure geometry, and a
question that can be answered in arithmetic should never be answered by
eyeballing thirty contact sheets.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ...core.logging import get_logger
from ...core.schema import BBox, PanelIndexFile
from .inkmask import _intersect

_log = get_logger("stages.s1_crop.validate")


@dataclass
class TextCoverage:
    """How much of the detected dialogue survived the crops."""

    total_regions: int = 0
    covered: int = 0
    clipped: int = 0
    unassigned: int = 0

    @property
    def ratio(self) -> float:
        return self.covered / self.total_regions if self.total_regions else 1.0

    def summary(self) -> str:
        if not self.total_regions:
            return "no text regions were detected, so there is no dialogue to lose"
        return (
            f"{self.covered}/{self.total_regions} text regions fully inside a panel "
            f"({self.ratio:.1%}); {self.clipped} clipped, {self.unassigned} unassigned"
        )


def check_text_coverage(
    index: PanelIndexFile, *, min_containment: float = 0.9
) -> tuple[TextCoverage, list[str]]:
    """Verify that every detected text region survived inside some panel crop.

    A region counts as covered when at least `min_containment` of its area falls
    inside the panels that claimed it. A bubble straddling a border is unioned
    into both neighbours by the cropper, so together they hold all of it; a
    bubble the cropper missed, or one belonging to a hand-authored box, does not.

    Returns the counts and a list of human-readable problems.
    """
    coverage = TextCoverage()
    problems: list[str] = []

    for page_number, regions in sorted(index.page_text_boxes.items()):
        panels = index.by_page().get(page_number, [])
        if not panels:
            continue

        # Which panels claim which region, so a shared border can be measured
        # against both sides together rather than either side alone.
        claims: dict[tuple[int, int, int, int], list[PanelIndexFile]] = {}
        for panel in panels:
            for box in panel.text_boxes:
                claims.setdefault((box.x1, box.y1, box.x2, box.y2), []).append(panel)

        for box in regions:
            coverage.total_regions += 1
            key = (box.x1, box.y1, box.x2, box.y2)
            owners = claims.get(key, [])

            if not owners:
                coverage.unassigned += 1
                problems.append(
                    f"Page {page_number}: a text region at {box.to_xywh()} was not "
                    "claimed by any panel, so nothing will describe it. It is most "
                    "likely page chrome, a caption or a floating SFX; if it is real "
                    "dialogue, add a manual box for this page in "
                    "02_panels/manual_boxes.json."
                )
                continue

            combined = BBox.union_all([panel.bbox for panel in owners])
            best_ratio = combined.contains_ratio(box) if combined else 0.0
            names = ", ".join(panel.panel_id for panel in owners)

            if best_ratio >= min_containment:
                coverage.covered += 1
            else:
                coverage.clipped += 1
                problems.append(
                    f"Page {page_number}: a text region at {box.to_xywh()} is only "
                    f"{best_ratio:.0%} inside {names}, so that dialogue is cut. "
                    "Raise crop.text_min_overlap or crop.padding_ratio, or add a "
                    f"manual box in 02_panels/manual_boxes.json for page {page_number}."
                )

    return coverage, problems


def union_area(boxes: list[BBox]) -> int:
    """Total area covered by `boxes`, counting overlaps once.

    Coordinate compression rather than a sum, because a page where one panel
    sits inside another would otherwise report more than the whole page, and
    that is precisely the number this check exists to sanity-test.
    """
    if not boxes:
        return 0
    xs = sorted({b.x1 for b in boxes} | {b.x2 for b in boxes})
    ys = sorted({b.y1 for b in boxes} | {b.y2 for b in boxes})

    total = 0
    for x1, x2 in zip(xs, xs[1:], strict=False):
        if x2 <= x1:
            continue
        for y1, y2 in zip(ys, ys[1:], strict=False):
            if y2 <= y1:
                continue
            if any(b.x1 <= x1 and x2 <= b.x2 and b.y1 <= y1 and y2 <= b.y2 for b in boxes):
                total += (x2 - x1) * (y2 - y1)
    return total


def check_page_coverage(
    index: PanelIndexFile, *, min_page_coverage: float = 0.45
) -> list[str]:
    """Flag pages where the detected panels cover implausibly little of the art.

    A missed panel does not look like a failure anywhere downstream. It looks
    like a slightly shorter chapter, and the story simply skips a beat with no
    complaint from any stage. On a colour page with large full-bleed panels the
    detector routinely returns the small framed panels and misses the artwork
    filling the rest of the sheet, and nothing in the output says so.

    The denominator is the page's drawn extent rather than its full area, so a
    page with wide margins is not reported as half-missing just because half of
    it is gutter. Where the drawn extent is unknown the page area is used, which
    is the old, pessimistic denominator and errs toward reporting.
    """
    problems: list[str] = []
    for page_number, panels in sorted(index.by_page().items()):
        drawn = index.page_content_bbox.get(page_number)
        area = drawn.area if drawn is not None else panels[0].page_width * panels[0].page_height
        if area <= 0:
            continue

        # Clamp to the drawn extent: a panel running into the margin is not
        # evidence that the margin was detected.
        clipped = [p.bbox for p in panels]
        if drawn is not None:
            clipped = [_intersect(p.bbox, drawn) for p in panels]
        ratio = union_area([b for b in clipped if b is not None]) / area

        if ratio >= min_page_coverage:
            continue

        candidates = index.page_missing_candidates.get(page_number, [])
        detail = (
            f" {len(candidates)} unclaimed ink region(s) look like missed panels: "
            f"{[b.to_xywh() for b in candidates[:3]]}."
            if candidates
            else ""
        )
        problems.append(
            f"Page {page_number}: detected panels cover only {ratio:.0%} of the "
            f"drawn page, below crop.min_page_coverage ({min_page_coverage:.0%})."
            f"{detail} Review 02_panels/_debug/page_{page_number:03d}_sheet.jpg and "
            f"add boxes to 02_panels/manual_boxes.json under \"{page_number:03d}.png\"."
        )
    return problems


def validate(
    index: PanelIndexFile,
    *,
    min_panels_per_page: int = 1,
    min_text_containment: float = 0.9,
    min_page_coverage: float = 0.45,
    check_text: bool = True,
) -> list[str]:
    """Return a list of human-readable problems. Empty means all good."""
    problems: list[str] = []

    if index.panel_count == 0:
        problems.append(
            "No panels were detected at all. Check the page images, or switch "
            "crop.detector in config.yaml."
        )
        return problems

    seen_pages: dict[int, int] = {}
    for panel in index.ordered():
        seen_pages[panel.page_number] = seen_pages.get(panel.page_number, 0) + 1

    for page_number, count in sorted(seen_pages.items()):
        if count < min_panels_per_page:
            problems.append(
                f"Page {page_number} yielded only {count} panel(s). "
                "This page may have been missed."
            )

    for panel in index.panels:
        if panel.area_ratio < 0.002:
            problems.append(
                f"{panel.panel_id} is very small ({panel.area_ratio:.4%} of the page). "
                "It is probably noise, a sound-effect fragment, or a stray mark."
            )
        if panel.bbox.height > panel.page_height * 0.98 and panel.bbox.width > panel.page_width * 0.98:
            # A full-page box usually means detection failed and returned the page.
            problems.append(
                f"{panel.panel_id} covers the entire page, which usually means "
                "the detector returned the page instead of the panels."
            )

    gaps = _order_gaps(index)
    if gaps:
        problems.append(f"Reading order has gaps: {gaps}")

    if check_text:
        coverage, text_problems = check_text_coverage(
            index, min_containment=min_text_containment
        )
        _log.info("Text coverage: %s", coverage.summary())
        problems.extend(text_problems)

    problems.extend(check_page_coverage(index, min_page_coverage=min_page_coverage))

    return problems


def _order_gaps(index: PanelIndexFile) -> list[tuple[int, int]]:
    """Find holes in the 1..N reading-order sequence."""
    orders = sorted(p.reading_order for p in index.panels)
    if not orders:
        return []
    expected = list(range(1, len(orders) + 1))
    return list(zip(
        [o for o in expected if o not in set(orders)][:5],
        [orders[i + 1] for i in range(len(orders) - 1) if orders[i + 1] != orders[i] + 1][:5],
        strict=False,
    ))


def write_contact_sheets(
    index: PanelIndexFile,
    pages_dir: Path,
    out_dir: Path,
    *,
    columns: int = 4,
    cell_width: int = 420,
    label_height: int = 28,
) -> list[Path]:
    """Write one contact sheet per page, panels numbered in reading order.

    Two bands. The top band is the whole page with every detected box drawn and
    numbered, which answers "did it find all the panels, and in what order". The
    bottom band is the crops themselves in reading order, which answers "is each
    crop the right thing".

    Speech-bubble boxes are drawn in blue on the top band, and speech bubbles
    that no panel claimed are drawn in orange. A blue box hanging outside a red
    one is a bubble that will be cut; an orange box is a bubble belonging to
    nothing at all, which almost always means a whole panel was missed. Both are
    invisible in a JSON file and obvious here.

    They are kept as separate bands because overlaying the crop on the page hides
    the very context the page provides.
    """
    from PIL import Image, ImageDraw

    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    panel_color = (255, 60, 60)
    text_color = (60, 160, 255)
    orphan_color = (255, 170, 40)
    candidate_color = (190, 90, 255)

    for page_number, panels in sorted(index.by_page().items()):
        page_path = pages_dir / f"page_{page_number:03d}.png"
        if not page_path.exists():
            continue

        page_image = Image.open(page_path).convert("RGB")

        # -- top band: the page with every box drawn and numbered -----------
        map_width = columns * cell_width
        map_scale = map_width / page_image.width
        map_height = max(1, int(page_image.height * map_scale))
        page_map = page_image.resize((map_width, map_height), Image.LANCZOS)
        map_draw = ImageDraw.Draw(page_map)

        for panel in panels:
            box = panel.bbox
            x1, y1 = int(box.x1 * map_scale), int(box.y1 * map_scale)
            x2, y2 = int(box.x2 * map_scale), int(box.y2 * map_scale)
            # A filled chip plus a number, so the reading order is legible at
            # thumbnail size.
            map_draw.rectangle([x1, y1, x2, y2], outline=panel_color, width=3)
            chip_x, chip_y = x1 + 2, y1 + 2
            map_draw.rectangle(
                [chip_x, chip_y, chip_x + 20, chip_y + 18], fill=panel_color
            )
            map_draw.text(
                (chip_x + 6, chip_y + 3), str(panel.reading_order), fill=(255, 255, 255)
            )
            for text_box in panel.text_boxes:
                map_draw.rectangle(
                    [
                        int(text_box.x1 * map_scale),
                        int(text_box.y1 * map_scale),
                        int(text_box.x2 * map_scale),
                        int(text_box.y2 * map_scale),
                    ],
                    outline=text_color,
                    width=2,
                )

        # -- bubbles no panel claimed: almost always a missed panel ----------
        claimed = {
            (b.x1, b.y1, b.x2, b.y2)
            for panel in panels
            for b in panel.text_boxes
        }
        orphans = [
            box
            for box in index.page_text_boxes.get(page_number, [])
            if (box.x1, box.y1, box.x2, box.y2) not in claimed
        ]
        for box in orphans:
            map_draw.rectangle(
                [
                    int(box.x1 * map_scale),
                    int(box.y1 * map_scale),
                    int(box.x2 * map_scale),
                    int(box.y2 * map_scale),
                ],
                outline=orphan_color,
                width=3,
            )

        # -- leftover ink: panels the detector may have walked past -----------
        candidates = index.page_missing_candidates.get(page_number, [])
        for box in candidates:
            map_draw.rectangle(
                [
                    int(box.x1 * map_scale),
                    int(box.y1 * map_scale),
                    int(box.x2 * map_scale),
                    int(box.y2 * map_scale),
                ],
                outline=candidate_color,
                width=3,
            )

        # -- bottom band: the crops in reading order ------------------------
        cell_height = int(cell_width * 1.5) + label_height
        rows = (len(panels) + columns - 1) // columns
        grid = Image.new(
            "RGB", (columns * cell_width, rows * cell_height), (24, 24, 28)
        )
        grid_draw = ImageDraw.Draw(grid)

        for position, panel in enumerate(panels):
            slot_x = (position % columns) * cell_width
            slot_y = (position // columns) * cell_height
            grid_draw.text(
                (slot_x + 6, slot_y + 7),
                f"#{panel.reading_order}  {panel.panel_id}",
                fill=(235, 235, 240),
            )

            crop_path = pages_dir.parent / panel.image_path
            if not crop_path.exists():
                continue
            crop = Image.open(crop_path).convert("RGB")
            crop.thumbnail(
                (cell_width - 12, cell_height - label_height - 12), Image.LANCZOS
            )
            grid.paste(
                crop,
                (
                    slot_x + (cell_width - crop.width) // 2,
                    slot_y + label_height + (cell_height - label_height - crop.height) // 2,
                ),
            )

        # -- assemble --------------------------------------------------------
        band_gap = 10
        caption = 26
        sheet = Image.new(
            "RGB",
            (map_width, caption + map_height + band_gap + grid.height),
            (16, 16, 20),
        )
        sheet_draw = ImageDraw.Draw(sheet)
        text_count = sum(len(p.text_boxes) for p in panels)
        sheet_draw.text(
            (6, 7),
            f"page {page_number}: {len(panels)} panels in reading order, "
            f"{text_count} text region(s) in blue, {len(orphans)} unclaimed in orange, "
            f"{len(candidates)} missed-panel candidate(s) in purple",
            fill=(235, 235, 245),
        )
        sheet.paste(page_map, (0, caption))
        sheet.paste(grid, (0, caption + map_height + band_gap))

        out_path = out_dir / f"page_{page_number:03d}_sheet.jpg"
        sheet.save(out_path, "JPEG", quality=90)
        written.append(out_path)

    return written
