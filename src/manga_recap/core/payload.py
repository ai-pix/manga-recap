"""Shipping a chapter's inputs to a Kaggle kernel.

A Kaggle kernel is a remote container with no access to this disk, so its inputs
have to be fetched from somewhere over HTTP. The original design pushed them as
a Kaggle Dataset, which works but is a heavyweight mechanism for what is really
"put these files where the kernel can read them": a dataset per chapter, a mount
path Kaggle controls, and a mount layout the kernel then has to guess.

So the inputs are zipped into one archive, uploaded to a plain file host, and the
kernel is told the URL. One request, one file, and the kernel does not care
where the host mounted anything.

The host defaults to 0x0.st, which needs no account. It is worth knowing what
that means: the URL is public to anyone who has it, and the host deletes files
that go untouched. That is fine for a chapter you are working on and is not fine
for anything you care about keeping. Set `tts.payload_url` to point somewhere you
control instead.
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import httpx

from .logging import get_logger

_log = get_logger("manga_recap.payload")

DEFAULT_HOST = "https://0x0.st"
CHUNK_BYTES = 1024 * 1024

# MediaFire has no anonymous upload: every call is authenticated with a key from
# a free account at mediafire.com/dev, read from the environment so it stays out
# of the repo. 0x0.st is the fallback because it needs no account, but it
# periodically switches uploads off, so a hosted key is the durable choice.
MEDIAFIRE_KEY_ENV = "MEDIAFIRE_API_KEY"
MEDIAFIRE_ENDPOINT = "https://upload.mediafire.com/api.php"


def build_archive(staging: Path, archive: Path) -> Path:
    """Zip a staged directory into one archive.

    Stored, not deflated. Panel PNGs are already compressed, so deflating them
    burns CPU on both ends to save nothing, and the kernel is paying for GPU
    minutes by the second.
    """
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(staging))
    return archive


def upload(
    archive: Path,
    *,
    host: str = DEFAULT_HOST,
    filename: str | None = None,
    timeout: float = 900.0,
) -> str:
    """Upload an archive and return the URL it can be fetched from.

    The host is named rather than implied, because the free ones are not equally
    dependable and each fails differently: 0x0.st disables uploads outright, and
    MediaFire needs a key and returns JSON rather than a bare URL.
    """
    name = filename or archive.name
    _log.info(
        "Uploading %s (%.1f MB) to %s",
        name,
        archive.stat().st_size / 1_000_000,
        host,
    )
    if "filebin.net" in host:
        return _upload_filebin(archive, name, host, timeout)
    if host.rstrip("/").endswith("mediafire.com"):
        return _upload_mediafire(archive, name, timeout)
    if host.rstrip("/").endswith("catbox.moe"):
        return _upload_catbox(archive, name, host, timeout)
    if "sendit.sh" in host:
        return _upload_sendit(archive, name, host, timeout)
    return _upload_plain(archive, name, host, timeout)


def _upload_filebin(archive: Path, name: str, host: str, timeout: float) -> str:
    """Upload to filebin.net via HTTP POST (direct public CDN download)."""
    import uuid

    bin_id = f"mr-{uuid.uuid4().hex[:10]}"
    clean_host = host.rstrip("/")
    clean_name = name.strip("/")
    url_target = f"{clean_host}/{bin_id}/{clean_name}"

    with archive.open("rb") as handle:
        response = httpx.post(
            url_target,
            content=handle.read(),
            timeout=timeout,
        )
    response.raise_for_status()
    _log.info("Payload uploaded to filebin: %s", url_target)
    return url_target


def _upload_sendit(archive: Path, name: str, host: str, timeout: float) -> str:
    """Upload to sendit.sh via HTTP PUT."""
    import re

    clean_host = host.rstrip("/")
    clean_name = name.strip("/")
    url_target = f"{clean_host}/{clean_name}"
    with archive.open("rb") as handle:
        response = httpx.put(
            url_target,
            content=handle.read(),
            timeout=timeout,
        )
    response.raise_for_status()
    match = re.search(r"https://sendit\.sh/[a-zA-Z0-9_\-]+/[^\s]+", response.text)
    if not match:
        raise RuntimeError(f"sendit.sh returned unexpected response: {response.text[:200]!r}")
    url = match.group(0).strip()
    _log.info("Payload uploaded: %s", url)
    return url


def _upload_catbox(archive: Path, name: str, host: str, timeout: float) -> str:
    """Upload to catbox.moe with retry and browser headers.

    No account, and the file survives, which matters more than it sounds: the
    kernel has to be able to fetch this some minutes later, so a host that
    deletes on a timer is a race rather than a solution.
    """
    import time

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
        )
    }
    attempts = 3
    last_err: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with archive.open("rb") as handle:
                response = httpx.post(
                    f"{host.rstrip('/')}/user/api.php",
                    headers=headers,
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": (name, handle, "application/zip")},
                    timeout=timeout,
                )
            response.raise_for_status()
            url = response.text.strip()
            if url.startswith("http"):
                _log.info("Payload uploaded: %s", url)
                return url
            last_err = RuntimeError(f"catbox returned invalid response: {response.text[:200]!r}")
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        if attempt < attempts:
            time.sleep(2 * attempt)

    raise RuntimeError(f"catbox upload failed after {attempts} attempts: {last_err}")


def _upload_mediafire(archive: Path, name: str, timeout: float) -> str:
    key = _require_env(MEDIAFIRE_KEY_ENV)
    with archive.open("rb") as handle:
        response = httpx.post(
            MEDIAFIRE_ENDPOINT,
            data={"key": key, "action": "upload", "time": "21600"},
            files={"file": (name, handle, "application/zip")},
            timeout=timeout,
        )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("response", {}).get("success"):
        raise RuntimeError(f"MediaFire rejected the upload: {payload}")
    url = payload["response"]["urls"]["single_download"]
    _log.info("Payload uploaded: %s", url)
    return url


def _upload_plain(archive: Path, name: str, host: str, timeout: float) -> str:
    with archive.open("rb") as handle:
        response = httpx.post(
            host,
            files={"file": (name, handle, "application/zip")},
            timeout=timeout,
        )
    response.raise_for_status()
    url = response.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(
            f"{host} did not return a URL. Response was: {response.text[:200]!r}"
        )
    _log.info("Payload uploaded: %s", url)
    return url


def _require_env(name: str) -> str:
    """Read a credential, failing with the fix rather than an empty key."""
    import os

    from .env import get_env

    value = os.environ.get(name) or get_env(name)
    if not value:
        raise RuntimeError(
            f"{name} is not set. Get a free key at mediafire.com/dev and put "
            f"{name}=your-key in config/.env, or set a different payload_host."
        )
    return value


PAYLOAD_TOKEN = "__PAYLOAD_URL__"
# The kernels write `PAYLOAD_URL = PAYLOAD_UNSET`, with the sentinel held in a
# separate constant. Replacing the assignment rather than the bare token is what
# keeps the kernel's own "was a URL set?" comparison intact.
PAYLOAD_ASSIGNMENT = "PAYLOAD_URL = PAYLOAD_UNSET"


def stage_from_url(
    *,
    kernel_dir: Path,
    url: str,
    work_dir: Path,
    metadata: dict | None = None,
) -> Path:
    """Copy the kernel to a scratch directory and compile the payload URL into it.

    Two things are per-run, so the push happens from a copy rather than from the
    checked-in directory: the payload URL, which would otherwise be hardcoded in
    a file meant to be safe to commit, and the kernel slug, which embeds a Kaggle
    username.

    The URL is substituted into the script itself rather than written beside it,
    because Kaggle runs a script kernel as `/kaggle/src/script.py`. Anything
    placed next to main.py at push time is simply not there when the code runs.
    """
    if work_dir.exists():
        shutil.rmtree(work_dir)
    # __pycache__ is local build output and would be uploaded as part of the
    # kernel source for no reason.
    shutil.copytree(
        kernel_dir, work_dir, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )

    code_path = work_dir / "main.py"
    if code_path.exists():
        source = code_path.read_text(encoding="utf-8")
        if PAYLOAD_ASSIGNMENT not in source:
            raise RuntimeError(
                f"{code_path} has no '{PAYLOAD_ASSIGNMENT}' line, so the payload "
                "URL cannot be supplied. The stage and the kernel disagree."
            )
        # Replace the whole assignment, never the bare token. A blind token swap
        # also rewrites the comparison that tests whether a URL was set, which
        # leaves the kernel deciding it has no URL after it was just given one.
        source = source.replace(
            PAYLOAD_ASSIGNMENT, f'PAYLOAD_URL = "{url.strip()}"'
        )
        code_path.write_text(source, encoding="utf-8")

    metadata_path = work_dir / "kernel-metadata.json"
    kernel_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    for key, value in (metadata or {}).items():
        kernel_metadata[key] = value
    if "dataset_sources" not in (metadata or {}):
        kernel_metadata.setdefault("dataset_sources", [])
    metadata_path.write_text(json.dumps(kernel_metadata, indent=2) + "\n", encoding="utf-8")
    return work_dir
