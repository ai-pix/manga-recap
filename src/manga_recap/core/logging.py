"""Logging: one console logger, one file logger, per-stage timing.

Stage timings matter here because the expensive stages are remote Kaggle runs.
Having the queue time and the compute time broken out is the difference
between "Kaggle is slow" and "Kaggle sat idle for 20 minutes".
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

from .paths import REPO_ROOT

_LOG_FORMAT = "%(message)s"
_configured = False
_console = Console(stderr=True)


def setup_logging(
    level: str = "INFO",
    log_file: str | Path | None = None,
    *,
    force: bool = False,
) -> logging.Logger:
    """Configure the `manga_recap` logger. Idempotent unless `force`."""
    global _configured
    if _configured and not force:
        return logging.getLogger("manga_recap")

    logger = logging.getLogger("manga_recap")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()
    logger.propagate = False

    console_handler = RichHandler(
        console=_console,
        show_time=False,
        show_path=False,
        rich_tracebacks=True,
        markup=False,
    )
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    logger.addHandler(console_handler)

    if log_file:
        path = Path(log_file)
        if not path.is_absolute():
            path = REPO_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
        )
        logger.addHandler(file_handler)

    _configured = True
    return logger


def get_logger(name: str = "") -> logging.Logger:
    """Child logger under the package root, e.g. `manga_recap.stages.s1_crop`."""
    base = logging.getLogger("manga_recap")
    if not base.handlers:
        setup_logging()
    return base.getChild(name) if name else base


@contextmanager
def timed(label: str, logger: logging.Logger | None = None) -> Iterator[dict[str, Any]]:
    """Time a block and log the duration.

    Yields a dict so the caller can attach extra fields to the result, e.g.
    queue_seconds versus compute_seconds on a Kaggle stage.
    """
    log = logger or get_logger()
    record: dict[str, Any] = {}
    started = time.perf_counter()
    log.info("[%s] started", label)
    try:
        yield record
    finally:
        elapsed = time.perf_counter() - started
        record["elapsed_seconds"] = round(elapsed, 2)
        log.info("[%s] finished in %s", label, format_duration(elapsed))


def write_stage_status(
    chapter_id: str,
    stage: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Record per-stage status as JSON so `manga status` can read it back."""
    payload: dict[str, Any] = {
        "chapter_id": chapter_id,
        "stage": stage,
        "status": status,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if extra:
        payload.update(extra)

    directory = REPO_ROOT / "logs" / chapter_id
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stage}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def format_duration(seconds: float) -> str:
    """Human-readable duration, e.g. 3725 -> '1h 2m 5s'."""
    seconds = int(round(seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {sec}s"
