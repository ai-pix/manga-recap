"""Render: clip expansion, ffmpeg graph construction, and a real encode."""

from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

import pytest
from PIL import Image

from manga_recap.core.schema import ScriptBlock
from manga_recap.render import sync
from manga_recap.render.ffmpeg import (
    Clip,
    blurred_backdrop_filter,
    build_clips,
    build_concat_command,
    build_segment_command,
    build_still_command,
    compose_filter,
    render,
)
from manga_recap.render.kenburns import StyleSettings, pick_bgm
from manga_recap.render.sync import coverage_gaps, plan_shots

# Blocks carry one sentence each, which is what the storyboard prompt asks for.
# `words` below are the word-level timings the aligner produces for them.
SCRIPT = {
    "blocks": [
        {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "First beat lands here."},
        {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "The second beat lands."},
        {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "And the last one lands."},
    ]
}

WORD_DURATION = 0.3


def _words(*texts):
    """Word timings laid end to end, the way the aligner emits them."""
    words = []
    clock = 0.0
    for text in texts:
        for token in text.split():
            words.append({"word": token.strip(".,!?").lower(), "start": clock, "end": clock + WORD_DURATION})
            clock += WORD_DURATION
    return words


_DURATION = WORD_DURATION * sum(len(t.split()) for t in (
    "First beat lands here. The second beat lands. And the last one lands.".split()
))

TIMELINE = {
    "duration": _DURATION,
    "blocks": [],
    "words": _words("First beat lands here.", "The second beat lands.", "And the last one lands."),
}


@pytest.fixture
def panels(tmp_path):
    directory = tmp_path / "panels"
    directory.mkdir()
    for index in range(1, 5):
        image = Image.new("RGB", (600, 850), (245, 245, 245))
        for y in range(0, 850, 30):
            for x in range(0, 600, 30):
                if (x + y + index * 20) % 90 == 0:
                    for dy in range(4):
                        for dx in range(4):
                            image.putpixel((x + dx, y + dy), (25, 25, 25))
        image.save(directory / f"panel_{index:04d}.png")
    return directory


@pytest.fixture
def audio(tmp_path):
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(24000)
        handle.writeframes(b"\x00\x01" * 24000 * 9)
    return path


# -- clip expansion ---------------------------------------------------------


def test_one_clip_per_bound_panel(panels):
    clips = build_clips(SCRIPT, TIMELINE, panels)
    assert [c.panel_id for c in clips] == ["panel_0001", "panel_0002", "panel_0003"]


def test_a_sentence_naming_two_panels_cuts_between_them(panels):
    """The user's core complaint: the picture must follow the sentence.

    A block whose narration describes two actions in order, bound to two
    panels, must produce a cut partway through the block rather than one panel
    held for the whole sentence.
    """
    text = "He grabs her wrist and drags her out the door."
    script = {
        "blocks": [
            {
                "block_id": "b1",
                "panel_ids": ["panel_0001", "panel_0002"],
                "narration": text,
            }
        ]
    }
    words = _words(text)

    report = plan_shots(
        script["blocks"], words, audio_duration=WORD_DURATION * len(text.split())
    )
    assert [s.panel_id for s in report.shots] == ["panel_0001", "panel_0002"]
    assert report.shots[0].end == pytest.approx(report.shots[1].start)


def test_each_shot_starts_on_the_first_word_of_its_clause(panels):
    words = _words("He grabs her wrist and drags her out the door.")
    script = {
        "blocks": [
            {
                "block_id": "b1",
                "panel_ids": ["panel_0001", "panel_0002"],
                "narration": "He grabs her wrist and drags her out the door.",
            }
        ]
    }
    report = plan_shots(
        script["blocks"], words, audio_duration=WORD_DURATION * 10, max_words_per_beat=5
    )

    assert len(report.shots) >= 2
    second = report.shots[1]
    # The second clause opens on "and", the fifth word, so that is where the cut
    # lands: the panel changes on the first word of the clause it belongs to.
    assert second.start == pytest.approx(words[4]["start"], abs=0.01)
    assert all(s.anchored for s in report.shots)


