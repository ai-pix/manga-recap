"""Stage 1 on Kaggle, for many chapters at once.

`s1_crop.run` executes on the local machine, and its YOLO pass is heavy
inference. That is exactly the work this project does not run locally: the
machine has a GTX 1650 and the rule is that ML inference goes to Kaggle. But the
per-chapter cost is small, about 90 seconds for a 31-page chapter, while a
kernel launch costs about as much again in queueing and image pull. One chapter
per launch therefore spends half the GPU-hour budget on overhead.

So this module batches. It stages a group of chapters into one payload, pushes
the kernel once, and unpacks every chapter's `01_pages` and `02_panels` out of a
single download.

The crop logic is not reimplemented. The payload carries `src/`, `config/` and
`models/`, and the kernel calls `s0_ingest.run` and `s1_crop.run` themselves, so
a chapter cropped here is cropped by the same code that runs locally.
"""

from __future__ import annotations

import json
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from ...core import payload
from ...core.config import Config
from ...core.kaggle_io import KaggleClient, KaggleError
from ...core.logging import get_logger, timed
from ...core.paths import ChapterPaths, repo_path
from ...core.schema import PanelIndexFile, load_model

_log = get_logger("stages.s1_crop.kaggle_batch")

KERNEL_DIR = repo_path("kaggle/kernel_crop")
REQUIREMENTS = repo_path("kaggle/kernel_crop/requirements-kaggle.txt")
MANIFEST_NAME = "crop_manifest.json"
LOG_NAME = "crop_log.txt"

# The payload is a plain zip on a free host, and catbox refuses anything over
# 200MB. The weights are ~15MB of every payload and raw page images are the rest,
# so this is the number that decides how many chapters fit in one run.
DEFAULT_BATCH_SIZE = 15


@dataclass
class BatchResult:
    """What one kernel run produced."""

    chapters: list[str] = field(default_factory=list)
    succeeded: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    panel_counts: dict[str, int] = field(default_factory=dict)
    problems: dict[str, list[str]] = field(default_factory=dict)
    kernel_seconds: float = 0.0
    total_panels: int = 0
    # The kernel's own manifest rows, kept because they hold the result URLs.
    rows: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed


def plan_batches(chapters: list[str], size: int = DEFAULT_BATCH_SIZE) -> list[list[str]]:
    """Split chapters into groups of at most `size`."""
    if size < 1:
        raise ValueError(f"batch size must be at least 1, got {size}")
    return [chapters[i : i + size] for i in range(0, len(chapters), size)]


def run_batch(
    chapters: list[str],
    config: Config,
    *,
    source_root: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    data_dir: Path | None = None,
    kernel_slug: str = "manga-recap-crop-batch",
    keep_payload: bool = False,
) -> list[BatchResult]:
    """Ingest and crop every chapter, one kernel run per batch.

    `source_root` holds one folder of page images per chapter, named after the
    chapter as it appears in the source (`Chapter 003`). The mapping from that
    name to a chapter id is resolved by `resolve_chapter_sources`.
    """
    if not chapters:
        raise ValueError("no chapters given")
    if not KERNEL_DIR.exists():
        raise FileNotFoundError(f"Kaggle kernel directory missing: {KERNEL_DIR}")

    base = Path(data_dir) if data_dir else repo_path("data") / "chapters"
    sources = resolve_chapter_sources(chapters, source_root)

    client = KaggleClient()
    results: list[BatchResult] = []
    for index, group in enumerate(plan_batches(chapters, batch_size), start=1):
        _log.info(
            "Batch %d: %d chapters (%s .. %s)",
            index,
            len(group),
            group[0],
            group[-1],
        )
        results.append(
            _run_one_group(group, config, sources, base, client, kernel_slug, keep_payload)
        )
    return results


