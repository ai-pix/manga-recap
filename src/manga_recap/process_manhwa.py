"""Fast, studio-grade Manhwa/Webtoon panel processor.

Handles continuous vertical-scroll manhwa chapters by:
1. Identifying seamless gutter boundaries across multiple slices (white and black gutters).
2. Slicing clean, 100% native resolution panels without cutting speech bubbles or action art.
3. Running DirectML GPU text and speech-bubble detection to generate high-res text crops in `_text/`.
4. Generating schema-compliant `panel_index.json` (`PanelIndexFile`).
5. Storing panels cleanly into dedicated per-manhwa directories:
   `data/chapters/<series_slug>/ch<num:02d>/02_panels/`
   with optional flat junctions for pipeline compatibility.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from manga_recap.core.schema import BBox, PanelIndex, PanelIndexFile, save_model

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_detector_session():
    try:
        import onnxruntime as ort

        model_path = REPO_ROOT / "models" / "detector.onnx"
        if not model_path.exists():
            return None
        providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
        return ort.InferenceSession(str(model_path), providers=providers)
    except Exception as e:
        print(f"Warning: Could not load ONNX detector: {e}")
        return None


def detect_bubbles_in_panel(sess, panel_img: Image.Image, conf_threshold: float = 0.35):
    """Run DirectML GPU inference on a single panel to find speech bubbles & text."""
    if sess is None:
        return []

    orig_w, orig_h = panel_img.size
    im_resized = panel_img.resize((640, 640), Image.BILINEAR)
    arr = np.array(im_resized, dtype=np.float32) / 255.0
    arr = np.transpose(arr, (2, 0, 1))
    arr = np.expand_dims(arr, 0)
    orig_sizes = np.array([[orig_h, orig_w]], dtype=np.int64)

    outputs = sess.run(None, {"images": arr, "orig_target_sizes": orig_sizes})
    labels, boxes, scores = outputs[0][0], outputs[1][0], outputs[2][0]

    detections = []
    # boxes format from model: [ymin, xmin, ymax, xmax]
    for lbl, box, score in zip(labels, boxes, scores, strict=False):
        if score >= conf_threshold:
            ymin, xmin, ymax, xmax = [float(coord) for coord in box]
            detections.append({
                "label": int(lbl),
                "score": float(score),
                "box": (int(round(xmin)), int(round(ymin)), int(round(xmax)), int(round(ymax))),  # (x1, y1, x2, y2)
            })
    return detections


def process_chapter(
    chapter_source_dir: Path,
    chapter_target_id: str,
    output_base: Path,
    sess=None,
    extract_text_crops: bool = True,
    padding: int = 14,
    min_panel_height: int = 120,
    force: bool = False,
) -> int:
    """Process a single manhwa chapter directory into clean panels."""
    files = sorted(
        glob.glob(os.path.join(str(chapter_source_dir), "*.jpg"))
        + glob.glob(os.path.join(str(chapter_source_dir), "*.png"))
    )
    if not files:
        safe_path = str(chapter_source_dir).encode("ascii", "replace").decode("ascii")
        print(f"No image files found in {safe_path}")
        return 0

    chapter_root = output_base / chapter_target_id
    panels_dir = chapter_root / "02_panels"
    text_dir = panels_dir / "_text"
    index_file = panels_dir / "panel_index.json"

    if not force and index_file.exists() and any(panels_dir.glob("panel_*.jpg")):
        print(f"[{chapter_target_id}] Already processed ({index_file.name} exists). Skipping.")
        try:
            from manga_recap.core.schema import load_model

            existing_idx = load_model(index_file, PanelIndexFile)
            return existing_idx.panel_count
        except Exception:
            pass

    panels_dir.mkdir(parents=True, exist_ok=True)
    if extract_text_crops:
        text_dir.mkdir(parents=True, exist_ok=True)

    # 1. Calculate slice offsets & detect gutters across the continuous strip
    slice_offsets = [0]
    is_gutter_list = []
    total_height = 0
    max_w = 0

    for f in files:
        with Image.open(f) as im:
            max_w = max(max_w, im.width)
            total_height += im.height
            slice_offsets.append(total_height)
            arr = np.asarray(im)
            std_row = np.std(arr, axis=(1, 2))
            mean_row = np.mean(arr, axis=(1, 2))
            # Gutter = uniform white (>235) or uniform black (<25)
            is_g = (std_row < 6.0) & ((mean_row > 235) | (mean_row < 25))
            is_gutter_list.append(is_g)

    full_gutter = np.concatenate(is_gutter_list)

    # 2. Extract panel boundaries from non-gutter segments
    blocks = []
    in_block = False
    sy = 0
    for y in range(len(full_gutter)):
        if not full_gutter[y]:
            if not in_block:
                in_block = True
                sy = y
        else:
            if in_block:
                in_block = False
                if y - sy >= min_panel_height:
                    blocks.append((sy, y))
    if in_block and len(full_gutter) - sy >= min_panel_height:
        blocks.append((sy, len(full_gutter)))

    print(
        f"[{chapter_target_id}] Found {len(blocks)} panels across {len(files)} slices ({total_height}px total height)...",
        flush=True,
    )

    # Helper to crop a global y-range [gy1, gy2]
    def crop_global_range(gy1, gy2):
        gy1 = max(0, gy1 - padding)
        gy2 = min(total_height, gy2 + padding)
        h = gy2 - gy1
        target_im = Image.new("RGB", (max_w, h), (255, 255, 255))

        cur_paste_y = 0
        for idx, f in enumerate(files):
            s_start = slice_offsets[idx]
            s_end = slice_offsets[idx + 1]
            if max(gy1, s_start) < min(gy2, s_end):
                overlap_start = max(gy1, s_start)
                overlap_end = min(gy2, s_end)
                local_y1 = overlap_start - s_start
                local_y2 = overlap_end - s_start
                with Image.open(f) as im:
                    slice_crop = im.crop((0, local_y1, im.width, local_y2))
                    target_im.paste(slice_crop, (0, cur_paste_y))
                cur_paste_y += overlap_end - overlap_start
        return target_im

    # 3. Save each panel, run bubble detection, build index
    panel_entries: list[PanelIndex] = []

    for idx, (gy1, gy2) in enumerate(blocks, start=1):
        panel_num_str = f"panel_{idx:04d}"
        panel_path = panels_dir / f"{panel_num_str}.jpg"
        panel_img = crop_global_range(gy1, gy2)
        panel_img.save(panel_path, quality=95)

        text_boxes_coords: list[tuple[int, int, int, int]] = []

        # Detect speech bubbles if detector session is available
        if sess is not None and extract_text_crops:
            detections = detect_bubbles_in_panel(sess, panel_img)
            valid_boxes = [d["box"] for d in detections if d["label"] in (0, 1)]  # bubble or text_bubble
            if valid_boxes:
                for b_idx, (bx1, by1, bx2, by2) in enumerate(valid_boxes):
                    bx1, by1 = max(0, bx1), max(0, by1)
                    bx2, by2 = min(panel_img.width, bx2), min(panel_img.height, by2)
                    if bx2 > bx1 and by2 > by1:
                        text_crop = panel_img.crop((bx1, by1, bx2, by2))
                        crop_name = (
                            f"{panel_num_str}_text_{b_idx:02d}.png"
                            if len(valid_boxes) > 1
                            else f"{panel_num_str}_text.png"
                        )
                        text_crop.save(text_dir / crop_name)
                        text_boxes_coords.append((bx1, by1, bx2, by2))

        panel_entries.append(
            PanelIndex(
                panel_id=panel_num_str,
                page_number=1,
                index_on_page=idx,
                reading_order=idx,
                bbox=BBox(x1=0, y1=0, x2=panel_img.width, y2=panel_img.height),
                image_path=f"02_panels/{panel_num_str}.jpg",
                source="yolo",
                page_width=panel_img.width,
                page_height=panel_img.height,
                text_boxes=[
                    BBox(x1=b[0], y1=b[1], x2=b[2], y2=b[3]) for b in text_boxes_coords
                ],
                text_image_path=(
                    f"02_panels/_text/{panel_num_str}_text.png"
                    if text_boxes_coords
                    else ""
                ),
                nested_in="",
            )
        )

    # 4. Save PanelIndexFile
    idx_doc = PanelIndexFile(
        chapter_id=chapter_target_id,
        page_count=1,
        panel_count=len(panel_entries),
        created_at=datetime.now(timezone.utc).isoformat(),
        panels=panel_entries,
    )
    save_model(idx_doc, index_file)
    return len(blocks)


def create_junction(source_target: Path, junction_link: Path) -> None:
    """Create a Windows directory junction if it doesn't already exist."""
    if junction_link.exists():
        return
    junction_link.parent.mkdir(parents=True, exist_ok=True)
    try:
        cmd = f'cmd /c mklink /J "{junction_link}" "{source_target}"'
        subprocess.run(cmd, shell=True, check=True, capture_output=True)
    except Exception as e:
        print(f"Note: Could not create junction {junction_link.name}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Process manhwa chapters into high-resolution, organized panels"
    )
    parser.add_argument(
        "--source",
        default=r"C:\Users\ravih\OneDrive\Pictures\Cocomic\SSS-Class Revival Hunter (Official)",
        help="Path to manhwa raw chapter folders",
    )
    parser.add_argument(
        "--series",
        default="sss-class-revival-hunter",
        help="Series slug/folder name under data/chapters",
    )
    parser.add_argument(
        "--alias",
        default="revival_hunter",
        help="Flat prefix alias for chapters (e.g. revival_hunter_ch01)",
    )
    parser.add_argument(
        "--output",
        default="data/chapters",
        help="Base output chapters directory",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=1,
        help="Start chapter number (default 1)",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=40,
        help="Number of chapters to process (default 40)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-processing of already processed chapters",
    )
    args = parser.parse_args()

    source_dir = Path(args.source)
    output_base = Path(args.output)
    series_slug = args.series
    alias_prefix = args.alias
    start_num = args.start
    count = args.count

    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    # Map available directories by chapter number
    ch_dirs = {}
    for d in os.listdir(source_dir):
        full_p = source_dir / d
        if full_p.is_dir():
            m = re.match(r"Chapter\s*(\d+)", d, re.IGNORECASE)
            if m:
                num = int(m.group(1))
                ch_dirs[num] = d

    # Select target chapters
    end_num = start_num + count - 1
    target_nums = [n for n in range(start_num, end_num + 1) if n in ch_dirs]

    print("=======================================================")
    print(f"MANHWA PANEL PROCESSOR: {series_slug}")
    print(f"Source: {source_dir}")
    print(f"Chapters to process: {len(target_nums)} (Ch {start_num:02d} to Ch {end_num:02d})")
    print(f"Output series dir: {output_base / series_slug}")
    print("=======================================================")

    sess = get_detector_session()
    if sess:
        print("DirectML ONNX Detector loaded successfully on GPU!\n")

    t0 = time.time()
    total_panels = 0

    for idx, num in enumerate(target_nums, start=1):
        ch_folder_name = ch_dirs[num]
        ch_source_path = source_dir / ch_folder_name
        rel_target_id = f"{series_slug}/ch{num:02d}"

        t_ch = time.time()
        safe_folder_name = ch_folder_name.encode("ascii", "replace").decode("ascii")
        print(f"[{idx}/{len(target_nums)}] Processing {safe_folder_name} -> {rel_target_id}...", flush=True)

        n_panels = process_chapter(
            chapter_source_dir=ch_source_path,
            chapter_target_id=rel_target_id,
            output_base=output_base,
            sess=sess,
            force=args.force,
        )
        total_panels += n_panels
        dur = time.time() - t_ch
        print(f"[{idx}/{len(target_nums)}] Finished {rel_target_id}: {n_panels} panels ({dur:.1f}s)", flush=True)

        # Create flat junction for legacy compatibility if alias provided
        if alias_prefix:
            canonical_path = output_base / series_slug / f"ch{num:02d}"
            junction_path = output_base / f"{alias_prefix}_ch{num:02d}"
            create_junction(canonical_path.resolve(), junction_path.resolve())

    total_time = time.time() - t0
    print("\n=======================================================")
    print(f"COMPLETED: Processed {len(target_nums)} chapters in {total_time:.1f}s ({total_time/60:.1f} min)")
    print(f"Total High-Resolution Panels Created: {total_panels}")
    print(f"Organized in: {(output_base / series_slug).resolve()}")
    print("=======================================================")


if __name__ == "__main__":
    main()