def test_shots_tile_the_whole_narration_with_no_gaps(panels):
    report = plan_shots(SCRIPT["blocks"], TIMELINE["words"], audio_duration=TIMELINE["duration"])

    assert report.problems == []
    assert report.shots[0].start == pytest.approx(0.0)
    assert report.shots[-1].end == pytest.approx(TIMELINE["duration"], abs=0.01)
    assert coverage_gaps(report.shots, TIMELINE["duration"]) == []
    assert report.drift == pytest.approx(0.0, abs=0.01)


def test_silence_between_blocks_shows_the_previous_panel(panels):
    """The bug this replaces: a gap in the audio used to drop a panel entirely.

    The old renderer chained clips and derived each cut from the sum of the
    durations before it, so the 0.7s of silence between two blocks was never
    accounted for. Over a chapter that accumulated into the video running tens
    of seconds ahead of the narration.
    """
    texts = ["First beat lands here.", "The second beat lands."]
    words = []
    clock = 0.0
    for text in texts:
        for token in text.split():
            words.append({"word": token.strip(".,!?").lower(), "start": clock, "end": clock + 0.3})
            clock += 0.3
        clock += 0.7  # the pause a narrator takes between blocks

    script = {
        "blocks": [
            {"block_id": "b1", "panel_ids": ["panel_0001"], "narration": texts[0]},
            {"block_id": "b2", "panel_ids": ["panel_0002"], "narration": texts[1]},
        ]
    }
    report = plan_shots(script["blocks"], words, audio_duration=clock)

    assert coverage_gaps(report.shots, clock) == []
    assert report.drift == pytest.approx(0.0, abs=0.01)
    # The first panel holds across the silence rather than cutting early.
    assert report.shots[0].end == pytest.approx(report.shots[1].start)
    assert report.shots[0].end > 1.5


def test_frames_sum_to_the_audio_length_with_no_rounding_drift(panels):
    """Frames come from absolute timestamps, so rounding cannot accumulate."""
    clips = build_clips(SCRIPT, TIMELINE, panels, fps=30)
    assert sum(c.frames for c in clips) == round(TIMELINE["duration"] * 30)

    boundaries = [c.start for c in clips] + [clips[-1].end]
    assert boundaries[0] == pytest.approx(0.0)
    assert boundaries[-1] == pytest.approx(TIMELINE["duration"], abs=1.0 / 30)


def test_a_long_chapter_does_not_accumulate_drift(panels):
    """A hundred blocks with realistic gaps must still cover the audio exactly."""
    blocks = []
    words = []
    clock = 0.0
    for index in range(100):
        text = f"Beat number {index} happens right now."
        blocks.append({"block_id": f"b{index:03d}", "panel_ids": ["panel_0001"], "narration": text})
        for token in text.split():
            words.append({"word": token.strip(".,!?").lower(), "start": clock, "end": clock + 0.3})
            clock += 0.3
        clock += 0.4

    report = plan_shots(blocks, words, audio_duration=clock)
    assert report.drift == pytest.approx(0.0, abs=0.01)
    assert coverage_gaps(report.shots, clock) == []

    clips = build_clips({"blocks": blocks}, {"duration": clock, "words": words}, panels, fps=30)
    assert sum(c.frames for c in clips) == round(clock * 30)


def test_borrowing_time_for_a_short_shot_does_not_overlap_the_next_one(panels):
    """Growing a brief shot must shorten its neighbour, not overlap it.

    A shot list that covers more audio than exists is the mirror image of the
    drift bug: the total no longer equals the narration length.
    """
    words = [
        {"word": "hi", "start": 0.0, "end": 0.1},
        {"word": "there", "start": 0.1, "end": 0.2},
        {"word": "this", "start": 5.0, "end": 5.4},
        {"word": "one", "start": 5.4, "end": 5.8},
        {"word": "runs", "start": 5.8, "end": 6.2},
        {"word": "long", "start": 6.2, "end": 6.6},
    ]
    blocks = [
        {"block_id": "b1", "panel_ids": ["panel_0001"], "narration": "Hi there"},
        {"block_id": "b2", "panel_ids": ["panel_0002"], "narration": "This one runs long"},
    ]

    report = plan_shots(blocks, words, audio_duration=7.0, min_shot_seconds=1.5)

    assert report.drift == pytest.approx(0.0, abs=0.01)
    assert coverage_gaps(report.shots, 7.0) == []
    for earlier, later in zip(report.shots, report.shots[1:], strict=False):
        assert later.start >= earlier.end - 1e-6, "shots must not overlap"


