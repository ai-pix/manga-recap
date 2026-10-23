"""Validate a storyboard before it costs money to narrate and render.

This is the last cheap point at which a problem can be fixed. Once a script
reaches TTS, every hour spent is money, so the checks here are strict and the
errors are specific enough to act on.

A validator that only says "invalid" wastes a round trip. Each problem says
which panel ids are involved and what to do about it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ...core.config import Config
from ...core.schema import DescriptionFile, ScriptFile


@dataclass
class ValidationReport:
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def add(self, message: str) -> None:
        self.problems.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def render(self) -> str:
        lines: list[str] = []
        for problem in self.problems:
            lines.append(f"  ERROR   {problem}")
        for warning in self.warnings:
            lines.append(f"  warning {warning}")
        return "\n".join(lines) if lines else "  (no problems)"


def validate(
    script: ScriptFile,
    descriptions: DescriptionFile,
    config: Config,
) -> ValidationReport:
    """Check a script against the panels it must cover."""
    report = ValidationReport()

    known_ids = {p.panel_id for p in descriptions.panels}
    skippable = {
        p.panel_id
        for p in descriptions.panels
        if p.is_skippable(_skippable_labels(config))
    }
    required = known_ids - skippable

    _check_ids(script, known_ids, report)
    _check_coverage(script, required, known_ids, config, report)
    _check_ordering(script, descriptions, report)
    _check_length(script, config, report)
    _check_blocks(script, config, report)
    _check_beat_binding(script, config, report)
    _check_quality(script, report)
    _check_transcription(descriptions, config, report)

    return report


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_ids(script: ScriptFile, known_ids: set[str], report: ValidationReport) -> None:
    unknown: set[str] = set()
    for block in script.blocks:
        for panel_id in block.panel_ids:
            if panel_id not in known_ids:
                unknown.add(panel_id)
    if unknown:
        report.add(
            f"Script references {len(unknown)} panel_id(s) that do not exist: "
            f"{sorted(unknown)[:10]}. The script must only use ids from the panel "
            "list. This is the most common failure and it breaks the render."
        )


def _check_coverage(
    script: ScriptFile,
    required: set[str],
    known_ids: set[str],
    config: Config,
    report: ValidationReport,
) -> None:
    if not config.get("script.require_full_panel_coverage", True):
        return
    missing = required - set(script.referenced_panels())
    if missing:
        sample = sorted(missing)[:10]
        report.add(
            f"{len(missing)} panel(s) are never referenced by the script: {sample}. "
            "Either narrate them or mark them as skippable in "
            "script.skippable_panel_labels."
        )


def _check_ordering(
    script: ScriptFile, descriptions: DescriptionFile, report: ValidationReport
) -> None:
    """Blocks should advance through the panels, not jump backwards.

    A small amount of reordering is normal, since one panel can play under two
    blocks and a late block may revisit an earlier panel. Large jumps usually
    mean the writer lost the thread, which desyncs the video from the narration.

    The tolerance scales with the chapter. A fixed number would be meaningless:
    a jump of eight panels is a big deal in a ten-panel chapter and trivial in a
    two-hundred-panel one.
    """
    order_of = {p.panel_id: p.reading_order for p in descriptions.panels}
    tolerance = max(2, int(0.15 * len(order_of)))

    highest_seen = 0
    large_jumps = 0
    for block in script.blocks:
        positions = [order_of[pid] for pid in block.panel_ids if pid in order_of]
        if not positions:
            continue
        block_high = max(positions)
        if block_high < highest_seen - tolerance:
            large_jumps += 1
        highest_seen = max(highest_seen, block_high)

    if large_jumps > max(3, len(script.blocks) * 0.15):
        report.warn(
            f"{large_jumps} block(s) jump backwards through the panels by more than "
            f"{tolerance} positions. The narration may be out of sync with the art."
        )


def _check_length(script: ScriptFile, config: Config, report: ValidationReport) -> None:
    target = int(config.get("script.target_words", 4000))
    if target <= 0:
        return
    tolerance = float(config.get("script.word_count_tolerance", 0.15))
    actual = script.total_words
    low, high = target * (1 - tolerance), target * (1 + tolerance)

    if actual < low:
        report.warn(
            f"Narration is {actual} words against a target of {target} "
            f"({(target - actual) / target:.0%} short). Raise script.target_words "
            "or ask for more per block."
        )
    elif actual > high:
        report.warn(
            f"Narration is {actual} words against a target of {target} "
            f"({(actual - target) / target:.0%} over). That is roughly "
            f"{actual // 165} minutes of video."
        )


def _check_blocks(script: ScriptFile, config: Config, report: ValidationReport) -> None:
    max_panels = int(config.get("script.max_panels_per_block", 4))
    max_words = int(config.get("script.max_words_per_block", 45))
    for block in script.blocks:
        if len(block.panel_ids) > max_panels:
            report.warn(
                f"{block.block_id} names {len(block.panel_ids)} panels "
                f"({block.panel_ids}). Blocks over {max_panels} panels usually "
                "mean one line is trying to cover too much."
            )
        words = block.word_count
        if words > max_words:
            report.warn(
                f"{block.block_id} is {words} words. Long blocks are hard to time "
                f"and drift out of sync with their panels; aim for 1-2 sentences "
                f"of about {max_words} words or fewer."
            )
        if words < 3:
            report.warn(
                f"{block.block_id} is only {words} words "
                f"({block.panel_ids}). A two-word block flashes past too fast."
            )


def _check_beat_binding(script: ScriptFile, config: Config, report: ValidationReport) -> None:
    """Check that each block's panels can actually be shown in sync.

    The renderer splits a block's narration into clauses and cuts on the spoken
    word. A block naming more panels than its narration can be split into is the
    failure that matters here: the extra panels are silently dropped from the
    video, so a line about three things shows one picture for all of it.
    """
    from ...render.sync import beats_for_blocks

    budget = int(config.get("render.max_words_per_beat", 14))

    for block in script.blocks:
        if not block.panel_ids:
            continue
        try:
            beats = beats_for_blocks([block], max_words=budget)
        except Exception as exc:  # noqa: BLE001 - a validator must not raise
            report.warn(f"{block.block_id} could not be split into beats: {exc}")
            continue

        if not beats:
            report.add(
                f"{block.block_id} has narration but produced no beats to time, so "
                f"its panels ({block.panel_ids}) will never reach the video."
            )
            continue

        bound = {b.panel_id for b in beats if b.panel_id}
        dropped = sorted(set(block.panel_ids) - bound)
        if dropped:
            report.add(
                f"{block.block_id} names {len(block.panel_ids)} panels but its "
                f"narration only splits into {len(beats)} beat(s), so {dropped} "
                f"would never appear on screen. Either split the line into one "
                f"sentence per panel, or declare explicit `beats`."
            )


def _check_quality(script: ScriptFile, report: ValidationReport) -> None:
    """Cheap heuristics for narration that will not survive a listen-through."""
    empty = [b.block_id for b in script.blocks if not b.narration.strip()]
    if empty:
        report.add(f"Blocks with empty narration: {empty}")

    repeated: dict[str, int] = {}
    for block in script.blocks:
        line = block.narration.strip().lower()
        if line:
            repeated[line] = repeated.get(line, 0) + 1
    duplicates = [line for line, count in repeated.items() if count > 2]
    if duplicates:
        report.warn(
            f"{len(duplicates)} narration line(s) repeat more than twice. "
            f"Example: {duplicates[0][:70]!r}"
        )

    ids = [b.block_id for b in script.blocks]
    if len(set(ids)) != len(ids):
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        report.add(f"Duplicate block_id values: {duplicates}")


def _check_transcription(
    descriptions: DescriptionFile, config: Config, report: ValidationReport
) -> None:
    """Refuse to narrate a chapter whose dialogue was never read.

    This is the gate that makes the rest of stage 2 worth building. A panel with
    unreadable text still has a perfectly good action and expression, so nothing
    downstream crashes: the narrator simply describes someone opening their mouth
    and has to guess why, which is how a recap stops being a recap. The failure
    is invisible unless something counts it, so something counts it here.

    The threshold is a share of the panels that actually contain text, not of the
    whole chapter. A chapter can be mostly wordless art and still be fine.
    """
    with_text = [p for p in descriptions.panels if p.has_detected_text]
    if not with_text:
        return

    gaps = [p.panel_id for p in with_text if p.is_untranscribed()]
    if not gaps:
        return

    ratio = len(gaps) / len(with_text)
    limit = float(config.get("describe.max_untranscribed_ratio", 0.1))
    sample = ", ".join(gaps[:10]) + (" ..." if len(gaps) > 10 else "")
    message = (
        f"{len(gaps)} of {len(with_text)} panel(s) contain text that was never "
        f"read ({ratio:.0%}): {sample}"
    )

    if ratio > limit:
        report.add(
            f"{message}. That is over describe.max_untranscribed_ratio "
            f"({limit:.0%}), so the narration would have to invent the dialogue. "
            "Re-run `manga describe --force` to re-transcribe, raise "
            "crop.text_crop_max_edge for sharper crops, or add manual boxes in "
            "02_panels/manual_boxes.json for the affected pages."
        )
    else:
        report.warn(
            f"{message}. Within the describe.max_untranscribed_ratio tolerance "
            f"of {limit:.0%}, so the script can proceed, but these beats will "
            "have no dialogue to work from."
        )


def _skippable_labels(config: Config) -> set[str]:
    return {str(label).lower() for label in config.get("script.skippable_panel_labels", [])}

def build_repair_prompt(script: ScriptFile, report: ValidationReport) -> str:
    """Turn a validation report into a focused correction request.

    Naming the exact problems beats resending the whole brief, because the model
    can fix a list of specific defects without re-deriving the chapter.
    """
    lines = [
        "The storyboard you produced has these problems:",
        "",
        report.render(),
        "",
        "Return the complete corrected storyboard as JSON in the same shape. "
        "Fix only the listed problems; keep the writing that already works.",
    ]
    return "\n".join(lines)
