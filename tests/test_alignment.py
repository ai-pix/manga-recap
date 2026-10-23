"""Alignment: mapping known narration text onto Whisper word timings."""

from __future__ import annotations

import pytest
from aligner import (
    align_tokens,
    block_boundaries,
    normalise_tokens,
    proportional_boundaries,
)

BLOCKS = [
    "Kidan walks into the room and everyone stops talking.",
    "Norio pretends he was never listening to begin with.",
    "Classic. Every single time this happens.",
]

WORD_DURATION = 0.3


def ground_truth(blocks=BLOCKS, corrupt=None):
    """Per-word timings with a known start and end for every block."""
    heard = []
    clock = 0.0
    for block in blocks:
        for token in block.split():
            clean = token.strip(".,!?").lower()
            heard.append((clean, clock, clock + WORD_DURATION))
            clock += WORD_DURATION
    if corrupt:
        heard = corrupt(heard)
    return heard


def truth_windows(blocks, heard):
    """True start/end per block, given the ground-truth word list."""
    windows = []
    cursor = 0
    for block in blocks:
        count = len(normalise_tokens(block))
        windows.append((heard[cursor][1], heard[cursor + count - 1][2]))
        cursor += count
    return windows


def run_alignment(blocks, heard):
    tokens = [t for b in blocks for t in normalise_tokens(b)]
    timings, ratio = align_tokens(tokens, heard)
    return block_boundaries(blocks, timings), ratio


# -- normalisation ----------------------------------------------------------


def test_normalisation_strips_case_and_punctuation():
    assert normalise_tokens("Hello, World! It's fine.") == ["hello", "world", "it's", "fine"]


def test_normalisation_drops_fillers():
    assert normalise_tokens("So basically, um, he just left") == ["he", "just", "left"]


def test_normalisation_collapses_whitespace():
    assert normalise_tokens("  a   b  ") == ["a", "b"]


# -- alignment --------------------------------------------------------------


def test_clean_transcript_is_exact():
    heard = ground_truth()
    boundaries, ratio = run_alignment(BLOCKS, heard)

    assert ratio == pytest.approx(1.0)
    for got, truth in zip(boundaries, truth_windows(BLOCKS, heard), strict=True):
        assert got[0] == pytest.approx(truth[0], abs=0.01)
        assert got[1] == pytest.approx(truth[1], abs=0.01)


def test_misheard_name_stays_within_tolerance():
    """Whisper renders a character name wrongly; the aligner must absorb it."""

    def corrupt(heard):
        heard = list(heard)
        heard[0] = ("kidding", heard[0][1], heard[0][2])
        return heard

    heard = ground_truth(corrupt=corrupt)
    boundaries, ratio = run_alignment(BLOCKS, heard)

    assert ratio > 0.85
    for got, truth in zip(boundaries, truth_windows(BLOCKS, heard), strict=True):
        assert got[0] == pytest.approx(truth[0], abs=0.6)
        assert got[1] == pytest.approx(truth[1], abs=0.6)


def test_dropped_word_does_not_break_later_blocks():
    def corrupt(heard):
        # Remove one word from the middle block.
        return [w for i, w in enumerate(heard) if i != 8]

    heard = ground_truth(corrupt=corrupt)
    boundaries, ratio = run_alignment(BLOCKS, heard)

    assert ratio > 0.85
    # The first and last blocks still land close to the truth.
    truth = truth_windows(BLOCKS, ground_truth())
    assert boundaries[0][0] == pytest.approx(truth[0][0], abs=0.6)
    assert boundaries[-1][1] == pytest.approx(truth[-1][1], abs=0.6)


def test_added_filler_word_does_not_break_alignment():
    def corrupt(heard):
        heard = list(heard)
        heard.append(("mm", heard[-1][2], heard[-1][2] + 0.1))
        return heard

    heard = ground_truth(corrupt=corrupt)
    boundaries, ratio = run_alignment(BLOCKS, heard)

    assert ratio > 0.85
    truth = truth_windows(BLOCKS, ground_truth())
    assert boundaries[0][0] == pytest.approx(truth[0][0], abs=0.3)


def test_degraded_transcript_reports_a_low_match_ratio():
    garbage = [("the", 0.0, 0.1)] * 3
    tokens = [t for b in BLOCKS for t in normalise_tokens(b)]
    timings, ratio = align_tokens(tokens, garbage)

    assert ratio < 0.5, "a bad transcript must not look trustworthy"
    assert len(timings) == len(tokens), "every script token still needs a slot"


def test_empty_script_tokens():
    timings, ratio = align_tokens([], [("hello", 0.0, 1.0)])
    assert timings == []
    assert ratio == 0.0


def test_no_heard_words_yields_zeroed_timings():
    tokens = ["hello", "world"]
    timings, ratio = align_tokens(tokens, [])
    assert ratio == 0.0
    assert all(t.start == 0.0 and t.end == 0.0 for t in timings)


def test_every_token_gets_a_non_decreasing_time():
    heard = ground_truth()
    tokens = [t for b in BLOCKS for t in normalise_tokens(b)]
    timings, _ = align_tokens(tokens, heard)

    for earlier, later in zip(timings, timings[1:], strict=False):
        assert later.start >= earlier.start - 1e-6
        assert later.end >= earlier.end - 1e-6


# -- boundaries -------------------------------------------------------------


def test_block_boundaries_consume_tokens_in_order():
    heard = ground_truth()
    boundaries, _ = run_alignment(BLOCKS, heard)
    assert len(boundaries) == len(BLOCKS)


def test_boundaries_are_non_overlapping_and_ordered():
    heard = ground_truth()
    boundaries, _ = run_alignment(BLOCKS, heard)

    for earlier, later in zip(boundaries, boundaries[1:], strict=False):
        assert earlier[1] <= later[1] + 1e-6


def test_empty_block_inherits_a_slot():
    boundaries = block_boundaries(["", "", ""], [])
    assert len(boundaries) == 3


# -- fallback ---------------------------------------------------------------


def test_proportional_fallback_tiles_the_timeline_exactly():
    spans = proportional_boundaries(BLOCKS, 9.0)

    assert len(spans) == len(BLOCKS)
    assert spans[0][0] == pytest.approx(0.0)
    assert spans[-1][1] == pytest.approx(9.0)
    for earlier, later in zip(spans, spans[1:], strict=False):
        assert earlier[1] == pytest.approx(later[0])


def test_proportional_fallback_allocates_by_length():
    short = ["Hi."]
    long = ["This block is considerably longer than the other one, by a lot."]
    spans = proportional_boundaries(short + long, 10.0)

    assert spans[0][1] < spans[1][0] + spans[0][1], "the longer block should get more time"
    assert (spans[1][1] - spans[1][0]) > (spans[0][1] - spans[0][0]) * 5


def test_proportional_fallback_handles_zero_weight_blocks():
    spans = proportional_boundaries(["", ""], 4.0)
    assert spans[-1][1] == pytest.approx(4.0)
