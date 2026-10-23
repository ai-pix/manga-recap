"""Command line entry point.

    manga run      ch01              run every stage, skipping completed ones
    manga run      ch01 --force      redo everything
    manga run      ch01 --from script   redo the script and everything after
    manga status   ch01              what is done and what is next
    manga ingest   ch01 --input D:/pages
    manga crop     ch01 --detector opencv
    manga crop-batch ch003 ch004 --source-root D:/pages   many chapters, one GPU run
    manga speak    ch01              Kaggle TTS only
    manga render   ch01              Kaggle render only

Every command takes a chapter id, which is a folder under data/chapters/, except
`crop-batch`, which takes many.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core.config import ConfigError, load_config
from .core.logging import get_logger, setup_logging
from .core.paths import ChapterPaths
from .stages.s1_crop.kaggle_batch import DEFAULT_BATCH_SIZE

_log = get_logger("cli")

# Commands that are not pipeline stages.
EXTRA_COMMANDS = ("status", "crop-batch")


def build_parser() -> argparse.ArgumentParser:
    # Global options are declared twice: once on the root parser with real
    # defaults, and once on every subcommand with SUPPRESS defaults. That way
    # `manga --data-dir X run ch01` and `manga run ch01 --data-dir X` both work,
    # and an option given before the subcommand is not clobbered by the
    # subparser's default.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=argparse.SUPPRESS, help="path to config.yaml")
    common.add_argument(
        "--log-level", default=argparse.SUPPRESS, help="DEBUG, INFO, WARNING, ERROR"
    )
    common.add_argument(
        "--data-dir", default=argparse.SUPPRESS, help="override the chapter data directory"
    )

    parser = argparse.ArgumentParser(
        prog="manga",
        description="Turn manga chapter pages into a narrated recap video.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--config", help="path to config.yaml (default: config/config.yaml)")
    parser.add_argument("--log-level", default=None, help="DEBUG, INFO, WARNING, ERROR")
    parser.add_argument("--data-dir", help="override the chapter data directory")

    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="run the pipeline", parents=[common])
    run_cmd.add_argument("chapter")
    run_cmd.add_argument("--force", action="store_true", help="redo every stage")
    run_cmd.add_argument("--from", dest="from_stage", help="start at this stage and continue")
    run_cmd.add_argument("--only", help="run a single stage")

    status_cmd = sub.add_parser("status", help="show progress for a chapter", parents=[common])
    status_cmd.add_argument("chapter")

    for name in ("ingest", "crop", "describe", "script", "speak", "render"):
        stage_cmd = sub.add_parser(name, help=f"run only the {name} stage", parents=[common])
        stage_cmd.add_argument("chapter")
        stage_cmd.add_argument("--force", action="store_true", help="redo this stage")
        if name == "ingest":
            stage_cmd.add_argument(
                "--input",
                help="folder or PDF to ingest from (default: the chapter's 00_input/)",
            )
        if name == "crop":
            stage_cmd.add_argument(
                "--detector",
                choices=("yolo", "opencv"),
                help="override crop.detector for this run",
            )

    fetch_cmd = sub.add_parser(
        "fetch-models", help="download the panel detector weights", parents=[common]
    )
    fetch_cmd.add_argument("--force", action="store_true", help="re-download even if present")
    fetch_cmd.add_argument(
        "--to", dest="destination", help="output path (default: crop.weights_path)"
    )

    batch_cmd = sub.add_parser(
        "crop-batch",
        help="ingest and crop many chapters in one Kaggle run",
        parents=[common],
    )
    batch_cmd.add_argument("chapters", nargs="+", help="chapter ids, e.g. ch003 ch004")
    batch_cmd.add_argument(
        "--source-root",
        required=True,
        help="folder holding one subfolder of page images per chapter",
    )
    batch_cmd.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"chapters per kernel run (default {DEFAULT_BATCH_SIZE})",
    )
    batch_cmd.add_argument(
        "--kernel-slug",
        default="manga-recap-crop-batch",
        help="Kaggle kernel to push (default manga-recap-crop-batch)",
    )
    batch_cmd.add_argument(
        "--keep-payload",
        action="store_true",
        help="keep the staged payload and kernel logs for inspection",
    )

    sub.add_parser(
        "check",
        help="verify API keys, model weights and Kaggle are configured",
        parents=[common],
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    level = args.log_level or str(config.get("logging.level", "INFO"))
    setup_logging(level, config.get("logging.log_file", "logs/manga_recap.log"), force=True)
    _log = get_logger("cli")

    # `check` and `fetch-models` are about the machine, not a chapter, so they
    # run without one. `crop-batch` has many chapters rather than one.
    if args.command in ("check", "fetch-models"):
        try:
            return _dispatch(args, None, config)
        except KeyboardInterrupt:
            return 130
        except (FileNotFoundError, ValueError, ConfigError) as exc:
            _log.error("%s", exc)
            return 1

    if args.command == "crop-batch":
        try:
            return _dispatch(args, None, config)
        except KeyboardInterrupt:
            _log.warning("Interrupted. Finished batches are saved; re-run to continue.")
            return 130
        except (FileNotFoundError, ValueError, ConfigError) as exc:
            _log.error("%s", exc)
            return 1

    paths = ChapterPaths.create(args.chapter, args.data_dir)

    try:
        return _dispatch(args, paths, config)
    except KeyboardInterrupt:
        _log.warning("Interrupted. Completed stages are saved; re-run to continue.")
        return 130
    except (FileNotFoundError, ValueError, ConfigError) as exc:
        _log.error("%s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001 - top-level handler
        _log.error("Unexpected failure: %s", exc)
        _log.error("Re-run with --log-level DEBUG for more detail.")
        return 1


def _dispatch(args, paths: ChapterPaths, config) -> int:
    from .stages.s6_pipeline import run_pipeline
    from .stages.s6_pipeline.status import render_status, status

    if args.command == "status":
        report = status(paths, config)
        render_status(report)
        return 0

    if args.command == "fetch-models":
        from .fetch_models import fetch

        target = args.destination or config.require("crop.weights_path")
        try:
            path = fetch(target, force=getattr(args, "force", False))
        except (ValueError, ImportError) as exc:
            _log.error("%s", exc)
            return 1
        _log.info("Detector ready: %s", path)
        return 0

    if args.command == "check":
        from .preflight import render, run_checks

        return 0 if render(run_checks(config)) else 1

    if args.command == "crop-batch":
        return _run_crop_batch(args, config)

    if args.command == "run":
        results = run_pipeline(
            paths,
            config,
            from_stage=getattr(args, "from_stage", None),
            only=getattr(args, "only", None),
            force=getattr(args, "force", False),
        )
        return 0 if "failed" not in results.values() else 1

    if args.command == "ingest":
        return _run_stage("s0_ingest", paths, config, args, extra=_ingest_extra(args))

    label = args.command
    stage_name = _stage_for_label(label)
    return _run_stage(stage_name, paths, config, args, extra=_crop_extra(args, config))


def _ingest_extra(args) -> dict:
    extra: dict = {}
    if getattr(args, "input", None):
        extra["input_override"] = Path(args.input)
    return extra


def _crop_extra(args, config) -> dict:
    detector = getattr(args, "detector", None)
    if detector:
        # Override just for this run, without editing config.yaml.
        config._data.setdefault("crop", {})["detector"] = detector
    return {}


def _run_stage(stage_name: str, paths: ChapterPaths, config, args, extra: dict) -> int:
    from .stages.s6_pipeline import run_pipeline

    if stage_name == "s0_ingest" and extra.get("input_override"):
        _stage_ingest_with_override(paths, extra["input_override"])

    results = run_pipeline(
        paths, config, only=stage_name, force=getattr(args, "force", False)
    )
    return 0 if results.get(stage_name) != "failed" else 1


def _run_crop_batch(args, config) -> int:
    """Crop many chapters on Kaggle, then confirm each one landed on disk.

    The exit code is 0 only when every chapter cropped *and* its images verify,
    so a partial batch cannot be mistaken for a finished one.
    """
    from .stages.s1_crop import kaggle_batch

    chapters = list(dict.fromkeys(args.chapters))
    results = kaggle_batch.run_batch(
        chapters,
        config,
        source_root=Path(args.source_root),
        batch_size=args.batch_size,
        data_dir=getattr(args, "data_dir", None),
        kernel_slug=args.kernel_slug,
        keep_payload=args.keep_payload,
    )

    failed: list[str] = []
    verified = 0
    for result in results:
        for chapter_id in result.chapters:
            if chapter_id in result.failed:
                failed.append(chapter_id)
                continue
            try:
                kaggle_batch.verify(chapter_id, getattr(args, "data_dir", None))
            except (FileNotFoundError, ValueError) as exc:
                _log.error("%s", exc)
                failed.append(chapter_id)
            else:
                verified += 1
                panels = result.panel_counts.get(chapter_id, 0)
                _log.info("%s: %d panels verified on disk", chapter_id, panels)

    _log.info(
        "crop-batch: %d/%d chapters cropped and verified",
        verified,
        len(chapters),
    )
    if failed:
        _log.error("crop-batch failed for: %s", ", ".join(sorted(failed)))
        return 1
    return 0


def _stage_ingest_with_override(paths: ChapterPaths, source: Path) -> None:
    """Copy an external source into the chapter's input folder, then ingest."""
    if not source.exists():
        raise FileNotFoundError(f"--input path does not exist: {source}")

    paths.ensure_dirs()
    import shutil

    copied = 0
    if source.is_file():
        shutil.copy2(source, paths.input_dir / source.name)
        copied = 1
    else:
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".pdf"):
                shutil.copy2(path, paths.input_dir / path.name)
                copied += 1

    if copied == 0:
        raise ValueError(f"No page images or PDFs found in {source}")
    get_logger("cli").info("Copied %d source file(s) from %s", copied, source)


def _stage_for_label(label: str) -> str:
    from .stages.s6_pipeline import STAGE_LABELS

    for name, mapped in STAGE_LABELS.items():
        if mapped == label:
            return name
    raise ValueError(f"Unknown command '{label}'")


if __name__ == "__main__":
    sys.exit(main())
