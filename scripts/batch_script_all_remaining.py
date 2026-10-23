"""Master batch runner for generating scripts across all remaining chapters (Ch 51 to 112)."""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate
from scripts.chapter_script_builder import build_chapter_script

BATCHES = [
    ("Batch 2", ["ch051", "ch052", "ch053", "ch054", "ch055", "ch056", "ch057", "ch058", "ch058_5", "ch059", "ch060"]),
    ("Batch 3", ["ch061", "ch062", "ch063", "ch064", "ch065", "ch066", "ch067", "ch068", "ch069", "ch070"]),
    ("Batch 4", ["ch071", "ch072", "ch073", "ch074", "ch075", "ch076", "ch077", "ch078", "ch079", "ch080"]),
    ("Batch 5", ["ch081", "ch082", "ch083", "ch084", "ch085", "ch086", "ch087", "ch088", "ch089", "ch090"]),
    ("Batch 6", ["ch091", "ch092", "ch093", "ch094", "ch095", "ch096", "ch097", "ch098", "ch099", "ch100"]),
    ("Batch 7", ["ch101", "ch102", "ch103", "ch103_5", "ch104", "ch105", "ch106", "ch107", "ch108", "ch109", "ch110", "ch111", "ch112"]),
]


def validate_chapter(ch_id: str, cfg):
    data_dir = Path("data/chapters")
    d_path = data_dir / ch_id / "03_descriptions.json"
    s_path = data_dir / ch_id / "04_script.json"
    if not s_path.exists():
        return False, 0, 0, ["Missing 04_script.json"]
    try:
        d = load_model(d_path, DescriptionFile)
        s = load_model(s_path, ScriptFile)
        rep = validate(s, d, cfg)
        return rep.ok, len(d.panels), s.total_words, rep.problems
    except Exception as e:
        return False, 0, 0, [str(e)]


def process_chapter(ch_id: str) -> tuple[str, bool, float]:
    t0 = time.time()
    try:
        ok = build_chapter_script(ch_id)
        elapsed = time.time() - t0
        return ch_id, ok, elapsed
    except Exception as e:
        elapsed = time.time() - t0
        print(f"[{ch_id}] Critical failure: {e}", flush=True)
        return ch_id, False, elapsed


def main():
    cfg = load_config()
    total_start = time.time()
    total_chapters = sum(len(ch_list) for _, ch_list in BATCHES)
    completed_so_far = 0

    print(f"Starting Script Generation across {len(BATCHES)} batches ({total_chapters} chapters total)...", flush=True)

    all_results = {}

    for batch_name, chapters in BATCHES:
        batch_start = time.time()
        print(f"\n{'='*70}", flush=True)
        print(f"STARTING {batch_name.upper()} ({len(chapters)} chapters): {', '.join(chapters)}", flush=True)
        print(f"{'='*70}\n", flush=True)

        batch_results = {}
        # Run 2 chapters concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_to_ch = {executor.submit(process_chapter, ch): ch for ch in chapters}
            for future in as_completed(future_to_ch):
                ch_id, ok, elapsed = future.result()
                batch_results[ch_id] = (ok, elapsed)
                completed_so_far += 1
                print(f"[{completed_so_far}/{total_chapters}] {ch_id} done in {elapsed:.1f}s (ok={ok})", flush=True)

        # Validate all chapters in this batch
        print(f"\n--- {batch_name} Validation Table ---", flush=True)
        print(f"{'Chapter':<10} | {'Panels':<8} | {'Words':<8} | {'Valid':<6} | {'Problems'}", flush=True)
        print("-" * 55, flush=True)
        for ch in chapters:
            ok, p_count, w_count, probs = validate_chapter(ch, cfg)
            all_results[ch] = ok
            p_str = str(len(probs)) if not ok else "0"
            print(f"{ch:<10} | {p_count:<8} | {w_count:<8} | {str(ok):<6} | {p_str}", flush=True)
            if probs:
                for p in probs[:3]:
                    print(f"   ERROR: {p}", flush=True)

        batch_elapsed = time.time() - batch_start
        print(f"\n{batch_name} completed in {batch_elapsed:.1f}s ({batch_elapsed/60:.2f}m)\n", flush=True)

    total_elapsed = time.time() - total_start
    success_count = sum(1 for ok in all_results.values() if ok)
    print(f"\n{'='*70}", flush=True)
    print(f"ALL BATCHES COMPLETE in {total_elapsed:.1f}s ({total_elapsed/60:.2f}m)")
    print(f"Total Success: {success_count}/{len(all_results)}")
    print(f"{'='*70}\n", flush=True)


if __name__ == "__main__":
    main()
