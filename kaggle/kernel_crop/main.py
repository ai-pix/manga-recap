"""Kaggle kernel: cut many chapters into panels in a single run.

Stage 1 is the only stage whose per-chapter cost is small enough that doing it
one chapter at a time is dominated by kernel spin-up. A 31-page chapter costs
about 90 seconds of real work; the queue, the image pull and the upload cost
about the same again. So this kernel takes a *list* of chapters and does all of
them per run, which is the difference between ~110 kernel launches and about 8.

The pipeline code itself is not reimplemented here. The payload carries `src/`,
`config/` and `models/`, and this kernel calls `s0_ingest.run` and `s1_crop.run`
exactly as `manga ingest` and `manga crop` do. A crop that the local pipeline
would reject is rejected here too, because it is the same code deciding.

Output is one zip of `01_pages` and one of `02_panels` per chapter plus a
manifest. Pages come back too even though only panels are the product: stage 2
reads `01_pages/page_NNN.png` to give the vision model page context, so a
chapter without them cannot be described.

One chapter failing does not fail the batch. A chapter that raises is recorded
in the manifest with its traceback and the run continues, because losing 17 good
chapters to one malformed folder is the worse outcome by far.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

WORKING = Path("/kaggle/working")
# The payload is unpacked under /tmp, deliberately NOT under /kaggle/working.
# Kaggle saves everything in /kaggle/working as the kernel's output, so an app
# directory left there ships the entire uploaded payload back down the same slow
# pipe as the results: the source page images, the detector weights and the
# whole of src/, none of which the caller wants. /tmp is scratch and is thrown
# away instead. /kaggle/input is not an option either, it is mounted read-only.
APP_ROOT = Path("/tmp/manga_crop_app")
OUT_DIR = WORKING / "out"
LOG_NAME = "crop_log.txt"
MANIFEST_NAME = "crop_manifest.json"
FAILURE_NAME = "failure.txt"

# Where finished chapter archives are pushed so the caller can fetch them in
# parallel. Kaggle's own output download is a single slow stream with a one hour
# ceiling, which a batch of this size cannot fit inside; a plain file host has
# neither problem.
#
# The list is a fallback chain, not a preference list. catbox answers 412
# Precondition Failed to every request from Kaggle's address range while
# accepting the identical request from a home connection, so it is blocked by IP
# rather than by anything wrong with the request. Each host is tried in turn and
# the first that accepts the file wins.
# litterbox first, catbox second.
#
# storage.to was tried here and removed. Its uploads are excellent: three signed
# requests straight to Cloudflare R2, unthrottled, no key, no account. But its
# downloads are gated behind a Cloudflare Turnstile challenge. The share page
# embeds `mint_challenge_required` and a `mint_proof` that the browser obtains by
# solving the challenge, and there is no documented API endpoint that returns
# bytes. A script can put a file there and cannot get it back out, which is the
# wrong half of the problem for a pipeline leg.
#
# catbox.moe itself answers 412 to every request from Kaggle's address range while
# accepting the identical request from a home connection, so it is blocked by IP
# and only works as a fallback for local uploads, not for kernel uploads.
RESULT_HOSTS = (
    "https://litterbox.catbox.moe/resources/internals/api.php",
    "https://catbox.moe",
)

# Publishing from Kaggle measured at roughly 90KB/s on a single connection, so
# concurrent uploads are what make a batch's transfer time bearable. Eight is
# enough to fill the pipe without looking like an attack, which is what gets an
# upload host to start refusing requests.
UPLOAD_WORKERS = 8

CHUNK_BYTES = 1024 * 1024


class LogTee:
    """Tee stdout to both the console and a persistent log in /kaggle/working."""

    def __init__(self, filepath: Path):
        self.file = filepath.open("w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, data: str) -> int:
        self.stdout.write(data)
        self.stdout.flush()
        self.file.write(data)
        self.file.flush()
        return len(data)

    def flush(self) -> None:
        self.stdout.flush()
        self.file.flush()

    def close(self) -> None:
        self.file.close()


# Some free file hosts refuse a bare urllib request and close the connection
# without a response. They serve the file fine to anything that identifies
# itself as a browser. Verified against catbox: the default agent gets
# RemoteDisconnected, this one gets the zip.
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    )
}

# Replaced with the real URL by the stage when it stages a push. It cannot live
# in a neighbouring file: Kaggle runs a script kernel as `/kaggle/src/script.py`,
# so nothing the push put beside main.py is next to the running code.
#
# The sentinel is a separate constant on purpose. The stage rewrites only the
# right-hand side of the assignment below, and if the token also appeared in the
# comparison that detects an unset URL, that comparison would be rewritten too
# and the kernel would never see a URL as set.
PAYLOAD_UNSET = "__PAYLOAD_URL__"
PAYLOAD_URL = PAYLOAD_UNSET


def payload_url() -> str:
    """Where this run's inputs are hosted."""
    if PAYLOAD_URL != PAYLOAD_UNSET and PAYLOAD_URL:
        return PAYLOAD_URL.strip()

    for candidate in (
        Path(__file__).resolve().parent / "payload_url.txt",
        Path("/kaggle/src/payload_url.txt"),
        Path("/kaggle/working/payload_url.txt"),
    ):
        if candidate.exists():
            value = candidate.read_text(encoding="utf-8").strip()
            if value:
                return value

    raise FileNotFoundError(
        "This kernel has no payload URL. The crop batch driver writes one into "
        "the kernel it pushes; pushing this directory by hand will not work."
    )


