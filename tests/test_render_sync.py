"""Beat-level sync: sentence splitting, word anchoring, and shot scheduling.

These are the tests that protect the complaint that started this work: a panel
must be on screen while the words describing it are spoken, and the picture must
never drift away from the audio.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from manga_recap.core.schema import ScriptBlock, ScriptFile, TimelineFile
from manga_recap.render import sync

WORD_DURATION = 0.3


def words_for(*texts, gap: float = 0.0):
    """Word timings laid end to end, the way the aligner emits them."""
    words = []
    clock = 0.0
    for text in texts:
        for token in text.split():
            words.append(
                {"word": token.strip(".,!?").lower(), "start": clock, "end": clock + WORD_DURATION}
            )
            clock += WORD_DURATION
        clock += gap
    return words


def block(block_id: str, narration: str, *panels: str, beats=None) -> dict:
    data = {
        "block_id": block_id,
        "panel_ids": list(panels) or ["panel_0001"],
        "narration": narration,
    }
    if beats:
        data["beats"] = beats
    return data


# -- tokenizing -------------------------------------------------------------


def test_alignment_tokens_match_the_aligner():
    """The tokenizer here indexes into the aligner's word timings.

    It is a deliberate duplicate of the one in `stages/s4_speech/aligner.py`,
    because the render kernel ships `src/` without the stage packages. If the
    two ever disagree, every cut in the video shifts by the number of tokens
    they differ on, silently.
    """
    from manga_recap.stages.s4_speech.aligner import normalise_tokens

    samples = [
        "Our story kicks off with our main character, Shun.",
        "So basically, um, he just left the tutorial zone!",
        "Don't you dare -- not again?!",
        "It's 100% broken, Mr. Shun said Dr. Kim loudly.",
        "Only Sense Online had 400,000 derived senses.",
    ]
    for text in samples:
        assert sync.alignment_tokens(text) == normalise_tokens(text), text
        assert sync.token_count(text) == len(normalise_tokens(text))


# -- sentence splitting -----------------------------------------------------


def test_sentences_split_on_terminators():
    assert sync.split_sentences("He ran. She hid! They waited?") == [
        "He ran.",
        "She hid!",
        "They waited?",
    ]


def test_an_ellipsis_ends_a_sentence():
    """Narration uses "He trailed off... and then he left."

    The continuation is lower case, so the capital lookahead that protects
    "3.5" cannot apply here without missing the beat.
    """
    assert sync.split_sentences("It had ended... mostly.") == ["It had ended...", "mostly."]


def test_an_abbreviation_does_not_end_a_sentence():
    """`Dr.` and `Mr.` are the commonest way a naive splitter breaks a line."""
    assert sync.split_sentences("Dr. Kim arrived. Mr. Shun followed.") == [
        "Dr. Kim arrived.",
        "Mr. Shun followed.",
    ]


def test_a_decimal_does_not_end_a_sentence():
    assert sync.split_sentences("He waited 3.5 seconds. Then he moved.") == [
        "He waited 3.5 seconds.",
        "Then he moved.",
    ]


def test_text_with_no_terminator_comes_back_whole():
    """A wrong cut is worse than no cut: it shows the wrong panel."""
    assert sync.split_sentences("One clause with no punctuation at all") == [
        "One clause with no punctuation at all"
    ]


def test_a_quoted_sentence_stays_joined():
    assert sync.split_sentences('He said "I am done." and left.') == [
        'He said "I am done." and left.'
    ]


def test_empty_text_yields_nothing():
    assert sync.split_sentences("") == []
    assert sync.split_sentences("   ") == []


# -- clause splitting -------------------------------------------------------


def test_a_short_sentence_is_not_split():
    assert sync.split_clauses("He runs away.", 14) == ["He runs away."]


def test_a_long_sentence_splits_at_the_conjunction():
    text = "He grabs her wrist and drags her out the door."
    assert len(sync.split_clauses(text, 5)) > 1


def test_a_long_sentence_splits_at_a_comma():
    text = "He types furiously on the keyboard, then freezes in horror."
    pieces = sync.split_clauses(text, 8)
    assert len(pieces) > 1
    assert all(p.strip() for p in pieces)


def test_clause_splitting_respects_the_word_budget():
    text = "One two three four five six seven eight nine ten eleven twelve."
    for budget in (4, 6, 8):
        for piece in sync.split_clauses(text, budget):
            assert len(piece.split()) <= budget or " " not in piece.strip()


def test_tiny_fragments_are_folded_into_their_neighbour():
    """A two-word piece like "and then" is not a shot of its own."""
    pieces = sync.split_clauses(
        "He stumbles, and then he falls flat on his face in the dirt.", 6
    )
    assert all(len(p.split()) >= 2 for p in pieces)
    # Nothing was dropped in the process.
    joined = " ".join(pieces)
    for word in ("stumbles", "falls", "dirt"):
        assert word in joined


def test_clause_splitting_never_loses_words():
    text = "He grabs her wrist, and drags her out the door, without looking back."
    joined = " ".join(sync.split_clauses(text, 7))
    assert set(joined.split()) == set(text.replace(",", "").split())


# -- beat derivation --------------------------------------------------------


def test_a_single_panel_block_becomes_one_beat():
    beats = sync.derive_beats(ScriptBlock.model_validate(block("b1", "He runs away.", "panel_0001")))
    assert len(beats) == 1
    assert beats[0].panel_id == "panel_0001"


def test_a_multi_panel_block_gets_one_beat_per_panel():
    text = "He grabs her wrist and drags her out the door."
    beats = sync.derive_beats(
        ScriptBlock.model_validate(block("b1", text, "panel_0001", "panel_0002"))
    )
    assert [b.panel_id for b in beats] == ["panel_0001", "panel_0002"]


def test_panels_are_dealt_out_in_reading_order():
    """A later panel must never end up under an earlier sentence."""
    text = "He walks in. He stares. He screams. He runs out."
    beats = sync.derive_beats(
        ScriptBlock.model_validate(
            block("b1", text, "panel_0001", "panel_0002", "panel_0003", "panel_0004")
        )
    )
    assert [b.panel_id for b in beats] == [
        "panel_0001",
        "panel_0002",
        "panel_0003",
        "panel_0004",
    ]


def test_extra_panels_are_never_dropped():
    """The failure this guards: a bound panel silently never reaching the video."""
    text = "He grabs her wrist and drags her out the door."
    beats = sync.derive_beats(
        ScriptBlock.model_validate(block("b1", text, "panel_0001", "panel_0002")),
        max_words=14,
    )
    assert {b.panel_id for b in beats} == {"panel_0001", "panel_0002"}


def test_explicit_beats_take_priority_over_the_splitter():
    parsed = ScriptBlock.model_validate(
        block(
            "b1",
            "He types furiously on the keyboard, then freezes in horror.",
            "panel_0001",
            "panel_0002",
            beats=[
                {"beat_id": "k", "text": "He types furiously on the keyboard", "panel_id": "panel_0002"},
                {"beat_id": "h", "text": "then freezes in horror.", "panel_id": "panel_0001"},
            ],
        )
    )
    beats = sync.derive_beats(parsed)
    assert [b.panel_id for b in beats] == ["panel_0002", "panel_0001"]
    assert all(b.explicit for b in beats)


def test_beat_word_indices_accumulate_across_blocks():
    blocks = [
        ScriptBlock.model_validate(block("b1", "One two three.", "panel_0001")),
        ScriptBlock.model_validate(block("b2", "Four five.", "panel_0002")),
    ]
    beats = sync.beats_for_blocks(blocks)
    assert [b.word_index for b in beats] == [0, 3]
    assert sum(b.word_count for b in beats) == 5


def test_a_block_with_no_panel_yields_a_beat_with_no_panel():
    beats = sync.derive_beats(block("b1", "Nothing here.", "panel_0001", beats=None) | {"panel_ids": []})
    assert beats == [] or all(b.panel_id == "" for b in beats)


# -- anchoring --------------------------------------------------------------


def test_a_beat_is_anchored_to_its_own_words():
    text = "He grabs her wrist and drags her out the door."
    words = words_for(text)
    report = sync.plan_shots(
        [block("b1", text, "panel_0001", "panel_0002")],
        words,
        audio_duration=WORD_DURATION * len(text.split()),
    )

    assert all(s.anchored for s in report.shots)
    # Each shot starts on the first word of its clause, not on a fraction of it.
    assert report.shots[1].start in {w["start"] for w in words}


def test_interpolation_is_reported_rather_than_hidden():
    text = "He grabs her wrist and drags her out the door."
    report = sync.plan_shots(
        [block("b1", text, "panel_0001", "panel_0002")],
        words_for(text)[:3],
        audio_duration=3.0,
    )
    assert any("word timings" in w for w in report.warnings)


def test_no_word_timings_still_produces_a_usable_cover():
    text = "He grabs her wrist and drags her out the door."
    report = sync.plan_shots([block("b1", text, "panel_0001")], [], audio_duration=3.0)
    assert report.problems == []
    assert not any(s.anchored for s in report.shots)
    assert report.drift == pytest.approx(0.0, abs=0.01)


# -- scheduling invariants --------------------------------------------------


def test_shots_tile_the_timeline_exactly():
    texts = ["First beat lands here.", "The second beat lands.", "And the last lands."]
    words = words_for(*texts, gap=0.7)
    clock = words[-1]["end"]
    blocks = [block(f"b{i+1}", t, f"panel_000{i+1}") for i, t in enumerate(texts)]

    report = sync.plan_shots(blocks, words, audio_duration=clock)

    assert report.problems == []
    assert sync.coverage_gaps(report.shots, clock) == []
    assert report.drift == pytest.approx(0.0, abs=0.01)


def test_the_last_shot_reaches_the_end_of_the_narration():
    text = "He runs away into the woods and does not look back."
    words = words_for(text)
    report = sync.plan_shots(
        [block("b1", text, "panel_0001")], words, audio_duration=words[-1]["end"] + 2.0
    )
    assert report.shots[-1].end == pytest.approx(words[-1]["end"] + 2.0)


def test_a_timeline_longer_than_the_script_is_reported():
    text = "He runs."
    words = words_for(text)
    report = sync.plan_shots(
        [block("b1", text, "panel_0001")], words, audio_duration=words[-1]["end"] + 5.0
    )
    assert report.problems == []
    assert report.shots[-1].end == pytest.approx(words[-1]["end"] + 5.0)


def test_a_zero_duration_timeline_is_refused():
    report = sync.plan_shots([block("b1", "He runs.", "panel_0001")], [], audio_duration=0.0)
    assert report.problems
    assert "duration of zero" in report.problems[0]


def test_shots_never_move_backwards_in_time():
    blocks = [block(f"b{i:03d}", f"Beat {i} happens now.", "panel_0001") for i in range(50)]
    words = words_for(*[f"Beat {i} happens now." for i in range(50)], gap=0.3)
    report = sync.plan_shots(blocks, words, audio_duration=words[-1]["end"] + 0.3)

    for earlier, later in zip(report.shots, report.shots[1:], strict=False):
        assert later.start >= earlier.start - 1e-6


def test_a_very_short_shot_is_grown_or_merged():
    """A panel that flashes for 200ms is a glitch, not a cut."""
    words = [
        {"word": "go", "start": 0.0, "end": 0.1},
        {"word": "now", "start": 8.0, "end": 8.4},
        {"word": "wait", "start": 8.4, "end": 8.8},
        {"word": "here", "start": 8.8, "end": 9.2},
    ]
    report = sync.plan_shots(
        [
            block("b1", "Go", "panel_0001"),
            block("b2", "Now wait here", "panel_0002"),
        ],
        words,
        audio_duration=9.2,
        min_shot_seconds=1.0,
    )

    assert all(s.duration >= 1.0 for s in report.shots)
    assert report.drift == pytest.approx(0.0, abs=0.01)
    assert sync.coverage_gaps(report.shots, 9.2) == []


def test_short_shots_on_the_same_panel_settle():
    """Two brief shots of one panel must not fight over the same second.

    Fixing them one after another lets each hand its shortfall back to its
    twin, so neither ever reaches the minimum and the pass limit trips. Working
    on the earliest short shot each time makes the loop converge.
    """
    words = [
        {"word": "a", "start": 0.0, "end": 0.3},
        {"word": "b", "start": 0.3, "end": 0.6},
        {"word": "c", "start": 1.0, "end": 1.4},
        {"word": "d", "start": 1.4, "end": 1.8},
        {"word": "e", "start": 4.0, "end": 5.0},
        {"word": "f", "start": 5.0, "end": 6.0},
        {"word": "g", "start": 6.0, "end": 7.0},
    ]
    blocks = [
        block("b1", "A b c d", "panel_0001", "panel_0001"),
        block("b2", "E f g", "panel_0002"),
    ]
    report = sync.plan_shots(blocks, words, audio_duration=7.0, min_shot_seconds=1.0)

    assert report.problems == [], report.problems
    assert sync.coverage_gaps(report.shots, 7.0) == []
    assert sum(s.duration for s in report.shots) == pytest.approx(7.0, abs=0.01)


def test_the_shot_list_tiles_the_audio_across_every_setting():
    """Swept, because the clause budget and the minimum interact.

    A denser split produces more short shots, and repairing them is exactly
    where an off-by-one turns into coverage drift.
    """
    words = []
    texts = []
    clock = 0.0
    for index in range(40):
        text = f"Beat {index} happens right now and it is quite funny."
        texts.append(text)
        for token in text.split():
            words.append(
                {"word": token.strip(".,!?").lower(), "start": clock, "end": clock + 0.25}
            )
            clock += 0.25
        clock += 0.3
    blocks = [block(f"b{i:03d}", t, "panel_0001") for i, t in enumerate(texts)]

    for budget in (4, 8, 14, 25):
        for minimum in (0.5, 1.0, 2.0):
            report = sync.plan_shots(
                blocks,
                words,
                audio_duration=clock,
                max_words_per_beat=budget,
                min_shot_seconds=minimum,
            )
            assert report.problems == [], (budget, minimum, report.problems)
            assert sync.coverage_gaps(report.shots, clock) == [], (budget, minimum)
            assert sum(s.duration for s in report.shots) == pytest.approx(clock, abs=0.02)


def test_growing_one_shot_never_leaves_a_hole():
    words = [
        {"word": "a", "start": 0.0, "end": 0.05},
        {"word": "b", "start": 0.05, "end": 0.1},
        {"word": "c", "start": 3.0, "end": 3.4},
        {"word": "d", "start": 3.4, "end": 3.8},
        {"word": "e", "start": 3.8, "end": 4.2},
        {"word": "f", "start": 4.2, "end": 4.6},
    ]
    report = sync.plan_shots(
        [block("b1", "A b", "panel_0001"), block("b2", "C d e f", "panel_0002")],
        words,
        audio_duration=4.6,
        min_shot_seconds=1.2,
    )
    assert sync.coverage_gaps(report.shots, 4.6) == []
    assert sum(s.duration for s in report.shots) == pytest.approx(4.6, abs=0.01)


def test_a_beat_with_no_panel_is_reported():
    report = sync.plan_shots(
        [{"block_id": "b1", "panel_ids": ["panel_0001"], "narration": "He runs.", "beats": [
            {"beat_id": "x", "text": "He runs", "panel_id": ""}
        ]}],
        words_for("He runs"),
        audio_duration=0.9,
    )
    assert any("no panel bound" in w for w in report.warnings)


# -- merging ----------------------------------------------------------------


def test_repeated_panels_merge_into_one_shot():
    text = "He grabs her wrist and drags her out the door."
    report = sync.plan_shots(
        [block("b1", text, "panel_0001")], words_for(text), audio_duration=3.0, max_words_per_beat=5
    )
    assert len(report.shots) > 1

    merged = sync.merge_repeats(report.shots)
    assert len(merged) == 1
    assert merged[0].start == pytest.approx(report.shots[0].start)
    assert merged[0].end == pytest.approx(report.shots[-1].end)


def test_different_panels_do_not_merge():
    text = "He grabs her wrist and drags her out the door."
    report = sync.plan_shots(
        [block("b1", text, "panel_0001", "panel_0002")],
        words_for(text),
        audio_duration=3.0,
    )
    assert len(sync.merge_repeats(report.shots)) == len(report.shots)


def test_merging_preserves_coverage():
    texts = ["First beat lands here.", "The second beat lands."]
    words = words_for(*texts, gap=0.7)
    blocks = [block("b1", texts[0], "panel_0001"), block("b2", texts[1], "panel_0001")]
    report = sync.plan_shots(blocks, words, audio_duration=words[-1]["end"] + 0.7)
    merged = sync.merge_repeats(report.shots)

    assert len(merged) == 1
    assert sync.coverage_gaps(merged, report.audio_duration) == []


# -- verification helpers ---------------------------------------------------


def test_coverage_gaps_finds_a_real_hole():
    shots = [sync.Shot("panel_0001", 0.0, 2.0), sync.Shot("panel_0002", 4.0, 6.0)]
    assert sync.coverage_gaps(shots, 6.0) == [(2.0, 4.0)]


def test_coverage_gaps_is_empty_for_a_full_cover():
    shots = [sync.Shot("panel_0001", 0.0, 2.0), sync.Shot("panel_0002", 2.0, 6.0)]
    assert sync.coverage_gaps(shots, 6.0) == []


def test_coverage_gaps_reports_uncovered_tail_audio():
    shots = [sync.Shot("panel_0001", 0.0, 2.0)]
    assert sync.coverage_gaps(shots, 6.0) == [(2.0, 6.0)]


def test_unbound_panels_lists_what_never_reached_the_screen():
    shots = [sync.Shot("panel_0001", 0.0, 1.0)]
    assert sync.unbound_panels([block("b1", "x", "panel_0001", "panel_0004")], shots) == ["panel_0004"]


def test_describe_shots_names_every_shot():
    text = "He grabs her wrist and drags her out the door."
    report = sync.plan_shots(
        [block("b1", text, "panel_0001", "panel_0002")], words_for(text), audio_duration=3.0
    )
    listed = sync.describe_shots(report.shots)
    assert "panel_0001" in listed
    assert len(listed.splitlines()) == len(report.shots)


def test_report_render_lists_problems_and_warnings():
    report = sync.SyncReport(problems=["bad"], warnings=["iffy"])
    assert "ERROR   bad" in report.render()
    assert "warning iffy" in report.render()
    assert not report.ok


# -- the real chapter -------------------------------------------------------


def test_chapter_one_schedules_with_no_drift_and_no_unbound_panels():
    """A regression guard on the actual artifacts, not synthetic fixtures."""
    root = Path(__file__).resolve().parents[1] / "data" / "chapters" / "ch01"
    script_file = root / "04_script.json"
    timeline_file = root / "06_timeline.json"
    if not script_file.exists() or not timeline_file.exists():
        pytest.skip("chapter 01 artifacts are not present")

    script = ScriptFile.model_validate(json.loads(script_file.read_text(encoding="utf-8")))
    timeline = TimelineFile.model_validate(json.loads(timeline_file.read_text(encoding="utf-8")))

    report = sync.plan_shots(script.blocks, timeline.words, audio_duration=timeline.duration)
    shots = sync.merge_repeats(report.shots)

    assert report.problems == [], report.problems
    assert sync.coverage_gaps(shots, timeline.duration) == []
    assert abs(report.drift) < 0.05, f"the video would drift {report.drift:.2f}s from the audio"
    assert not any(w for w in report.warnings if "no word timings" in w), (
        "chapter 01 has word timings; interpolated cuts would be a regression"
    )
    assert sync.unbound_panels(script.blocks, shots) == []


def test_chapter_one_beats_split_further_than_its_blocks():
    """The beat layer has to actually produce more cuts than the block count.

    If it did not, the render would be back to one panel per sentence, which is
    the state this work set out to fix.
    """
    import json
    root = Path(__file__).resolve().parents[1] / "data" / "chapters" / "ch01"
    script_file = root / "04_script.json"
    if not script_file.exists():
        pytest.skip("chapter 01 artifacts are not present")

    script = ScriptFile.model_validate(json.loads(script_file.read_text(encoding="utf-8")))
    beats = sync.beats_for_blocks(script.blocks)
    assert len(beats) > len(script.blocks)
