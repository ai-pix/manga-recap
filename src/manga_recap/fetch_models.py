"""Fetch the panel detector weights.

The YOLO weights are not committed to the repository, since they are a large
binary that would dominate the history. This downloads them from the model hub
into the path `crop.weights_path` points at, and verifies the file looks like a
YOLO checkpoint rather than an HTML error page.
"""

from __future__ import annotations

from pathlib import Path

from .logging import get_logger, timed
from .paths import repo_path

_log = get_logger("fetch_models")

# Manga109-trained panel and text detector. mAP50 0.957 on the validation set,
# 15MB, and fast enough to run a whole chapter on CPU.
DEFAULT_REPO = "leoxs22/manga-panel-detector-yolo26n"
DEFAULT_FILE = "manga_panel_detector_fp32.pt"


def fetch(
    destination: str | Path = "models/panel_detector.pt",
    *,
    repo_id: str = DEFAULT_REPO,
    filename: str = DEFAULT_FILE,
    force: bool = False,
) -> Path:
    """Download the detector weights unless they are already present."""
    target = repo_path(destination)

    if target.exists() and not force:
        size_mb = target.stat().st_size / 1_000_000
        _log.info("%s is already present (%.1f MB). Use force to re-download.", target, size_mb)
        return target

    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise ImportError(
            "huggingface_hub is required to fetch the model. "
            "Install it with `pip install huggingface_hub`, or download "
            f"{repo_id}/{filename} manually into {target}."
        ) from exc

    with timed("fetch model"):
        _log.info("Downloading %s from %s", filename, repo_id)
        cached = hf_hub_download(repo_id=repo_id, filename=filename)
        _verify(Path(cached))

        import shutil

        shutil.copy2(cached, target)

    size_mb = target.stat().st_size / 1_000_000
    _log.info("Saved %s (%.1f MB)", target, size_mb)
    return target


def _verify(path: Path) -> None:
    """Fail loudly on a download that is not a real checkpoint.

    A failed or rate-limited fetch can return a small HTML or JSON file, and
    ultralytics would fail much later with a confusing error.
    """
    size = path.stat().st_size
    if size < 1_000_000:
        head = path.read_bytes()[:200]
        raise ValueError(
            f"Downloaded file is only {size} bytes, which is too small to be a "
            f"detector checkpoint. It may be an error page: {head[:200]!r}\n"
            "Check the network, or download the weights manually into "
            f"{path}."
        )
