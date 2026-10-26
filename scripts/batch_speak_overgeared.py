"""Batch speech synthesis for Overgeared chapters (ch02 to ch30) using Fish Audio.

Free tier model: s2.1-pro-free
Voice ID: 802e3bc2b27e49c2995d23ef70e6ac89 (Energetic YouTube Recap Voice)
Concurrency: 4
"""

import sys
import time

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.core.schema import ScriptFile, TimelineFile, load_model
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts

sys.stdout.reconfigure(encoding="utf-8")


def main():
    cfg = load_config()

    start_ch = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    end_ch = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    print("=" * 65)
    print(f"BATCH FISH AUDIO SYNTHESIS: Overgeared ch{start_ch:02d} to ch{end_ch:02d}")
    print("Engine: Fish Audio (s2.1-pro-free | Voice: 802e3bc2 | Concurrency: 4)")
    print("=" * 65)

    t_all = time.time()
    completed = 0
    failed = []

    for i in range(start_ch, end_ch + 1):
        ch_id = f"overgeared/ch{i:02d}"
        paths = ChapterPaths.create(ch_id)

        if not paths.script_file.exists():
            print(f"[{i:02d}/{end_ch:02d}] {ch_id}: No script found ({paths.script_file}), skipping!")
            failed.append((ch_id, "No script found"))
            continue

        script = load_model(paths.script_file, ScriptFile)
        num_script_blocks = len(script.blocks)

        # Check if already synthesized and valid
        if paths.narration_file.exists() and paths.timeline_file.exists():
            try:
                timeline = load_model(paths.timeline_file, TimelineFile)
                if len(timeline.blocks) == num_script_blocks:
                    print(
                        f"[{i:02d}/{end_ch:02d}] {ch_id}: Already complete "
                        f"({timeline.duration:.1f}s, {len(timeline.blocks)} blocks, {len(timeline.words)} words)."
                    )
                    completed += 1
                    continue
                else:
                    print(
                        f"[{i:02d}/{end_ch:02d}] {ch_id}: Existing timeline has {len(timeline.blocks)} "
                        f"blocks vs script {num_script_blocks} blocks. Re-synthesizing..."
                    )
            except Exception:
                print(f"[{i:02d}/{end_ch:02d}] {ch_id}: Existing timeline corrupt. Re-synthesizing...")

        print(f"\n[{i:02d}/{end_ch:02d}] Synthesizing {ch_id} ({num_script_blocks} blocks)...")
        t0 = time.time()

        max_chapter_retries = 3
        success = False
        for attempt in range(1, max_chapter_retries + 1):
            try:
                timeline = run_fish_tts(paths, cfg, force=(attempt > 1))
                dur = timeline.duration
                num_blocks = len(timeline.blocks)
                num_words = len(timeline.words)
                elapsed = time.time() - t0
                print(
                    f"  -> SUCCESS in {elapsed:.1f}s: {dur:.1f}s audio ({dur/60:.2f} min), "
                    f"{num_blocks} blocks, {num_words} words"
                )
                completed += 1
                success = True
                break
            except Exception as exc:
                print(f"  -> Attempt {attempt}/{max_chapter_retries} failed: {exc}")
                if attempt < max_chapter_retries:
                    print("     Pausing 10s before retry...")
                    time.sleep(10.0)

        if not success:
            failed.append((ch_id, "Max retries exceeded"))

    elapsed_all = time.time() - t_all
    print("\n" + "=" * 65)
    print(f"BATCH SYNTHESIS FINISHED in {elapsed_all:.1f}s ({elapsed_all/60:.2f} min)!")
    print(f"Successfully synthesized: {completed}/{end_ch - start_ch + 1}")
    if failed:
        print(f"Failed chapters: {failed}")
    print("=" * 65)


if __name__ == "__main__":
    main()
