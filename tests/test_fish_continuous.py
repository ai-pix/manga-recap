"""Tests for continuous Fish narration and strict forced alignment."""

from __future__ import annotations

import json

import pytest
import soundfile as sf

from manga_recap.core.config import Config
from manga_recap.core.paths import ChapterPaths
from manga_recap.core.schema import ScriptBeat, ScriptBlock, ScriptFile, TimelineFile, save_model
from manga_recap.render.sync import alignment_tokens, beats_for_blocks
from manga_recap.stages import s4_speech
from manga_recap.stages.s4_speech import fish_continuous_engine


def make_config(**tts_extra) -> Config:
    tts = {
        "backend": "fish-whisper",
        "kernel_slug": "manga-recap-tts",
        "align_dataset_prefix": "manga-recap-align",
        "poll_interval_seconds": 1,
        "max_wait_seconds": 60,
    }
    tts.update(tts_extra)
    return Config(
        {
            "project": {"slug": "test"},
            "llm": {
                "vision": {"provider": "gemini", "model": "test"},
                "script": {"provider": "gemini", "model": "test"},
            },
            "crop": {"detector": "opencv"},
            "tts": tts,
            "align": {
                "whisper_model": "large-v3-turbo",
                "device": "cuda",
                "compute_type": "float16",
                "min_match_ratio": 0.85,
                "strict": True,
            },
            "render": {"max_words_per_beat": 14, "min_shot_seconds": 0.7},
        }
    )


@pytest.fixture
def mini_script(tmp_path):
    paths = ChapterPaths.create("ch01", data_dir=tmp_path)
    paths.root.mkdir(parents=True, exist_ok=True)
    script = ScriptFile(
        chapter_id="ch01",
        title="Test Chapter",
        series="test-series",
        created_at="2026-11-04T00:00:00Z",
        model="test",
        blocks=[
            ScriptBlock(
                block_id="b001",
                panel_ids=["panel_0001", "panel_0002"],
                narration="Our story starts here. Shun wakes up confused.",
                beats=[
                    ScriptBeat(
                        beat_id="b001_b00",
                        panel_id="panel_0001",
                        text="Our story starts here.",
                    ),
                    ScriptBeat(
                        beat_id="b001_b01",
                        panel_id="panel_0002",
                        text="Shun wakes up confused.",
                    ),
                ],
            )
        ],
    )
    save_model(script, paths.script_file)
    return paths, script


def test_s4_speech_dispatches_continuous_fish_backend(mini_script, monkeypatch):
    paths, _ = mini_script
    called = False

    def fake_run(paths_arg, config, *, force=False):
        nonlocal called
        called = True
        return TimelineFile(
            chapter_id="ch01",
            audio_file="05_narration.wav",
            sample_rate=44100,
            duration=1.0,
            created_at="2026-11-04T00:00:00Z",
            blocks=[{"block_id": "b001", "start": 0.0, "end": 1.0}],
        )

    monkeypatch.setattr(fish_continuous_engine, "run_fish_continuous_tts", fake_run)
    s4_speech.run(paths, make_config(), force=True)
    assert called is True


def test_validate_timeline_rejects_wrong_word_count(mini_script):
    _, script = mini_script
    timeline = TimelineFile(
        chapter_id="ch01",
        audio_file="05_narration.wav",
        sample_rate=44100,
        duration=2.0,
        created_at="2026-11-04T00:00:00Z",
        words=[{"word": "story", "start": 0.0, "end": 0.2}],
        blocks=[{"block_id": "b001", "start": 0.0, "end": 2.0}],
    )

    with pytest.raises(ValueError, match="word timings"):
        fish_continuous_engine._validate_timeline(
            timeline,
            script,
            make_config(),
            expected_sample_rate=44100,
            expected_duration=2.0,
        )


