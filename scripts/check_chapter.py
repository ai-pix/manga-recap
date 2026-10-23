"""One command that proves a chapter's stage 2-4 artifacts are usable.

Everything the handoff documents asks for by hand, in three places: the describe
schema, the script validator, and the pre-render shot dry-run. This runs all of
them and prints a single verdict, so an agent working on a chapter can check its
own work without pasting four different one-liners.

Usage:
    python scripts/check_chapter.py ch003
    python scripts/check_chapter.py ch003 --stage script
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from manga_recap.core.config import load_config
from manga_recap.core.paths import repo_path
from manga_recap.core.schema import (
    DescriptionFile,
    PanelIndexFile,
    ScriptFile,
    TimelineFile,
    load_model,
)

BANNED_WORDS = [
    "panel",
    "panels",
    "chapter",
    "chapters",
    "page",
    "pages",
    "manga",
    "manhwa",
    "author",
    "artist",
    "drawing",
    "drawn",
    "illustration",
    "reader",
    "readers",
    "viewers",
]
_WORD_RE = re.compile(r"[a-z']+")

# Shun's hair is dark. Light hair is the reliable negative test, and it is the
# one that actually fires: several workers took a *light* spiky-haired boy for
# him because the fringe is the memorable feature, and the fringe is drawn
# differently from panel to panel. Colour does not vary.
#
# A regex, not a phrase list. The phrase "light hair" missed "light spiky hair
# whipped back", which is exactly how the art describes it.
_LIGHT = r"(?:light|fair|pale|blond|blonde|flaxen|silver|golden|ash|grey|gray|white)"
LIGHT_HAIR_RE = re.compile(rf"{_LIGHT}(?:[\w-]{{0,14}}\s){{0,2}}hair|hair[^.;]{{0,14}}{_LIGHT}")
# The fringe genuinely settles identity only when it completely hides the eyes,
# which the art does often but not always. Anything weaker is too noisy to act on.
FRINGE_MARKERS = (
    "covers his eyes",
    "covering his eyes",
    "hair covering",
    "eyes entirely hidden",
    "hair hides",
    "hides the eyes",
)
NOT_SHUN = ("miu", "magi", "onee_chan", "takumi", "shop_clerk", "stall_merchant")


def _entry_text(entry) -> str:
    """Flatten a body-language entry to lowercase text, pydantic model or dict."""
    if isinstance(entry, dict):
        parts = [entry.get("character", ""), entry.get("pose", "")]
        parts.append(entry.get("action", ""))
        parts.append(entry.get("expression_detail", ""))
    else:
        parts = [entry.character, entry.pose, entry.action, entry.expression_detail]
    return " ".join(str(part) for part in parts).lower()


def roster_suspects(descriptions: DescriptionFile) -> list[tuple[str, str]]:
    """Panels whose record contradicts the roster's hard visual discriminators."""
    suspects: list[tuple[str, str]] = []
    for panel in descriptions.panels:
        cast = {str(name).strip().lower() for name in panel.characters}
        panel_text = f"{panel.action} {panel.expression} {' '.join(panel.props)}".lower()
        for entry in panel.body_language:
            name = str(entry.character).strip().lower()
            text = _entry_text(entry)
            if name == "shun" and LIGHT_HAIR_RE.search(text):
                suspects.append((panel.panel_id, "`shun` described with light hair"))
            if name in NOT_SHUN and any(marker in text for marker in FRINGE_MARKERS):
                suspects.append((panel.panel_id, f"`{entry.character}` wears the eyes-out fringe"))
        # Panel prose is only usable when Shun is alone: with a co-star on screen,
        # "her light hair" is a true statement about somebody else. Tightening it
        # this way is what stopped 30-odd false positives on panels where a
        # light-haired sister stands next to him.
        if cast == {"shun"} and LIGHT_HAIR_RE.search(panel_text):
            suspects.append((panel.panel_id, "Shun alone in frame but described light-haired"))
    return suspects



def chapter_dir(chapter_id: str) -> Path:
    return repo_path("data") / "chapters" / chapter_id


