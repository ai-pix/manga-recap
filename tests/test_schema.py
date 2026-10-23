"""Data contracts: the schemas that guard every stage handoff."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from manga_recap.core.schema import (
    BBox,
    BlockTiming,
    DescriptionFile,
    PanelDescription,
    PanelIndex,
    PanelIndexFile,
    ScriptBlock,
    ScriptFile,
    TimelineFile,
    WordTiming,
    load_model,
    save_model,
    validate_or_raise,
)

# -- BBox -------------------------------------------------------------------


def test_bbox_rejects_zero_extent():
    with pytest.raises(ValidationError, match="non-positive extent"):
        BBox(x1=10, y1=10, x2=10, y2=20)


def test_bbox_rejects_inverted_box():
    with pytest.raises(ValidationError):
        BBox(x1=50, y1=50, x2=10, y2=10)


def test_bbox_geometry():
    box = BBox(x1=10, y1=20, x2=110, y2=220)
    assert (box.width, box.height, box.area) == (100, 200, 20000)
    assert box.to_xywh() == [10, 20, 100, 200]


def test_bbox_iou_is_zero_for_disjoint_boxes():
    a = BBox(x1=0, y1=0, x2=10, y2=10)
    b = BBox(x1=100, y1=100, x2=110, y2=110)
    assert a.iou(b) == 0.0


def test_bbox_iou_is_one_for_identical_boxes():
    a = BBox(x1=0, y1=0, x2=10, y2=10)
    assert a.iou(BBox(x1=0, y1=0, x2=10, y2=10)) == pytest.approx(1.0)


def test_bbox_iou_of_a_half_overlap():
    a = BBox(x1=0, y1=0, x2=10, y2=10)   # area 100
    b = BBox(x1=5, y1=0, x2=15, y2=10)   # area 100, intersection 50
    assert a.iou(b) == pytest.approx(50 / 150)


# -- Panel index ------------------------------------------------------------


def test_panel_index_rejects_duplicate_reading_order():
    with pytest.raises(ValidationError, match="Duplicate reading_order"):
        PanelIndexFile(
            chapter_id="c1",
            page_count=1,
            panel_count=2,
            created_at="now",
            panels=[
                PanelIndex(
                    panel_id="p1", page_number=1, index_on_page=1, reading_order=1,
                    bbox=BBox(x1=0, y1=0, x2=10, y2=10),
                    image_path="a.png", page_width=100, page_height=100,
                ),
                PanelIndex(
                    panel_id="p2", page_number=1, index_on_page=2, reading_order=1,
                    bbox=BBox(x1=0, y1=0, x2=20, y2=20),
                    image_path="b.png", page_width=100, page_height=100,
                ),
            ],
        )


def test_panel_index_ordered_sorts_by_reading_order():
    def panel(panel_id, order):
        return PanelIndex(
            panel_id=panel_id, page_number=1, index_on_page=1, reading_order=order,
            bbox=BBox(x1=0, y1=0, x2=10 * order, y2=10),
            image_path=f"{panel_id}.png", page_width=100, page_height=100,
        )

    index = PanelIndexFile(
        chapter_id="c1", page_count=1, panel_count=2, created_at="now",
        panels=[panel("p2", 2), panel("p1", 1)],
    )
    assert [p.panel_id for p in index.ordered()] == ["p1", "p2"]


def test_panel_index_area_ratio():
    panel = PanelIndex(
        panel_id="p1", page_number=1, index_on_page=1, reading_order=1,
        bbox=BBox(x1=0, y1=0, x2=50, y2=50),  # 2500 of 10000
        image_path="a.png", page_width=100, page_height=100,
    )
    assert panel.area_ratio == pytest.approx(0.25)


# -- Descriptions -----------------------------------------------------------


def test_description_rejects_blank_action():
    with pytest.raises(ValidationError, match="action must not be empty"):
        PanelDescription(panel_id="p1", page_number=1, reading_order=1,
                         image_path="a.png", action="   ")


def test_description_file_rejects_duplicate_ids():
    with pytest.raises(ValidationError, match="Duplicate panel_id"):
        DescriptionFile(
            chapter_id="c1", created_at="now", panel_count=2,
            panels=[
                PanelDescription(panel_id="p1", page_number=1, reading_order=1,
                                 image_path="a.png", action="x"),
                PanelDescription(panel_id="p1", page_number=1, reading_order=2,
                                 image_path="b.png", action="y"),
            ],
        )


def test_skippable_panels_are_detected():
    ad = PanelDescription(panel_id="p1", page_number=1, reading_order=1,
                          image_path="a.png", action="advertisement", is_credits_or_ad=True)
    story = PanelDescription(panel_id="p2", page_number=1, reading_order=2,
                             image_path="b.png", action="a fight breaks out")

    labels = {"credits", "ad", "blank"}
    assert ad.is_skippable(labels)
    assert not story.is_skippable(labels)


def test_context_line_carries_the_essentials():
    panel = PanelDescription(
        panel_id="p0001", page_number=1, reading_order=1, image_path="a.png",
        characters=["Kidan", "Norio"], setting="classroom",
        action="Kidan leans in and whispers", expression="deadpan",
        speech_bubbles=["not a word"], sfx_text=["DON"],
    )
    line = panel.to_context_line()
    assert "[p0001]" in line
    assert "Kidan, Norio" in line
    assert "classroom" in line
    assert "not a word" in line
    assert "DON" in line


# -- Script -----------------------------------------------------------------


def block(block_id, panels, narration):
    return ScriptBlock(block_id=block_id, panel_ids=panels, narration=narration)


def test_script_block_rejects_duplicate_panels():
    with pytest.raises(ValidationError, match="Duplicate panel_ids"):
        block("b1", ["p1", "p1"], "hello")


def test_script_block_requires_at_least_one_panel():
    with pytest.raises(ValidationError):
        block("b1", [], "hello")


def test_script_word_count_and_total():
    script = ScriptFile(
        chapter_id="c1", created_at="now",
        blocks=[block("b1", ["p1"], "one two three"), block("b2", ["p2"], "four five")],
    )
    assert script.total_words == 5


def test_referenced_panels_deduplicates():
    script = ScriptFile(
        chapter_id="c1", created_at="now",
        blocks=[block("b1", ["p1", "p2"], "a"), block("b2", ["p2", "p3"], "b")],
    )
    assert script.referenced_panels() == ["p1", "p2", "p3"]


def test_full_text_joins_blocks_in_order():
    script = ScriptFile(
        chapter_id="c1", created_at="now",
        blocks=[block("b1", ["p1"], "First line."), block("b2", ["p2"], "Second line.")],
    )
    assert script.full_text() == "First line.\n\nSecond line."


def test_block_char_spans_match_full_text():
    script = ScriptFile(
        chapter_id="c1", created_at="now",
        blocks=[block("b1", ["p1"], "First line."), block("b2", ["p2"], "Second line.")],
    )
    text = script.full_text()
    for b, (start, end) in zip(script.blocks, script.block_char_spans(), strict=True):
        assert text[start:end] == b.narration.strip()


def test_script_requires_at_least_one_block():
    with pytest.raises(ValidationError):
        ScriptFile(chapter_id="c1", created_at="now", blocks=[])


# -- Timeline ---------------------------------------------------------------


def timeline_with(blocks):
    return TimelineFile(
        chapter_id="c1", audio_file="a.wav", sample_rate=24000, duration=10.0,
        created_at="now", blocks=blocks,
    )


def test_timeline_rejects_out_of_order_blocks():
    with pytest.raises(ValidationError, match="before the previous block ended"):
        timeline_with([
            BlockTiming(block_id="b1", start=5.0, end=7.0),
            BlockTiming(block_id="b2", start=1.0, end=3.0),
        ])


def test_timeline_accepts_adjacent_blocks():
    ok = timeline_with([
        BlockTiming(block_id="b1", start=0.0, end=3.0),
        BlockTiming(block_id="b2", start=3.0, end=6.0),
    ])
    assert len(ok.blocks) == 2


def test_degraded_blocks_are_flagged():
    t = timeline_with([
        BlockTiming(block_id="b1", start=0.0, end=3.0, match_ratio=0.95),
        BlockTiming(block_id="b2", start=3.0, end=6.0, method="fallback_proportional"),
        BlockTiming(block_id="b3", start=6.0, end=9.0, match_ratio=0.4),
    ])
    degraded = {b.block_id for b in t.degraded_blocks()}
    assert degraded == {"b2", "b3"}


def test_block_timing_duration():
    assert BlockTiming(block_id="b1", start=1.0, end=4.5).duration == pytest.approx(3.5)


def test_word_timing_order():
    with pytest.raises(ValidationError):
        WordTiming(word="hi", start=2.0, end=1.0)


# -- persistence ------------------------------------------------------------


def test_save_and_load_round_trip(tmp_path):
    script = ScriptFile(
        chapter_id="c1", created_at="now", target_words=100,
        blocks=[block("b1", ["p0001", "p0002"], "Kidan walks in, very quietly.")],
    )
    path = tmp_path / "script.json"
    save_model(script, path)

    loaded = load_model(path, ScriptFile)
    assert loaded.chapter_id == "c1"
    assert loaded.blocks[0].panel_ids == ["p0001", "p0002"]
    assert loaded.blocks[0].narration == script.blocks[0].narration


def test_saved_json_is_utf8_and_readable(tmp_path):
    script = ScriptFile(
        chapter_id="c1", created_at="now",
        blocks=[block("b1", ["p1"], "Il walks in — très calmement.")],
    )
    path = tmp_path / "script.json"
    save_model(script, path)
    assert "très" in path.read_text(encoding="utf-8")


def test_load_model_reports_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing"):
        load_model(tmp_path / "absent.json", ScriptFile)


def test_load_model_surfaces_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_model(path, ScriptFile)


def test_validate_or_raise_names_the_context():
    with pytest.raises(ValueError, match="My context failed validation"):
        validate_or_raise(ScriptFile, {"chapter_id": "c"}, context="My context")