def _require_zip(path: Path, url: str) -> None:
    """Fail with the real reason if what came down is not a readable archive."""
    with path.open("rb") as handle:
        head = handle.read(4)
    if head[:2] != b"PK":
        preview = path.read_bytes()[:200].decode("utf-8", "replace")
        raise RuntimeError(
            f"payload at {url} is not a zip: it starts {head!r}, not PK. "
            f"The host returned an error page instead of the file. Body starts: "
            f"{preview!r}"
        )
    try:
        with zipfile.ZipFile(path, "r") as bundle:
            bad = bundle.testzip()
    except zipfile.BadZipFile as exc:
        raise RuntimeError(f"payload at {url} is a truncated zip: {exc}") from exc
    if bad is not None:
        raise RuntimeError(f"payload at {url} has a corrupt member: {bad}")


def _download(request, attempts: int = 4):
    """Open a URL, retrying a few times with a growing delay."""
    delay = 5
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return urllib.request.urlopen(request, timeout=900)
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  download attempt {attempt}/{attempts} failed: {exc}", flush=True)
            if attempt < attempts:
                time.sleep(delay)
                delay = min(delay * 2, 60)
    raise RuntimeError(f"could not download the payload after {attempts} attempts: {last}")


def fetch_payload() -> Path:
    """Download the payload archive and unpack it under /tmp/manga_crop_app.

    The download is validated before it is unpacked. catbox answers a throttled or
    rejected request with 200 and an HTML error page rather than an error status,
    and `zipfile` then fails deep inside its own constructor with a message about
    the end of the central directory. That reads like a corrupt payload and sends
    you hunting through the upload code when the real problem is one refused GET.
    """
    url = payload_url()
    print(f"[kernel] payload: {url}", flush=True)

    zip_path = WORKING / "payload.zip"
    request = urllib.request.Request(url, headers=FETCH_HEADERS)
    with _download(request) as response, open(zip_path, "wb") as handle:
        shutil.copyfileobj(response, handle, CHUNK_BYTES)

    size_mb = zip_path.stat().st_size / 1e6
    print(f"[kernel] payload is {size_mb:.1f} MB, unpacking", flush=True)
    _require_zip(zip_path, url)

    if APP_ROOT.exists():
        shutil.rmtree(APP_ROOT)
    APP_ROOT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as bundle:
        bundle.extractall(APP_ROOT)
    zip_path.unlink()

    # REPO_ROOT in manga_recap.core.paths is parents[3] of that module, so the
    # package must sit at <root>/src/manga_recap for config/ and models/ to
    # resolve next to it. Pointing sys.path anywhere else silently sends the
    # stage looking for config.yaml in a directory that does not exist.
    src = APP_ROOT / "src"
    if not src.is_dir():
        raise FileNotFoundError(f"payload has no src/ directory at {src}")
    sys.path.insert(0, str(src))
    os.chdir(APP_ROOT)
    print(f"[kernel] app root {APP_ROOT}, src on path", flush=True)
    return APP_ROOT


