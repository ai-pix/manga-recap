"""Turn narration into a frame-accurate shot list.

The video is only watchable if the picture on screen matches the sentence being
spoken, and the two drift apart for a mundane reason: audio knows about words,
the renderer knows about panels, and nothing in between says when one clause
should have been replaced by the next.

This module is that missing layer. It works in three steps.

1. **Split.** A block's narration is cut into *beats*, one clause each, and
   each beat is bound to exactly one panel. A sentence describing three actions
   becomes three panels, so the third panel appears while the third action is
   being described rather than six seconds later.

2. **Anchor.** Each beat's start and end are read from the word-level timings
   in `06_timeline.json`, by counting how many spoken words precede it. The
   panel changes on the word that introduces the new clause, which is the only
   cut point a viewer perceives as intentional.

3. **Schedule.** Every shot runs until the *next* shot starts, so the silence
   between two blocks shows the panel that was already up instead of a black
   frame, and the last shot runs to the end of the audio. The shot list
   therefore covers the whole timeline with no holes and no drift, by
   construction rather than by correction.

Everything downstream reads `plan_shots()` and never re-derives timing, which
is why the stages cannot disagree about when a beat plays.

The word tokenizer here is a deliberate duplicate of the one in
`stages/s4_speech/aligner.py`. A render kernel ships `src/` without the stage
packages, so importing the stage's tokenizer would make this module
unimportable on Kaggle. `tests/test_render_sync.py` asserts the two agree
token-for-token, because a divergence here would silently shift every cut.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Tokenizer, matching stages/s4_speech/aligner.py
# ---------------------------------------------------------------------------

_FILLER = {
    "um", "uh", "er", "ah", "eh", "hmm", "mm", "like", "basically",
    "actually", "literally", "so", "yeah", "right", "okay", "ok",
}

_TOKEN_RE = re.compile(r"[a-z0-9']+")


def alignment_tokens(text: str) -> list[str]:
    """Reduce text to the tokens the aligner counts.

    These are the units `06_timeline.json`'s word timings are indexed by, so
    the count of a clause is what locates that clause in the audio.
    """
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _FILLER]


def token_count(text: str) -> int:
    return len(alignment_tokens(text))


# ---------------------------------------------------------------------------
# Text splitting
# ---------------------------------------------------------------------------

# A sentence ends at . ! ? but only when real prose follows. The capital
# lookahead is what stops a decimal or an initial from splitting a sentence in
# half. An ellipsis ends a sentence whatever follows, because narration uses
# "He trailed off... and then he left." where the continuation is lower case.
_SENTENCE_END = re.compile(r"(?<=[.!?…])[\"'”’)\]]*\s+(?=[\"'“‘(]*[A-Z0-9])")
# A run of ellipsis stops a sentence whatever follows it. Split on it only
# after the capital-lookahead pass, so the two rules cannot fight over the same
# text and a decimal is never mistaken for an ellipsis.
_ELLIPSIS_TAIL = re.compile(r"(?:\.{2,}|…+|\?{2,}|!{2,})[\"'”’)\]]*\s+")

# Clause boundaries inside a sentence, each a place where the narration turns
# and therefore where a new panel belongs. Ordered so the strongest break wins:
# a sentence end beats a comma, and "and then" beats a bare "and".
_CLAUSE_BREAKS = (
    _SENTENCE_END,
    _ELLIPSIS_TAIL,
    re.compile(r";\s+"),
    re.compile(r"\s+—\s+"),
    re.compile(r"\s*,\s+(?=(?:and\s+then|but|so|then|before|after|while|when|because|which)\b)", re.I),
    re.compile(r"\s+(?=(?:and\s+then|but|so|then|before|after|while|when|because)\b)", re.I),
    re.compile(r"\s*,\s+"),
    re.compile(r"\s+(?=(?:and|or)\b)", re.I),
    # Last resort. A run-on with no punctuation at all still has to be cut
    # somewhere, and a cut in the wrong place is better than one panel held for
    # a paragraph.
    re.compile(r"\s+"),
)

_WORDISH = re.compile(r"[^\W_]+", re.UNICODE)

# Abbreviations whose trailing period is not a sentence end. Matched
# case-insensitively so "Dr." and "dr." both survive.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "mt", "vs", "etc",
    "inc", "ltd", "co", "no", "vol", "ch", "pp", "approx", "dept", "est",
}

# A fragment shorter than this cannot hold a panel of its own, so it is folded
# into the clause it introduces.
_MIN_CLAUSE_WORDS = 3

# Upper bound on passes when growing shots to the minimum length. Each pass
# fixes at least one shot, so this only trips on a pathological timeline, and
# tripping it reports a problem rather than looping forever.
_MINIMUM_PASSES = 512


def split_sentences(text: str) -> list[str]:
    """Split narration into sentences, keeping terminal punctuation.

    Deliberately conservative: text with no terminal punctuation comes back
    whole rather than being guessed apart. A wrong cut is worse than no cut,
    because a wrong cut shows the wrong panel for the span of a real clause.
    """
    guarded = _protect_abbreviations(text.strip())
    if not guarded:
        return []

    # Sentence ends first, using a lookahead so the terminator stays with the
    # sentence it closes. Then ellipsis tails, which end a sentence whatever
    # case follows: `He trailed off... and then he left.` would otherwise be
    # missed, because the capital lookahead has to reject "3.5".
    parts: list[str] = []
    for chunk in _SENTENCE_END.split(guarded):
        if chunk.strip():
            parts.extend(_split_keeping_delimiter(chunk, _ELLIPSIS_TAIL))
    return [_restore_abbreviations(p.strip()) for p in parts if p.strip()]


def _split_keeping_delimiter(text: str, pattern: re.Pattern[str]) -> list[str]:
    """Split on `pattern`, keeping what it matched at the end of each piece.

    A bare `re.split` throws the matched text away, which would strip the very
    punctuation marking the end of the sentence it just closed.
    """
    pieces: list[str] = []
    cursor = 0
    for match in pattern.finditer(text):
        head = text[cursor : match.start()].rstrip()
        if head:
            pieces.append(head + match.group(0).rstrip())
        cursor = match.end()
    tail = text[cursor:]
    if tail.strip():
        pieces.append(tail)
    return pieces


def split_clauses(text: str, max_words: int) -> list[str]:
    """Cut one sentence into clauses of at most `max_words` words.

    Boundaries are where the thought turns: sentence ends, semicolons, dashes,
    and the conjunctions that introduce a new action.
    """
    text = text.strip()
    if not text:
        return []
    if _count_words(text) <= max_words:
        return [text]

    pieces = [text]
    for pattern in _CLAUSE_BREAKS[:-1]:
        expanded: list[str] = []
        for piece in pieces:
            if _count_words(piece) <= max_words:
                expanded.append(piece)
                continue
            expanded.extend(p.strip() for p in pattern.split(piece) if p.strip())
        if len(expanded) <= len(pieces):
            continue
        pieces = _merge_runts(expanded)
        if all(_count_words(p) <= max_words for p in pieces):
            return pieces

    # Some pieces are still over budget: punctuation ran out partway through.
    # Pack only those, so the clause boundaries already found survive. Packing
    # the whole text instead would throw them away and land every cut on a
    # fixed word count rather than on where the sentence actually turns.
    final: list[str] = []
    for piece in pieces:
        if _count_words(piece) <= max_words:
            final.append(piece)
            continue
        final.extend(_pack(piece.split(), max_words))
    return final


def _pack(words: list[str], max_words: int) -> list[str]:
    """Group words into pieces of at most `max_words`, losing none of them."""
    packed: list[str] = []
    for start in range(0, len(words), max_words):
        packed.append(" ".join(words[start : start + max_words]))
    return packed


def read_field(obj, name: str, default=None):
    """Read a field from a schema model or a plain dict.

    The render kernel reads `script.json` straight off disk, so the shot
    planner is handed dicts in production and `ScriptBlock` objects in tests.
    Both shapes reach it, and neither is worth converting.
    """
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _protect_abbreviations(text: str) -> str:
    """Hide an abbreviation's period from the sentence splitter.

    The period is swapped for U+2060 WORD JOINER, which matches no word
    character and so cannot terminate a sentence, then restored afterwards. A
    negative lookbehind over a name list would be both slower and unable to
    handle a title-cased "Dr.".
    """

    def swap(match: re.Match[str]) -> str:
        word = match.group(1)
        if word.lower() in _ABBREVIATIONS:
            return f"{word}\u2060"
        return match.group(0)

    return re.sub(r"\b([A-Za-z][A-Za-z]{0,4})\.", swap, text)


def _restore_abbreviations(text: str) -> str:
    return text.replace("\u2060", ".")


def _merge_runts(pieces: list[str]) -> list[str]:
    """Fold fragments too short to hold a panel into their neighbour."""
    merged: list[str] = []
    for piece in pieces:
        if merged and _count_words(piece) < _MIN_CLAUSE_WORDS:
            merged[-1] = f"{merged[-1]} {piece}".strip()
            continue
        merged.append(piece)
    # If the first piece is a runt and there is a subsequent piece, fold it forward
    if len(merged) > 1 and _count_words(merged[0]) < _MIN_CLAUSE_WORDS:
        merged[1] = f"{merged[0]} {merged[1]}".strip()
        merged.pop(0)
    return merged



def _count_words(text: str) -> int:
    return len(_WORDISH.findall(text))


# ---------------------------------------------------------------------------
# Beats: clauses bound to panels
# ---------------------------------------------------------------------------


@dataclass
class Beat:
    """One clause of narration and the single panel that shows it."""

    beat_id: str
    block_id: str
    text: str
    panel_id: str
    # Index of this beat's first word within the whole script's token stream.
    word_index: int = 0
    word_count: int = 0
    # True when a writer bound this clause to this panel by hand rather than
    # letting the splitter guess.
    explicit: bool = False


def derive_beats(block, *, max_words: int = 14) -> list[Beat]:
    """Split one block's narration into clause-sized beats.

    An explicit `beats` list on the block wins outright: a writer who bound "the
    part about the keyboard" to the keyboard panel knows something a regex
    cannot see. Otherwise the narration is cut on clause boundaries and the
    block's panels are dealt out across the clauses in reading order, which is
    the only assignment that cannot put a later panel under an earlier sentence.
    """
    block_id = str(read_field(block, "block_id", ""))
    declared = [
        b for b in (read_field(block, "beats") or []) if str(read_field(b, "text", "")).strip()
    ]
    if declared:
        # Beats with no panel are kept rather than filtered out. Dropping one
        # here would hide a writer's mistake behind a plausible-looking cut,
        # and the report is where that mistake belongs.
        explicit = declared
    else:
        explicit = []
    if explicit:
        return [
            Beat(
                beat_id=str(read_field(b, "beat_id", "")),
                block_id=block_id,
                text=str(read_field(b, "text")).strip(),
                panel_id=str(read_field(b, "panel_id")),
                explicit=True,
            )
            for b in explicit
        ]

    narration = str(read_field(block, "narration", "") or "")
    panels = [str(p) for p in (read_field(block, "panel_ids") or [])]

    segments = _segment(narration, max_words, needed=len(panels))
    return [
        Beat(
            beat_id=f"{block_id}_b{index:02d}",
            block_id=block_id,
            text=text,
            panel_id=_deal_panels(index, len(segments), panels),
        )
        for index, text in enumerate(segments)
    ]


def _segment(narration: str, max_words: int, *, needed: int) -> list[str]:
    """Split a block's narration, splitting further if panels are left over.

    A writer who bound two panels to one sentence is asking for a cut in the
    middle of it, and that request outranks the length heuristic: honouring
    `max_words` instead would silently drop the second panel from the video
    entirely, which is the exact failure the beat system exists to prevent. So
    the clause budget is halved and retried until there are at least as many
    clauses as panels.
    """
    segments: list[str] = []
    for sentence in split_sentences(narration):
        segments.extend(split_clauses(sentence, max_words))
    if not segments:
        segments = [narration.strip()]

    budget = max_words
    while needed > 1 and len(segments) < needed and budget > _MIN_CLAUSE_WORDS:
        budget = max(_MIN_CLAUSE_WORDS, budget // 2)
        retry: list[str] = []
        for sentence in split_sentences(narration):
            retry.extend(split_clauses(sentence, budget))
        if len(retry) <= len(segments):
            break
        segments = retry

    return segments


def _deal_panels(index: int, total: int, panels: list[str]) -> str:
    """Hand panel `i` of `n` to the clause covering that stretch of the block.

    With at least as many panels as clauses, each clause takes the panel at its
    own proportional position, so the sequence advances through the art in
    order. With fewer panels than clauses the panels repeat, because holding one
    panel across two related clauses reads better than freezing on the last
    panel for the second.
    """
    if not panels:
        return ""
    if len(panels) >= total:
        return panels[min(index * len(panels) // total, len(panels) - 1)]
    return panels[min(index, len(panels) - 1)]


def beats_for_blocks(blocks, *, max_words: int = 14) -> list[Beat]:
    """Every beat in the chapter, in narration order, with word indices filled.

    Indices are cumulative across blocks and count tokens the way the aligner
    did, which is what lets a beat be located in the timeline by arithmetic
    rather than by searching the audio for its text.
    """
    beats: list[Beat] = []
    cursor = 0
    for block in blocks:
        for beat in derive_beats(block, max_words=max_words):
            beat.word_index = cursor
            beat.word_count = token_count(beat.text)
            cursor += beat.word_count
            beats.append(beat)
    return beats


# ---------------------------------------------------------------------------
# Shot list
# ---------------------------------------------------------------------------


@dataclass
class Shot:
    """One panel on screen for a span of the timeline."""

    panel_id: str
    start: float
    end: float
    beat_id: str = ""
    block_id: str = ""
    text: str = ""
    # True when the boundary came from word timings rather than interpolation.
    anchored: bool = True

    def __post_init__(self) -> None:
        if self.end < self.start:
            self.end = self.start

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


# Beyond this many warnings of one kind, the scheduler records a count instead
# of more lines. A dense chapter can produce hundreds of brief-shot notes, and
# a log nobody can read is how a real problem gets missed inside the noise.
_MAX_SAME_WARNING = 8


@dataclass
class SyncReport:
    """The shot list plus everything the scheduler could not do cleanly."""

    shots: list[Shot] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    audio_duration: float = 0.0
    # How many warnings of each kind were suppressed, keyed by the leading word.
    suppressed: dict[str, int] = field(default_factory=dict)

    def warn(self, message: str) -> None:
        """Record a warning, collapsing repeats of the same kind past a limit.

        A dense chapter produces one brief-shot warning per beat, which is
        hundreds of lines describing one condition. Collapsing them keeps the
        first few, where the detail is useful, and counts the rest.
        """
        kind = message.split()[0] if message.split() else message
        seen = sum(1 for w in self.warnings if w.split()[:1] == [kind])
        if seen >= _MAX_SAME_WARNING:
            self.suppressed[kind] = self.suppressed.get(kind, 0) + 1
            return
        self.warnings.append(message)

    def warning_summary(self) -> str:
        """One line per suppressed warning kind, for the log."""
        return " ".join(
            f"({count} more like '{kind} ...')" for kind, count in sorted(self.suppressed.items())
        )

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def covered_duration(self) -> float:
        return sum(s.duration for s in self.shots)

    @property
    def drift(self) -> float:
        """Seconds of audio the shot list fails to cover. Should be ~0."""
        return self.audio_duration - self.covered_duration

    def render(self) -> str:
        lines = [f"  {s.beat_id or '-':<12} {s.panel_id:<14} {s.start:7.2f} -> {s.end:7.2f}"
                 for s in self.shots]
        lines += [f"  ERROR   {p}" for p in self.problems]
        lines += [f"  warning {w}" for w in self.warnings]
        return "\n".join(lines) if lines else "  (nothing to schedule)"


def plan_shots(
    blocks,
    words,
    *,
    audio_duration: float,
    max_words_per_beat: int = 14,
    min_shot_seconds: float = 0.7,
) -> SyncReport:
    """Build the shot list for a chapter.

    `words` is the timeline's word-level timing list, in the same order as the
    script's token stream. When it is missing or the wrong length, beats are
    spread inside each block proportionally and the report says so, because an
    interpolated cut is a guess and a guess has to be visible.
    """
    report = SyncReport(audio_duration=audio_duration)
    beats = beats_for_blocks(blocks, max_words=max_words_per_beat)
    if not beats:
        report.problems.append("No beats could be derived from the script.")
        return report

    needed = sum(b.word_count for b in beats)
    word_timings = list(words or [])
    exact = bool(word_timings) and len(word_timings) == needed
    if word_timings and not exact:
        report.warn(
            f"The timeline holds {len(word_timings)} word timings but the script "
            f"needs {needed}. Cuts were interpolated inside each block instead of "
            "read off the audio, so a panel may change a moment early or late."
        )
    elif not word_timings:
        report.warn(
            "The timeline has no word timings, so cuts were interpolated inside "
            "each block by word count. Re-run `manga speak` for exact cuts."
        )

    if audio_duration <= 0:
        # No audio means no time to schedule against. Producing zero-length
        # shots here would let a broken timeline render a video of the wrong
        # length rather than fail here.
        report.problems.append(
            "The timeline reports a duration of zero, so there is nothing to "
            "schedule against. Re-run `manga speak`."
        )
        return report

    shots: list[Shot] = []
    for index, beat in enumerate(beats):
        if not beat.panel_id:
            report.warn(
                f"{beat.beat_id} has no panel bound to it, so those words play "
                "over whatever is already on screen."
            )
            continue

        window = _beat_window(index, beats, word_timings, exact, audio_duration)
        start, end, anchored = window
        shots.append(
            Shot(
                panel_id=beat.panel_id,
                start=start,
                end=end,
                beat_id=beat.beat_id,
                block_id=beat.block_id,
                text=beat.text,
                anchored=anchored,
            )
        )

    _schedule(shots, audio_duration=audio_duration, min_shot_seconds=min_shot_seconds, report=report)
    report.shots = shots
    return report


def _beat_window(
    index: int,
    beats: list[Beat],
    words: list,
    exact: bool,
    audio_duration: float,
) -> tuple[float, float, bool]:
    """Where one beat sits in the audio, preferring the word timings."""
    beat = beats[index]
    if exact:
        first = words[beat.word_index]
        last = words[beat.word_index + beat.word_count - 1]
        start = float(read_field(first, "start", 0.0) or 0.0)
        end = float(read_field(last, "end", 0.0) or 0.0)
        if end > start:
            return start, end, True

    # Fallback: this beat's share of the whole narration, by word count. Coarse
    # but continuous, which matters more than being right to the word.
    needed = sum(b.word_count for b in beats) or 1
    start = audio_duration * beat.word_index / needed
    end = audio_duration * (beat.word_index + beat.word_count) / needed
    return start, max(start, end), False


def _schedule(
    shots: list[Shot],
    *,
    audio_duration: float,
    min_shot_seconds: float,
    report: SyncReport,
) -> None:
    """Make the shot list tile the timeline with no holes.

    Two invariants, enforced here rather than assumed:

    - **Coverage.** Every shot ends where the next begins, the first starts at
      zero, and the last ends at the audio's end. Silence between blocks is
      therefore covered by the panel that was already up, and the shots sum to
      exactly the audio length. A shot list that falls short is the mechanism
      behind a video that ends before the narration does.
    - **Monotonicity.** Starts never move backwards, so no panel is shown
      before the sentence that describes it.
    """
    if not shots:
        report.problems.append(
            "No renderable shots: no block in the script bound a panel to its narration."
        )
        return

    if shots[0].start > 0.0:
        report.warn(
            f"The first panel starts at {shots[0].start:.2f}s; leading silence is "
            "covered by holding it."
        )
        shots[0].start = 0.0

    # Extend each shot to the next one's start. This absorbs the gap between
    # blocks into the panel that was already on screen, which is both what the
    # viewer expects and what keeps the total equal to the audio length.
    for current, following in zip(shots, shots[1:], strict=False):
        current.end = max(current.start, following.start)

    if audio_duration > 0:
        if shots[-1].end > audio_duration + 0.5:
            report.problems.append(
                f"The last panel ends at {shots[-1].end:.2f}s but the audio is only "
                f"{audio_duration:.2f}s. The timeline and the script disagree."
            )
        shots[-1].end = max(shots[-1].start, audio_duration)

    _enforce_minimum(shots, min_shot_seconds, audio_duration, report)

    for shot in shots:
        if shot.end < shot.start:
            report.problems.append(f"{shot.beat_id} ends before it starts.")


def _enforce_minimum(
    shots: list[Shot],
    minimum: float,
    audio_duration: float,
    report: SyncReport,
) -> None:
    """Grow shots too brief to read, taking time only from later shots.

    A panel that flashes for 200ms is a glitch, not a cut. The time comes from
    the *following* shot, so the fix can never move a boundary earlier than the
    word it is anchored to. With nothing left to take, the shot is merged
    forward instead, which is the honest outcome: two beats were one beat.

    Every adjustment moves a boundary later and never earlier, so repeating
    until nothing is too short terminates: the shot list is finite and each pass
    fixes at least one shot. Adjusting each shot exactly once does not work,
    because taking time from a neighbour can leave that neighbour too short.
    """
    for _ in range(_MINIMUM_PASSES):
        index = _first_short_shot(shots, minimum)
        if index is None:
            return

        shot = shots[index]
        following = shots[index + 1] if index + 1 < len(shots) else None
        if following is None:
            # Nothing follows, so there is nothing to borrow from. The shot runs
            # to the end of the audio, which is what it already does; the only
            # honest thing to report is that it stays brief.
            report.warn(
                f"{shot.beat_id} is only {shot.duration:.2f}s and is the final shot, "
                "so there is no later time to borrow."
            )
            return

        if following.duration - minimum >= deficit_of(shot, minimum):
            # Borrow by moving the following start later. Extending this shot's
            # end alone would overlap the two and make the list cover more audio
            # than exists.
            shot.end += deficit_of(shot, minimum)
            following.start = shot.end
            continue

        # Nothing to spare: the two beats were one beat.
        shot.end = following.end
        following.start = shot.end
        del shots[index + 1]
        report.warn(
            f"{shot.beat_id} was {shot.duration:.2f}s, too brief to read; "
            "merged forward into a single shot."
        )

    report.problems.append(
        f"Could not make every shot at least {minimum:.2f}s long after "
        f"{_MINIMUM_PASSES} passes. The narration may be too dense for the "
        "requested minimum shot length; lower render.min_shot_seconds."
    )


def deficit_of(shot: Shot, minimum: float) -> float:
    return max(0.0, minimum - shot.duration)


def _first_short_shot(shots: list[Shot], minimum: float) -> int | None:
    """Index of the earliest shot below the minimum, or None.

    Always the *earliest* one. Working on the latest instead can leave two
    shots of the same panel fighting over the same second of audio: the later
    one hands time back to the earlier one, which falls below the minimum again.
    """
    for index, shot in enumerate(shots):
        if shot.duration < minimum - 1e-9:
            return index
    return None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def coverage_gaps(shots: list[Shot], audio_duration: float) -> list[tuple[float, float]]:
    """Intervals of the timeline no shot covers. Should be empty.

    Returned rather than asserted so a caller can print the actual hole against
    the actual audio instead of trusting a boolean.
    """
    gaps: list[tuple[float, float]] = []
    cursor = 0.0
    for shot in shots:
        if shot.start > cursor + 1e-3:
            gaps.append((cursor, shot.start))
        cursor = max(cursor, shot.end)
    if audio_duration > cursor + 1e-3:
        gaps.append((cursor, audio_duration))
    return gaps


def unbound_panels(blocks, shots: list[Shot]) -> list[str]:
    """Panels the script named that never reached the screen."""
    shown = {s.panel_id for s in shots}
    named = {str(pid) for block in blocks for pid in (read_field(block, "panel_ids") or [])}
    return sorted(named - shown)


def merge_repeats(shots: list[Shot]) -> list[Shot]:
    """Join consecutive shots that show the same panel.

    Two clauses bound to one panel are visually one shot, so cutting between
    them buys nothing and costs a segment to encode. Merging also stops the
    Ken Burns move from restarting mid-panel, which is a visible jump rather
    than a cut. Word-level sync is untouched: the merged shot still begins on
    the first word of the first clause.

    The input is not mutated. The report returned by `plan_shots` holds the same
    Shot objects, and widening them here would silently change the coverage the
    report claims.
    """
    merged: list[Shot] = []
    for shot in shots:
        if merged and merged[-1].panel_id == shot.panel_id and merged[-1].end >= shot.start:
            previous = merged[-1]
            merged[-1] = Shot(
                panel_id=previous.panel_id,
                start=previous.start,
                end=max(previous.end, shot.end),
                beat_id=previous.beat_id,
                block_id=previous.block_id,
                text=f"{previous.text} {shot.text}".strip(),
                anchored=previous.anchored and shot.anchored,
            )
            continue
        merged.append(
            Shot(
                panel_id=shot.panel_id,
                start=shot.start,
                end=shot.end,
                beat_id=shot.beat_id,
                block_id=shot.block_id,
                text=shot.text,
                anchored=shot.anchored,
            )
        )
    return merged


def describe_shots(shots: list[Shot]) -> str:
    """A human-readable shot list, for logs and for eyeballing a sync report."""
    if not shots:
        return "(no shots)"
    return "\n".join(
        f"{index:>4}  {s.start:8.2f} -> {s.end:8.2f}  {s.duration:6.2f}s  "
        f"{s.panel_id:<14} {'anchored' if s.anchored else 'interpolated':<12} {s.text[:60]}"
        for index, s in enumerate(shots)
    )
