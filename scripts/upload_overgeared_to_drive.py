"""Fast multi-threaded Google Drive uploader for Overgeared chapters.

Uploads unzipped folders directly to Google Drive using Google Drive REST API v3:
Root: 'Overgeared_Manhwa'
  - ch01/
    - 01_pages/
      - page_001.webp
      - ...
    - 02_panels/
      - panel_0001.webp
      - ...
      - panel_index.json
  - ch02/
  ...
  - ch30/

Features:
- Auto token refresh using client_secrets.json + tokens.json
- Concurrent multipart file uploads (up to 8 threads)
- Progress tracking and resumption (skips already uploaded files)
- Zero local heavy compute
"""

from __future__ import annotations

import io
import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENT_SECRETS_PATH = REPO_ROOT / "client_secrets.json"
TOKENS_PATH = Path(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json")
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters" / "overgeared"

# Global lock for token refresh and folder caching
_LOCK = Lock()
_FOLDER_CACHE: dict[str, str] = {}  # "parent_id/name" -> folder_id
_CURRENT_ACCESS_TOKEN: str = ""


def get_access_token() -> str:
    global _CURRENT_ACCESS_TOKEN
    with _LOCK:
        if _CURRENT_ACCESS_TOKEN:
            return _CURRENT_ACCESS_TOKEN

        tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
        acc = tokens["accounts"]["default"]
        refresh_token = acc["refreshToken"]

        client_info = json.loads(CLIENT_SECRETS_PATH.read_text(encoding="utf-8"))
        installed = client_info.get("installed", client_info.get("web", {}))
        client_id = installed["client_id"]
        client_secret = installed["client_secret"]

        params = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")

        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=params)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _CURRENT_ACCESS_TOKEN = data["access_token"]
            return _CURRENT_ACCESS_TOKEN


def refresh_token_now() -> str:
    global _CURRENT_ACCESS_TOKEN
    with _LOCK:
        tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
        acc = tokens["accounts"]["default"]
        refresh_token = acc["refreshToken"]

        client_info = json.loads(CLIENT_SECRETS_PATH.read_text(encoding="utf-8"))
        installed = client_info.get("installed", client_info.get("web", {}))
        client_id = installed["client_id"]
        client_secret = installed["client_secret"]

        params = urllib.parse.urlencode({
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")

        req = urllib.request.Request("https://oauth2.googleapis.com/token", data=params)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _CURRENT_ACCESS_TOKEN = data["access_token"]
            return _CURRENT_ACCESS_TOKEN


def make_request(url: str, data: bytes | None = None, headers: dict | None = None, method: str | None = None) -> dict:
    if headers is None:
        headers = {}

    retries = 3
    for attempt in range(retries):
        token = get_access_token()
        headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                content = resp.read()
                if content:
                    return json.loads(content.decode("utf-8"))
                return {}
        except urllib.error.HTTPError as e:
            if e.code == 401:
                refresh_token_now()
                continue
            elif e.code in (429, 500, 502, 503):
                time.sleep(2 ** attempt)
                continue
            else:
                body = e.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"HTTP {e.code} for {url}: {body}") from e
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1)
    return {}


def get_or_create_folder(folder_name: str, parent_id: str | None = None) -> str:
    cache_key = f"{parent_id or 'root'}/{folder_name}"
    with _LOCK:
        if cache_key in _FOLDER_CACHE:
            return _FOLDER_CACHE[cache_key]

    # Search for existing folder
    if parent_id:
        q = f"name = '{folder_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    else:
        q = f"name = '{folder_name}' and 'root' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"

    url = "https://www.googleapis.com/drive/v3/files?q=" + urllib.parse.quote(q)
    res = make_request(url)
    files = res.get("files", [])
    if files:
        fid = files[0]["id"]
        with _LOCK:
            _FOLDER_CACHE[cache_key] = fid
        return fid

    # Create folder
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    body = json.dumps(metadata).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    res = make_request("https://www.googleapis.com/drive/v3/files", data=body, headers=headers)
    fid = res["id"]
    with _LOCK:
        _FOLDER_CACHE[cache_key] = fid
    return fid


def list_existing_files(folder_id: str) -> set[str]:
    """Returns set of file names already in folder."""
    q = f"'{folder_id}' in parents and trashed = false"
    url = "https://www.googleapis.com/drive/v3/files?pageSize=1000&fields=files(name)&q=" + urllib.parse.quote(q)
    existing = set()
    page_token = None
    while True:
        req_url = url
        if page_token:
            req_url += f"&pageToken={page_token}"
        res = make_request(req_url)
        for f in res.get("files", []):
            existing.add(f["name"])
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return existing


def upload_single_file(local_path: Path, parent_folder_id: str, mime_type: str = "image/webp") -> int:
    """Uploads a file to parent_folder_id using multipart upload. Returns bytes uploaded."""
    file_size = local_path.stat().st_size
    file_bytes = local_path.read_bytes()

    metadata = {
        "name": local_path.name,
        "parents": [parent_folder_id],
    }

    boundary = "-------314159265358979323846"
    delimiter = f"\r\n--{boundary}\r\n".encode()
    close_delimiter = f"\r\n--{boundary}--\r\n".encode()

    body = io.BytesIO()
    body.write(delimiter)
    body.write(b"Content-Type: application/json; charset=UTF-8\r\n\r\n")
    body.write(json.dumps(metadata).encode("utf-8"))
    body.write(delimiter)
    body.write(f"Content-Type: {mime_type}\r\n\r\n".encode())
    body.write(file_bytes)
    body.write(close_delimiter)

    payload = body.getvalue()
    headers = {
        "Content-Type": f"multipart/related; boundary={boundary}",
        "Content-Length": str(len(payload)),
    }

    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
    make_request(url, data=payload, headers=headers)
    return file_size


