"""Batch compress panels from Chapter 30 to final chapter and package into a ZIP archive.

- Target chapters: ch030 to ch112
- Downscaling: Max dimension 1024px (OpenCV INTER_AREA for high-fidelity decimation)
- Output format: JPEG quality 88
- Original files: Completely untouched
- Archive: data/panels_ch030_ch112_optimized.zip
"""

import concurrent.futures
import glob
import os
import sys
import time
import zipfile

import cv2

MAX_DIM = 1024
JPEG_QUALITY = 88
OUTPUT_ZIP = "data/panels_ch030_ch112_optimized.zip"
CHAPTERS_DIR = "data/chapters"


def get_target_chapters():
    dirs = sorted([d for d in os.listdir(CHAPTERS_DIR) if os.path.isdir(os.path.join(CHAPTERS_DIR, d)) and d.startswith("ch")])
    target = []
    for d in dirs:
        num_str = d[2:].split("_")[0]
        try:
            if int(num_str) >= 30:
                target.append(d)
        except ValueError:
            pass
    return sorted(target)


def process_panel(item):
    chapter, panel_path = item
    try:
        img = cv2.imread(panel_path)
        if img is None:
            return None
        h, w = img.shape[:2]
        if max(h, w) > MAX_DIM:
            scale = MAX_DIM / max(h, w)
            new_w, new_h = int(round(w * scale)), int(round(h * scale))
            resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            resized = img

        _, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
        panel_id = os.path.splitext(os.path.basename(panel_path))[0]
        arcname = f"{chapter}/{panel_id}.jpg"
        return arcname, buf.tobytes()
    except Exception as e:
        print(f"Error processing {panel_path}: {e}", file=sys.stderr)
        return None


def main():
    target_chapters = get_target_chapters()
    print(f"Target chapters ({len(target_chapters)}): {target_chapters[0]} to {target_chapters[-1]}")

    all_items = []
    for ch in target_chapters:
        panels = sorted(glob.glob(f"{CHAPTERS_DIR}/{ch}/02_panels/panel_*.png"))
        panels = [p for p in panels if "_text" not in p and "_debug" not in p]
        for p in panels:
            all_items.append((ch, p))

    total_count = len(all_items)
    print(f"Total panels to process: {total_count}")

    os.makedirs(os.path.dirname(OUTPUT_ZIP), exist_ok=True)
    if os.path.exists(OUTPUT_ZIP):
        os.remove(OUTPUT_ZIP)

    t0 = time.time()
    processed_count = 0

    num_workers = min(os.cpu_count() or 4, 8)
    print(f"Processing with {num_workers} parallel workers...")

    # Process in batches to balance memory and streaming speed into zip
    chunk_size = 200
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_STORED) as zf:
        with concurrent.futures.ProcessPoolExecutor(max_workers=num_workers) as executor:
            for i in range(0, total_count, chunk_size):
                chunk = all_items[i : i + chunk_size]
                results = executor.map(process_panel, chunk)
                for res in results:
                    if res is not None:
                        arcname, data = res
                        zf.writestr(arcname, data)
                        processed_count += 1

                elapsed = time.time() - t0
                speed = processed_count / max(elapsed, 0.001)
                percent = (processed_count / total_count) * 100
                print(
                    f"\r[{percent:5.1f}%] Processed {processed_count}/{total_count} panels ({speed:.1f} panels/s)",
                    end="",
                    flush=True,
                )

    total_time = time.time() - t0
    final_sz_mb = os.path.getsize(OUTPUT_ZIP) / (1024 * 1024)
    print(f"\n\nSUCCESS! Created {OUTPUT_ZIP}")
    print(f"Total panels archived: {processed_count}")
    print(f"Total time elapsed:    {total_time:.2f}s ({processed_count / total_time:.1f} panels/s)")
    print(f"Final archive size:    {final_sz_mb:.2f} MB")


if __name__ == "__main__":
    main()