def test_missing_word_timings_fall_back_and_say_so(panels):
    """An interpolated cut is a guess, and the report has to admit it."""
    report = plan_shots(SCRIPT["blocks"], [], audio_duration=TIMELINE["duration"])

    assert report.problems == []
    assert report.warnings
    assert not any(s.anchored for s in report.shots)
    assert report.drift == pytest.approx(0.0, abs=0.01)


def test_a_mismatched_word_count_is_reported(panels):
    report = plan_shots(SCRIPT["blocks"], TIMELINE["words"][:3], audio_duration=TIMELINE["duration"])
    assert any("word timings" in w for w in report.warnings)


def test_missing_panel_image_is_skipped_not_fatal(panels):
    script = {"blocks": [{"block_id": "b1", "panel_ids": ["panel_9999"], "narration": "gone"}]}
    timeline = {"duration": 3.0, "words": _words("gone")}
    assert build_clips(script, timeline, panels) == []


def test_empty_timeline_produces_no_clips(panels):
    assert build_clips(SCRIPT, {"duration": 0.0, "words": []}, panels) == []


def test_explicit_beats_override_the_splitter(panels):
    """A writer who bound a clause to a panel by hand wins over the regex."""
    block = ScriptBlock.model_validate(
        {
            "block_id": "b1",
            "panel_ids": ["panel_0001", "panel_0002"],
            "narration": "He types furiously on the keyboard, then freezes in horror.",
            "beats": [
                {"beat_id": "k", "text": "He types furiously on the keyboard", "panel_id": "panel_0002"},
                {"beat_id": "h", "text": "then freezes in horror.", "panel_id": "panel_0001"},
            ],
        }
    )
    beats = sync.derive_beats(block)
    assert [b.panel_id for b in beats] == ["panel_0002", "panel_0001"]
    assert all(b.explicit for b in beats)


def test_merge_repeats_joins_consecutive_shots_of_one_panel(panels):
    """Two clauses on one panel are one shot; cutting between them is a no-op."""
    text = "He grabs her wrist and drags her out the door."
    report = plan_shots(
        [{"block_id": "b1", "panel_ids": ["panel_0001"], "narration": text}],
        _words(text),
        audio_duration=WORD_DURATION * 10,
        max_words_per_beat=5,
    )
    assert len(report.shots) > 1, "the sentence should split into clauses"

    merged = sync.merge_repeats(report.shots)
    assert len(merged) == 1
    assert merged[0].start == pytest.approx(report.shots[0].start)
    assert merged[0].end == pytest.approx(report.shots[-1].end)


def test_unbound_panels_are_reported(panels):
    report = plan_shots(SCRIPT["blocks"], TIMELINE["words"], audio_duration=TIMELINE["duration"])
    blocks = [{"panel_ids": ["panel_0001", "panel_0004"]}]
    assert sync.unbound_panels(blocks, report.shots) == ["panel_0004"]


# -- command construction ---------------------------------------------------


def test_a_static_shot_runs_no_filters(panels, tmp_path):
    """With no Ken Burns move, the segment command touches no pixels.

    This is the whole efficiency claim: a still is held by looping it, so the
    per-frame cost of a panel is the encoder alone.
    """
    clips = build_clips(SCRIPT, TIMELINE, panels)
    command = build_segment_command(
        tmp_path / "still.png",
        tmp_path / "seg.mp4",
        clips[0].frames,
        width=320,
        height=180,
        zoom_end=1.0,
    )
    assert "-vf" not in command
    assert command[command.index("-frames:v") + 1] == str(clips[0].frames)
    assert "libx264" in command
    assert "yuv420p" in command


def test_a_moving_shot_crops_the_oversized_still_instead_of_rescaling(panels, tmp_path):
    """Ken Burns is a moving crop over a pre-scaled still, not a per-frame rescale."""
    clips = build_clips(SCRIPT, TIMELINE, panels)
    command = build_segment_command(
        tmp_path / "still.png",
        tmp_path / "seg.mp4",
        clips[0].frames,
        width=320,
        height=180,
        zoom_end=1.06,
    )
    graph = command[command.index("-vf") + 1]
    assert graph.startswith("crop=")
    assert "zoompan" not in graph
    assert "boxblur" not in graph


