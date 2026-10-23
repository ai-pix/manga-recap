"""Stage 1: cut a chapter's pages into individual panels.

Runs locally. Reads `01_pages/`, writes `02_panels/` plus a `panel_index.json`
that every later stage depends on.

Two detectors, selected by `crop.detector` in config.yaml:

    yolo     uses crop.weights_path, more accurate on busy pages
    opencv   recursive XY-cut, no weights needed, the default-safe fallback

A hand-authored `02_panels/manual_boxes.json` overrides both, for the page
where automatic detection never works.

Whatever detector runs, its speech-bubble boxes are kept rather than thrown
away. Each panel crop is grown to contain its own bubbles, and a tight
native-resolution crop of those bubbles is written to `02_panels/_text/` for
the transcription pass in stage 2. A bubble that would otherwise be sliced in
half is the failure this stage cannot detect on its own, so it is prevented
structurally and then asserted on.
"""

from __future__ import annotations

from pathlib import Path

from ...core.config import Config
from ...core.logging import get_logger, timed, write_stage_status
from ...core.paths import ChapterPaths, repo_path
from ...core.schema import PanelIndexFile, save_model

_log = get_logger("stages.s1_crop")

INDEX_FILENAME = "panel_index.json"


def run(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> PanelIndexFile:
    """Detect, order and crop every panel in the chapter."""
    page_images = paths.page_images()
    if not page_images:
        raise FileNotFoundError(
            f"No page images in {paths.pages_dir}. Run `manga ingest` first."
        )

    with timed(f"stage 1 crop ({len(page_images)} pages)"):
        index = _crop(paths, config, page_images, force=force)
        index = index.model_copy(update={"chapter_id": paths.chapter_id})
        index_path = paths.panels_dir / INDEX_FILENAME
        save_model(index, index_path)
        _log.info(
            "Stage 1: %d panels across %d pages -> %s",
            index.panel_count,
            index.page_count,
            index_path,
        )

    problems = _validate(index, config)
    write_stage_status(
        paths.chapter_id,
        "s1_crop",
        "completed" if not problems else "completed_with_warnings",
        {"panel_count": index.panel_count, "page_count": index.page_count, "problems": problems},
    )
    for problem in problems:
        _log.warning("Stage 1 check: %s", problem)
    return index


def _crop(
    paths: ChapterPaths, config: Config, page_images: list[Path], *, force: bool
) -> PanelIndexFile:
    from .cropper import crop_chapter
    from .detector import detect

    detector_name = str(config.get("crop.detector", "yolo")).lower()
    weights = repo_path(config.get("crop.weights_path", "models/panel_detector.pt"))
    crop_config = config.section("crop")
    opencv_settings = config.section("opencv_crop")
    yolo_settings = config.section("yolo_crop")

    def detect_page(page_path: Path):
        return detect(
            page_path,
            detector=detector_name,
            weights_path=weights,
            confidence=float(crop_config.get("confidence", 0.45)),
            iou_threshold=float(crop_config.get("iou_threshold", 0.45)),
            min_area_ratio=float(crop_config.get("min_area_ratio", 0.008)),
            opencv_settings=opencv_settings,
            yolo_settings=yolo_settings,
            manual_dir=paths.panels_dir,
            text_class_ids=_parse_text_class_ids(yolo_settings),
            text_min_area_ratio=float(crop_config.get("text_min_area_ratio", 0.0002)),
        )

    index = crop_chapter(
        page_images,
        paths.panels_dir,
        detector=detect_page,
        crop_config=crop_config,
        text_dir=paths.panel_text_dir,
        force=force,
    )

    if crop_config.get("write_debug_sheets", True):
        from .validate import write_contact_sheets

        sheets = write_contact_sheets(index, paths.pages_dir, paths.panel_debug_dir)
        if sheets:
            _log.info(
                "Stage 1: contact sheets in %s - review these to confirm the cuts, "
                "with blue boxes marking speech bubbles and red boxes marking panels",
                paths.panel_debug_dir,
            )

    return index


def _validate(index: PanelIndexFile, config: Config) -> list[str]:
    from .validate import validate

    return validate(
        index,
        min_panels_per_page=int(config.get("crop.min_panels_per_page", 1)),
        min_text_containment=float(config.get("crop.min_text_containment", 0.9)),
        min_page_coverage=float(config.get("crop.min_page_coverage", 0.45)),
        check_text=bool(config.get("crop.check_text_coverage", True)),
    )


def load_index(paths: ChapterPaths) -> PanelIndexFile:
    """Read a previously written panel index."""
    from ...core.schema import load_model

    return load_model(paths.panels_dir / INDEX_FILENAME, PanelIndexFile)


def _parse_text_class_ids(yolo_settings: dict) -> tuple[int, ...] | None:
    """Which detector classes count as speech or text rather than panels.

    Defaults to class 1, the class the bundled panel model uses for text. An
    empty list disables bubble retention entirely, which is correct for a
    single-class detector that reports no text boxes to begin with. `None` is
    *not* usable here: it means "accept every class", and a text box would then
    be promoted to a panel.
    """
    settings = yolo_settings or {}
    if "text_class_ids" not in settings:
        return (1,)
    value = settings.get("text_class_ids")
    if value is None:
        return ()
    if isinstance(value, int):
        return (value,)
    return tuple(int(v) for v in value)
