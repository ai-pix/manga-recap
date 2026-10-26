"""Upload a single file to sendit.sh with progress reporting."""

from __future__ import annotations

import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path


def upload_to_sendit(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    size_mb = file_path.stat().st_size / (1024 * 1024)
    safe_name = urllib.parse.quote(file_path.name)
    target_url = f"https://sendit.sh/{safe_name}"

    print(f"Uploading: {file_path.name}")
    print(f"Size: {size_mb:.2f} MB ({size_mb / 1024:.2f} GB)")
    print(f"Target: {target_url}\n", flush=True)

    t0 = time.time()
    cmd = [
        "curl.exe",
        "-#",  # Progress bar
        "-S",
        "--retry", "3",
        "--retry-delay", "5",
        "--max-time", "3600",
        target_url,
        "-T", str(file_path),
    ]

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    stdout, stderr = proc.communicate()
    elapsed = time.time() - t0
    speed = size_mb / elapsed if elapsed > 0 else 0

    if proc.returncode != 0:
        raise RuntimeError(f"curl exited with code {proc.returncode}:\nSTDERR: {stderr}\nSTDOUT: {stdout}")

    full_output = f"{stdout}\n{stderr}"
    match = re.search(r"https://sendit\.sh/[a-zA-Z0-9_\-]+/[^\s]+", full_output)
    if not match:
        raise RuntimeError(f"Could not parse sendit URL from output:\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}")

    url = match.group(0).strip()
    print(f"\nUpload Successful in {elapsed:.1f}s ({speed:.2f} MB/s)!")
    print(f"URL: {url}")
    return url


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Tomb Raider King - Chapters and Panels.zip")
    upload_to_sendit(target)
