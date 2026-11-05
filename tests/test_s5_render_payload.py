"""Tests for the stage 5 payload: script choice, word coverage, privacy."""

from __future__ import annotations

import json

import pytest
import soundfile as sf

from manga_recap.core.config import Config
from manga_recap.core.paths import ChapterPaths
from manga_recap.core.schema import (
    ScriptBeat,
    ScriptBlock,
    ScriptFile,
    TimelineFile,
    save_model,
)
from manga_recap.render.sync import beats_for_blocks
from manga_recap.stages import s5_render


def make_config(**render_extra) -> Config:
    render = {
        "kernel_slug": "manga-recap-render",
        "max_words_per_beat": 14,
        "min_shot_seconds": 0.7,
        "engine": "pynv",
        "encoder": "h264_nvenc",
    }
    render.update(render_extra)
    return Config(
        {
            "project": {"slug": "test"},
            "llm": {
                "vision": {"provider": "gemini", "model": "test"},
                "script": {"provider": "gemini", "model": "test"},
            },
            "tts": {"backend": "fish-whisper"},
            "render": render,
        }
    )


def _script(narration: str) -> ScriptFile:
    first, _, second = narration.partition(". ")
    return ScriptFile(
        chapter_id="ch01",
        title="Test Chapter",
        series="test-series",
        created_at="2026-01-01T00:00:00Z",
        model="test",
        blocks=[
            ScriptBlock(
                block_id="b001",
                panel_ids=["panel_0001", "panel_0002"],
                narration=narration,
                beats=[
                    ScriptBeat(beat_id="b001_b00", panel_id="panel_0001", text=f"{first}."),
                    ScriptBeat(beat_id="b001_b01", panel_id="panel_0002", text=second),
                ],
            )
        ],
    )


@pytest.fixture
def chapter(tmp_path):
    paths = ChapterPaths.create("ch01", data_dir=tmp_path)
    (paths.panels_dir).mkdir(parents=True, exist_ok=True)
    (paths.panels_dir / "panel_0001.webp").write_bytes(b"RIFFfake")
    (paths.panels_dir / "panel_0002.webp").write_bytes(b"RIFFfake")
    sf.write(str(paths.narration_file), [0.0] * 4410, 4410, subtype="PCM_16")
    return paths


def _timeline(words: list[str]) -> TimelineFile:
    timings = [
        {"word": word, "start": index * 0.2, "end": index * 0.2 + 0.15}
        for index, word in enumerate(words)
    ]
    return TimelineFile(
        chapter_id="ch01",
        audio_file="05_narration.wav",
        sample_rate=4410,
        duration=max(t["end"] for t in timings) + 0.1,
        created_at="2026-01-01T00:00:00Z",
        words=timings,
        blocks=[{"block_id": "b001", "start": 0.0, "end": timings[-1]["end"]}],
    )


def _fake_client(calls: dict):
    class FakeClient:
        username = "tester"

        def upload_dataset(self, source_dir, slug, **kwargs):
            calls["dataset"] = (source_dir, slug, kwargs)
            return f"tester/{slug}"

    return FakeClient


def test_the_narration_script_wins_over_the_root_script(chapter, monkeypatch):
    """Stage 4 spoke 04_script_fish.json, so stage 5 must cut to that text."""
    save_model(_script("Kayden falls hard. He gets back up."), chapter.script_file)
    live_only = _script("A completely different story happens here. Nobody says it aloud.")
    save_model(live_only, chapter.root / "04_script_fish.json")
    save_model(_timeline(["a", "story", "happens", "nobody", "says", "aloud"]), chapter.timeline_file)
    monkeypatch.setattr(s5_render, "KaggleClient", _fake_client({}))

    assert s5_render._script_source(chapter).name == "04_script_fish.json"

    s5_render._build_payload(chapter, make_config(), s5_render._script_source(chapter))
    staged = json.loads(
        (chapter.root / "_kaggle_input" / "script.json").read_text(encoding="utf-8")
    )
    assert staged["blocks"][0]["narration"] == live_only.blocks[0].narration


def test_a_timeline_short_of_the_script_is_refused(chapter):
    script = _script("Kayden falls hard. He gets back up again.")
    needed = sum(beat.word_count for beat in beats_for_blocks(script.blocks, max_words=14))

    with pytest.raises(ValueError, match="word timings"):
        s5_render._check_word_coverage(script, _timeline(["kayden", "falls"]), "script.json", "timeline.json")

    assert needed > 2


def test_an_exact_timeline_is_accepted(chapter):
    script = _script("Kayden falls hard. He gets back up again.")
    needed = sum(beat.word_count for beat in beats_for_blocks(script.blocks, max_words=14))
    words = [f"w{index}" for index in range(needed)]

    s5_render._check_word_coverage(script, _timeline(words), "script.json", "timeline.json")


def test_payload_goes_to_a_private_dataset_instead_of_a_file_host(chapter, monkeypatch):
    calls = {}

    def fail_upload(*args, **kwargs):
        raise AssertionError("stage 5 must not push a render payload to a public host")

    monkeypatch.setattr(s5_render, "KaggleClient", _fake_client(calls))
    monkeypatch.setattr(s5_render.payload, "upload", fail_upload)

    save_model(_script("Kayden falls hard. He gets back up."), chapter.script_file)
    save_model(
        _timeline(["kayden", "falls", "hard", "he", "gets", "back", "up"]),
        chapter.timeline_file,
    )

    url, dataset = s5_render._build_payload(chapter, make_config(), chapter.script_file)

    assert url == ""
    assert dataset == "tester/manga-recap-render-ch01"
    assert calls["dataset"][2]["private"] is True

    staging = chapter.root / "_kaggle_input"
    assert (staging / "panels" / "panel_0001.webp").exists()
    assert (staging / "narration.wav").exists()
    assert (staging / "timeline.json").exists()
    assert (staging / "lib").is_dir()
