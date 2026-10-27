"""Batch panel extractor for Hakuniku manhwa series.

Extracts panels chapter-wise using vertical continuous-scroll gutter detection.
Handles Unicode file paths on Windows via open() + cv2.imdecode / cv2.imencode.
Tracks progress and updates Google Sheet 'To do' tab status as each series completes.
"""

import sys
import os
import re
import time
import json
from pathlib import Path
import numpy as np
import cv2
import requests

# Base output path
PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels")

# Google Sheets Configuration
SHEET_ID = "1sHI3qIU9y6Aiznfo9_d8Ari8Bu0WWqW6UHzNhsSnfxA"
SECRET_PATH = Path(r"C:\Users\ravih\Downloads\client_secret_532039068995-k60ntg8pgpnr1nn04asb31r8q9uisp78.apps.googleusercontent.com.json")
TOKENS_PATH = Path(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json")

SERIES_CONFIG = [
    {
        "name": "Omniscient Reader's Viewpoint",
        "input_dir": Path(r"D:\Python Projects\Hakuniku\cli\downloads\Asura\Omniscient Reader’s Viewpoint"),
        "sheet_row": 3,
        "expected_chapters": 31
    },
    {
        "name": "Second Life Ranker",
        "input_dir": Path(r"D:\Python Projects\Hakuniku\cli\downloads\Comix\Second Life Ranker"),
        "sheet_row": 4,
        "expected_chapters": 30
    },
    {
        "name": "The Tutorial Is Too Hard",
        "input_dir": Path(r"D:\Python Projects\Hakuniku\cli\downloads\The Tutorial is Too Hard"),
        "sheet_row": 5,
        "expected_chapters": 30
    },
    {
        "name": "Kill the Hero",
        "input_dir": Path(r"D:\Python Projects\Hakuniku\cli\downloads\Comix\Kill the Hero"),
        "sheet_row": 6,
        "expected_chapters": 30
    },
    {
        "name": "Return of the Disaster-Class Hero",
        "input_dir": Path(r"D:\Python Projects\Hakuniku\cli\downloads\Asura\Return of the Disaster-Class Hero"),
        "sheet_row": 7,
        "expected_chapters": 30
    }
]

def update_sheet_status(row_idx: int, status: str):
    try:
        with open(SECRET_PATH) as f:
            secret_data = json.load(f)["installed"]
        with open(TOKENS_PATH) as f:
            token_data = json.load(f)
        refresh_token = token_data["accounts"]["default"]["refreshToken"]
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": secret_data["client_id"],
            "client_secret": secret_data["client_secret"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }, timeout=15)
        token = resp.json()["access_token"]

        url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'To do'!C{row_idx}?valueInputOption=USER_ENTERED"
        requests.put(url, headers={"Authorization": f"Bearer {token}"}, json={"values": [[status]]}, timeout=15)
        print(f"[Sheet] Updated 'To do'!C{row_idx} -> {status}", flush=True)
    except Exception as e:
        print(f"[Sheet Warning] Failed to update row {row_idx}: {e}", flush=True)

def safe_imread(path: Path):
    try:
        with open(path, "rb") as f:
            buf = np.frombuffer(f.read(), np.uint8)
            return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def safe_imwrite(path: Path, img: np.ndarray):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        ok, buf = cv2.imencode(".png", img)
        if ok:
            with open(path, "wb") as f:
                f.write(buf.tobytes())
            return True
        return False
    except Exception as e:
        print(f"Error writing {path}: {e}")
        return False

def natural_sort_key(s: str):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

def detect_gutters(img_gray: np.ndarray, std_thresh=6.5, min_gutter_h=20, merge_gap=15):
    h, w = img_gray.shape
    row_stds = np.std(img_gray, axis=1)
    is_solid = row_stds < std_thresh

    gutters = []
    in_gutter = False
    start_y = 0
    for y in range(h):
        if is_solid[y] and not in_gutter:
            in_gutter = True
            start_y = y
        elif not is_solid[y] and in_gutter:
            in_gutter = False
            if (y - start_y) >= min_gutter_h:
                gutters.append((start_y, y))
    if in_gutter and (h - start_y) >= min_gutter_h:
        gutters.append((start_y, h))

    # Merge close gutters
    merged = []
    for g in gutters:
        if not merged:
            merged.append(g)
        else:
            prev_s, prev_e = merged[-1]
            if g[0] - prev_e <= merge_gap:
                merged[-1] = (prev_s, g[1])
            else:
                merged.append(g)
    return merged

