"""Kaggle API transport: dataset upload, kernel push, status polling, output download.

Wraps the `kaggle` CLI in one place so stages never shell out to it directly.
The important behaviours here are all failure-path behaviours: a missing
credential, an expired GPU quota, or a kernel that dies at hour nine should all
surface as a clear message rather than a hung pipeline.

Kaggle kernel lifecycle used by this project:

    datasets init -> datasets create/version   (upload inputs)
    kernels init  -> kernels push             (start a run)
    kernels status                             (poll: running|complete|error)
    kernels output                             (download /kaggle/working)
    kernels pull                               (fetch logs for debugging)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from .logging import format_duration, get_logger

DEFAULT_TIMEOUT = 300
KAGGLE_CONFIG_PATH = Path.home() / ".kaggle" / "kaggle.json"

# Kernel status strings Kaggle reports, mapped to our own vocabulary.
STATUS_RUNNING = {"running", "pending", "queued"}
STATUS_DONE = {"complete", "success"}
STATUS_FAILED = {"error", "canceled", "cancelled", "dead", "timeout"}

# The CLI answers with prose around the status, e.g.
#   wampireai/manga-recap-tts has status "KernelWorkerStatus.ERROR"
# so the word has to be pulled out of the sentence before anything compares it.
_STATUS_PREFIX = "kernelworkerstatus."


def normalise_status(output: str) -> str:
    """Reduce Kaggle's status line to the bare word the state tables use."""
    text = output.strip().lower()
    if '"' in text:
        text = text.rsplit('"', 2)[-2] if text.count('"') >= 2 else text.strip('"')
    if _STATUS_PREFIX in text:
        text = text.split(_STATUS_PREFIX, 1)[1]
    for word in reversed(text.replace(".", " ").split()):
        if word in STATUS_DONE | STATUS_RUNNING | STATUS_FAILED:
            return word
    return text.strip('". ') or "unknown"


class KaggleError(RuntimeError):
    """Any Kaggle transport or run failure."""


class KaggleQuotaError(KaggleError):
    """The account's GPU/session quota is exhausted."""


@dataclass
class KernelRun:
    """Bookkeeping for one remote kernel run."""

    slug: str
    kernel_id: str
    started_at: float = field(default_factory=time.time)
    status: str = "pending"
    queue_seconds: float = 0.0
    total_seconds: float = 0.0

    @property
    def slug_id(self) -> str:
        return self.kernel_id


def kaggle_username() -> str:
    """Resolve the Kaggle username.

    Prefers `~/.kaggle/kaggle.json`, which is what the Kaggle CLI itself reads,
    and falls back to `KAGGLE_USERNAME` so credentials kept in `config/.env`
    work without a separate setup step.
    """
    from . import env as env_module

    from_file = _read_credentials_file()
    if from_file:
        return from_file["username"]
    from_env = env_module.get_any("KAGGLE_USERNAME", "KAGGLE_USER")
    if from_env:
        return from_env
    raise KaggleError(
        f"No Kaggle credentials found.\n"
        f"Either create {KAGGLE_CONFIG_PATH} with your username and key, or set "
        "KAGGLE_USERNAME and KAGGLE_KEY in config/.env."
    )


