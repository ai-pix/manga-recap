"""Stage registry and the resume-aware pipeline runner.

Every stage declares the artifact it produces, so `run` can skip work that is
already done and `--force` knows what to redo. This is what makes the pipeline
cheap to iterate on: you only pay for the stage you actually changed.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from ...core.config import Config
from ...core.logging import get_logger, write_stage_status
from ...core.paths import ChapterPaths

_log = get_logger("pipeline")


@dataclass(frozen=True)
class Stage:
    """One pipeline step: a name, its output artifact, and how to run it."""

    name: str
    produces: str
    description: str
    run: Callable[..., object]


def _build_stages() -> list[Stage]:
    """Import stages lazily so a missing optional dependency in one stage
    (ultralytics, say) does not stop the others from loading."""
    from .. import s0_ingest, s1_crop, s2_describe, s3_script, s4_speech, s5_render

    return [
        Stage(
            name="s0_ingest",
            produces="01_pages/",
            description="Normalise source pages",
            run=lambda paths, config, force: s0_ingest.run(paths, force=force),
        ),
        Stage(
            name="s1_crop",
            produces="02_panels/",
            description="Detect and crop panels",
            run=s1_crop.run,
        ),
        Stage(
            name="s2_describe",
            produces="03_descriptions.json",
            description="Vision model reads every panel",
            run=s2_describe.run,
        ),
        Stage(
            name="s3_script",
            produces="04_script.json",
            description="Write the storyboard script",
            run=s3_script.run,
        ),
        Stage(
            name="s4_speech",
            produces="06_timeline.json",
            description="Narrate and time on Kaggle",
            run=s4_speech.run,
        ),
        Stage(
            name="s5_render",
            produces="07_final.mp4",
            description="Render the video on Kaggle",
            run=s5_render.run,
        ),
    ]


STAGE_NAMES = [
    "s0_ingest",
    "s1_crop",
    "s2_describe",
    "s3_script",
    "s4_speech",
    "s5_render",
]

STAGE_LABELS = {
    "s0_ingest": "ingest",
    "s1_crop": "crop",
    "s2_describe": "describe",
    "s3_script": "script",
    "s4_speech": "speak",
    "s5_render": "render",
}


def stage_artifact_exists(stage: Stage, paths: ChapterPaths) -> bool:
    """Has this stage's output already been produced?"""
    if stage.produces.endswith("/"):
        target = paths.root / stage.produces.rstrip("/")
        return target.exists() and any(target.iterdir())
    return (paths.root / stage.produces).exists()


def run_pipeline(
    paths: ChapterPaths,
    config: Config,
    *,
    from_stage: str | None = None,
    only: str | None = None,
    force: bool = False,
) -> dict[str, str]:
    """Run stages in order, skipping any whose output already exists.

    `from_stage` starts at a named stage and continues to the end, which is how
    you re-run the back half after editing the script. `only` runs a single
    stage, which is how you iterate on one piece in isolation.
    """
    stages = _build_stages()

    if only:
        stages = [s for s in stages if s.name == only or STAGE_LABELS[s.name] == only]
        if not stages:
            raise ValueError(
                f"Unknown stage '{only}'. Available: {', '.join(STAGE_LABELS.values())}"
            )
    elif from_stage:
        names = [s.name for s in stages]
        labels = [STAGE_LABELS[n] for n in names]
        key = from_stage if from_stage in names else None
        index = names.index(key) if key else _label_index(labels, from_stage)
        stages = stages[index:]

    paths.ensure_dirs()
    results: dict[str, str] = {}
    started = time.time()

    _log.info("=" * 62)
    _log.info("Chapter %s", paths.chapter_id)
    _log.info("Working directory: %s", paths.root)
    _log.info("=" * 62)

    for stage in stages:
        label = STAGE_LABELS[stage.name]
        already_done = stage_artifact_exists(stage, paths)

        if already_done and not force:
            _log.info("[%s] %s already exists, skipping", label, stage.produces)
            results[stage.name] = "skipped"
            continue

        if force:
            _log.info("[%s] %s (forced)", label, stage.description)
        else:
            _log.info("[%s] %s", label, stage.description)

        stage_started = time.time()
        try:
            result = _invoke(stage, paths, config, force)
        except Exception as exc:  # noqa: BLE001 - report, then stop the chain
            write_stage_status(
                paths.chapter_id, stage.name, "failed", {"error": str(exc)[:800]}
            )
            _log.error("[%s] failed: %s", label, exc)
            _log.error("Pipeline halted. Fix the cause and re-run; completed stages are skipped.")
            results[stage.name] = "failed"
            raise

        results[stage.name] = "completed"
        _log.info(
            "[%s] done in %.1fs", label, time.time() - stage_started
        )
        del result

    _log.info("=" * 62)
    _log.info("Pipeline finished in %.1fs: %s", time.time() - started, _summary(results))
    _log.info("=" * 62)
    return results


def _invoke(stage: Stage, paths: ChapterPaths, config: Config, force: bool):
    """Call a stage, matching whichever signature it declared.

    Stage 0 predates the config argument and does not need it; everything else
    takes (paths, config, force).
    """
    import inspect

    parameters = inspect.signature(stage.run).parameters
    if "config" in parameters:
        return stage.run(paths, config, force=force)
    return stage.run(paths, force=force)


def _label_index(labels: list[str], wanted: str) -> int:
    if wanted not in labels:
        raise ValueError(
            f"Unknown stage '{wanted}'. Available: {', '.join(labels)}"
        )
    return labels.index(wanted)


def _summary(results: dict[str, str]) -> str:
    completed = sum(1 for v in results.values() if v == "completed")
    skipped = sum(1 for v in results.values() if v == "skipped")
    failed = sum(1 for v in results.values() if v == "failed")
    parts = [f"{completed} completed"]
    if skipped:
        parts.append(f"{skipped} skipped")
    if failed:
        parts.append(f"{failed} failed")
    return ", ".join(parts)