def extract_chapter_panels(ch_dir: Path, out_ch_dir: Path, min_panel_h=50):
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    image_files = []
    for ext in extensions:
        image_files.extend(ch_dir.glob(ext))
    image_files.sort(key=lambda p: natural_sort_key(p.name))

    if not image_files:
        return 0, 0

    panel_idx = 1
    # Process images in order. Manhwa strips are vertical slices.
    for img_p in image_files:
        img = safe_imread(img_p)
        if img is None:
            continue
        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gutters = detect_gutters(gray)

        # Slice content segments
        segments = []
        cur_y = 0
        for gs, ge in gutters:
            if gs - cur_y >= min_panel_h:
                segments.append((cur_y, gs))
            cur_y = ge
        if h - cur_y >= min_panel_h:
            segments.append((cur_y, h))

        if not segments:
            # If no gutters found, treat the whole slice as a panel if height is reasonable
            segments = [(0, h)]

        for sy, ey in segments:
            seg_img = img[sy:ey, :]
            # Filter out completely blank or uniform non-content slivers
            if np.std(seg_img) < 5.0 and (ey - sy) < 100:
                continue
            out_name = f"panel_{panel_idx:04d}.png"
            safe_imwrite(out_ch_dir / out_name, seg_img)
            panel_idx += 1

    return len(image_files), panel_idx - 1

def process_series(config: dict):
    name = config["name"]
    input_dir = config["input_dir"]
    sheet_row = config["sheet_row"]
    out_dir = PANELS_ROOT / name
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=======================================================", flush=True)
    print(f"Starting series: {name}", flush=True)
    print(f"Source: {input_dir}", flush=True)
    print(f"Destination: {out_dir}", flush=True)
    print(f"=======================================================", flush=True)

    update_sheet_status(sheet_row, "In progress")

    ch_dirs = [d for d in input_dir.iterdir() if d.is_dir()]
    ch_dirs.sort(key=lambda d: natural_sort_key(d.name))

    start_time = time.time()
    total_panels = 0
    total_images = 0
    chapter_stats = []

    for i, ch_dir in enumerate(ch_dirs, 1):
        out_ch_dir = out_dir / ch_dir.name
        t0 = time.time()
        num_imgs, num_panels = extract_chapter_panels(ch_dir, out_ch_dir)
        dt = time.time() - t0
        total_images += num_imgs
        total_panels += num_panels
        chapter_stats.append({
            "chapter": ch_dir.name,
            "images": num_imgs,
            "panels": num_panels,
            "time_sec": round(dt, 2)
        })
        print(f"[{i}/{len(ch_dirs)}] {name} - {ch_dir.name}: {num_imgs} imgs -> {num_panels} panels ({dt:.1f}s)", flush=True)

    total_time = round(time.time() - start_time, 2)
    summary = {
        "series": name,
        "total_chapters": len(ch_dirs),
        "total_source_images": total_images,
        "total_extracted_panels": total_panels,
        "total_time_seconds": total_time,
        "chapters": chapter_stats
    }
    (out_dir / "extraction_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Completed {name}: {total_panels} panels from {total_images} images across {len(ch_dirs)} chapters in {total_time}s", flush=True)

    update_sheet_status(sheet_row, "Done")
    return summary

def main():
    target_idx = None
    if len(sys.argv) > 1:
        target_idx = int(sys.argv[1])

    if target_idx is not None:
        configs = [SERIES_CONFIG[target_idx]]
    else:
        configs = SERIES_CONFIG

    for cfg in configs:
        process_series(cfg)

if __name__ == "__main__":
    main()
