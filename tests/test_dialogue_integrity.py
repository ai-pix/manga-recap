"""Dialogue must survive cropping.

The failure these tests exist for is invisible in the finished artifact: a
speech bubble sliced by the panel border still produces a valid panel image, a
valid description and a valid script. The only symptom is that the narrator has
to invent why anyone did anything. So the crop has to be provably correct, and
these tests check the geometry that makes it so.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import PAGE_H, PAGE_W

from manga_recap.core.schema import BBox, PanelIndex, PanelIndexFile
from manga_recap.stages.s1_crop.cropper import _pad, _texts_for, crop_chapter
from manga_recap.stages.s1_crop.detector import DetectionResult, dedupe
from manga_recap.stages.s1_crop.validate import check_page_coverage, check_text_coverage, union_area

# ---------------------------------------------------------------------------
# BBox geometry
# ---------------------------------------------------------------------------


def test_contains_ratio_measures_the_smaller_box():
    outer = BBox(x1=0, y1=0, x2=100, y2=100)
    inner = BBox(x1=10, y1=10, x2=20, y2=20)

    assert outer.contains_ratio(inner) == 1.0
    # Asymmetric on purpose: the question is "how much of the bubble is inside
    # the panel", not "how much of the panel is bubble".
    assert inner.contains_ratio(outer) == pytest.approx(0.01)
    assert outer.contains_ratio(BBox(x1=500, y1=500, x2=510, y2=510)) == 0.0


def test_contains_ratio_detects_a_clipped_bubble():
    """A bubble half outside its panel is exactly 50% covered."""
    panel = BBox(x1=50, y1=50, x2=150, y2=150)
    # 100 wide, but the left 50 sits outside the panel.
    bubble = BBox(x1=100, y1=60, x2=200, y2=80)

    assert panel.contains_ratio(bubble) == pytest.approx(0.5)


def test_center_inside_finds_an_overhanging_bubble():
    """Centre-inside catches a bubble the overlap test alone would miss."""
    panel = BBox(x1=0, y1=0, x2=200, y2=200)
    # Runs from the panel's left edge well past its right edge, so only 50% is
    # inside, but its centre still sits on the panel's border.
    bubble = BBox(x1=0, y1=90, x2=400, y2=110)

    assert panel.contains_ratio(bubble) == pytest.approx(0.5)
    assert bubble.center_inside(panel) is True
    assert BBox(x1=300, y1=300, x2=400, y2=400).center_inside(panel) is False


def test_union_all_returns_the_smallest_enclosing_box():
    boxes = [
        BBox(x1=10, y1=10, x2=20, y2=20),
        BBox(x1=0, y1=50, x2=15, y2=60),
    ]
    assert BBox.union_all(boxes) == BBox(x1=0, y1=10, x2=20, y2=60)
    assert BBox.union_all([]) is None


# ---------------------------------------------------------------------------
# Deduping: merge, never discard
# ---------------------------------------------------------------------------


def test_dedupe_merges_a_jittered_duplicate_rather_than_dropping_it():
    """Two detections of one panel become the union, so nothing is lost."""
    a = BBox(x1=100, y1=100, x2=300, y2=300)
    b = BBox(x1=95, y1=104, x2=302, y2=297)

    result = dedupe([a, b], iou_threshold=0.5)

    assert len(result) == 1
    assert result[0].contains_ratio(a) == 1.0
    assert result[0].contains_ratio(b) == 1.0


def test_dedupe_keeps_two_genuinely_overlapping_panels():
    """The old code kept the larger and silently deleted the smaller.

    A layout with two panels that overlap is not common, but when it happens
    the dropped panel takes its artwork and its dialogue with it, and a shorter
    chapter is indistinguishable from a correct one.
    """
    big = BBox(x1=0, y1=0, x2=400, y2=400)
    # Same area, offset enough that the union is far larger than either.
    overlapping = BBox(x1=300, y1=300, x2=700, y2=700)

    result = dedupe([big, overlapping], iou_threshold=0.5)

    assert len(result) == 2
    assert any(b.iou(big) > 0.9 for b in result)
    assert any(b.iou(overlapping) > 0.9 for b in result)


# ---------------------------------------------------------------------------
# Assigning text to panels
# ---------------------------------------------------------------------------


def test_text_fully_inside_a_panel_is_claimed():
    panel = BBox(x1=0, y1=0, x2=300, y2=300)
    bubble = BBox(x1=40, y1=40, x2=120, y2=80)

    assert _texts_for(panel, [bubble], min_overlap=0.15) == [bubble]


def test_text_centred_on_the_border_is_claimed_by_both_neighbours():
    """A bubble drawn across a divider belongs to both sides, not to neither."""
    left = BBox(x1=0, y1=0, x2=100, y2=100)
    right = BBox(x1=110, y1=0, x2=210, y2=100)
    straddling = BBox(x1=85, y1=40, x2=125, y2=60)

    assert _texts_for(left, [straddling], min_overlap=0.15) == [straddling]
    assert _texts_for(right, [straddling], min_overlap=0.15) == [straddling]


def test_text_far_outside_a_panel_is_left_alone():
    panel = BBox(x1=0, y1=0, x2=100, y2=100)
    elsewhere = BBox(x1=500, y1=500, x2=600, y2=560)

    assert _texts_for(panel, [elsewhere], min_overlap=0.15) == []


def test_high_overlap_threshold_rejects_a_bubble_that_only_grazes():
    panel = BBox(x1=0, y1=0, x2=100, y2=100)
    # 10% inside, 90% outside.
    grazing = BBox(x1=90, y1=20, x2=190, y2=40)

    assert _texts_for(panel, [grazing], min_overlap=0.5) == []
    assert _texts_for(panel, [grazing], min_overlap=0.05) == [grazing]


# ---------------------------------------------------------------------------
# Padding
# ---------------------------------------------------------------------------


def test_padding_scales_with_the_panel_instead_of_being_flat():
    """A 6px margin is generous on a small panel and useless on a large one."""
    # Centred in the page so the page-edge clamp cannot distort the measurement.
    small = BBox(x1=400, y1=300, x2=500, y2=400)
    large = BBox(x1=100, y1=50, x2=800, y2=750)

    def pad(box):
        return _pad(
            box, PAGE_W, PAGE_H, floor_px=6, ratio=0.02, min_px=8, max_px=40
        )

    small_growth = pad(small).width - small.width
    large_growth = pad(large).width - large.width

    assert small_growth == 16  # 2% of 100 is only 2px, floored to padding_min_px
    assert large_growth == 28  # 2% of 700
    assert large_growth > small_growth


def test_padding_is_clamped_at_both_ends():
    tiny = BBox(x1=48, y1=48, x2=52, y2=52)
    huge = BBox(x1=0, y1=0, x2=5000, y2=5000)

    # ratio would ask for 20px of margin on a 4px panel; max_px caps it at 8.
    assert (
        _pad(tiny, 100, 100, floor_px=0, ratio=5.0, min_px=0, max_px=8).width == 20
    )
    # And the page itself is the hard ceiling.
    assert (
        _pad(huge, 100, 100, floor_px=0, ratio=0.5, min_px=0, max_px=8).width == 100
    )


def test_padding_never_escapes_the_page():
    box = BBox(x1=0, y1=0, x2=10, y2=10)
    padded = _pad(box, 100, 100, floor_px=50, ratio=0.1, min_px=0, max_px=50)

    assert (padded.x1, padded.y1) == (0, 0)
    assert (padded.x2, padded.y2) == (60, 60)


def test_absolute_floor_still_applies():
    """`padding_px` still protects a page from losing a panel border."""
    box = BBox(x1=100, y1=100, x2=110, y2=110)
    padded = _pad(box, 1000, 1000, floor_px=20, ratio=0.0, min_px=0, max_px=40)

    assert padded.x1 == 80


# ---------------------------------------------------------------------------
# End-to-end cropper behaviour
# ---------------------------------------------------------------------------


def _stub_detector(panels, texts=()):
    def detect(page_path: Path) -> DetectionResult:
        return DetectionResult(list(panels), "yolo", list(texts))

    return detect


def _chapter_root(tmp_path: Path) -> Path:
    return tmp_path / "ch_test"


def _write_pages(tmp_path: Path, count: int = 1) -> list[Path]:
    from PIL import Image

    pages_dir = _chapter_root(tmp_path) / "01_pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for number in range(1, count + 1):
        path = pages_dir / f"page_{number:03d}.png"
        Image.new("RGB", (400, 600), (255, 255, 255)).save(path)
        paths.append(path)
    return paths


def test_panel_box_grows_to_contain_an_overhanging_bubble(tmp_path):
    """The structural fix: the crop cannot cut dialogue in the first place."""
    pages = _write_pages(tmp_path)
    root = _chapter_root(tmp_path)
    # Panel stops at x=200. The bubble runs 30px past it.
    panel = BBox(x1=50, y1=50, x2=200, y2=250)
    bubble = BBox(x1=150, y1=80, x2=230, y2=120)

    index = crop_chapter(
        pages,
        root / "02_panels",
        detector=_stub_detector([panel], [bubble]),
        crop_config={"padding_px": 0, "padding_ratio": 0.0, "padding_min_px": 0},
        text_dir=root / "02_panels" / "_text",
    )

    entry = index.panels[0]
    assert entry.bbox.contains_ratio(bubble) == 1.0
    assert entry.bbox.x2 >= bubble.x2
    assert entry.has_text is True


def test_a_text_crop_is_written_for_transcription(tmp_path):
    pages = _write_pages(tmp_path)
    root = _chapter_root(tmp_path)
    text_dir = root / "02_panels" / "_text"
    panel = BBox(x1=50, y1=50, x2=350, y2=550)
    bubble = BBox(x1=100, y1=100, x2=300, y2=160)

    index = crop_chapter(
        pages,
        root / "02_panels",
        detector=_stub_detector([panel], [bubble]),
        crop_config={},
        text_dir=text_dir,
    )

    entry = index.panels[0]
    assert entry.text_image_path == "02_panels/_text/panel_0001_text.png"
    assert (root / entry.text_image_path).exists()


def test_text_crops_are_not_mistaken_for_panels(tmp_path):
    """`panel_0001_text` must not be read as a second panel by later stages."""
    from manga_recap.core.paths import ChapterPaths

    pages = _write_pages(tmp_path)
    root = _chapter_root(tmp_path)
    crop_chapter(
        pages,
        root / "02_panels",
        detector=_stub_detector(
            [BBox(x1=50, y1=50, x2=350, y2=550)], [BBox(x1=100, y1=100, x2=300, y2=160)]
        ),
        crop_config={},
        text_dir=root / "02_panels" / "_text",
    )

    paths = ChapterPaths.create("ch_test", tmp_path)
    assert [p.name for p in paths.panel_images()] == ["panel_0001.png"]
    assert [p.name for p in paths.panel_text_images()] == ["panel_0001_text.png"]


def test_a_panel_with_no_text_gets_no_text_crop(tmp_path):
    pages = _write_pages(tmp_path)
    root = _chapter_root(tmp_path)
    index = crop_chapter(
        pages,
        root / "02_panels",
        detector=_stub_detector([BBox(x1=50, y1=50, x2=350, y2=550)]),
        crop_config={},
        text_dir=root / "02_panels" / "_text",
    )

    entry = index.panels[0]
    assert entry.has_text is False
    assert entry.text_image_path == ""


def test_nested_panels_are_kept_and_flagged(tmp_path):
    """An inset panel is real content. Collapsing it into its parent loses it."""
    pages = _write_pages(tmp_path)
    root = _chapter_root(tmp_path)
    outer = BBox(x1=20, y1=20, x2=380, y2=580)
    inner = BBox(x1=100, y1=100, x2=300, y2=300)

    index = crop_chapter(
        pages,
        root / "02_panels",
        detector=_stub_detector([outer, inner]),
        crop_config={"padding_px": 0, "padding_ratio": 0.0, "padding_min_px": 0},
    )

    assert index.panel_count == 2
    by_id = index.by_id()
    # Reading order puts the outer panel first because its top edge is higher.
    assert by_id["panel_0001"].nested_in == ""
    assert by_id["panel_0002"].nested_in == "panel_0001"


# ---------------------------------------------------------------------------
# The coverage invariant
# ---------------------------------------------------------------------------


def _index_with(panels: list[PanelIndex], page_text: dict | None = None) -> PanelIndexFile:
    """Build an index. `page_text` is the detector's raw per-page text list.

    It defaults to every text box the panels claim, which is the normal case.
    Pass it explicitly to model a region that no panel took.
    """
    if page_text is None:
        page_text = {}
        seen: set[tuple[int, int, int, int]] = set()
        for panel in panels:
            for box in panel.text_boxes:
                key = (box.x1, box.y1, box.x2, box.y2)
                if key in seen:
                    continue
                seen.add(key)
                page_text.setdefault(panel.page_number, []).append(box)
    return PanelIndexFile(
        chapter_id="ch_test",
        page_count=1,
        panel_count=len(panels),
        created_at="2026-01-01T00:00:00",
        panels=panels,
        page_text_boxes=page_text,
    )


def _panel(panel_id, bbox, text_boxes=(), reading_order=1):
    return PanelIndex(
        panel_id=panel_id,
        page_number=1,
        index_on_page=reading_order,
        reading_order=reading_order,
        bbox=bbox,
        image_path=f"02_panels/{panel_id}.png",
        page_width=400,
        page_height=600,
        text_boxes=list(text_boxes),
    )


def test_fully_covered_text_reports_no_problems():
    index = _index_with(
        [
            _panel(
                "panel_0001",
                BBox(x1=0, y1=0, x2=400, y2=600),
                [BBox(x1=50, y1=50, x2=200, y2=120)],
            )
        ]
    )

    coverage, problems = check_text_coverage(index)

    assert problems == []
    assert (coverage.total_regions, coverage.covered) == (1, 1)
    assert coverage.ratio == 1.0


def test_clipped_text_is_reported_with_the_shortfall():
    index = _index_with(
        [
            _panel(
                "panel_0001",
                BBox(x1=0, y1=0, x2=200, y2=200),
                [BBox(x1=100, y1=40, x2=300, y2=80)],
            )
        ]
    )

    coverage, problems = check_text_coverage(index)

    assert coverage.clipped == 1
    assert len(problems) == 1
    assert "50% inside panel_0001" in problems[0]
    assert "dialogue is cut" in problems[0]


def test_text_on_a_shared_border_is_covered_by_the_two_panels_together():
    """Neither panel holds 90% of a straddling bubble, but together they do.

    This is the case the union exists for. Flagging it would be a false alarm
    on exactly the layout the union feature was built to handle.
    """
    bubble = BBox(x1=180, y1=40, x2=220, y2=80)
    index = _index_with(
        [
            _panel("panel_0001", BBox(x1=0, y1=0, x2=200, y2=200), [bubble], 1),
            _panel("panel_0002", BBox(x1=200, y1=0, x2=400, y2=200), [bubble], 2),
        ]
    )

    coverage, problems = check_text_coverage(index)

    assert coverage.total_regions == 1
    assert coverage.clipped == 0
    assert coverage.covered == 1
    assert problems == []


def test_a_border_bubble_reaching_past_both_owners_is_still_clipped():
    """The union only helps for a bubble inside the two crops' shared span.

    This is the hand-authored-boxes case, which is exactly where the check earns
    its keep: nothing grows the boxes, so a bubble can overhang their outer edge.
    """
    bubble = BBox(x1=180, y1=40, x2=340, y2=80)
    index = _index_with(
        [
            # Together they span x=0..300, so 75% of the bubble is covered.
            _panel("panel_0001", BBox(x1=0, y1=0, x2=200, y2=200), [bubble], 1),
            _panel("panel_0002", BBox(x1=200, y1=0, x2=300, y2=200), [bubble], 2),
        ]
    )

    coverage, problems = check_text_coverage(index)

    assert coverage.clipped == 1
    assert "75% inside panel_0001, panel_0002" in problems[0]


def test_text_claimed_by_no_panel_is_reported():
    """A bubble in the gutter belongs to nothing, and that is a silent loss."""
    orphan = BBox(x1=0, y1=0, x2=30, y2=30)
    index = _index_with(
        [_panel("panel_0001", BBox(x1=50, y1=50, x2=350, y2=550))],
        page_text={1: [orphan]},
    )

    coverage, problems = check_text_coverage(index)

    assert coverage.total_regions == 1
    assert coverage.unassigned == 1
    assert coverage.clipped == 0
    assert "not claimed by any panel" in problems[0]
    assert "page chrome" in problems[0]


def test_a_page_with_no_panels_is_skipped_rather_than_falsely_flagged():
    index = _index_with([], page_text={1: [BBox(x1=0, y1=0, x2=30, y2=30)]})

    coverage, problems = check_text_coverage(index)

    assert problems == []
    assert coverage.total_regions == 0


def test_coverage_on_a_chapter_with_no_detected_text_is_vacuously_fine():
    index = _index_with([_panel("panel_0001", BBox(x1=0, y1=0, x2=400, y2=600))])

    coverage, problems = check_text_coverage(index)

    assert problems == []
    assert coverage.total_regions == 0
    assert coverage.ratio == 1.0


# ---------------------------------------------------------------------------
# Missed panels
# ---------------------------------------------------------------------------


def test_union_area_counts_overlaps_once():
    """A sum would report more than the page and mask the gap being looked for."""
    outer = BBox(x1=0, y1=0, x2=400, y2=600)
    inner = BBox(x1=100, y1=100, x2=200, y2=200)

    assert union_area([outer, inner]) == outer.area
    assert union_area([]) == 0
    # Two side-by-side panels on a 400-wide page cover it exactly.
    assert union_area([BBox(x1=0, y1=0, x2=200, y2=600), BBox(x1=200, y1=0, x2=400, y2=600)]) == 400 * 600


def _wide_page_index(panels, page_text=None) -> PanelIndexFile:
    """Same helper, but on a page the index reports as 400x600."""
    return _index_with(panels, page_text=page_text)


def test_a_page_with_a_big_undetected_area_is_flagged():
    """The page-10 case: one small panel found, the rest of the sheet missed."""
    index = _wide_page_index(
        [
            _panel(
                "panel_0001",
                BBox(x1=10, y1=10, x2=390, y2=80),
                [],
            )
        ],
        page_text={1: [BBox(x1=30, y1=200, x2=120, y2=400)]},
    )
    index.page_missing_candidates = {1: [BBox(x1=20, y1=180, x2=200, y2=420)]}

    problems = check_page_coverage(index, min_page_coverage=0.45)

    assert len(problems) == 1
    assert "cover only 11% of the drawn page" in problems[0]
    # The leftover ink is the tell that a whole panel was skipped, so the
    # message has to carry the coordinates rather than just a low number.
    assert "unclaimed ink region(s) look like missed panels" in problems[0]
    assert "page_001_sheet.jpg" in problems[0]
    assert "manual_boxes.json" in problems[0]


def test_coverage_is_measured_against_drawn_area_not_page_area():
    """Wide margins are gutter, not missed panels.

    The same panel is 11% of a 400x600 sheet and the overwhelming majority of a
    page whose art only occupies its middle. Flagging the first and passing the
    second is the difference between a useful warning and noise.
    """
    narrow_ink = _wide_page_index(
        [_panel("panel_0001", BBox(x1=100, y1=200, x2=300, y2=400))]
    )
    narrow_ink.page_content_bbox = {1: BBox(x1=90, y1=190, x2=310, y2=410)}

    assert check_page_coverage(narrow_ink, min_page_coverage=0.45) == []


def test_a_panel_covering_blank_sheet_is_not_credited_for_the_area():
    """Half the sheet, and none of the art on it.

    Measured against page area this looks like 50% coverage and passes. The art
    is all in the bottom two-thirds, so the panel actually covers a quarter of
    what was drawn, which is the case worth warning about.
    """
    index = _wide_page_index([_panel("panel_0001", BBox(x1=0, y1=0, x2=400, y2=300))])
    index.page_content_bbox = {1: BBox(x1=0, y1=200, x2=400, y2=600)}

    problems = check_page_coverage(index, min_page_coverage=0.45)

    assert len(problems) == 1
    assert "cover only 25%" in problems[0]


def test_a_well_detected_page_is_not_flagged():
    index = _wide_page_index(
        [
            _panel("panel_0001", BBox(x1=0, y1=0, x2=200, y2=600)),
            _panel("panel_0002", BBox(x1=200, y1=0, x2=400, y2=600), reading_order=2),
        ]
    )

    assert check_page_coverage(index, min_page_coverage=0.45) == []


def test_page_coverage_ignores_pages_with_no_panels():
    """A page with nothing detected is already reported by the panel count check."""
    index = _wide_page_index([_panel("panel_0001", BBox(x1=0, y1=0, x2=400, y2=600))])
    index.page_text_boxes[2] = [BBox(x1=0, y1=0, x2=30, y2=30)]

    assert check_page_coverage(index, min_page_coverage=0.45) == []
