"""Stage 3: write the storyboard script from the panel descriptions.

One LLM call for the whole chapter. The panel descriptions are the model's
source of truth, so this stage is where a manga becomes a story.

Output is `04_script.json`: a list of blocks, each naming the panels it plays
over. That binding is what lets the renderer put the right picture on screen at
the right moment, so it is validated hard before anything downstream runs.
"""

from __future__ import annotations

import time

from ...core.config import Config
from ...core.logging import get_logger, timed, write_stage_status
from ...core.paths import ChapterPaths, repo_path
from ...core.schema import (
    DescriptionFile,
    ScriptBlock,
    ScriptFile,
    load_model,
    save_model,
    validate_or_raise,
)
from ...llm.base import LLMError
from ...llm.registry import build_provider
from .validate import build_repair_prompt as build_repair_prompt
from .validate import validate

_log = get_logger("stages.s3_script")


def run(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> ScriptFile:
    """Write and validate the chapter storyboard."""
    descriptions = load_model(paths.descriptions_file, DescriptionFile)
    if descriptions.panel_count == 0:
        raise ValueError("No panel descriptions found. Run `manga describe` first.")

    if paths.script_file.exists() and not force:
        _log.info("Stage 3: script already exists, skipping (use --force to rewrite)")
        return load_model(paths.script_file, ScriptFile)

    with timed("stage 3 script"):
        payload = _build_payload(paths, descriptions, config)
        prompt = _load_prompt("config/prompts/storyboard.md")

        provider = build_provider(config, "script")
        _log.info(
            "Stage 3: writing script for %d panels, target %d words",
            descriptions.panel_count,
            len(payload["panel_lines"]) and int(config.get("script.target_words", 4000)),
        )

        response = provider.write_script(
            payload,
            prompt,
            max_tokens=int(config.get("llm.script.max_tokens", 16000)),
            temperature=float(config.get("llm.script.temperature", 0.9)),
        )

        script = _to_script(response, paths, descriptions, config)
        report = validate(script, descriptions, config)

        if not report.ok:
            _log.warning("Stage 3: script has problems, attempting one repair pass")
            for line in report.problems:
                _log.warning("  %s", line)
            script = _repair(script, provider, report, paths, descriptions, config)

        if report.warnings:
            for warning in report.warnings:
                _log.warning("  %s", warning)

        save_model(script, paths.script_file)

    _log.info(
        "Stage 3: %d blocks, %d words -> %s",
        len(script.blocks),
        script.total_words,
        paths.script_file,
    )
    write_stage_status(
        paths.chapter_id,
        "s3_script",
        "completed",
        {"block_count": len(script.blocks), "word_count": script.total_words},
    )
    return script


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------


def _build_payload(
    paths: ChapterPaths, descriptions: DescriptionFile, config: Config
) -> dict:
    """Assemble the full context the script writer reads in one call.

    `to_context_line` keeps each panel to one dense line, because the whole
    chapter goes in a single request and per-panel verbosity is multiplied by
    seventy.
    """
    skippable = {str(x).lower() for x in config.get("script.skippable_panel_labels", [])}
    ordered = descriptions.ordered()

    return {
        "series_bible": _load_series_bible(config, paths.chapter_id),
        "chapter_title": descriptions.title or f"Chapter for {paths.chapter_id}",
        "known_characters": _known_characters(ordered),
        "panel_count": len(ordered),
        "panel_lines": [p.to_context_line() for p in ordered],
        "target_words": int(config.get("script.target_words", 4000)),
        "coverage_requirements": _coverage_note(ordered, skippable),
    }


def _load_series_bible(config: Config, chapter_id: str) -> str:
    """Read the series bible if the user has written one.

    This is what lets the narrator "know the story": recurring jokes and
    character names have to come from somewhere.
    """
    series = str(config.get("project.series_name", "default"))
    bible = repo_path("data/series") / series / "series.md"
    if bible.exists():
        _log.info("Stage 3: using series bible at %s", bible)
        return bible.read_text(encoding="utf-8")

    # Fall back to a bible written for this chapter alone.
    local = repo_path("data/series") / series / f"{chapter_id}.md"
    if local.exists():
        return local.read_text(encoding="utf-8")

    _log.info(
        "Stage 3: no series bible found. Create data/series/%s/series.md to give "
        "the narrator character names and running gags.",
        series,
    )
    return ""


def _known_characters(descriptions) -> list[str]:
    """Every character name the vision stage saw, deduplicated and ordered."""
    seen: list[str] = []
    for panel in descriptions:
        for name in panel.characters:
            if name and name not in seen:
                seen.append(name)
    return seen


def _coverage_note(descriptions, skippable: set[str]) -> str:
    must_show = [p.panel_id for p in descriptions if not p.is_skippable(skippable)]
    may_skip = [p.panel_id for p in descriptions if p.is_skippable(skippable)]
    lines = [
        f"Every one of these {len(must_show)} panels must appear in some block:",
        ", ".join(must_show),
    ]
    if may_skip:
        lines.append("")
        lines.append(
            f"These {len(may_skip)} panels are credits, ads or blanks. You may skip "
            "them, and should not waste narration on them: " + ", ".join(may_skip)
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------


def _to_script(
    response: dict,
    paths: ChapterPaths,
    descriptions: DescriptionFile,
    config: Config,
) -> ScriptFile:
    """Turn raw provider output into a validated ScriptFile."""
    blocks_raw = response.get("blocks")
    if not isinstance(blocks_raw, list) or not blocks_raw:
        raise LLMError(
            "Script writer returned no blocks. Expected a 'blocks' list. "
            f"Got keys: {list(response)[:10]}"
        )

    blocks: list[ScriptBlock] = []
    for index, raw in enumerate(blocks_raw, start=1):
        if not isinstance(raw, dict):
            continue
        panel_ids = raw.get("panel_ids")
        if isinstance(panel_ids, str):
            panel_ids = [panel_ids]
        if not isinstance(panel_ids, list):
            panel_ids = []
        narration = str(raw.get("narration", "")).strip()
        if not panel_ids or not narration:
            continue
        blocks.append(
            ScriptBlock(
                block_id=str(raw.get("block_id") or f"b{index:03d}").strip(),
                panel_ids=[str(p).strip() for p in panel_ids if str(p).strip()],
                narration=narration,
                direction=str(raw.get("direction", "")).strip(),
            )
        )

    if not blocks:
        raise LLMError(
            "Script writer returned blocks, but none had both panel_ids and "
            "narration. Check the prompt is producing the expected shape."
        )

    return validate_or_raise(
        ScriptFile,
        {
            "chapter_id": paths.chapter_id,
            "title": str(response.get("title", "")).strip(),
            "series": str(config.get("project.series_name", "default")),
            "created_at": _now(),
            "model": str(config.get("llm.script.model", "")),
            "target_words": int(config.get("script.target_words", 4000)),
            "blocks": [b.model_dump() for b in blocks],
        },
        context="Script from the script writer",
    )


def _repair(
    script: ScriptFile,
    provider,
    report,
    paths: ChapterPaths,
    descriptions: DescriptionFile,
    config: Config,
) -> ScriptFile:
    """One targeted repair pass for a script that failed validation."""
    try:
        response = provider.write_script(
            {
                "series_bible": _load_series_bible(config, paths.chapter_id),
                "chapter_title": script.title or paths.chapter_id,
                "known_characters": _known_characters(descriptions.ordered()),
                "panel_count": descriptions.panel_count,
                "panel_lines": [p.to_context_line() for p in descriptions.ordered()],
                "target_words": script.target_words,
                "coverage_requirements": _coverage_note(
                    descriptions.ordered(),
                    {str(x).lower() for x in config.get("script.skippable_panel_labels", [])},
                ),
            },
            _load_prompt("config/prompts/storyboard.md"),
            max_tokens=int(config.get("llm.script.max_tokens", 16000)),
            temperature=float(config.get("llm.script.temperature", 0.9)),
        )
    except LLMError as exc:
        _log.error("Stage 3: repair call failed, keeping the unvalidated script: %s", exc)
        return script

    repaired = _to_script(response, paths, descriptions, config)
    new_report = validate(repaired, descriptions, config)
    if new_report.ok:
        _log.info("Stage 3: repair pass fixed the script")
        return repaired

    _log.error(
        "Stage 3: repair pass still has problems. Review %s by hand:\n%s",
        paths.script_file,
        new_report.render(),
    )
    return repaired


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_prompt(relative: str) -> str:
    path = repo_path(relative)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file missing: {path}")
    return path.read_text(encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