def get_mime_type(p: Path) -> str:
    ext = p.suffix.lower()
    if ext == ".webp":
        return "image/webp"
    elif ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".json":
        return "application/json"
    return "application/octet-stream"


def main():
    print("=" * 70)
    print("GOOGLE DRIVE FOLDER UPLOADER: OVERGEARED (CH01 - CH30)")
    print("Zero-Zip Direct Folder Tree Upload")
    print("=" * 70, flush=True)

    t0 = time.time()
    root_folder_id = get_or_create_folder("Overgeared_Manhwa")
    print(f"Target Root Drive Folder: 'Overgeared_Manhwa' (ID: {root_folder_id})\n", flush=True)

    chapter_dirs = sorted([d for d in CHAPTERS_ROOT.iterdir() if d.is_dir() and d.name.startswith("ch")])
    total_chapters = len(chapter_dirs)

    # Pre-collect all tasks to upload
    # Task item: (local_file_path, parent_folder_id, mime_type)
    upload_tasks: list[tuple[Path, str, str]] = []
    skipped_existing = 0

    print("Analyzing Drive folders and synchronizing tree...")
    for idx, ch_dir in enumerate(chapter_dirs, 1):
        ch_name = ch_dir.name
        ch_folder_id = get_or_create_folder(ch_name, root_folder_id)

        # 1. 01_pages
        pages_dir = ch_dir / "01_pages"
        if pages_dir.exists():
            pages_folder_id = get_or_create_folder("01_pages", ch_folder_id)
            existing_pages = list_existing_files(pages_folder_id)
            for f in sorted(pages_dir.glob("*.webp")):
                if f.name in existing_pages:
                    skipped_existing += 1
                else:
                    upload_tasks.append((f, pages_folder_id, "image/webp"))

        # 2. 02_panels
        panels_dir = ch_dir / "02_panels"
        if panels_dir.exists():
            panels_folder_id = get_or_create_folder("02_panels", ch_folder_id)
            existing_panels = list_existing_files(panels_folder_id)
            # Manifest
            idx_file = panels_dir / "panel_index.json"
            if idx_file.exists():
                if idx_file.name in existing_panels:
                    skipped_existing += 1
                else:
                    upload_tasks.append((idx_file, panels_folder_id, "application/json"))
            # Panel images
            for f in sorted(panels_dir.glob("*.webp")):
                if f.name in existing_panels:
                    skipped_existing += 1
                else:
                    upload_tasks.append((f, panels_folder_id, "image/webp"))

        sys.stdout.write(f"\rMapped {idx}/{total_chapters} chapters... (Found {len(upload_tasks)} files to upload, {skipped_existing} already present)")
        sys.stdout.flush()

    print("\n" + "-" * 70)
    print(f"Total files queued for upload: {len(upload_tasks)}")
    print(f"Already existing on Drive: {skipped_existing}")
    total_bytes_queued = sum(f[0].stat().st_size for f in upload_tasks)
    print(f"Total size to upload: {total_bytes_queued / (1024*1024):.2f} MB ({total_bytes_queued / (1024**3):.2f} GB)")
    print("-" * 70, flush=True)

    if not upload_tasks:
        print("All files are already uploaded to Google Drive!")
        return

    # Multi-threaded concurrent upload
    uploaded_count = 0
    uploaded_bytes = 0
    max_workers = 8

    print(f"Starting concurrent upload with {max_workers} worker threads...\n", flush=True)
    start_upload_time = time.time()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(upload_single_file, path, folder_id, mime): path
            for path, folder_id, mime in upload_tasks
        }

        for fut in as_completed(future_map):
            p = future_map[fut]
            try:
                b = fut.result()
                uploaded_count += 1
                uploaded_bytes += b
                pct = (uploaded_count / len(upload_tasks)) * 100
                elapsed = time.time() - start_upload_time
                mb_per_sec = (uploaded_bytes / (1024 * 1024)) / max(1.0, elapsed)
                rem_sec = ((len(upload_tasks) - uploaded_count) / max(1, uploaded_count)) * elapsed

                if uploaded_count % 25 == 0 or uploaded_count == len(upload_tasks):
                    print(
                        f"  [{uploaded_count}/{len(upload_tasks)}] {pct:5.1f}% | "
                        f"{uploaded_bytes/(1024*1024):6.1f} MB uploaded | "
                        f"{mb_per_sec:.2f} MB/s | ETA: {rem_sec/60:.1f}m | "
                        f"Latest: {p.parent.parent.name}/{p.parent.name}/{p.name}",
                        flush=True
                    )
            except Exception as e:
                print(f"\n[ERROR] Failed to upload {p}: {e}", flush=True)

    total_time = time.time() - t0
    print("\n" + "=" * 70)
    print(f"UPLOAD COMPLETE IN {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Total Files Uploaded: {uploaded_count}")
    print(f"Total Bytes Uploaded: {uploaded_bytes / (1024*1024):.2f} MB ({uploaded_bytes / (1024**3):.2f} GB)")
    print(f"Drive Destination: 'Overgeared_Manhwa' (ID: {root_folder_id})")
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