def _run_one_group(
    group: list[str],
    config: Config,
    sources: dict[str, Path],
    data_dir: Path,
    client: KaggleClient,
    kernel_slug: str,
    keep_payload: bool,
) -> BatchResult:
    label = f"{group[0]}-{group[-1]}"
    work_dir = repo_path("data") / "chapters" / f"_batch_{label}"
    result = BatchResult(chapters=list(group))

    with timed(f"crop batch {label} (Kaggle {kernel_slug})"):
        staging = _stage(group, sources, config, work_dir)
        archive = payload.build_archive(staging, work_dir / f"{label}.zip")
        size_mb = archive.stat().st_size / 1_000_000
        if size_mb > 190:
            # Worth failing loudly here rather than after a wasted GPU wait: the
            # host rejects the upload, so the kernel would fail on a missing URL.
            raise RuntimeError(
                f"payload is {size_mb:.0f}MB, over the 200MB host limit. "
                f"Lower the batch size below {len(group)}."
            )

        host = str(config.get("crop.payload_host", payload.DEFAULT_HOST))
        url = _upload_with_retry(archive, host, f"crop-{label}.zip")

        kernel_dir = payload.stage_from_url(
            kernel_dir=KERNEL_DIR,
            url=url,
            work_dir=work_dir / "kernel",
            metadata={
                "id": f"{client.username}/{kernel_slug}",
                "title": kernel_slug,
                "enable_gpu": bool(config.get("crop.enable_gpu", True)),
            },
        )
        client.push_kernel(kernel_dir)
        kernel_id = f"{client.username}/{kernel_slug}"
        _log.info("Waiting for %s (payload %.0fMB)", kernel_id, size_mb)
        run_info = client.wait_for_kernel(
            kernel_id,
            poll_interval=int(config.get("crop.poll_interval_seconds", 30)),
            max_wait=int(config.get("crop.max_wait_seconds", 21600)),
        )
        result.kernel_seconds = round(run_info.total_seconds, 1)
        download_dir = client.download_kernel_output(
            kernel_id, work_dir / "out"
        )

    manifest_path = _locate(download_dir, MANIFEST_NAME)
    if manifest_path is None:
        raise KaggleError(
            f"{kernel_id} produced no {MANIFEST_NAME}. "
            f"Check {work_dir / 'out'} and the kernel log."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    log_file = _locate(download_dir, LOG_NAME)
    if log_file is not None:
        shutil.copy2(log_file, work_dir / LOG_NAME)

    for row in manifest.get("chapters", []):
        chapter_id = row.get("chapter_id", "?")
        result.rows.append(row)
        if row.get("ok"):
            result.succeeded.append(chapter_id)
            result.panel_counts[chapter_id] = int(row.get("panel_count", 0))
            result.total_panels += int(row.get("panel_count", 0))
            problems = row.get("problems") or []
            if problems:
                result.problems[chapter_id] = problems
        else:
            result.failed[chapter_id] = row.get("error", "unknown error")

    _install(download_dir, group, data_dir, result)
    shutil.rmtree(download_dir, ignore_errors=True)
    if not keep_payload:
        shutil.rmtree(work_dir, ignore_errors=True)

    _log.info(
        "Batch %s: %d/%d chapters, %d panels, %ss",
        label,
        len(result.succeeded),
        len(result.chapters),
        result.total_panels,
        result.kernel_seconds,
    )
    for chapter_id, problems in result.problems.items():
        for problem in problems:
            _log.warning("Stage 1 check (%s): %s", chapter_id, problem)
    for chapter_id, error in result.failed.items():
        _log.error("Stage 1 failed (%s): %s", chapter_id, error)
    return result


def _stage(
    group: list[str],
    sources: dict[str, Path],
    config: Config,
    work_dir: Path,
) -> Path:
    """Lay out everything the kernel needs: code, config, weights, page images."""
    if work_dir.exists():
        shutil.rmtree(work_dir)
    staging = work_dir / "payload"
    chapters_dir = staging / "data" / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(
        repo_path("src"),
        staging / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        dirs_exist_ok=True,
    )
    _stage_config(staging)
    if REQUIREMENTS.exists():
        shutil.copy2(REQUIREMENTS, staging / "requirements-kaggle.txt")

    weights = repo_path(config.get("crop.weights_path", "models/panel_detector.pt"))
    if weights.exists():
        (staging / "models").mkdir(parents=True, exist_ok=True)
        shutil.copy2(weights, staging / "models" / weights.name)
    else:
        _log.warning("Detector weights not found at %s; the kernel will fail", weights)

    for chapter_id in group:
        source = sources.get(chapter_id)
        if source is None:
            raise FileNotFoundError(f"no source folder resolved for {chapter_id}")
        target = chapters_dir / chapter_id / "00_input"
        target.mkdir(parents=True, exist_ok=True)
        images = sorted(p for p in source.iterdir() if p.is_file())
        for image in images:
            shutil.copy2(image, target / image.name)
        _log.debug("%s: staged %d images", chapter_id, len(images))

    (staging / "job.json").write_text(
        json.dumps({"chapters": list(group)}, indent=2), encoding="utf-8"
    )
    return staging


def _upload_with_retry(archive: Path, host: str, name: str, attempts: int = 4) -> str:
    """Upload the payload and return a URL that verifiably serves the bytes.

    Retrying is not enough on its own. catbox returned HTTP 200 for an upload that
    had in fact been truncated to nothing, and because it deduplicates on filename
    a retry of the *same* name returns that same broken entry. So each attempt
    gets a fresh name, and the URL is fetched back and length-checked before it
    is handed to the kernel. Without that check the kernel spends a GPU slot
    downloading zero bytes and dies in `zipfile`, which reads like a corrupt
    payload and sends you looking in the wrong place.
    """
    delay = 5.0
    last: str = "no attempt made"
    for attempt in range(1, attempts + 1):
        # A unique name per attempt, because the hosts key on it.
        attempt_name = f"{name}.{attempt}" if attempt > 1 else name
        try:
            url = payload.upload(archive, host=host, filename=attempt_name)
            size = _remote_size(url)
            if size == archive.stat().st_size:
                return url
            last = f"host served {size} bytes, expected {archive.stat().st_size}"
            _log.warning("Payload upload attempt %d/%d: %s", attempt, attempts, last)
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            _log.warning("Payload upload attempt %d/%d failed: %s", attempt, attempts, exc)
        if attempt < attempts:
            time.sleep(delay)
            delay = min(delay * 2, 30)
    raise RuntimeError(f"could not upload a complete payload to {host}: {last}")


def _remote_size(url: str) -> int:
    """Bytes a URL actually serves, or -1 when it cannot be read.

    Only the length is fetched. A HEAD is tried first because it is free, but
    several of these hosts answer HEAD with 405, so a ranged GET is the fallback
    rather than a full download.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = httpx.head(url, headers=headers, timeout=120, follow_redirects=True)
        if response.status_code == 200:
            declared = response.headers.get("content-length")
            if declared and declared.isdigit():
                return int(declared)
    except Exception:  # noqa: BLE001 - fall through to the ranged GET
        pass

    try:
        with httpx.stream(
            "GET", url, headers={**headers, "Range": "bytes=0-0"}, timeout=120
        ) as response:
            if response.status_code not in (200, 206):
                return -1
            content_range = response.headers.get("content-range", "")
            if "/" in content_range:
                total = content_range.rsplit("/", 1)[-1].strip()
                if total.isdigit():
                    return int(total)
            declared = response.headers.get("content-length")
            return int(declared) if declared and declared.isdigit() else -1
    except Exception:  # noqa: BLE001
        return -1


def _stage_config(staging: Path) -> None:
    """Copy config.yaml and the prompts, and nothing else.

    `config/` also holds `.env`, which is where the Gemini and Kaggle keys live.
    The payload is uploaded to a public file host and its URL is handed to a
    remote container, so copying the whole directory publishes both credentials
    to anyone who has the link. Only the two things the kernel actually reads are
    copied, by name.
    """
    config_dir = repo_path("config")
    target = staging / "config"
    target.mkdir(parents=True, exist_ok=True)

    config_yaml = config_dir / "config.yaml"
    if not config_yaml.exists():
        raise FileNotFoundError(f"config.yaml missing at {config_yaml}")
    shutil.copy2(config_yaml, target / "config.yaml")

    prompts = config_dir / "prompts"
    if prompts.is_dir():
        shutil.copytree(
            prompts,
            target / "prompts",
            ignore=shutil.ignore_patterns(".env*"),
            dirs_exist_ok=True,
        )

    # Belt and braces: if anything secret-looking is still sitting in the staged
    # tree, drop it rather than upload it.
    for stray in list(target.rglob(".env*")) + list(target.rglob("*.pem")):
        _log.warning("Refusing to ship credential file %s in the payload", stray.name)
        stray.unlink()


def _install(
    download_dir: Path,
    group: list[str],
    data_dir: Path,
    result: BatchResult,
) -> None:
    """Bring each chapter's archives home and unpack them into its folder.

    The kernel pushes each archive to a plain file host and records the URL, so
    these are fetched concurrently. Kaggle's own output download is one slow
    sequential stream with a one hour ceiling, which a batch this size does not
    fit inside; a thread pool over separate URLs does, and it is the difference
    between minutes and hours.
    """
    work = download_dir.parent / "fetched"
    work.mkdir(parents=True, exist_ok=True)

    # A field holding a URL was published by the kernel and is fetched directly.
    # A bare file name means no host took it and the archive is still in the
    # kernel output, so it is read from what came down the Kaggle pipe instead.
    remote: list[tuple[str, str, str]] = []
    local: dict[tuple[str, str], Path] = {}
    for row in result.rows:
        if not row.get("ok"):
            continue
        chapter_id = row["chapter_id"]
        for field_name, kind in (("pages_zip", "pages"), ("panels_zip", "panels")):
            value = row.get(field_name)
            if not value:
                continue
            if value.startswith("http"):
                remote.append((chapter_id, kind, value))
            else:
                found = _locate(download_dir, value)
                if found is not None:
                    local[(chapter_id, kind)] = found

    fetched = dict(local)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(_fetch, url, work / f"{chapter_id}__{kind}.zip"): (
                chapter_id,
                kind,
            )
            for chapter_id, kind, url in remote
        }
        for future in as_completed(futures):
            key = futures[future]
            try:
                fetched[key] = future.result()
            except Exception as exc:  # noqa: BLE001
                result.failed[key[0]] = f"could not fetch {key[1]}: {exc}"
                _log.error("%s: fetch failed: %s", key[0], exc)

    for chapter_id in list(result.succeeded):
        panels = fetched.get((chapter_id, "panels"))
        if panels is None:
            result.failed[chapter_id] = "02_panels archive never arrived"
            result.succeeded.remove(chapter_id)
            continue
        paths = ChapterPaths.create(chapter_id, data_dir)
        paths.ensure_dirs()
        pages = fetched.get((chapter_id, "pages"))
        if pages is not None:
            shutil.unpack_archive(pages, paths.pages_dir)
        shutil.unpack_archive(panels, paths.panels_dir)


def _fetch(url: str, target: Path, attempts: int = 4) -> Path:
    """Stream one archive to disk, retrying a few times.

    catbox occasionally answers a range request with an error page, so a short
    file is treated as a failure rather than a success.
    """
    delay = 5
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = httpx.get(url, timeout=httpx.Timeout(120.0), follow_redirects=True)
            request.raise_for_status()
            body = request.content
            if len(body) < 1024 or not body.startswith(b"PK"):
                raise ValueError(
                    f"got {len(body)} bytes that are not a zip, "
                    f"starting {body[:16]!r}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            return target
        except Exception as exc:  # noqa: BLE001
            last = exc
            _log.debug("fetch attempt %d/%d for %s failed: %s", attempt, attempts, url, exc)
            if attempt < attempts:
                time.sleep(delay)
                delay = min(delay * 2, 30)
    raise RuntimeError(f"could not fetch {url} after {attempts} attempts: {last}")


def verify(chapter_id: str, data_dir: Path | None = None) -> PanelIndexFile:
    """Read back a cropped chapter's index and confirm it matches the images."""
    paths = ChapterPaths.create(chapter_id, data_dir)
    index = load_model(paths.panels_dir / "panel_index.json", PanelIndexFile)
    missing = [
        panel.image_path
        for panel in index.panels
        if not (paths.root / panel.image_path).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"{chapter_id}: {len(missing)} panel image(s) missing, "
            f"first is {missing[0]}"
        )
    return index


def resolve_chapter_sources(
    chapters: list[str], source_root: Path
) -> dict[str, Path]:
    """Map each chapter id to its folder of page images.

    `Chapter 003` and `chapter_003` both have to resolve to `ch003`, because
    neither the source library nor this repo agrees on how to write a chapter
    name and guessing wrong would ingest the wrong pages.
    """
    if not source_root.is_dir():
        raise FileNotFoundError(f"source root does not exist: {source_root}")

    folders = {p.name: p for p in source_root.iterdir() if p.is_dir()}
    resolved: dict[str, Path] = {}
    missing: list[str] = []
    for chapter_id in chapters:
        digits = "".join(ch for ch in chapter_id if ch.isdigit())
        match = None
        for name, folder in folders.items():
            name_digits = "".join(ch for ch in name if ch.isdigit())
            if name_digits == digits:
                match = folder
                break
        if match is None:
            missing.append(chapter_id)
        else:
            resolved[chapter_id] = match
    if missing:
        raise FileNotFoundError(
            f"no source folder under {source_root} for: {', '.join(missing)}"
        )
    return resolved


def _locate(directory: Path, filename: str) -> Path | None:
    """Find a kernel output, newest first.

    `kaggle kernels output` can return artifacts from more than one run, and a
    plain rglob walks in name order, so an older copy of a file could be
    unpacked over a newer one.
    """
    if not directory.exists():
        return None
    direct = directory / filename
    if direct.exists():
        return direct
    candidates = [p for p in directory.rglob(filename) if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, str(p)))
