"""A temporary file host on this machine, for Kaggle to push results into.

Kaggle cannot reach this disk, so every artefact has to be parked on a public host
first. That is what this replaces: a throwaway HTTP server that accepts a PUT and
serves the bytes back, reached through a Cloudflare tunnel.

It is deliberately minimal and deliberately temporary.

    python -m manga_recap.tools.dropbox --port 8790 --dir .dropbox

Kaggle then PUTs to `https://<tunnel>.trycloudflare.com/<name>` and reads the same
URL to download it. Nothing is kept after the process exits.

Why not just use catbox: catbox accepted a 22MB upload in six seconds and then
served the URL as `content-length: 0`. litterbox refuses this address with 403.
0x0.st is unreachable from Kaggle. Every free host that would take anonymous
uploads either would not take them from Kaggle's address range or would not give
the bytes back, and the pipeline needs both halves.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# Cloudflare's free quick tunnels hand out a random subdomain under this host.
TUNNEL_HOST = "trycloudflare.com"
MAX_BYTES = 2 * 1024**3  # 2GB, matching what a 25GB host would allow


class Handler(BaseHTTPRequestHandler):
    """PUT to store a file, GET to read one back, plus a status endpoint."""

    server_version = "manga-dropbox/1.0"
    root: Path = Path(".")
    quiet: bool = False

    # -- helpers ---------------------------------------------------------
    def _name(self) -> str | None:
        raw = self.path.split("?", 1)[0].strip("/")
        if not raw:
            return None
        # Only a bare file name. A path here would let a caller write outside
        # the drop directory, and there is no reason for one to contain a path.
        candidate = Path(raw)
        if candidate.name != raw or raw in (".", "..") or "\\" in raw:
            self._error(400, "use a bare file name, not a path")
            return None
        return raw

    def _error(self, code: int, message: str) -> None:
        body = json.dumps({"error": message}).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _log(self, message: str) -> None:
        if not self.quiet:
            print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)

    # -- verbs -----------------------------------------------------------
    def do_PUT(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        name = self._name()
        if name is None:
            return
        try:
            declared = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._error(400, "bad Content-Length")
            return
        if declared <= 0:
            self._error(400, "empty upload")
            return
        if declared > MAX_BYTES:
            self._error(413, f"over the {MAX_BYTES // 1024**2}MB ceiling")
            return

        target = self.root / name
        digest = hashlib.sha256()
        received = 0
        started = time.time()
        try:
            with target.open("wb") as handle:
                while received < declared:
                    chunk = self.rfile.read(min(1024 * 1024, declared - received))
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
        except Exception as exc:  # noqa: BLE001
            target.unlink(missing_ok=True)
            self._error(500, f"could not write: {exc}")
            return

        if received != declared:
            # A short read means the connection died mid-transfer. Leaving the
            # partial file would let the next reader download a truncated archive
            # and blame the pipeline, so it is removed here.
            target.unlink(missing_ok=True)
            self._error(400, f"short upload: {received} of {declared} bytes")
            return

        elapsed = max(time.time() - started, 0.001)
        self._log(
            f"PUT {name} {received / 1e6:.1f}MB "
            f"in {elapsed:.1f}s = {received / 1e6 / elapsed:.2f} MB/s "
            f"sha256={digest.hexdigest()[:16]}"
        )
        body = json.dumps(
            {
                "name": name,
                "size": received,
                "sha256": digest.hexdigest(),
                "seconds": round(elapsed, 2),
            }
        ).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-SHA256", digest.hexdigest())
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("/status", "/status"):
            body = json.dumps(
                {
                    "ok": True,
                    "files": sorted(p.name for p in self.root.iterdir() if p.is_file()),
                    "bytes": sum(
                        p.stat().st_size for p in self.root.iterdir() if p.is_file()
                    ),
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        name = self._name()
        if name is None:
            return
        target = self.root / name
        if not target.is_file():
            self._error(404, f"no such file: {name}")
            return

        size = target.stat().st_size
        started = time.time()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(size))
        self.send_header("X-Content-SHA256", hashlib.sha256(target.read_bytes()).hexdigest())
        self.end_headers()
        sent = 0
        with target.open("rb") as handle:
            while sent < size:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)
                sent += len(chunk)
        elapsed = max(time.time() - started, 0.001)
        self._log(
            f"GET {name} {sent / 1e6:.1f}MB in {elapsed:.1f}s "
            f"= {sent / 1e6 / elapsed:.2f} MB/s"
        )

    def do_HEAD(self) -> None:  # noqa: N802
        name = self._name()
        if name is None:
            return
        target = self.root / name
        if not target.is_file():
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        return  # do_GET/do_PUT log their own lines with throughput


def tunnel_url_from_log(text: str) -> str | None:
    """Pull the https://*.trycloudflare.com URL out of cloudflared's output."""
    match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
    return match.group(0) if match else None


def serve(port: int, directory: Path, quiet: bool = False) -> ThreadingHTTPServer:
    directory.mkdir(parents=True, exist_ok=True)
    Handler.root = directory
    Handler.quiet = quiet
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"dropbox serving {directory} on http://127.0.0.1:{port}", flush=True)
    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8790)
    parser.add_argument("--dir", default=".dropbox", help="where files are kept")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    server = serve(args.port, Path(args.dir), args.quiet)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\ndropbox stopped", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