def test_the_still_is_scaled_oversized_when_a_move_is_configured(panels, tmp_path):
    """The crop needs somewhere to travel, so the still is made larger."""
    clips = build_clips(SCRIPT, TIMELINE, panels)
    moving = build_still_command(
        clips[0], tmp_path / "still.png", width=1920, height=1080, zoom_end=1.06
    )
    static = build_still_command(
        clips[0], tmp_path / "still.png", width=1920, height=1080, zoom_end=1.0
    )

    assert "1920" not in moving[moving.index("-vf") + 1].split("scale=")[1][:6]
    assert moving[moving.index("-vf") + 1] != static[static.index("-vf") + 1]
    assert "-frames:v" in moving
    assert moving[moving.index("-frames:v") + 1] == "1"


def test_solid_mode_never_crops_the_art(panels, tmp_path):
    clips = build_clips(SCRIPT, TIMELINE, panels)
    command = build_still_command(
        clips[0], tmp_path / "still.png", width=1920, height=1080, background="0x0d0d12"
    )
    graph = command[command.index("-vf") + 1]
    assert "force_original_aspect_ratio=decrease" in graph
    assert "pad=" in graph
    assert "boxblur" not in graph


def test_crop_mode_fills_the_frame(panels, tmp_path):
    clips = build_clips(SCRIPT, TIMELINE, panels)
    command = build_still_command(
        clips[0], tmp_path / "still.png", width=1920, height=1080, background="crop"
    )
    graph = command[command.index("-vf") + 1]
    assert "force_original_aspect_ratio=increase" in graph
    assert "crop=" in graph
    assert "pad=" not in graph


def test_blurred_mode_composites_the_panel_over_a_blur_of_itself(panels, tmp_path):
    clips = build_clips(SCRIPT, TIMELINE, panels)
    command = build_still_command(
        clips[0], tmp_path / "still.png", width=1920, height=1080, background="blurred"
    )
    graph = command[command.index("-vf") + 1]
    assert "split=2" in graph
    assert "overlay=" in graph
    assert "boxblur" in graph
    assert "eq=brightness=-0.12" in graph


def test_blurred_mode_leaves_the_foreground_unpadded(panels):
    """A padded foreground hides the backdrop, which is the whole point.

    Padding the foreground to the full frame fills the margins with the pad
    colour, so `overlay` covers the blur with solid black and the mode silently
    degrades into the bars it was added to remove.
    """
    graph = compose_filter(width=1920, height=1080, background="blurred")
    # rsplit: the first `[fgsrc]` is the split's output label, the second is the
    # link that actually carries the foreground filter chain.
    foreground = graph.rsplit("[fgsrc]", 1)[1].split("[fg]")[0]
    assert "pad=" not in foreground, foreground
    assert "force_original_aspect_ratio=decrease" in foreground


def test_the_blur_runs_on_a_downscaled_copy(panels):
    """The whole reason a blurred backdrop is affordable.

    A full-resolution boxblur over two megapixels per panel is the most
    expensive thing this renderer can do. Blurring a 64-pixel-wide copy and
    scaling it back up is visually the same, because a blurred backdrop has no
    detail to lose.
    """
    graph = blurred_backdrop_filter(width=1920, height=1080)
    downscale = graph.split("scale=")[2]
    assert downscale.startswith("512:"), "the blur must happen at 512px wide"
    assert graph.index("boxblur") > graph.index("scale=512:")
    # And it is upscaled back to full size afterwards.
    assert "scale=1920:1080:flags=bicubic" in graph


def test_blur_settings_reach_the_filter():
    graph = blurred_backdrop_filter(
        width=1920, height=1080, blur_width=40, blur_radius=12, darken=0.25
    )
    assert "scale=40:" in graph
    assert "boxblur=12:1" in graph
    assert "eq=brightness=-0.250" in graph


