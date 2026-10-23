"""Parallel video rendering across chapters using 2 Kaggle GPU kernels.

Spawns 2 concurrent workers:
- Worker 1 drives kernel: manga-recap-render
- Worker 2 drives kernel: manga-recap-render-2

Renders all remaining chapters (ch004 through ch030) simultaneously.
Skips chapters that already have 07_final.mp4.
"""

from __future__ import annotations

import concurrent.futures
import queue
import time
import traceback

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s5_render import run as run_render

# All chapters 1-30 in order
ALL_CHAPTERS = [
    "ch01", "ch02", "ch003", "ch004", "ch005", "ch005_5", "ch06", "ch007", "ch008", "ch009",
    "ch010", "ch011", "ch012", "ch013", "ch014", "ch015", "ch016", "ch017", "ch018", "ch019",
    "ch020", "ch021", "ch022", "ch023", "ch024", "ch025", "ch026", "ch027", "ch028", "ch029", "ch030"
]

KERNEL_SLUGS = [
    "manga-recap-render",
    "manga-recap-render-2"
]


def render_worker(
    worker_id: int,
    kernel_slug: str,
    ch_queue: queue.Queue[str],
    results: list[tuple[str, bool, str]],
) -> None:
    config = load_config()

    while True:
        try:
            ch_name = ch_queue.get_nowait()
        except queue.Empty:
            print(f"[Worker {worker_id} ({kernel_slug})] Queue empty. Worker exiting.", flush=True)
            break

        print(f"\n[Worker {worker_id} ({kernel_slug})] >>> Starting chapter: {ch_name}", flush=True)
        paths = ChapterPaths.create(ch_name)

        if not paths.timeline_file.exists() or not paths.narration_file.exists():
            print(f"[Worker {worker_id} ({kernel_slug})] [SKIP] Missing narration or timeline for {ch_name}", flush=True)
            results.append((ch_name, False, "Missing narration or timeline"))
            ch_queue.task_done()
            continue

        t0 = time.time()
        try:
            manifest = run_render(paths, config, force=True, kernel_slug=kernel_slug)
            elapsed = time.time() - t0
            print(
                f"[Worker {worker_id} ({kernel_slug})] [OK] Completed {ch_name} in {elapsed / 60:.1f}m "
                f"(duration: {manifest.duration:.1f}s, clips: {manifest.clip_count})",
                flush=True,
            )
            results.append((ch_name, True, f"{elapsed / 60:.1f}m"))
        except Exception as exc:
            elapsed = time.time() - t0
            print(
                f"[Worker {worker_id} ({kernel_slug})] [FAIL] Failed {ch_name} after {elapsed / 60:.1f}m: {exc}",
                flush=True,
            )
            traceback.print_exc()
            results.append((ch_name, False, str(exc)))
        finally:
            ch_queue.task_done()


def main() -> None:
    # Filter only chapters that still need rendering
    needed = []
    already_done = []
    for ch in ALL_CHAPTERS:
        paths = ChapterPaths.create(ch)
        if paths.final_file.exists():
            already_done.append(ch)
        else:
            needed.append(ch)

    print("============================================================", flush=True)
    print(f"PARALLEL KAGGLE RENDER: {len(needed)} chapters to render across 2 kernels", flush=True)
    print(f"Already completed: {len(already_done)} chapters ({', '.join(already_done)})", flush=True)
    print(f"Kernel 1: {KERNEL_SLUGS[0]}", flush=True)
    print(f"Kernel 2: {KERNEL_SLUGS[1]}", flush=True)
    print("============================================================\n", flush=True)

    if not needed:
        print("All chapters already have 07_final.mp4! Nothing to render.", flush=True)
        return

    ch_queue: queue.Queue[str] = queue.Queue()
    for ch in needed:
        ch_queue.put(ch)

    results: list[tuple[str, bool, str]] = []
    start_time = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(render_worker, 1, KERNEL_SLUGS[0], ch_queue, results)
        f2 = executor.submit(render_worker, 2, KERNEL_SLUGS[1], ch_queue, results)

        for f in (f1, f2):
            if f.exception():
                print(f"[ERROR] Worker thread crashed with: {f.exception()}", flush=True)

    total_time = time.time() - start_time
    print("\n============================================================", flush=True)
    print(f"ALL PARALLEL RENDERS FINISHED in {total_time / 60:.1f} minutes", flush=True)
    successes = [r for r in results if r[1]]
    failures = [r for r in results if not r[1]]
    print(f"Newly Rendered: {len(successes)} / {len(needed)}", flush=True)
    print(f"Total Video Library: {len(already_done) + len(successes)} / {len(ALL_CHAPTERS)} complete", flush=True)
    if failures:
        print(f"Failures: {len(failures)} -> {failures}", flush=True)
    print("============================================================", flush=True)


if __name__ == "__main__":
    main()
