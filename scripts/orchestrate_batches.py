"""Multi-kernel parallel batch renderer.

Executes batches of up to 10 chapters concurrently across 2 Kaggle GPU kernels:
- Kernel 1: manga-recap-render (Runs Batch 1: ch004 - ch012)
- Kernel 2: manga-recap-render-2 (Runs Batch 2: ch013 - ch022)
When either kernel finishes, it immediately claims Batch 3 (ch023 - ch030).
"""

from __future__ import annotations

import concurrent.futures
import queue
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.config import Config, load_config  # noqa: E402
from scripts.run_batch_render import run_batch  # noqa: E402

BATCHES = [
    {
        "batch_id": "batch_1",
        "chapters": ["ch004", "ch005", "ch005_5", "ch06", "ch007", "ch008", "ch009", "ch010", "ch011", "ch012"],
    },
    {
        "batch_id": "batch_2",
        "chapters": ["ch013", "ch014", "ch015", "ch016", "ch017", "ch018", "ch019", "ch020", "ch021", "ch022"],
    },
    {
        "batch_id": "batch_3",
        "chapters": ["ch023", "ch024", "ch025", "ch026"],
    },
    {
        "batch_id": "batch_4",
        "chapters": ["ch027", "ch028", "ch029", "ch030"],
    },
]

BATCH_URLS = {
    "batch_1": "https://sendit.sh/1HWxo/Do5eu.zip",
    "batch_2": "https://sendit.sh/Bpqh8/5UZgH.zip",
    "batch_3": "https://sendit.sh/UNplX/Csd6k.zip",
    "batch_4": "https://sendit.sh/Ik5c9/1Myiz.zip",
}

AVAILABLE_KERNELS = ["manga-recap-render", "manga-recap-render-2"]


def worker_loop(
    kernel_slug: str,
    work_queue: queue.Queue,
    config: Config,
    results: list,
):
    """Worker thread dedicated to one Kaggle kernel."""
    while True:
        try:
            batch_info = work_queue.get_nowait()
        except queue.Empty:
            break

        batch_id = batch_info["batch_id"]
        chapters = batch_info["chapters"]

        # Check if all chapters in this batch are already rendered
        remaining = [c for c in chapters if not (Path(f"data/chapters/{c}/07_final.mp4")).exists()]
        if not remaining:
            print(f"[{kernel_slug}] Batch {batch_id} all chapters already rendered, skipping.", flush=True)
            results.append((batch_id, True, "All already rendered"))
            work_queue.task_done()
            continue

        print(f"\n>>> [{kernel_slug}] Assigned {batch_id} ({len(remaining)} chapters remaining) <<<", flush=True)
        try:
            payload_url = BATCH_URLS.get(batch_id)
            success = run_batch(batch_id, remaining, kernel_slug, config, payload_url=payload_url)
            results.append((batch_id, success, f"Rendered on {kernel_slug}"))
        except Exception as exc:  # noqa: BLE001
            print(f"[{kernel_slug}] [EXCEPTION] in {batch_id}: {exc}", flush=True)
            results.append((batch_id, False, str(exc)))
        finally:
            work_queue.task_done()


def main():
    start_time = time.time()
    config = load_config()

    print("============================================================", flush=True)
    print("STARTING DUAL-KERNEL 10-CHAPTER BATCH RENDERING PIPELINE", flush=True)
    print("Kernel 1: manga-recap-render", flush=True)
    print("Kernel 2: manga-recap-render-2", flush=True)
    print(f"Total batches to schedule: {len(BATCHES)}", flush=True)
    for b in BATCHES:
        print(f"  {b['batch_id']}: {len(b['chapters'])} chapters -> {b['chapters']}", flush=True)
    print("============================================================\n", flush=True)

    work_queue = queue.Queue()
    for b in BATCHES:
        work_queue.put(b)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(AVAILABLE_KERNELS)) as executor:
        futures = [
            executor.submit(worker_loop, slug, work_queue, config, results)
            for slug in AVAILABLE_KERNELS
        ]
        concurrent.futures.wait(futures)

    total_time = time.time() - start_time
    print("\n============================================================", flush=True)
    print(f"ALL 10-CHAPTER BATCH RENDERING FINISHED in {total_time / 60:.1f} minutes", flush=True)
    for batch_id, success, msg in results:
        status_str = "[OK]" if success else "[FAIL]"
        print(f"  {status_str} {batch_id}: {msg}", flush=True)
    print("============================================================", flush=True)


if __name__ == "__main__":
    main()