def test_the_blur_never_runs_per_frame(panels, tmp_path):
    """The composition is baked into the still, so encoding touches no pixels.

    This is the invariant that separates a cheap blurred backdrop from the
    expensive one: `boxblur` may appear in the still-prep filter and nowhere
    else. If it ever shows up in a segment command, the backdrop has gone back
    to being computed 19,000 times.
    """
    clips = build_clips(SCRIPT, TIMELINE, panels)
    for zoom in (1.0, 1.06):
        segment = build_segment_command(
            tmp_path / "still.png",
            tmp_path / "seg.mp4",
            clips[0].frames,
            width=320,
            height=180,
            zoom_end=zoom,
        )
        assert "boxblur" not in " ".join(segment), f"blur leaked into encoding at zoom {zoom}"


def test_the_still_command_asks_for_exactly_one_frame(panels, tmp_path):
    """Whatever the composition, it is a single frame, so it is paid once."""
    clips = build_clips(SCRIPT, TIMELINE, panels)
    command = build_still_command(
        clips[0], tmp_path / "still.png", width=320, height=180, background="blurred"
    )
    assert command[command.index("-frames:v") + 1] == "1"


def test_a_static_shot_is_not_rendered_oversized(panels, tmp_path):
    """No move means no headroom, and the frame must come out at exact size.

    Adding a percentage of headroom unconditionally made every static still 1%
    oversized, and with no crop to trim it back the encoder emitted the video at
    the wrong resolution. Invisible while Ken Burns was on, since the crop hid
    it.
    """
    clips = build_clips(SCRIPT, TIMELINE, panels)
    static = build_still_command(
        clips[0], tmp_path / "still.png", width=1920, height=1080,
        background="blurred", zoom_end=1.0,
    )
    graph = static[static.index("-vf") + 1]
    assert "1920:1080" in graph
    assert "1938" not in graph and "1939" not in graph
    assert "1086" not in graph and "1088" not in graph


def test_a_moving_shot_is_oversized_so_the_crop_has_room(panels, tmp_path):
    clips = build_clips(SCRIPT, TIMELINE, panels)
    moving = build_still_command(
        clips[0], tmp_path / "still.png", width=1920, height=1080,
        background="blurred", zoom_end=1.06,
    )
    graph = moving[moving.index("-vf") + 1]
    # The crop target is exactly the output size even though the still is larger.
    assert "crop=2054:1156" in graph
    assert "scale=2054:1156" in graph


def test_concat_copies_the_video_and_encodes_only_the_audio(audio, tmp_path):
    segments = [tmp_path / "a.mp4", tmp_path / "b.mp4"]
    command = build_concat_command(segments, audio, tmp_path / "out.mp4")

    assert "-c:v" in command
    assert command[command.index("-c:v") + 1] == "copy"
    assert command[command.index("-c:a") + 1] == "aac"
    assert "-shortest" in command


def test_concat_rejects_an_empty_segment_list(audio, tmp_path):
    with pytest.raises(ValueError, match="No segments"):
        build_concat_command([], audio, tmp_path / "out.mp4")


def test_missing_ffmpeg_explains_where_it_belongs(monkeypatch, panels):
    monkeypatch.setattr("manga_recap.render.ffmpeg.shutil.which", lambda _: None)
    with pytest.raises(FileNotFoundError, match="Kaggle"):
        build_still_command(Clip("panel_0001", Path("p.png"), 0.0, 1.0), Path("o.png"), width=1, height=1)


# -- real encode ------------------------------------------------------------

needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg is not installed locally"
)


def _render(panels, audio, output, **overrides):
    settings = {
        "width": 320,
        "height": 180,
        "fps": 15,
        "crf": 30,
        "preset": "ultrafast",
        "encoder": "libx264",
        "zoom_end": 1.0,
        "max_workers": 2,
    }
    settings.update(overrides)
    return render(SCRIPT, TIMELINE, panels, audio, output, settings)


