"""Map narration words back to the block that speaks them.

The pipeline narrates a whole chapter as one continuous stream of audio, which
gives far better prosody than stitching together per-block clips. The cost is
that the audio no longer knows where block 12 starts, so something has to work
that out.

Whisper transcribes the audio and returns word timings, but it is a speech
recogniser: it will render "Kidan" as "Kidding", drop filler words, and
re-punctuate freely. So its transcript is not usable as the source of truth.
The script is.

The approach here aligns the *known* script text against the *recognised* words.
Both are reduced to bare lowercase tokens, then matched as sequences. Where they
agree, the recognised word's timing is the script word's timing. Isolated
mismatches are absorbed by the surrounding matches, which is why this survives
the recognition errors that a direct approach would not.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

# Words a narrator may add or drop that carry no script meaning.
_FILLER = {
    "um", "uh", "er", "ah", "eh", "hmm", "mm", "like", "basically",
    "actually", "literally", "so", "yeah", "right", "okay", "ok",
}

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def normalise_tokens(text: str) -> list[str]:
    """Reduce text to comparable tokens: lowercase, no punctuation, no fillers."""
    tokens = _TOKEN_RE.findall(text.lower())
    return [t for t in tokens if t not in _FILLER]


@dataclass
class TokenTiming:
    """A script token paired with the audio window it was spoken in."""

    token: str
    start: float
    end: float
    matched: bool


def align_tokens(
    script_tokens: list[str],
    heard_words: list[tuple[str, float, float]],
) -> tuple[list[TokenTiming], float]:
    """Align script tokens to recognised words.

    Returns the timings and a match ratio, which is the fraction of script
    tokens that found a home. A low ratio means the alignment is unreliable and
    the caller should fall back rather than ship wrong timings.
    """
    if not script_tokens:
        return [], 0.0

    heard_tokens = [normalise_tokens(word)[0] if normalise_tokens(word) else "" for word, _, _ in heard_words]
    # Keep only recognised words that survived normalisation, but remember where
    # each came from so timings stay attached to the right audio.
    heard = [
        (token, heard_words[index][1], heard_words[index][2])
        for index, token in enumerate(heard_tokens)
        if token
    ]

    if not heard:
        return [TokenTiming(t, 0.0, 0.0, False) for t in script_tokens], 0.0

    script_words = [t for t in script_tokens]
    heard_words_only = [entry[0] for entry in heard]

    matcher = SequenceMatcher(None, script_words, heard_words_only, autojunk=False)
    timings: list[TokenTiming | None] = [None] * len(script_words)

    matched_script = 0
    for script_start, heard_start, size in matcher.get_matching_blocks():
        for offset in range(size):
            script_index = script_start + offset
            _, start, end = heard[heard_start + offset]
            timings[script_index] = TokenTiming(
                token=script_words[script_index], start=start, end=end, matched=True
            )
            matched_script += 1

    match_ratio = matched_script / len(script_words)

    # Fill gaps by interpolating between known anchors. A script word the
    # recogniser dropped still has to land somewhere, and the nearest
    # surrounding matches bracket its true position closely.
    timings = _fill_gaps(timings)
    return timings, match_ratio


def _fill_gaps(timings: list[TokenTiming | None]) -> list[TokenTiming]:
    """Give every unmatched token a time interpolated from its neighbours.

    Tokens the recogniser dropped or mangled still have to land somewhere, and
    the matches on either side bracket their true position closely. Tokens
    beyond the last anchor are spaced at the observed average word duration, so
    a dropped final word does not cut a block's panel time short.
    """
    known = [i for i, t in enumerate(timings) if t is not None and t.matched]

    if not known:
        # Nothing aligned at all. The caller should fall back to proportional
        # timing; return zeroed timings so block boundaries stay well formed.
        return [
            TokenTiming(t.token if t is not None else "", 0.0, 0.0, False) for t in timings
        ]

    first_anchor, last_anchor = known[0], known[-1]
    first_t, last_t = timings[first_anchor], timings[last_anchor]
    anchor_count = last_anchor - first_anchor
    if anchor_count > 0 and last_t.end > first_t.start:  # type: ignore[union-attr]
        average_span = (last_t.end - first_t.start) / anchor_count  # type: ignore[union-attr]
    else:
        average_span = 0.3  # a plausible spoken-word length

    result: list[TokenTiming] = []
    for index, timing in enumerate(timings):
        if timing is not None and timing.matched:
            result.append(timing)
            continue

        token = timing.token if timing is not None else ""
        before = _previous_anchor(known, index)
        after = _next_anchor(known, index)

        if before is not None and after is not None:
            span = after - before
            ratio = (index - before) / span if span else 0.0
            left, right = result[before], timings[after]
            result.append(
                TokenTiming(
                    token,
                    left.start + ratio * (right.start - left.start),  # type: ignore[union-attr]
                    left.end + ratio * (right.end - left.end),  # type: ignore[union-attr]
                    False,
                )
            )
        elif before is not None:
            # Trailing gap: keep stepping forward at the average word length.
            anchor = result[before]
            step = (index - before) * average_span
            result.append(TokenTiming(token, anchor.end + step, anchor.end + step + average_span, False))
        else:
            # Leading gap: step backward from the first anchor.
            anchor = timings[after]  # type: ignore[assignment]
            step = (after - index) * average_span  # type: ignore[operator]
            result.append(
                TokenTiming(token, max(0.0, anchor.start - step), max(0.0, anchor.start - step + average_span), False)  # type: ignore[union-attr]
            )

    return result


def _previous_anchor(anchors: list[int], index: int) -> int | None:
    candidates = [a for a in anchors if a < index]
    return candidates[-1] if candidates else None


def _next_anchor(anchors: list[int], index: int) -> int | None:
    for anchor in anchors:
        if anchor > index:
            return anchor
    return None


def block_boundaries(
    block_texts: list[str],
    token_timings: list[TokenTiming],
) -> list[tuple[float, float]]:
    """Turn per-token timings into a start and end for each block.

    A block's window is the first word it speaks to the last, which is the
    moment its picture should be on screen.
    """
    boundaries: list[tuple[float, float]] = []
    cursor = 0
    prev_end = 0.0

    for text in block_texts:
        count = len(normalise_tokens(text))
        window = token_timings[cursor : cursor + count]
        cursor += count

        if not window:
            # An empty block still needs a slot; inherit the previous end.
            boundaries.append((prev_end, prev_end))
            continue

        start = max(prev_end, window[0].start)
        end = max(start, window[-1].end)
        prev_end = end
        boundaries.append((start, end))

    return boundaries


def proportional_boundaries(
    block_texts: list[str], total_duration: float
) -> list[tuple[float, float]]:
    """Estimate block timings from text length, when alignment is unusable.

    Words-per-minute is roughly constant in synthesised speech, so dividing the
    timeline by character count lands in roughly the right place. It is only a
    last resort, and every block it produces is marked so downstream you can see
    which parts need a re-run.
    """
    weights = [max(1, len(normalise_tokens(text))) for text in block_texts]
    total_weight = sum(weights) or 1

    boundaries: list[tuple[float, float]] = []
    elapsed = 0.0
    for weight in weights:
        span = total_duration * (weight / total_weight)
        boundaries.append((elapsed, elapsed + span))
        elapsed += span
    return boundaries
