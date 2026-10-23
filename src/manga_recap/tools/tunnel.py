"""Start the dropbox and a Cloudflare quick tunnel, and print the public URL.

Two processes. The dropbox is a local HTTP server on 127.0.0.1; the tunnel is
`cloudflared tunnel --url`, which asks Cloudflare for a random
`*.trycloudflare.com` subdomain and forwards it here. No account, no token, and
the URL is only valid while both are running.

The URL is printed to stdout as soon as cloudflared reports it, and also written
to `.dropbox_url` so a script does not have to scrape the log.
"""

from __future__ import annotations

import re
import subprocess
import sys
import threading
import time
from pathlib import Path

CLOUDFLARED = Path(
    r"C:\Users\ravih\AppData\Local\Temp\opencode\cloudflared\cloudflared.exe"
)
URL_FILE = Path(".dropbox_url")


def read_url(stream, stop: threading.Event) -> str | None:
    """Watch cloudflared's output for the URL it was assigned."""
    pattern = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
    for line in stream:
        text = line.decode("utf-8", "replace") if isinstance(line, bytes) else line
        print(f"[tunnel] {text.rstrip()}", flush=True)
        match = pattern.search(text)
        if match:
            return match.group(0)
        if stop.is_set():
            return None
    return None


def main() -> int:
    if not CLOUDFLARED.exists():
        print(f"cloudflared not found at {CLOUDFLARED}", file=sys.stderr)
        return 1

    stop = threading.Event()
    process = subprocess.Popen(
        [
            str(CLOUDFLARED),
            "tunnel",
            "--url",
            "http://127.0.0.1:8790",
            "--no-autoupdate",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
    )

    found: list[str] = []
    watcher = threading.Thread(target=_collect, args=(process, stop, found), daemon=True)
    watcher.start()

    deadline = time.time() + 90
    while time.time() < deadline and not found:
        if process.poll() is not None:
            print("cloudflared exited before assigning a URL", file=sys.stderr)
            return 1
        time.sleep(1)

    if not found:
        print("timed out waiting for a tunnel URL", file=sys.stderr)
        process.terminate()
        return 1

    url = found[0]
    URL_FILE.write_text(url + "\n", encoding="utf-8")
    print(f"\nDROPBOX_URL={url}", flush=True)
    print("keep this process alive for the duration of the batch", flush=True)

    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
    finally:
        stop.set()
        URL_FILE.unlink(missing_ok=True)
    return 0


def _collect(process, stop, sink: list[str]) -> None:
    url = read_url(process.stdout, stop)
    if url:
        sink.append(url)


if __name__ == "__main__":
    raise SystemExit(main())
