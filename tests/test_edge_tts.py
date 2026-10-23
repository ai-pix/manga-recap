"""Unit tests for the Edge-TTS engine and Stage 4 speech dispatch."""

from __future__ import annotations

import pydantic
import pytest

from manga_recap.core.config import Config
from manga_recap.core.paths import ChapterPaths
from manga_recap.core.schema import ScriptBlock, ScriptFile, TimelineFile, save_model
from manga_recap.stages import s4_speech
from manga_recap.stages.s4_speech.edge_tts_engine import run_edge_tts


def make_config(tts_extra=None):
    tts_dict = {"backend": "edge-tts"}
    if tts_extra:
        tts_dict.update(tts_extra)
    return Config(
        {
            "llm": {
                "vision": {"provider": "gemini", "model": "gemini-2.0-flash"},
                "script": {"provider": "gemini", "model": "gemini-2.0-flash"},
            },
            "crop": {"detector": "opencv"},
            "tts": tts_dict,
        }
    )


@pytest.fixture
def mini_script(tmp_path):
    chapter_dir = tmp_path / "ch01"
    chapter_dir.mkdir(parents=True)
    paths = ChapterPaths.create("ch01", data_dir=tmp_path)
    paths.panels_dir.mkdir(parents=True, exist_ok=True)

    script = ScriptFile(
        chapter_id="ch01",
        title="Test Chapter",
        series="test-series",
        created_at="2026-10-01T00:00:00Z",
        model="agent",
        blocks=[
            ScriptBlock(
                block_id="b001",
                panel_ids=["panel_0001"],
                narration="Our story kicks off with our main character, Shun.",
                direction="establishing",
            ),
            ScriptBlock(
                block_id="b002",
                panel_ids=["panel_0002"],
                narration="He sits up clutching his knees, wondering what went wrong.",
                direction="beat",
            ),
        ],
    )
    save_model(script, paths.script_file)
    return paths


def test_edge_tts_empty_script_raises(tmp_path):
    paths = ChapterPaths.create("ch01", data_dir=tmp_path)
    paths.root.mkdir(parents=True, exist_ok=True)
    script = ScriptFile(
        chapter_id="ch01",
        title="Empty",
        created_at="2026-10-01T00:00:00Z",
        blocks=[
            ScriptBlock(
                block_id="b001",
                panel_ids=["panel_0001"],
                narration="Placeholder",
            )
        ],
    )
    script.blocks = []  # Bypass min_length validation for the test
    paths.script_file.write_text(script.model_dump_json(), encoding="utf-8")

    config = make_config()
    with pytest.raises((ValueError, pydantic.ValidationError)):
        run_edge_tts(paths, config)


def test_s4_speech_dispatch_edge_tts(mini_script, monkeypatch):
    """Verify s4_speech.run dispatches to edge-tts when configured."""
    config = make_config()
    called = False

    def mock_run_edge_tts(paths, conf, force=False):
        nonlocal called
        called = True
        return TimelineFile(
            chapter_id="ch01",
            audio_file="05_narration.wav",
            sample_rate=24000,
            duration=5.0,
            tts_backend="edge-tts (mock)",
            created_at="2026-10-01T00:00:00Z",
            blocks=[
                {
                    "block_id": "b001",
                    "start": 0.0,
                    "end": 2.5,
                    "method": "aligned",
                    "match_ratio": 1.0,
                },
                {
                    "block_id": "b002",
                    "start": 2.7,
                    "end": 5.0,
                    "method": "aligned",
                    "match_ratio": 1.0,
                },
            ],
        )

    monkeypatch.setattr("manga_recap.stages.s4_speech.edge_tts_engine.run_edge_tts", mock_run_edge_tts)
    timeline = s4_speech.run(mini_script, config, force=True)
    assert called is True
    assert timeline.duration == 5.0
    assert len(timeline.blocks) == 2
