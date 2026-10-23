"""Batch synthesis for chapters 1 through 30 using Fish Audio with 6 workers.

Iterates through all chapters from ch01 to ch030, loading the expressive 04_script_fish.json
and synthesizing blocks using 6 concurrent worker threads per chapter.
"""

from __future__ import annotations

import time

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts

CHAPTERS_1_TO_30 = [
    "ch01", "ch02", "ch003", "ch004", "ch005", "ch005_5", "ch06", "ch007", "ch008", "ch009",
    "ch010", "ch011", "ch012", "ch013", "ch014", "ch015", "ch016", "ch017", "ch018", "ch019",
    "ch020", "ch021", "ch022", "ch023", "ch024", "ch025", "ch026", "ch027", "ch028", "ch029", "ch030"
]


def main() -> None:
    config = load_config()
    start_total = time.time()
    successes = []
    failures = []

    print(f"Starting Fish TTS expressive synthesis for {len(CHAPTERS_1_TO_30)} chapters with 6 workers...\n")

    for idx, ch_name in enumerate(CHAPTERS_1_TO_30, start=1):
        print("============================================================")
        print(f"[{idx}/{len(CHAPTERS_1_TO_30)}] Processing chapter: {ch_name}")
        print("============================================================")

        paths = ChapterPaths.create(ch_name)
        if not paths.script_file.exists():
            print(f"Skipping {ch_name}: script file not found.")
            failures.append((ch_name, "Script not found"))
            continue

        try:
            t0 = time.time()
            timeline = run_fish_tts(paths, config, force=True)
            elapsed = time.time() - t0
            print(f"Successfully finished {ch_name} in {elapsed:.1f}s (audio: {timeline.duration:.1f}s, blocks: {len(timeline.blocks)})\n")
            successes.append(ch_name)
        except Exception as exc:
            print(f"ERROR processing {ch_name}: {exc}\n")
            failures.append((ch_name, str(exc)))

    total_elapsed = time.time() - start_total
    print("\n============================================================")
    print(f"BATCH SYNTHESIS COMPLETE in {total_elapsed / 60:.1f} minutes")
    print(f"Successful: {len(successes)} chapters")
    if failures:
        print(f"Failed: {len(failures)} chapters -> {failures}")
    print("============================================================")


if __name__ == "__main__":
    main()
