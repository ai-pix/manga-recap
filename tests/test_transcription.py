"""Reading the dialogue back, and refusing to script without it.

Crops can be geometrically perfect and the recap can still be worthless, because
a downscaled panel turns manga text into `[illegible]`. These tests cover the
second pass that re-reads bubbles at native resolution, the continuity carried
between independent batches, and the gate that stops stage 3 from inventing
motivation the manga actually stated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.core.schema import (
    BBox,
    DescriptionFile,
    PanelDescription,
    PanelIndex,
    PanelIndexFile,
)
from manga_recap.llm.base import LLMError, LLMResponseError, normalise_transcripts
from manga_recap.stages.s2_describe import (
    _needs_transcript,
    _page_references,
    _with_continuity,
)
from manga_recap.stages.s3_script.validate import ValidationReport, _check_transcription

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _panel(panel_id, page=1, order=1, *, text=False, landscape=False):
    width, height = (600, 400) if landscape else (400, 600)
    panel = PanelIndex(
        panel_id=panel_id,
        page_number=page,
        index_on_page=order,
        reading_order=order,
        bbox=BBox(x1=10, y1=10, x2=width - 10, y2=height - 10),
        image_path=f"02_panels/{panel_id}.png",
        page_width=width,
        page_height=height,
        text_boxes=[BBox(x1=50, y1=50, x2=200, y2=90)] if text else [],
    )
    if text:
        panel.text_image_path = f"02_panels/_text/{panel_id}_text.png"
    return panel


def _index(panels):
    return PanelIndexFile(
        chapter_id="ch_test",
        page_count=3,
        panel_count=len(panels),
        created_at="2026-01-01T00:00:00",
        panels=panels,
    )


def _description(panel_id, order, **kwargs):
    return PanelDescription(
        panel_id=panel_id,
        page_number=1,
        reading_order=order,
        image_path=f"02_panels/{panel_id}.png",
        action="A character stands in a room.",
        **kwargs,
    )


def _descriptions(panels):
    return DescriptionFile(
        chapter_id="ch_test",
        created_at="2026-01-01T00:00:00",
        panel_count=len(panels),
        panels=panels,
    )


# ---------------------------------------------------------------------------
# Transcript response shapes
# ---------------------------------------------------------------------------


def test_normalise_transcripts_accepts_the_usual_shapes():
    assert normalise_transcripts({"panels": [{"panel_id": "a"}]}) == [{"panel_id": "a"}]
    # `extract_json` wraps a bare list under `items`, so providers hand it over.
    assert normalise_transcripts({"items": [{"panel_id": "a"}]}) == [{"panel_id": "a"}]
    assert normalise_transcripts({"transcripts": [{"panel_id": "a"}]}) == [
        {"panel_id": "a"}
    ]


def test_normalise_transcripts_rejects_a_shapeless_response():
    with pytest.raises(LLMResponseError):
        normalise_transcripts({"note": "I could not read any of it"})


# ---------------------------------------------------------------------------
# Which panels get re-read
# ---------------------------------------------------------------------------


def test_only_panels_with_unread_text_are_sent_for_transcription():
    index = _index(
        [
            _panel("panel_0001", order=1, text=True),
            _panel("panel_0002", order=2, text=False),
            _panel("panel_0003", order=3, text=True),
        ]
    )
    described = {
        "panel_0001": _description("panel_0001", 1, has_detected_text=True),
        "panel_0002": _description("panel_0002", 2),
        # Already read during the description pass, so it is left alone.
        "panel_0003": _description(
            "panel_0003",
            3,
            has_detected_text=True,
            speech_bubbles=["Are you serious?"],
        ),
    }

    assert [p.panel_id for p in _needs_transcript(index, described)] == ["panel_0001"]


def test_a_panel_never_described_is_still_sent_for_transcription():
    index = _index([_panel("panel_0001", order=1, text=True)])

    assert [p.panel_id for p in _needs_transcript(index, {})] == ["panel_0001"]


# ---------------------------------------------------------------------------
# Continuity between independent batches
# ---------------------------------------------------------------------------


def test_continuity_carries_the_character_roster_forward():
    """Without this the same person gets a new name in every batch."""
    described = {
        "panel_0001": _description(
            "panel_0001", 1, characters=["tall_blond_boy", "sensei"]
        )
    }

    prompt = _with_continuity("BASE BRIEF", described, window=3, page_count=0)

    assert prompt.startswith("BASE BRIEF")
    assert "sensei" in prompt
    assert "tall_blond_boy" in prompt
    assert "Reuse these exact labels" in prompt


def test_continuity_mentions_the_preceding_panels():
    described = {
        "panel_0001": _description("panel_0001", 1, characters=["kidan"]),
        "panel_0002": _description("panel_0002", 2, characters=["kidan"]),
        "panel_0003": _description("panel_0003", 3, characters=["kidan"]),
    }

    prompt = _with_continuity("BASE", described, window=2, page_count=0)

    lookbehind = prompt.split("The panels immediately before this batch")[1]
    assert "panel_0003" in lookbehind
    assert "panel_0002" in lookbehind
    assert "panel_0001" not in lookbehind


def test_the_first_batch_gets_no_continuity_and_keeps_the_base_prompt():
    assert _with_continuity("BASE", {}, window=3, page_count=0) == "BASE"


def test_continuity_explains_the_layout_reference_images():
    described = {"panel_0001": _description("panel_0001", 1)}

    prompt = _with_continuity("BASE", described, window=0, page_count=1)

    assert "not themselves panels to describe" in prompt


# ---------------------------------------------------------------------------
# Choosing which pages to send as reference
# ---------------------------------------------------------------------------


def _paths_with_pages(tmp_path: Path, page_numbers) -> ChapterPaths:
    from PIL import Image

    paths = ChapterPaths.create("ch_test", tmp_path)
    paths.pages_dir.mkdir(parents=True, exist_ok=True)
    for number in page_numbers:
        Image.new("RGB", (400, 600), (255, 255, 255)).save(
            paths.pages_dir / f"page_{number:03d}.png"
        )
    return paths


def test_a_spread_page_is_sent_as_a_layout_reference(tmp_path):
    """The two halves of a double-page spread mean nothing in isolation."""
    paths = _paths_with_pages(tmp_path, [1])
    batch = [
        _panel("panel_0001", page=1, order=1, landscape=True),
        _panel("panel_0002", page=1, order=2, landscape=True),
    ]

    references = _page_references(paths, batch, limit=2)

    assert [p.name for p in references] == ["page_001.png"]


def test_a_batch_straddling_a_page_break_gets_both_pages(tmp_path):
    paths = _paths_with_pages(tmp_path, [1, 2])
    batch = [
        _panel("panel_0001", page=1, order=1),
        _panel("panel_0002", page=2, order=2),
    ]

    references = _page_references(paths, batch, limit=2)

    assert [p.name for p in references] == ["page_001.png", "page_002.png"]


def test_an_ordinary_single_page_batch_sends_no_reference(tmp_path):
    """The panels already carry the art; a page image here is pure cost."""
    paths = _paths_with_pages(tmp_path, [1])
    batch = [_panel("panel_0001", page=1, order=1), _panel("panel_0002", page=1, order=2)]

    assert _page_references(paths, batch, limit=2) == []


def test_page_references_respect_the_limit(tmp_path):
    paths = _paths_with_pages(tmp_path, [1, 2, 3])
    batch = [
        _panel("panel_0001", page=1, order=1),
        _panel("panel_0002", page=2, order=2),
        _panel("panel_0003", page=3, order=3),
    ]

    assert len(_page_references(paths, batch, limit=2)) == 2


# ---------------------------------------------------------------------------
# Detecting a lost transcript
# ---------------------------------------------------------------------------


def test_untranscribed_distinguishes_a_wordless_panel_from_a_failed_read():
    wordless = _description("panel_0001", 1)
    assert wordless.is_untranscribed() is False

    failed = _description("panel_0001", 1, has_detected_text=True)
    assert failed.is_untranscribed() is True

    read = _description("panel_0001", 1, has_detected_text=True, speech_bubbles=["Hi"])
    assert read.is_untranscribed() is False

    sfx_only = _description("panel_0001", 1, has_detected_text=True, sfx_text=["DOOM"])
    assert sfx_only.is_untranscribed() is False


def test_too_much_lost_dialogue_stops_the_script():
    """Above the threshold the narrator would have to invent the dialogue."""
    report = ValidationReport()
    descriptions = _descriptions(
        [
            _description("panel_0001", 1, has_detected_text=True, speech_bubbles=["A"]),
            _description("panel_0002", 2, has_detected_text=True),
            _description("panel_0003", 3, has_detected_text=True),
            _description("panel_0004", 4, has_detected_text=True),
        ]
    )
    config = load_config()

    _check_transcription(descriptions, config, report)

    assert not report.ok
    assert "would have to invent the dialogue" in report.problems[0]
    assert "panel_0002" in report.problems[0]


def test_a_little_lost_dialogue_only_warns():
    report = ValidationReport()
    # One gap out of twelve is under the default 10% tolerance.
    panels = [
        _description(
            f"panel_{number:04d}",
            number,
            has_detected_text=True,
            speech_bubbles=[] if number == 3 else [f"line {number}"],
        )
        for number in range(1, 13)
    ]
    config = load_config()

    _check_transcription(_descriptions(panels), config, report)

    assert report.ok
    assert len(report.warnings) == 1
    assert "1 of 12" in report.warnings[0]


def test_a_chapter_with_no_text_is_never_gated():
    report = ValidationReport()
    descriptions = _descriptions([_description("panel_0001", 1)])

    _check_transcription(descriptions, load_config(), report)

    assert report.ok and not report.warnings


def test_context_line_marks_a_panel_whose_dialogue_was_lost():
    """The script writer has to be able to see the gap, not guess at it."""
    line = _description(
        "panel_0001", 1, has_detected_text=True, speech_bubbles=["I like her"]
    ).to_context_line()
    assert "They say: I like her" in line

    blank = _description("panel_0001", 1, has_detected_text=True).to_context_line()
    assert "Dialogue present in the art but unreadable." in blank


def test_llm_error_is_importable_from_the_transcription_path():
    """Guards the except clauses in the transcription loop."""
    assert issubclass(LLMError, RuntimeError)
