"""Batch synthesize narration voiceovers and timelines using Fish Audio API with multi-chapter parallelism."""

import argparse
import concurrent.futures
import time
from pathlib import Path

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts


def process_chapter(ch: str, cfg) -> tuple[str, bool, float, int, str]:
    paths = ChapterPaths(ch, Path("data/chapters"))
    t0 = time.time()
    try:
        timeline = run_fish_tts(paths, cfg, force=False)
        dur = time.time() - t0
        return (ch, True, timeline.duration, len(timeline.blocks), f"{dur:.1f}s")
    except Exception as exc:
        dur = time.time() - t0
        return (ch, False, 0.0, 0, str(exc))

def main():
    parser = argparse.ArgumentParser(description="Parallel Fish TTS Voice Synthesis")
    parser.add_argument("chapters", nargs="*", help="List of chapters to process")
    parser.add_argument("--parallel", type=int, default=2, help="Number of chapters to process simultaneously")
    args = parser.parse_args()

    cfg = load_config()

    if args.chapters:
        chapters = args.chapters
    else:
        chapters_dir = Path("data/chapters")
        all_chs = sorted([d.name for d in chapters_dir.iterdir() if d.is_dir() and d.name.startswith("ch")])
        chapters = [ch for ch in all_chs if not (chapters_dir / ch / "05_narration.wav").exists() and (chapters_dir / ch / "04_script.json").exists()]

    print(f"Total chapters to process in this run: {len(chapters)}")
    print(f"Parallel chapters: {args.parallel}")
    print(f"Chapters: {chapters}", flush=True)

    total_t0 = time.time()
    success_count = 0
    failed_chapters = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.parallel) as executor:
        future_to_ch = {executor.submit(process_chapter, ch, cfg): ch for ch in chapters}
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_ch):
            completed_count += 1
            ch, success, duration, blocks, msg = future.result()
            if success:
                success_count += 1
                print(f"[{completed_count}/{len(chapters)}] SUCCESS {ch}: {duration:.1f}s audio ({blocks} blocks) in {msg}", flush=True)
            else:
                failed_chapters.append((ch, msg))
                print(f"[{completed_count}/{len(chapters)}] FAILED {ch}: {msg}", flush=True)

    total_dur = time.time() - total_t0
    print(f"\n{'='*70}")
    print(f"BATCH FINISHED in {total_dur/60:.2f} minutes.")
    print(f"Success: {success_count}/{len(chapters)}")
    if failed_chapters:
        print(f"Failures ({len(failed_chapters)}): {failed_chapters}")
    print(f"{'='*70}", flush=True)

if __name__ == "__main__":
    main()
