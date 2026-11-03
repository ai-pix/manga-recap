"""Parallel Fish Audio Batch Voiceover Synthesizer for Omniscient Reader's Viewpoint (ORV).

Synthesizes chapters concurrently using Fish Audio API streams.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.config import Config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts
import yaml

with open(REPO_ROOT / "config" / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = Config(yaml.safe_load(f))


def synthesize_chapter(ch_num: int, force: bool = False):
    ch_name = f"orv_ch{ch_num:02d}"
    paths = ChapterPaths(ch_name, REPO_ROOT / "data" / "chapters")

    if not paths.script_file.exists():
        print(f"[{ch_name}] Script missing: {paths.script_file}", flush=True)
        return ch_name, False, "Script missing"

    if not force and paths.narration_file.exists() and paths.narration_file.stat().st_size > 1000 and paths.timeline_file.exists():
        if paths.script_file.stat().st_mtime < paths.narration_file.stat().st_mtime:
            print(f"[{ch_name}] Audio & timeline up-to-date with script, skipping.", flush=True)
            return ch_name, True, "Already up-to-date"

    t0 = time.time()
    print(f"[{ch_name}] >>> STARTING parallel synthesis via Fish Audio...", flush=True)
    try:
        timeline = run_fish_tts(paths, CONFIG, force=True)
        dur = timeline.duration
        elapsed = time.time() - t0
        print(f"[{ch_name}] <<< SUCCESS in {elapsed:.1f}s: {dur:.1f}s audio, {len(timeline.words)} words!", flush=True)
        return ch_name, True, f"Done {dur:.1f}s"
    except Exception as e:
        print(f"[{ch_name}] !!! ERROR: {e}", flush=True)
        return ch_name, False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Parallel Fish Audio Synthesis for ORV")
    parser.add_argument("--chapter", type=int, default=None, help="Single chapter number")
    parser.add_argument("--start", type=int, default=0, help="Start chapter number")
    parser.add_argument("--end", type=int, default=30, help="End chapter number")
    parser.add_argument("--workers", type=int, default=5, help="Concurrent chapter workers")
    parser.add_argument("--force", action="store_true", help="Force re-synthesis even if audio exists")
    args = parser.parse_args()

    if args.chapter is not None:
        chapters = [args.chapter]
    else:
        chapters = list(range(args.start, args.end + 1))

    print("=" * 65)
    print(f"FISH AUDIO BATCH SYNTHESIS FOR {len(chapters)} CHAPTERS: {chapters}")
    print(f"Workers: {args.workers} | Force: {args.force}")
    print("=" * 65, flush=True)

    t_start = time.time()
    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_ch = {executor.submit(synthesize_chapter, c, args.force): c for c in chapters}
        for future in concurrent.futures.as_completed(future_to_ch):
            c = future_to_ch[future]
            try:
                ch_name, success, msg = future.result()
                results[ch_name] = (success, msg)
            except Exception as exc:
                results[f"orv_ch{c:02d}"] = (False, str(exc))

    elapsed_total = time.time() - t_start
    success_count = sum(1 for ok, _ in results.values() if ok)
    print("=" * 65)
    print(f"SYNTHESIS FINISHED in {elapsed_total:.1f}s ({elapsed_total/60:.1f} min)")
    print(f"Completed: {success_count}/{len(chapters)}")
    for ch, (ok, msg) in sorted(results.items()):
        print(f"  {ch}: {'[OK]' if ok else '[FAIL]'} {msg}")
    print("=" * 65)


if __name__ == "__main__":
    main()