@needs_ffmpeg
def test_the_blurred_backdrop_actually_shows_in_the_margins(tmp_path):
    """Render a portrait panel both ways and compare the edge pixels.

    The solid version has black bars; the blurred version has a soft, darkened
    copy of the art. Asserted on real pixels because a filter string can look
    correct and still composite to something entirely different — an earlier
    version padded the foreground and produced pure black bars while every
    string assertion still passed.
    """
    import numpy as np
    from PIL import Image

    portrait = tmp_path / "portrait.png"
    Image.new("RGB", (400, 640), (240, 240, 240)).save(portrait)
    clip = Clip("panel_0001", portrait, 0.0, 1.0)

    edges = {}
    for mode in ("blurred", "0x0d0d12"):
        out = tmp_path / f"{mode}.png"
        result = subprocess.run(
            build_still_command(clip, out, width=320, height=180, background=mode),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr[-1500:]
        edges[mode] = np.asarray(Image.open(out).convert("RGB"), dtype=int)[90, 4]

    # The solid version pads with 0x0d0d12.
    assert tuple(edges["0x0d0d12"]) == (13, 13, 18)
    blurred = edges["blurred"]
    assert blurred.mean() > 40, "the backdrop should be visible, not black"
    assert blurred.std() < 30, "a backdrop should be smooth, not a hard edge"


@needs_ffmpeg
def test_render_produces_a_playable_video(panels, audio, tmp_path):
    output = tmp_path / "out.mp4"
    summary = _render(panels, audio, output)

    assert output.exists()
    assert output.stat().st_size > 1000
    assert summary["clip_count"] == 3
    assert summary["panels_shown"] == ["panel_0001", "panel_0002", "panel_0003"]


@needs_ffmpeg
def test_render_segmented_engine_produces_valid_video(panels, audio, tmp_path):
    output = tmp_path / "segmented_out.mp4"
    summary = _render(panels, audio, output, engine="segmented")

    assert output.exists()
    assert output.stat().st_size > 1000
    assert summary["clip_count"] == 3
    assert summary["panels_shown"] == ["panel_0001", "panel_0002", "panel_0003"]


@needs_ffmpeg
def test_rendered_duration_matches_the_narration(panels, audio, tmp_path):
    """The check that would have caught the old renderer finishing early."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        pytest.skip("ffprobe is not installed")

    output = tmp_path / "out.mp4"
    _render(panels, audio, output)

    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(output)],
        capture_output=True, text=True,
    )
    assert float(probe.stdout.strip()) == pytest.approx(TIMELINE["duration"], abs=0.2)


@needs_ffmpeg
def test_render_leaves_no_temporary_files_behind(panels, audio, tmp_path):
    output = tmp_path / "out.mp4"
    _render(panels, audio, output)
    assert not (tmp_path / "_render_segments").exists()


@needs_ffmpeg
def test_render_rejects_a_script_with_no_bound_panels(panels, audio, tmp_path):
    script = {"blocks": [{"block_id": "b1", "panel_ids": ["panel_9999"], "narration": "gone"}]}
    timeline = {"duration": 1.0, "words": _words("gone")}
    with pytest.raises(ValueError, match="No renderable clips"):
        render(script, timeline, panels, audio, tmp_path / "out.mp4", {"width": 320, "height": 180})


# -- style ------------------------------------------------------------------


def test_style_reads_the_job():
    job = {
        "render": {"width": 1280, "height": 720, "fps": 24,
                   "kenburns": {"enabled": False, "zoom_end": 1.4}},
        "bgm": {"enabled": True, "mode": "fixed", "fixed_file": "track.mp3"},
    }
    style = StyleSettings.from_job(job)

    assert (style.width, style.height, style.fps) == (1280, 720, 24)
    assert style.kenburns_enabled is False
    assert style.bgm_enabled is True
    assert style.bgm_fixed_file == "track.mp3"


def test_style_disabling_kenburns_removes_the_move():
    kwargs = StyleSettings(kenburns_enabled=False, zoom_end=1.2).as_render_kwargs()
    assert kwargs["zoom_end"] == 1.0


def test_style_passes_the_move_through_when_enabled():
    kwargs = StyleSettings(kenburns_enabled=True, zoom_end=1.06).as_render_kwargs()
    assert kwargs["zoom_end"] == 1.06


def test_style_defaults_to_bgm_off():
    assert StyleSettings.from_job({}).bgm_enabled is False


def test_bgm_is_not_picked_when_disabled(tmp_path):
    assert pick_bgm(StyleSettings(bgm_enabled=False), tmp_path) is None


def test_bgm_returns_none_for_an_empty_directory(tmp_path):
    assert pick_bgm(StyleSettings(bgm_enabled=True), tmp_path) is None


def test_bgm_picks_a_track_when_enabled(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"fake")
    (tmp_path / "b.mp3").write_bytes(b"fake")
    chosen = pick_bgm(StyleSettings(bgm_enabled=True, bgm_mode="random"), tmp_path)
    assert chosen is not None and chosen.endswith(".mp3")


def test_bgm_fixed_mode_selects_the_named_track(tmp_path):
    (tmp_path / "a.mp3").write_bytes(b"fake")
    (tmp_path / "wanted.mp3").write_bytes(b"fake")
    chosen = pick_bgm(
        StyleSettings(bgm_enabled=True, bgm_mode="fixed", bgm_fixed_file="wanted.mp3"),
        tmp_path,
    )
    assert chosen.endswith("wanted.mp3")


def test_gpu_composer_creates_valid_still(tmp_path):
    from manga_recap.render.gpu_composer import compose_still

    src = tmp_path / "panel.png"
    Image.new("RGB", (400, 600), (200, 100, 50)).save(src)
    dst = tmp_path / "composed.png"

    res = compose_still(src, dst, width=1920, height=1080, background="blurred")
    assert res.exists()
    with Image.open(res) as im:
        assert im.size == (1920, 1080)


def test_prepare_stills_fast_batches_correctly(tmp_path):
    from manga_recap.render.gpu_composer import prepare_stills_fast

    stills_dir = tmp_path / "stills"
    p1 = tmp_path / "p1.png"
    p2 = tmp_path / "p2.png"
    Image.new("RGB", (300, 500), (50, 150, 250)).save(p1)
    Image.new("RGB", (500, 300), (250, 150, 50)).save(p2)

    clips = [
        Clip("panel_0001", p1, 0.0, 1.0),
        Clip("panel_0002", p2, 1.0, 2.0),
        Clip("panel_0001", p1, 2.0, 3.0),  # Repeat should be deduplicated
    ]

    results = prepare_stills_fast(clips, stills_dir, width=640, height=360, workers=2)
    assert len(results) == 2
    assert (stills_dir / "panel_0001.png").exists()
    assert (stills_dir / "panel_0002.png").exists()


def test_has_cuda_device_probe():
    from manga_recap.render.ffmpeg import has_cuda_device

    # Should return a bool and not raise
    res = has_cuda_device("fake_ffmpeg_bin_that_does_not_exist", 0)
    assert res is False


def test_direct_stream_filtergraph_content(tmp_path):
    from unittest.mock import patch

    from manga_recap.render.direct_stream import StreamShot, _encode_stream_filtergraph

    still1 = tmp_path / "panel_0001.png"
    still2 = tmp_path / "panel_0002.png"
    Image.new("RGB", (640, 360), (10, 20, 30)).save(still1)
    Image.new("RGB", (640, 360), (40, 50, 60)).save(still2)

    shots = [
        StreamShot(panel_id="panel_0001", still_path=still1, frames=30, pan="in", zoom_end=1.0),
        StreamShot(panel_id="panel_0002", still_path=still2, frames=30, pan="left", zoom_end=1.05),
    ]

    script_file = tmp_path / "filter.txt"
    out_file = tmp_path / "out.mp4"

    # Mock has_cuda_device to True to test CUDA filtergraph branch
    with patch("manga_recap.render.direct_stream.has_cuda_device", return_value=True):
        with patch("subprocess.Popen") as mock_popen:
            mock_proc = mock_popen.return_value
            mock_proc.stdout = []
            mock_proc.communicate.return_value = ("", "")
            mock_proc.returncode = 0

            _encode_stream_filtergraph(
                executable="ffmpeg",
                shots=shots,
                fps=30,
                width=640,
                height=360,
                gpu_id=0,
                preset="p1",
                crf=20,
                output_file=out_file,
                script_file=script_file,
            )

            # Check that script file was generated with hwupload_cuda
            content = script_file.read_text(encoding="utf-8")
            assert "format=nv12,hwupload_cuda[outv]" in content
            assert "crop=640:360" in content

            # Check command arguments include -init_hw_device and -pix_fmt cuda
            cmd = mock_popen.call_args[0][0]
            assert "-init_hw_device" in cmd
            assert "cuda=cuda_0:0" in cmd
            assert "-filter_hw_device" in cmd
            assert "cuda_0" in cmd
            assert "-pix_fmt" in cmd
            assert "cuda" in cmd


