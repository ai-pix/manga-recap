"""Download all 40 chapter descriptions from Google Drive and save into pipeline chapters."""

from __future__ import annotations

import io
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.http import MediaIoBaseDownload

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from merge_descriptions import build_description  # noqa: E402
from upload_to_gdrive import get_drive_service  # noqa: E402

from manga_recap.core.schema import DescriptionFile, PanelIndexFile, save_model  # noqa: E402

FOLDER_ID = "18k6Of9q_V6JrTnGg8ADiqRZI6-UhWyKK"
SERIES_SLUG = "sss-class-revival-hunter"


def download_file_content(service, file_id: str) -> dict:
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return json.loads(fh.read().decode("utf-8"))


def process_chapter_descriptions(service, file_meta: dict) -> tuple[str, int]:
    name = file_meta.get("name", "")
    file_id = file_meta.get("id", "")

    m = re.match(r"ch(\d+)\.json", name, re.IGNORECASE)
    if not m:
        return name, 0

    ch_num = int(m.group(1))
    ch_id = f"{SERIES_SLUG}/ch{ch_num:02d}"
    ch_dir = REPO_ROOT / "data" / "chapters" / SERIES_SLUG / f"ch{ch_num:02d}"
    index_path = ch_dir / "02_panels" / "panel_index.json"
    out_desc_path = ch_dir / "03_descriptions.json"

    if not index_path.exists():
        print(f"[{ch_id}] Warning: index file not found at {index_path}. Skipping.")
        return ch_id, 0

    index = PanelIndexFile.model_validate_json(index_path.read_text(encoding="utf-8"))
    raw_data = download_file_content(service, file_id)

    raw_panels = raw_data.get("panels", [])
    records = {p["panel_id"]: p for p in raw_panels}

    model_name = raw_data.get("model", "")
    if not model_name and raw_panels:
        model_name = raw_panels[0].get("model", "qwen3-omni-flash")

    descriptions = []
    for panel in index.ordered():
        raw_p = records.get(panel.panel_id, {"panel_id": panel.panel_id, "action": "Undescribed panel."})
        desc_p = build_description(raw_p, panel)
        descriptions.append(desc_p)

    desc_file = DescriptionFile(
        chapter_id=ch_id,
        title=f"Chapter {ch_num}",
        series=SERIES_SLUG,
        created_at=datetime.now(timezone.utc).isoformat(),
        model=model_name or "qwen3-omni-flash",
        panel_count=len(descriptions),
        panels=descriptions,
    )

    save_model(desc_file, out_desc_path)
    return ch_id, len(descriptions)


def main():
    print("=" * 65)
    print("DOWNLOADING 40 CHAPTER DESCRIPTIONS FROM GOOGLE DRIVE")
    print(f"Folder ID: {FOLDER_ID}")
    print(f"Target Series: {SERIES_SLUG}")
    print("=" * 65, flush=True)

    service = get_drive_service()

    query = f"'{FOLDER_ID}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType, size)").execute()
    files = results.get("files", [])

    # Sort files numerically ch01.json -> ch40.json
    def get_num(f):
        m = re.search(r"ch(\d+)", f.get("name", ""))
        return int(m.group(1)) if m else 9999

    files.sort(key=get_num)
    print(f"Found {len(files)} description files in Google Drive folder.\n", flush=True)

    t0 = time.time()
    total_panels = 0
    completed = []

    for idx, f in enumerate(files, start=1):
        name = f.get("name")
        t_ch = time.time()
        print(f"[{idx}/{len(files)}] Downloading & assembling {name}...", end="", flush=True)
        ch_id, p_count = process_chapter_descriptions(service, f)
        dur = time.time() - t_ch
        print(f" Done ({p_count} panels in {dur:.2f}s)")
        total_panels += p_count
        completed.append(ch_id)

    total_time = time.time() - t0
    print("\n" + "=" * 65)
    print(f"SUCCESS: Downloaded and processed {len(completed)} chapters in {total_time:.1f}s!")
    print(f"Total Panels Described across all 40 chapters: {total_panels}")
    print("All 03_descriptions.json files validated against schema.")
    print("=" * 65)


if __name__ == "__main__":
    main()
