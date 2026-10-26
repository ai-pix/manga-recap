"""Upload requested manhwa zip files to sendit.sh and output individual download URLs."""

from __future__ import annotations

import json
import re
import subprocess
import time
import urllib.parse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = REPO_ROOT / "data" / "sendit_zip_uploads.json"

FILES = [
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Bastard.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Weak Hero.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\The Horizon.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Dare I Hope.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\The Fable.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Murim Login.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\The Tutorial Is Too Hard.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Dungeon Reset.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Frozen Hearts.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\The King of Bugs.zip"),
    Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips\Returning With Absolutely Nothing.zip"),
]


def load_state() -> dict[str, dict]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict[str, dict]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def upload_file(path: Path) -> str:
    safe_name = urllib.parse.quote(path.name)
    url_target = f"https://sendit.sh/{safe_name}"

    cmd = [
        "curl.exe",
        "-s",
        "-S",
        "--retry", "3",
        "--retry-delay", "5",
        "--max-time", "1800",
        url_target,
        "-T", str(path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"curl failed with code {result.returncode}: {result.stderr}")

    match = re.search(r"https://sendit\.sh/[a-zA-Z0-9_\-]+/[^\s]+", result.stdout)
    if not match:
        raise RuntimeError(f"Could not parse URL from sendit response:\n{result.stdout}")

    return match.group(0).strip()


def main() -> None:
    state = load_state()

    # Pre-populate already verified ones if not present
    if "Dare I Hope.zip" not in state:
        state["Dare I Hope.zip"] = {
            "name": "Dare I Hope.zip",
            "size_mb": 15.82,
            "url": "https://sendit.sh/VOuO-/Cqff1.zip",
            "uploaded_at": "2026-10-26T00:14:29+05:30",
        }
    if "Returning With Absolutely Nothing.zip" not in state:
        state["Returning With Absolutely Nothing.zip"] = {
            "name": "Returning With Absolutely Nothing.zip",
            "size_mb": 17.80,
            "url": "https://sendit.sh/k09Hp/gY6Lx.zip",
            "uploaded_at": "2026-10-26T00:13:58+05:30",
        }
    save_state(state)

    total_files = len(FILES)
    print("=" * 70)
    print(f"UPLOADING {total_files} ZIP FILES TO SENDIT.SH")
    print("=" * 70)

    for idx, path in enumerate(FILES, start=1):
        name = path.name
        if not path.exists():
            print(f"[{idx}/{total_files}] SKIP: {name} (file not found)")
            continue

        size_mb = path.stat().st_size / (1024 * 1024)

        if name in state and state[name].get("url"):
            print(f"[{idx}/{total_files}] ALREADY UPLOADED: {name} ({size_mb:.2f} MB)")
            print(f"       URL: {state[name]['url']}")
            continue

        print(f"\n[{idx}/{total_files}] UPLOADING: {name} ({size_mb:.2f} MB)...", flush=True)
        t0 = time.time()
        try:
            url = upload_file(path)
            elapsed = time.time() - t0
            speed = size_mb / elapsed if elapsed > 0 else 0
            print(f"       [SUCCESS] ({elapsed:.1f}s, {speed:.2f} MB/s) -> {url}", flush=True)
            state[name] = {
                "name": name,
                "size_mb": round(size_mb, 2),
                "url": url,
                "elapsed_s": round(elapsed, 1),
                "speed_mbps": round(speed, 2),
            }
            save_state(state)
        except Exception as e:
            print(f"       [ERROR] Failed to upload {name}: {e}", flush=True)

    print("\n" + "=" * 70)
    print("ALL UPLOADS COMPLETE! SUMMARY OF URLS:")
    print("=" * 70)
    for path in FILES:
        name = path.name
        info = state.get(name, {})
        url = info.get("url", "FAILED/NOT UPLOADED")
        print(f"{name}: {url}")


if __name__ == "__main__":
    main()
