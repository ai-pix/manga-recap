"""Storyboard validation: the gate that runs before anything costs money."""

from __future__ import annotations

import pytest

from manga_recap.core.config import load_config
from manga_recap.core.schema import (
    DescriptionFile,
    PanelDescription,
    ScriptBlock,
    ScriptFile,
)
from manga_recap.stages.s3_script.validate import build_repair_prompt, validate


@pytest.fixture
def config():
    return load_config()


def make_descriptions(panel_ids, skippable_ids=()):
    return DescriptionFile(
        chapter_id="c1",
        created_at="now",
        panel_count=len(panel_ids),
        panels=[
            PanelDescription(
                panel_id=pid,
                page_number=1,
                reading_order=index + 1,
                image_path=f"{pid}.png",
                action="something happens",
                is_credits_or_ad=pid in skippable_ids,
            )
            for index, pid in enumerate(panel_ids)
        ],
    )


def make_script(blocks, target_words=4000):
    return ScriptFile(
        chapter_id="c1",
        created_at="now",
        target_words=target_words,
        blocks=[
            ScriptBlock(
                block_id=b.get("block_id", f"b{i + 1:03d}"),
                panel_ids=b["panel_ids"],
                narration=b["narration"],
                direction=b.get("direction", ""),
            )
            for i, b in enumerate(blocks)
        ],
    )


PANELS = [f"p{i:04d}" for i in range(1, 11)]


def test_a_well_formed_script_passes():
    script = make_script([{"panel_ids": [p], "narration": "A line of narration here."} for p in PANELS])
    report = validate(script, make_descriptions(PANELS), load_config())
    assert report.ok, report.render()


def test_invented_panel_id_is_an_error():
    script = make_script([
        {"panel_ids": [p], "narration": "A line of narration here."} for p in PANELS[:-1]
    ] + [{"panel_ids": ["p9999"], "narration": "A line of narration here."}])
    report = validate(script, make_descriptions(PANELS), load_config())

    assert not report.ok
    assert any("do not exist" in p and "p9999" in p for p in report.problems)


def test_uncovered_panel_is_an_error():
    script = make_script([{"panel_ids": [p], "narration": "A line."} for p in PANELS[:5]])
    report = validate(script, make_descriptions(PANELS), load_config())

    assert not report.ok
    assert any("never referenced" in p for p in report.problems)


def test_skippable_panels_may_be_omitted():
    descriptions = make_descriptions(PANELS, skippable_ids={PANELS[-1]})
    script = make_script([{"panel_ids": [p], "narration": "A line."} for p in PANELS[:-1]])
    report = validate(script, descriptions, load_config())

    assert report.ok, report.render()


def test_word_count_outside_tolerance_warns():
    short = make_script(
        [{"panel_ids": [p], "narration": "Short."} for p in PANELS], target_words=4000
    )
    report = validate(short, make_descriptions(PANELS), load_config())

    assert report.ok, "a short script is a warning, not a hard failure"
    assert any("short" in w for w in report.warnings)


def test_overlong_word_count_warns():
    long_narration = " ".join(["word"] * 900)
    long_script = make_script(
        [{"panel_ids": [p], "narration": long_narration} for p in PANELS], target_words=100
    )
    report = validate(long_script, make_descriptions(PANELS), load_config())
    assert any("over" in w for w in report.warnings)


def test_too_many_panels_in_one_block_warns():
    script = make_script([
        {"panel_ids": PANELS[:6], "narration": "One line covering a lot."},
        *({"panel_ids": [p], "narration": "A line of narration here."} for p in PANELS[6:]),
    ])
    report = validate(script, make_descriptions(PANELS), load_config())
    assert any("panels" in w for w in report.warnings)


def test_backwards_jump_warns():
    reversed_blocks = [{"panel_ids": [p], "narration": "A line of narration."} for p in reversed(PANELS)]
    script = make_script(reversed_blocks)
    report = validate(script, make_descriptions(PANELS), load_config())
    assert any("jump" in w for w in report.warnings)


def test_repeated_narration_warns():
    line = "The exact same sentence, over and over again, repeating without end."
    script = make_script([{"panel_ids": [p], "narration": line} for p in PANELS])
    report = validate(script, make_descriptions(PANELS), load_config())
    assert any("repeat" in w for w in report.warnings)


def test_duplicate_block_ids_is_an_error():
    script = make_script([
        {"block_id": "b001", "panel_ids": [p], "narration": "A line of narration."} for p in PANELS
    ])
    report = validate(script, make_descriptions(PANELS), load_config())
    assert not report.ok
    assert any("Duplicate block_id" in p for p in report.problems)


def test_errors_render_with_severity():
    script = make_script([{"panel_ids": ["nope"], "narration": "A line."}])
    report = validate(script, make_descriptions(PANELS), load_config())
    rendered = report.render()
    assert "ERROR" in rendered
    assert "nope" in rendered


def test_repair_prompt_lists_every_problem():
    script = make_script([{"panel_ids": ["nope"], "narration": "A line."}])
    report = validate(script, make_descriptions(PANELS), load_config())
    prompt = build_repair_prompt(script, report)

    assert "nope" in prompt
    assert "corrected storyboard" in prompt
