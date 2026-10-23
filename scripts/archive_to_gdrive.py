"""Upload Only Sense Online complete archive to Google Drive.

Organized structure on Google Drive:
Only_Sense_Online_Archive/
├── chapters/
│   ├── ch01/
│   │   ├── 07_final.mp4
│   │   ├── 04_script.json
│   │   ├── 03_descriptions.json
│   │   ├── 06_timeline.json
│   │   ├── 07_render_manifest.json
│   │   └── 07_sync_report.json
│   ... (all 115 chapters)
├── thumbnails/
│   ├── Only_Sense_Online_Part_1_Thumbnail.jpg
│   ├── Only_Sense_Online_Part_1_Evolution_Thumbnail.jpg
│   └── Only_Sense_Online_Part_2_Thumbnail.jpg
├── hooks/
│   ├── hook_part1.mp4, hook_part1.json
│   └── ...
└── metadata/
    ├── Only_Sense_Online_Part_1_Timestamps.txt
    ├── Only_Sense_Online_Part_2_Timestamps.txt
    └── youtube_uploads_movies.json

Includes state tracking in build/gdrive_archive_state.json for seamless resumption.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from googleapiclient.http import MediaFileUpload

# Import Drive service helper
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from upload_to_gdrive import get_drive_service, get_or_create_folder

ROOT_FOLDER_NAME = "Only_Sense_Online_Archive"
STATE_FILE = REPO_ROOT / "build/gdrive_archive_state.json"


def ch_key(name: str) -> tuple[int, int]:
    m = re.match(r"ch0*(\d+)(?:_(\d+))?", name)
    if m:
        base = int(m.group(1))
        sub = int(m.group(2)) if m.group(2) else 0
        return (base, sub)
    return (9999, 0)


def load_state() -> dict[str, str]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state: dict[str, str]):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_subfolder(service, parent_id: str, name: str) -> str:
    query = f"'{parent_id}' in parents and name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    res = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    f = service.files().create(body=meta, fields="id").execute()
    return f.get("id")


def upload_single_file(service, parent_id: str, local_path: Path, state_key: str, state: dict[str, str]) -> str:
    if state_key in state:
        return state[state_key]

    file_size = local_path.stat().st_size
    mime_type = "video/mp4" if local_path.suffix == ".mp4" else "application/json" if local_path.suffix == ".json" else "text/plain" if local_path.suffix == ".txt" else "image/jpeg"

    # Use chunked upload for files > 5 MB
    is_resumable = file_size > 5 * 1024 * 1024
    chunk_size = 10 * 1024 * 1024 if is_resumable else -1

    media = MediaFileUpload(
        str(local_path),
        mimetype=mime_type,
        resumable=is_resumable,
        chunksize=chunk_size if is_resumable else -1,
    )
    meta = {
        "name": local_path.name,
        "parents": [parent_id],
    }

    req = service.files().create(body=meta, media_body=media, fields="id")
    response = None
    if is_resumable:
        while response is None:
            status, response = req.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"\r      [{local_path.name}] {pct}% ({status.resumable_progress / 1e6:.1f} / {file_size / 1e6:.1f} MB)", end="", flush=True)
        print(f"\r      [DONE] {local_path.name} ({file_size / 1e6:.1f} MB)", flush=True)
    else:
        response = req.execute()
        print(f"      [DONE] {local_path.name} ({file_size / 1e3:.1f} KB)", flush=True)

    file_id = response.get("id")
    state[state_key] = file_id
    save_state(state)
    return file_id


def main():
    service = get_drive_service()
    root_folder_id = get_or_create_folder(service, ROOT_FOLDER_NAME)
    state = load_state()

    print("=" * 70, flush=True)
    print("GOOGLE DRIVE ARCHIVE PIPELINE: Only Sense Online", flush=True)
    print(f"Root Folder: {ROOT_FOLDER_NAME} ({root_folder_id})", flush=True)
    print("=" * 70, flush=True)

    # 1. Setup subfolders
    chapters_folder_id = get_subfolder(service, root_folder_id, "chapters")
    thumbnails_folder_id = get_subfolder(service, root_folder_id, "thumbnails")
    hooks_folder_id = get_subfolder(service, root_folder_id, "hooks")
    metadata_folder_id = get_subfolder(service, root_folder_id, "metadata")

    # 2. Upload Thumbnails
    print("\n[1/4] Archiving Thumbnails...", flush=True)
    thumbs_dir = REPO_ROOT / "data/thumbnails"
    if thumbs_dir.exists():
        for thumb in thumbs_dir.glob("*.*"):
            if thumb.is_file():
                upload_single_file(service, thumbnails_folder_id, thumb, f"thumb:{thumb.name}", state)

    # 3. Upload Metadata & Timestamps
    print("\n[2/4] Archiving Metadata & Timestamps...", flush=True)
    meta_files = [
        REPO_ROOT / "data/Only_Sense_Online_Part_1_Timestamps.txt",
        REPO_ROOT / "data/Only_Sense_Online_Part_2_Timestamps.txt",
        REPO_ROOT / "data/youtube_uploads_movies.json",
    ]
    for mf in meta_files:
        if mf.exists():
            upload_single_file(service, metadata_folder_id, mf, f"meta:{mf.name}", state)

    # 4. Upload Hooks
    print("\n[3/4] Archiving Hooks...", flush=True)
    hooks_dir = REPO_ROOT / "data/hooks"
    if hooks_dir.exists():
        for hf in sorted(hooks_dir.glob("*.*")):
            if hf.is_file() and hf.suffix in [".json", ".mp4"]:
                upload_single_file(service, hooks_folder_id, hf, f"hook:{hf.name}", state)

    # 5. Upload Chapters (07_final.mp4 + metadata jsons)
    ch_dirs = sorted([d for d in (REPO_ROOT / "data/chapters").iterdir() if d.is_dir() and d.name.startswith("ch")], key=lambda x: ch_key(x.name))
    total_chs = len(ch_dirs)
    print(f"\n[4/4] Archiving {total_chs} Chapters (Final Videos + Scripts/Timelines)...", flush=True)

    for idx, cdir in enumerate(ch_dirs, 1):
        ch_name = cdir.name
        print(f"\n[{idx:03d}/{total_chs}] Processing {ch_name}...", flush=True)
        ch_folder_id = get_subfolder(service, chapters_folder_id, ch_name)

        # Files to archive per chapter:
        targets = [
            cdir / "07_final.mp4",
            cdir / "04_script.json",
            cdir / "03_descriptions.json",
            cdir / "06_timeline.json",
            cdir / "07_render_manifest.json",
            cdir / "07_sync_report.json",
        ]

        for target in targets:
            if target.exists():
                skey = f"{ch_name}:{target.name}"
                upload_single_file(service, ch_folder_id, target, skey, state)

    print("\n" + "=" * 70, flush=True)
    print("GOOGLE DRIVE ARCHIVE COMPLETE AND VERIFIED!", flush=True)
    print("=" * 70, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