def test_validate_timeline_rejects_fallback_alignment(mini_script):
    _, script = mini_script
    beats = beats_for_blocks(script.blocks, max_words=14)
    tokens = [token for beat in beats for token in alignment_tokens(beat.text)]
    words = [
        {"word": token, "start": index * 0.1, "end": index * 0.1 + 0.08}
        for index, token in enumerate(tokens)
    ]
    timeline = TimelineFile(
        chapter_id="ch01",
        audio_file="05_narration.wav",
        sample_rate=44100,
        duration=float(len(tokens) * 0.1),
        created_at="2026-11-04T00:00:00Z",
        words=words,
        blocks=[
            {
                "block_id": "b001",
                "start": 0.0,
                "end": float(len(tokens) * 0.1),
                "method": "fallback_proportional",
                "match_ratio": 0.4,
            }
        ],
    )

    with pytest.raises(ValueError, match="match ratio"):
        fish_continuous_engine._validate_timeline(
            timeline,
            script,
            make_config(),
            expected_sample_rate=44100,
            expected_duration=float(len(tokens) * 0.1),
        )


def test_validate_timeline_accepts_exact_word_anchored_beats(mini_script):
    _, script = mini_script
    beats = beats_for_blocks(script.blocks, max_words=14)
    tokens = [token for beat in beats for token in alignment_tokens(beat.text)]
    duration = float(len(tokens) * 0.1)
    words = [
        {"word": token, "start": index * 0.1, "end": index * 0.1 + 0.08}
        for index, token in enumerate(tokens)
    ]
    timeline = TimelineFile(
        chapter_id="ch01",
        audio_file="05_narration.wav",
        sample_rate=44100,
        duration=duration,
        created_at="2026-11-04T00:00:00Z",
        words=words,
        blocks=[{"block_id": "b001", "start": 0.0, "end": duration}],
    )

    fish_continuous_engine._validate_timeline(
        timeline,
        script,
        make_config(),
        expected_sample_rate=44100,
        expected_duration=duration,
    )


def test_align_payload_uses_private_dataset_and_renderer_sync(mini_script, monkeypatch):
    paths, script = mini_script
    sf.write(str(paths.narration_file), [0.0] * 4410, 4410, subtype="PCM_16")

    calls = {}

    class FakeRun:
        total_seconds = 1.0

    class FakeClient:
        username = "tester"

        def upload_dataset(self, source_dir, slug, **kwargs):
            calls["dataset"] = (source_dir, slug, kwargs)
            return f"tester/{slug}"

        def wait_for_kernel(self, kernel_id, **kwargs):
            calls["kernel_id"] = kernel_id
            return FakeRun()

        def download_kernel_output(self, kernel_id, destination):
            destination.mkdir(parents=True, exist_ok=True)
            timeline = {
                "chapter_id": "ch01",
                "audio_file": "narration.wav",
                "sample_rate": 4410,
                "duration": 1.0,
                "created_at": "2026-11-04T00:00:00Z",
                "words": [],
                "blocks": [{"block_id": "b001", "start": 0.0, "end": 1.0}],
            }
            (destination / "timeline.json").write_text(json.dumps(timeline), encoding="utf-8")
            return destination

    def fake_push(client, slug, payload_url, paths_arg, *, input_dataset=None):
        calls["push"] = (slug, payload_url, input_dataset)

    monkeypatch.setattr(fish_continuous_engine, "KaggleClient", FakeClient)
    monkeypatch.setattr(s4_speech, "_push_kernel", fake_push)
    monkeypatch.setattr(fish_continuous_engine, "_validate_timeline", lambda *args, **kwargs: None)

    timeline = fish_continuous_engine._align_on_kaggle_gpu(paths, make_config(), script)

    assert timeline.words == []
    assert calls["push"] == ("manga-recap-tts", "", "tester/manga-recap-align-ch01")
    assert calls["dataset"][2]["private"] is True

    staging = paths.root / "_align_input"
    job = json.loads((staging / "job.json").read_text(encoding="utf-8"))
    assert job["mode"] == "align"
    assert job["align"]["strict"] is True
    assert job["render"]["max_words_per_beat"] == 14
    assert (staging / "lib" / "recap_sync.py").exists()
    assert (staging / "narration.wav").exists()