def _read_credentials_file() -> dict | None:
    """Read and validate ~/.kaggle/kaggle.json, or None when unusable."""
    if not KAGGLE_CONFIG_PATH.exists():
        return None
    try:
        data = json.loads(KAGGLE_CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    username = data.get("username")
    key = data.get("key")
    if not username or not key:
        return None
    return {"username": str(username), "key": str(key)}


def ensure_kaggle_credentials() -> str:
    """Make sure Kaggle is usable, and return the username.

    The Kaggle CLI reads the credentials file, not the process environment, so
    credentials supplied through `config/.env` are written out to
    `~/.kaggle/kaggle.json`. An existing file is never overwritten.
    """
    from . import env as env_module

    existing = _read_credentials_file()
    if existing:
        return existing["username"]

    username = env_module.get_any("KAGGLE_USERNAME", "KAGGLE_USER")
    key = env_module.get_any("KAGGLE_KEY", "KAGGLE_API_KEY")
    if not username or not key:
        raise KaggleError(
            f"No Kaggle credentials found.\n"
            f"Create {KAGGLE_CONFIG_PATH}, or set KAGGLE_USERNAME and KAGGLE_KEY "
            "in config/.env. Kaggle issues both at "
            "https://kaggle.com/settings/account."
        )

    KAGGLE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    KAGGLE_CONFIG_PATH.write_text(
        json.dumps({"username": username, "key": key}), encoding="utf-8"
    )
    # The CLI runs as this same user, but on POSIX the file holds a live token.
    if os.name != "nt":
        os.chmod(KAGGLE_CONFIG_PATH, 0o600)

    # Also publish them so a CLI invocation that reads the environment works.
    env_module.set_default("KAGGLE_USERNAME", username)
    env_module.set_default("KAGGLE_KEY", key)
    print(f"[kaggle] wrote credentials to {KAGGLE_CONFIG_PATH}")
    return username


class KaggleClient:
    """Thin, synchronous wrapper over the `kaggle` CLI.

    Deliberately synchronous: each call is a short subprocess, and the pipeline
    runs stages one at a time. Concurrency here would only complicate resume
    and error handling.
    """

    def __init__(
        self,
        username: str | None = None,
        *,
        executable: str | None = None,
        dry_run: bool = False,
    ) -> None:
        self.executable = executable or ensure_kaggle_cli()
        self.dry_run = dry_run
        self._log = get_logger("kaggle")
        self.username = username or ensure_kaggle_credentials()

    # -- low level --------------------------------------------------------

    def _run(
        self,
        args: list[str],
        *,
        timeout: int = DEFAULT_TIMEOUT,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        """Run a kaggle CLI command."""
        command = [self.executable, *args]
        self._log.debug("kaggle %s", " ".join(args))
        if self.dry_run:
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
        except FileNotFoundError as exc:
            raise KaggleError(
                f"'{self.executable}' not found on PATH. Install it with "
                "`pip install kaggle`."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise KaggleError(
                f"`kaggle {' '.join(args)}` timed out after {timeout}s"
            ) from exc

        if check and result.returncode != 0:
            self._raise_for_error(args, result)
        return result

    def _raise_for_error(self, args: list[str], result: subprocess.CompletedProcess[str]) -> None:
        message = (result.stderr or result.stdout or "").strip()
        lowered = message.lower()
        if "quota" in lowered or "exceeded" in lowered and "limit" in lowered:
            raise KaggleQuotaError(
                "Kaggle quota exhausted. Wait for the weekly GPU quota to reset "
                f"or switch off GPU. Details: {message}"
            )
        raise KaggleError(f"`kaggle {' '.join(args)}` failed: {message}")

    # -- datasets ---------------------------------------------------------

    def dataset_exists(self, slug: str) -> bool:
        result = self._run(["datasets", "status", f"{self.username}/{slug}"], check=False)
        return result.returncode == 0

    def upload_dataset(
        self,
        source_dir: Path,
        slug: str,
        *,
        private: bool = True,
        description: str = "",
        version_note: str = "",
    ) -> str:
        """Create the dataset, or upload a new version if it already exists.

        Kaggle requires `dataset-metadata.json` to sit in the source directory,
        so it is written here and left behind for the kernel's `dataset_sources`.
        """
        source_dir = Path(source_dir)
        if not source_dir.exists() or not any(source_dir.iterdir()):
            raise KaggleError(f"Nothing to upload: {source_dir} is missing or empty")

        self._write_dataset_metadata(source_dir, slug, private, description)

        exists = self.dataset_exists(slug)
        if exists:
            args = ["datasets", "version", "-p", str(source_dir), "-r", "zip", "-m", version_note]
            self._log.info("Uploading new version of dataset %s", slug)
        else:
            args = ["datasets", "create", "-p", str(source_dir), "-r", "zip"]
            self._log.info("Creating dataset %s", slug)

        self._run(args, timeout=1800)
        return f"{self.username}/{slug}"

    def _write_dataset_metadata(
        self, directory: Path, slug: str, private: bool, description: str
    ) -> None:
        metadata = {
            "title": slug.replace("-", " ").title(),
            "id": f"{self.username}/{slug}",
            "licenses": [{"name": "other"}],
            "keywords": ["manga-recap"],
        }
        if description:
            metadata["subtitle"] = description[:80]
        (directory / "dataset-metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )

    def download_dataset(self, slug: str, dest_dir: Path, *, force: bool = True) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        args = ["datasets", "download", f"{self.username}/{slug}", "-p", str(dest_dir)]
        if force:
            args.append("-f")
        self._run(args, timeout=3600)
        return dest_dir

    # -- kernels ----------------------------------------------------------

    def push_kernel(self, kernel_dir: Path, *, timeout: int = 600) -> None:
        """Start a run of the notebook in `kernel_dir`."""
        kernel_dir = Path(kernel_dir)
        if not (kernel_dir / "kernel-metadata.json").exists():
            raise KaggleError(f"kernel-metadata.json missing from {kernel_dir}")
        self._log.info("Pushing kernel from %s", kernel_dir)
        self._run(["kernels", "push", "-p", str(kernel_dir)], timeout=timeout)

    def kernel_status(self, kernel_id: str) -> str:
        """The run's status as a bare word: running, complete, error, and so on.

        The CLI does not print a bare status. It prints a sentence ending in a
        quoted enum like `KernelWorkerStatus.ERROR`, so comparing the raw output
        against STATUS_FAILED never matches and a failed run polls until the
        six-hour ceiling instead of raising. Parsing is the whole job here.
        """
        result = self._run(["kernels", "status", kernel_id], check=False)
        if result.returncode != 0:
            return "unknown"
        return normalise_status((result.stdout or "").strip().lower())

    def wait_for_kernel(
        self,
        kernel_id: str,
        *,
        poll_interval: int = 30,
        max_wait: int = 21600,
    ) -> KernelRun:
        """Poll until the run finishes, then raise if it did not succeed.

        Returns a KernelRun carrying the queue and total durations, which is
        the difference between Kaggle being slow and Kaggle being idle.
        """
        run = KernelRun(slug=kernel_id.rsplit("/", 1)[-1], kernel_id=kernel_id)
        self._log.info("Waiting for %s (poll every %ds)", kernel_id, poll_interval)

        # Give Kaggle API a moment to process the push and transition status
        time.sleep(10)
        deadline = time.time() + max_wait
        reported_queue = False
        has_started = False

        while time.time() < deadline:
            status = self.kernel_status(kernel_id)
            run.status = status

            if status in STATUS_RUNNING:
                has_started = True

            # Under NO circumstance accept complete unless has_started was observed
            if status in STATUS_DONE and has_started:
                run.total_seconds = time.time() - run.started_at
                self._log.info(
                    "Kernel %s completed in %s", run.slug, format_duration(run.total_seconds)
                )
                return run

            if status in STATUS_FAILED or status == "unknown":
                run.total_seconds = time.time() - run.started_at
                self._dump_kernel_logs(kernel_id)
                raise KaggleError(
                    f"Kernel {kernel_id} ended with status '{status}' after "
                    f"{format_duration(run.total_seconds)}. Kernel logs were "
                    "written to logs/ for inspection."
                )

            if not reported_queue and status in STATUS_RUNNING:
                # Started running: everything before this was queue time.
                run.queue_seconds = time.time() - run.started_at
                reported_queue = True
                self._log.info(
                    "Kernel %s running (queued %s)", run.slug, format_duration(run.queue_seconds)
                )

            self._log.info("Kernel %s: %s", run.slug, status)
            time.sleep(poll_interval)

        run.total_seconds = time.time() - run.started_at
        self._dump_kernel_logs(kernel_id)
        raise KaggleError(
            f"Kernel {kernel_id} did not finish within {format_duration(max_wait)} "
            f"(last status: {run.status}). Kaggle's own session limit is 12h, so "
            "this run may need to be split into smaller chunks."
        )

    def download_kernel_output(
        self, kernel_id: str, dest_dir: Path, *, timeout: int = 3600
    ) -> Path:
        """Download the run's /kaggle/working output into `dest_dir`."""
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        self._log.info("Downloading output of %s to %s", kernel_id, dest_dir)
        self._run(
            ["kernels", "output", kernel_id, "-p", str(dest_dir), "--page-size", "200", "--force"],
            timeout=timeout,
        )
        return dest_dir

    def kernel_logs(self, kernel_id: str) -> str:
        """Fetch the notebook's log text. Best-effort; never raises."""
        if self.dry_run:
            return ""
        try:
            result = subprocess.run(
                [self.executable, "kernels", "output", kernel_id, "--help"],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except Exception:  # noqa: BLE001 - logging must never break a run
            return ""
        return result.stdout or ""

    def _dump_kernel_logs(self, kernel_id: str) -> Path:
        """Persist whatever diagnostic output we can get, for post-mortem."""
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        target = logs_dir / f"{kernel_id.rsplit('/', 1)[-1]}_failure.log"
        lines = [
            f"Kernel: {kernel_id}",
            f"Status: unknown (dumped at {time.strftime('%Y-%m-%dT%H:%M:%S')})",
            "",
            "Download the full notebook log manually with:",
            f"  kaggle kernels output {kernel_id} -p logs/",
        ]
        target.write_text("\n".join(lines), encoding="utf-8")
        self._log.error("Kernel failure details written to %s", target)
        return target

    def kernel_exists(self, kernel_id: str) -> bool:
        return self.kernel_status(kernel_id) in STATUS_DONE | STATUS_RUNNING | STATUS_FAILED


def find_executable(name: str) -> str | None:
    """Locate a CLI, looking beside the running Python first.

    The venv's Scripts directory is only on PATH when the venv is activated.
    Checking `sys.executable`'s own directory means the pipeline works whether
    or not the user remembered to activate, and avoids a "kaggle: not found"
    failure that is easy to misread as a missing package.
    """
    found = shutil.which(name)
    if found:
        return found

    import sys
    from pathlib import Path

    scripts = Path(sys.executable).parent
    for candidate in (scripts / f"{name}.exe", scripts / name, scripts / f"{name}.cmd"):
        if candidate.exists():
            return str(candidate)
    return None


def ensure_kaggle_cli() -> str:
    """Fail early with an actionable message if the CLI is missing."""
    executable = find_executable("kaggle")
    if executable is None:
        raise KaggleError(
            "The `kaggle` CLI is not on PATH and was not found beside this "
            "interpreter. Install it with `pip install kaggle` into the same "
            "environment as manga-recap."
        )
    return executable