def check_describe(root: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    descriptions_path = root / "03_descriptions.json"
    index_path = root / "02_panels" / "panel_index.json"
    if not descriptions_path.exists():
        return False, [f"missing {descriptions_path.name}"]
    if not index_path.exists():
        return False, [f"missing {index_path.name}"]
    try:
        descriptions = load_model(descriptions_path, DescriptionFile)
    except Exception as exc:  # noqa: BLE001 - report, do not raise
        return False, [f"03_descriptions.json failed schema validation: {exc}"]
    try:
        index = load_model(index_path, PanelIndexFile)
    except Exception as exc:  # noqa: BLE001
        return False, [f"panel_index.json failed schema validation: {exc}"]

    if descriptions.panel_count != len(descriptions.panels):
        problems.append(
            f"panel_count {descriptions.panel_count} != len(panels) "
            f"{len(descriptions.panels)}"
        )
    if len(descriptions.panels) != index.panel_count:
        problems.append(
            f"{len(descriptions.panels)} described against {index.panel_count} "
            f"indexed panels"
        )

    known = {p.panel_id for p in index.panels}
    unknown = sorted({p.panel_id for p in descriptions.panels} - known)
    if unknown:
        problems.append(f"{len(unknown)} described panel_id(s) not in the index: {unknown[:8]}")

    orders = [p.reading_order for p in descriptions.panels]
    if orders != sorted(orders):
        problems.append("panels are not in reading order")

    with_text = [p for p in descriptions.panels if p.has_detected_text]
    gaps = [p.panel_id for p in with_text if p.is_untranscribed()]
    ratio = len(gaps) / len(with_text) if with_text else 0.0
    config = load_config()
    limit = float(config.get("describe.max_untranscribed_ratio", 0.1))
    if ratio > limit:
        problems.append(
            f"{len(gaps)} of {len(with_text)} text panels unread ({ratio:.0%} > "
            f"{limit:.0%}): {', '.join(gaps[:10])}"
        )

    print(
        f"describe: {len(descriptions.panels)}/{index.panel_count} panels, "
        f"{len(with_text)} with text, {len(gaps)} unread ({ratio:.1%}), "
        f"model={descriptions.model!r}"
    )
    suspects = roster_suspects(descriptions)
    if suspects:
        seen: set[str] = set()
        for panel_id, reason in suspects:
            if panel_id in seen:
                continue
            seen.add(panel_id)
            print(f"  suspect   {panel_id}: {reason}")
        print(
            f"  suspect   {len(seen)} panel(s) attribute the protagonist's fringe "
            f"to another character. Re-open them before scripting."
        )
    return not problems, problems


def check_script(root: Path) -> tuple[bool, list[str]]:
    from manga_recap.stages.s3_script.validate import validate

    descriptions_path = root / "03_descriptions.json"
    script_path = root / "04_script.json"
    if not script_path.exists():
        return False, [f"missing {script_path.name}"]
    try:
        descriptions = load_model(descriptions_path, DescriptionFile)
        script = load_model(script_path, ScriptFile)
    except Exception as exc:  # noqa: BLE001
        return False, [f"script/descriptions failed schema validation: {exc}"]

    config = load_config()
    report = validate(script, descriptions, config)

    hits: dict[str, list[str]] = {}
    for block in script.blocks:
        for word in _WORD_RE.findall(block.narration.lower()):
            if word in BANNED_WORDS:
                hits.setdefault(word, []).append(block.block_id)
    for word, block_ids in sorted(hits.items()):
        report.add(
            f"Banned word {word!r} in {len(block_ids)} block(s): "
            f"{', '.join(block_ids[:8])}"
        )

    target = int(config.get("script.target_words", 4000))
    words = script.total_words
    if words < 1000 or words > 2000:
        report.warn(f"Narration is {words} words; the recap standard is 1200-1700.")

    print(
        f"script:   {len(script.blocks)} blocks, {words} words "
        f"(target {target}), {len(script.referenced_panels())} panels referenced"
    )
    for warning in report.warnings:
        print(f"  warning  {warning}")
    for problem in report.problems:
        print(f"  ERROR    {problem}")
    return report.ok, list(report.problems)


def check_sync(root: Path) -> tuple[bool, list[str]]:
    from manga_recap.render.sync import coverage_gaps, plan_shots

    script_path = root / "04_script.json"
    timeline_path = root / "06_timeline.json"
    narration_path = root / "05_narration.wav"
    problems: list[str] = []
    if not script_path.exists() or not timeline_path.exists():
        return False, [f"missing {timeline_path.name} (run `manga speak`)"]
    if not narration_path.exists():
        problems.append("missing 05_narration.wav")

    script = load_model(script_path, ScriptFile)
    timeline = load_model(timeline_path, TimelineFile)
    result = plan_shots(
        script.blocks, timeline.words, audio_duration=timeline.duration
    )
    gaps = coverage_gaps(result.shots, timeline.duration)
    degraded = timeline.degraded_blocks()
    anchored = sum(1 for shot in result.shots if getattr(shot, "anchored", True))

    print(
        f"speech:   {timeline.tts_backend} {timeline.duration:.1f}s "
        f"({timeline.duration / 60:.2f} min), {len(timeline.words)} word timings, "
        f"{len(timeline.blocks)} blocks, {len(degraded)} degraded"
    )
    print(
        f"sync:     {len(result.shots)} shots, drift {result.drift:.4f}, "
        f"{len(gaps)} gaps, {len(result.problems)} problems, "
        f"{anchored}/{len(result.shots)} anchored"
    )
    if abs(result.drift) > 0.001:
        problems.append(f"shot drift {result.drift:.4f}s is not zero")
    if gaps:
        problems.append(f"{len(gaps)} coverage gap(s) in the shot plan")
    problems.extend(result.problems)
    for problem in problems:
        print(f"  ERROR    {problem}")
    return not problems, problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter_id")
    parser.add_argument(
        "--stage",
        default="all",
        choices=["all", "describe", "script", "sync"],
        help="Stop after this stage. 'sync' also covers script.",
    )
    args = parser.parse_args()

    root = chapter_dir(args.chapter_id)
    if not root.is_dir():
        print(f"FAIL no such chapter directory: {root}")
        return 1

    print(f"== {args.chapter_id}")
    ok = True
    all_problems: list[str] = []

    describe_ok, describe_problems = check_describe(root)
    all_problems.extend(describe_problems)
    ok = ok and describe_ok
    if args.stage == "describe":
        # Workers are told to look for RESULT OK, so every stage prints it.
        print(f"RESULT {'OK' if ok else 'FAIL'} ({len(all_problems)} problem(s))")
        return 0 if ok else 1

    script_ok, script_problems = check_script(root)
    all_problems.extend(script_problems)
    ok = ok and script_ok
    if args.stage == "script":
        print(f"RESULT {'OK' if ok else 'FAIL'} ({len(all_problems)} problem(s))")
        return 0 if ok else 1

    if args.stage in ("all", "sync"):
        if not script_ok:
            print("sync:    skipped, the script does not validate yet")
        else:
            sync_ok, sync_problems = check_sync(root)
            all_problems.extend(sync_problems)
            ok = ok and sync_ok

    print(f"RESULT {'OK' if ok else 'FAIL'} ({len(all_problems)} problem(s))")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
