"""Batch runner for Batch 1 scripts (ch042 to ch050)."""

import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.chapter_script_builder import build_chapter_script

BATCH_1 = [
    "ch042",
    "ch043",
    "ch044",
    "ch045",
    "ch046",
    "ch047",
    "ch048",
    "ch049",
    "ch050",
]


def main():
    print(f"Starting Batch 1 Script Generation ({len(BATCH_1)} chapters)...", flush=True)
    start_total = time.time()
    results = {}

    for idx, ch in enumerate(BATCH_1, start=1):
        print(f"\n[{idx}/{len(BATCH_1)}] Processing {ch}...", flush=True)
        t0 = time.time()
        ok = build_chapter_script(ch)
        elapsed = time.time() - t0
        results[ch] = (ok, elapsed)
        print(f"[{ch}] Finished in {elapsed:.1f}s - Success: {ok}", flush=True)

    print(f"\n{'=' * 60}", flush=True)
    print(f"Batch 1 Complete in {time.time() - start_total:.1f}s", flush=True)
    for ch, (ok, el) in results.items():
        status = "OK" if ok else "FAILED"
        print(f"  {ch}: {status} ({el:.1f}s)", flush=True)
    print(f"{'=' * 60}\n", flush=True)


if __name__ == "__main__":
    main()