def ensure_dependencies() -> None:
    """Install ultralytics, the one package the Kaggle image does not ship.

    Nothing may pin or upgrade torch: the image's CUDA build is already correct
    and replacing it costs more than the install saves. `uv` is used when it is
    available because it resolves against what is already installed, so an
    already-satisfied torch is left alone.
    """
    requirements = next(APP_ROOT.glob("**/requirements-kaggle.txt"), None)
    if requirements is None:
        print("[kernel] no requirements file in the payload", flush=True)
        return

    wanted = [
        line.strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    if not wanted:
        return

    if shutil.which("uv"):
        print(f"[kernel] installing {wanted} with uv...", flush=True)
        result = subprocess.run(
            ["uv", "pip", "install", "--system", *wanted], check=False
        )
        if result.returncode == 0 and _ultralytics_imports():
            print("[kernel] ultralytics ready", flush=True)
            return

    # --no-deps is the fallback because a plain `pip install ultralytics` will
    # happily pull a CPU torch wheel over the image's CUDA one.
    print("[kernel] falling back to pip --no-deps", flush=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-input", "--no-deps", *wanted],
        check=False,
    )
    if not _ultralytics_imports():
        raise RuntimeError(
            "ultralytics could not be imported after installing it. The detector "
            "is unusable, so this run cannot crop anything."
        )


def _ultralytics_imports() -> bool:
    try:
        import torch  # noqa: F401
        from ultralytics import YOLO  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        print(f"[kernel] ultralytics import failed: {exc}", flush=True)
        return False
    return True


def _load_pipeline():
    """Import the pipeline lazily, after src/ is on the path."""
    from manga_recap.core.config import load_config
    from manga_recap.core.paths import ChapterPaths
    from manga_recap.stages import s0_ingest, s1_crop
    from manga_recap.stages.s1_crop.validate import validate as validate_index

    return load_config, ChapterPaths, s0_ingest, s1_crop, validate_index


def process_chapter(chapter_id: str, config, data_dir: Path) -> tuple[dict, list[Path]]:
    """Ingest and crop one chapter.

    Returns the manifest row and the archives still waiting to be published. The
    upload is deliberately not done here: publishing is the slowest part of a
    chapter and it has no business blocking the crop of the next one.
    """
    load_config, ChapterPaths, s0_ingest, s1_crop, validate_index = _load_pipeline()

    started = time.time()
    paths = ChapterPaths.create(chapter_id, data_dir)
    row: dict = {
        "chapter_id": chapter_id,
        "ok": False,
        "page_count": 0,
        "panel_count": 0,
        "problems": [],
        "error": "",
        "pages_zip": "",
        "panels_zip": "",
    }

    source = paths.input_dir
    if not source.is_dir():
        row["error"] = f"no source images at {source}"
        return row, []

    images = sorted(p.name for p in source.iterdir() if p.is_file())
    print(f"[kernel] {chapter_id}: {len(images)} source images", flush=True)

    pages = s0_ingest.run(paths, force=True)
    row["page_count"] = pages

    index = s1_crop.run(paths, config, force=True)
    row["panel_count"] = index.panel_count
    row["problems"] = validate_index(
        index,
        min_panels_per_page=int(config.get("crop.min_panels_per_page", 1)),
        min_text_containment=float(config.get("crop.min_text_containment", 0.9)),
        min_page_coverage=float(config.get("crop.min_page_coverage", 0.45)),
        check_text=bool(config.get("crop.check_text_coverage", True)),
    )

    archives = [
        path
        for path in (
            _zip_dir(paths.pages_dir, chapter_id, "pages"),
            _zip_dir(paths.panels_dir, chapter_id, "panels"),
        )
        if path is not None
    ]
    row["ok"] = True
    row["seconds"] = round(time.time() - started, 1)
    print(
        f"[kernel] {chapter_id}: {pages} pages, {index.panel_count} panels "
        f"in {row['seconds']}s",
        flush=True,
    )
    return row, archives


def _zip_dir(source: Path, chapter_id: str, kind: str) -> Path | None:
    """Zip one chapter directory into the out/ staging area."""
    if not source.is_dir():
        return None
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{chapter_id}__{kind}"
    shutil.make_archive(str(OUT_DIR / name), "zip", str(source))
    return OUT_DIR / f"{name}.zip"


def _publish(archive: Path, name: str) -> str:
    """Upload one archive to whichever result host will take it. "" if none will.

    The archive is read into memory once and reused across hosts, because these
    files are tens of megabytes and re-reading them per attempt is what makes a
    slow host slow.
    """
    payload_bytes = archive.read_bytes()
    print(
        f"[kernel]   publishing {name} ({len(payload_bytes) / 1e6:.1f} MB)",
        flush=True,
    )
    for host in RESULT_HOSTS:
        url = _publish_to(host, name, payload_bytes)
        if url:
            print(f"[kernel]   {name} -> {host} ok", flush=True)
            return url
        print(f"[kernel]   {host} refused {name}", flush=True)
    return ""


def _publish_to(host: str, name: str, payload_bytes: bytes) -> str:
    """Try one host. Returns its URL, or "" on any failure."""
    try:
        if "litterbox" in host:
            boundary = "----mangarecaplitter"
            body = b"".join(
                [
                    f"--{boundary}\r\n".encode(),
                    b'Content-Disposition: form-data; name="reqtype"\r\n\r\n',
                    b"fileupload\r\n",
                    f"--{boundary}\r\n".encode(),
                    b'Content-Disposition: form-data; name="time"\r\n\r\n',
                    b"72h\r\n",
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="fileToUpload"; filename="{name}"\r\n'.encode(),
                    b"Content-Type: application/zip\r\n\r\n",
                    payload_bytes,
                    f"\r\n--{boundary}--\r\n".encode(),
                ]
            )
            request = urllib.request.Request(
                host,
                data=body,
                headers={
                    **FETCH_HEADERS,
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                },
            )
            with urllib.request.urlopen(request, timeout=1800) as response:
                text = response.read().decode("utf-8", "replace").strip()
            return text if text.startswith("http") else ""

        # catbox and anything else that expects the fileToUpload field name.
        boundary = "----mangarecapcrop"
        body = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                b'Content-Disposition: form-data; name="reqtype"\r\n\r\n',
                b"fileupload\r\n",
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="fileToUpload"; filename="{name}"\r\n'.encode(),
                b"Content-Type: application/zip\r\n\r\n",
                payload_bytes,
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
        request = urllib.request.Request(
            host.rstrip("/") + "/user/api.php",
            data=body,
            headers={
                **FETCH_HEADERS,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
        )
        with urllib.request.urlopen(request, timeout=1800) as response:
            text = response.read().decode("utf-8", "replace").strip()
        return text if text.startswith("http") else ""
    except Exception as exc:  # noqa: BLE001 - a refused host must not sink the batch
        print(f"[kernel]   {host} error: {exc}", flush=True)
        return ""


def _publish_and_record(row: dict, archive: Path, kind: str) -> None:
    """Publish one archive and write its URL into the chapter's manifest row.

    Falls back to leaving the archive in the kernel output, which still works,
    just slowly: the caller falls back to the Kaggle download when the field holds
    a bare file name rather than a URL.
    """
    name = archive.name
    url = _publish(archive, name)
    if url:
        row[kind] = url
        archive.unlink(missing_ok=True)
        return
    row[kind] = name
    print(
        f"[kernel]   {name} kept in kernel output (no host took it)",
        flush=True,
    )


def main() -> int:
    started = time.time()
    WORKING.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fetch_payload()
    ensure_dependencies()

    job = json.loads((APP_ROOT / "job.json").read_text(encoding="utf-8"))
    chapters = job.get("chapters") or []
    if not chapters:
        raise ValueError("job.json lists no chapters. Nothing to crop.")
    print(f"[kernel] {len(chapters)} chapters queued: {chapters}", flush=True)

    config_path = APP_ROOT / "config" / "config.yaml"
    load_config, _ChapterPaths, _s0, _s1, _validate = _load_pipeline()
    config = load_config(config_path, reload=True)
    data_dir = APP_ROOT / "data" / "chapters"

    rows: list[dict] = []
    pending: list[tuple[dict, Path, str]] = []

    # Uploads run alongside cropping rather than after it. Publishing from Kaggle
    # measured at roughly 90KB/s per connection, so a batch's archives are the
    # slowest part of the run by a wide margin; overlapping them with the next
    # chapter's detection is what keeps a batch's wall clock near its compute
    # time instead of the sum of the two.
    with ThreadPoolExecutor(max_workers=UPLOAD_WORKERS) as pool:
        for position, chapter_id in enumerate(chapters, start=1):
            print(
                f"[kernel] --- {position}/{len(chapters)} {chapter_id} ---",
                flush=True,
            )
            try:
                row, archives = process_chapter(chapter_id, config, data_dir)
            except Exception:  # noqa: BLE001 - one bad chapter must not sink the batch
                detail = traceback.format_exc()
                print(f"[kernel] {chapter_id} FAILED:\n{detail}", flush=True)
                row = {
                    "chapter_id": chapter_id,
                    "ok": False,
                    "page_count": 0,
                    "panel_count": 0,
                    "problems": [],
                    "error": detail.strip().splitlines()[-1],
                    "pages_zip": "",
                    "panels_zip": "",
                }
                archives = []
            rows.append(row)
            for archive in archives:
                kind = "pages_zip" if archive.stem.endswith("pages") else "panels_zip"
                pending.append((row, archive, kind))
                pool.submit(_publish_and_record, row, archive, kind)

        print(f"[kernel] cropping done; awaiting {len(pending)} upload(s)", flush=True)
        pool.shutdown(wait=True)

    succeeded = [r for r in rows if r["ok"]]
    failed = [r for r in rows if not r["ok"]]
    manifest = {
        "chapters": rows,
        "chapter_count": len(rows),
        "succeeded": len(succeeded),
        "failed": len(failed),
        "total_pages": sum(r["page_count"] for r in rows),
        "total_panels": sum(r["panel_count"] for r in rows),
        "seconds": round(time.time() - started, 1),
    }
    (WORKING / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        f"[kernel] DONE {len(succeeded)}/{len(rows)} chapters, "
        f"{manifest['total_panels']} panels, {manifest['seconds']}s",
        flush=True,
    )
    for row in failed:
        print(f"[kernel] FAILED {row['chapter_id']}: {row['error']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.stdout = LogTee(WORKING / LOG_NAME)
    sys.stderr = sys.stdout
    # `sys.exit` is deliberately outside the handler. It raises SystemExit, which
    # is a BaseException: wrapping it would write a failure.txt on every
    # *successful* run, which is exactly what the render kernel used to do.
    try:
        _code = main()
    except Exception:  # noqa: BLE001
        _detail = traceback.format_exc()
        print(_detail, flush=True)
        try:
            (WORKING / FAILURE_NAME).write_text(_detail, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        raise
    sys.exit(_code)
