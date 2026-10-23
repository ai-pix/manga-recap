"""Per-chapter status: which artifacts exist and what runs next.

Cheap to call and safe to call at any point. It reads the filesystem rather than
trusting the stage status files, so it stays correct even if a run was killed
mid-stage.
"""

from __future__ import annotations

from ...core.config import Config
from ...core.paths import ChapterPaths
from ...core.schema import (
    DescriptionFile,
    PanelIndexFile,
    ScriptFile,
    TimelineFile,
    load_model,
)
from . import STAGE_LABELS, _build_stages, stage_artifact_exists


def status(paths: ChapterPaths, config: Config) -> dict:
    """Report each stage's state plus whatever detail is cheaply available."""
    stages = _build_stages()
    entries = []
    next_stage = None

    for stage in stages:
        done = stage_artifact_exists(stage, paths)
        if not done and next_stage is None:
            # The next stage is the first one still outstanding, which on a
            # fresh chapter is stage 0.
            next_stage = STAGE_LABELS[stage.name]
        entries.append(
            {
                "name": stage.name,
                "label": STAGE_LABELS[stage.name],
                "artifact": stage.produces,
                "description": stage.description,
                "done": done,
            }
        )

    return {
        "chapter_id": paths.chapter_id,
        "root": str(paths.root),
        "stages": entries,
        "next_stage": next_stage,
        "complete": all(e["done"] for e in entries),
        "details": _details(paths, config),
    }


def _details(paths: ChapterPaths, config: Config) -> dict:
    """Pull headline numbers out of the artifacts that exist."""
    details: dict[str, object] = {}

    try:
        index = load_model(paths.panels_dir / "panel_index.json", PanelIndexFile)
        details["pages"] = index.page_count
        details["panels"] = index.panel_count
    except Exception:  # noqa: BLE001 - absent artifacts are normal
        pass

    try:
        descriptions = load_model(paths.descriptions_file, DescriptionFile)
        details["described_panels"] = descriptions.panel_count
        details["vision_model"] = descriptions.model
    except Exception:  # noqa: BLE001
        pass

    try:
        script = load_model(paths.script_file, ScriptFile)
        details["blocks"] = len(script.blocks)
        details["words"] = script.total_words
        details["panels_in_script"] = len(script.referenced_panels())
        details["script_model"] = script.model
    except Exception:  # noqa: BLE001
        pass

    try:
        timeline = load_model(paths.timeline_file, TimelineFile)
        details["narration_seconds"] = round(timeline.duration, 1)
        details["timing_method"] = timeline.blocks[0].method if timeline.blocks else None
        fallback = len(timeline.degraded_blocks())
        if fallback:
            details["fallback_timed_blocks"] = fallback
    except Exception:  # noqa: BLE001
        pass

    if paths.final_file.exists():
        details["video_mb"] = round(paths.final_file.stat().st_size / 1_000_000, 1)

    return details


def render_status(report: dict) -> str:
    """Format a status report for the terminal."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    table = Table(title=f"Chapter {report['chapter_id']}", title_style="bold")
    table.add_column("Stage")
    table.add_column("Artifact")
    table.add_column("State")

    for entry in report["stages"]:
        state = "[green]done[/green]" if entry["done"] else "[dim]pending[/dim]"
        table.add_row(entry["label"], entry["artifact"], state)

    console.print(table)

    details = report.get("details", {})
    if details:
        console.print("  ".join(f"{k}={v}" for k, v in details.items()))

    if report["complete"]:
        console.print("[green]Chapter is complete.[/green]")
    else:
        console.print(f"Next stage: [bold]{report['next_stage']}[/bold]")

    return ""
