"""Parallel Fish Audio Batch Voiceover Synthesizer for Tomb Raider King (Ch 02-30).

Dispatches concurrent chapter workers to synthesize voiceovers simultaneously across
multiple Fish Audio API streams, clearing all chapters in parallel with word-level timelines.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.config import Config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts
import yaml

with open(REPO_ROOT / "config" / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = Config(yaml.safe_load(f))

PROGRESS_FILE = REPO_ROOT / "scripts" / "batch_voiceover_progress.json"


def load_progress():
    if PROGRESS_FILE.exists():
        try:
            return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"completed": [], "failed": {}}


def save_progress(prog):
    PROGRESS_FILE.write_text(json.dumps(prog, indent=2), encoding="utf-8")


def synthesize_chapter(ch_num: int, force: bool = False):
    ch_name = f"series3_ch{ch_num:02d}"
    paths = ChapterPaths(ch_name, REPO_ROOT / "data" / "chapters")

    if not paths.script_file.exists():
        print(f"[{ch_name}] Script missing: {paths.script_file}", flush=True)
        return ch_name, False, "Script missing"

    if not force and paths.narration_file.exists() and paths.narration_file.stat().st_size > 1000 and paths.timeline_file.exists():
        print(f"[{ch_name}] Audio & timeline already exist, skipping.", flush=True)
        return ch_name, True, "Already exists"

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
    parser = argparse.ArgumentParser(description="Parallel Fish Audio Synthesis for Tomb Raider King")
    parser.add_argument("--force", action="store_true", help="Force re-synthesis of existing audio/timelines")
    parser.add_argument("--chapter", type=int, help="Single chapter number (e.g. 2)")
    parser.add_argument("--workers", type=int, default=6, help="Concurrent chapter workers")
    args = parser.parse_args()

    if args.chapter:
        ch_name, ok, msg = synthesize_chapter(args.chapter, force=args.force)
        print(f"Result for {ch_name}: {ok} ({msg})")
        return

    prog = load_progress() if not args.force else {"completed": [], "failed": {}}
    target_chapters = list(range(1, 31))
    remaining = [c for c in target_chapters if f"series3_ch{c:02d}" not in prog.get("completed", [])]

    print("=" * 70)
    print(f"PARALLEL FISH AUDIO SYNTHESIS FOR {len(remaining)} CHAPTERS: {remaining}")
    print(f"Workers: {args.workers} concurrent | Force: {args.force}")
    print("=" * 70, flush=True)

    if not remaining:
        print("All chapters already completed!")
        return

    max_workers = min(len(remaining), args.workers)
    t_start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ch = {executor.submit(synthesize_chapter, c, args.force): c for c in remaining}
        for future in concurrent.futures.as_completed(future_to_ch):
            ch_name, success, msg = future.result()
            if success:
                if ch_name not in prog["completed"]:
                    prog["completed"].append(ch_name)
                    save_progress(prog)
            else:
                prog["failed"][ch_name] = msg
                save_progress(prog)

    elapsed_total = time.time() - t_start
    print("=" * 70)
    print(f"PARALLEL SYNTHESIS FINISHED in {elapsed_total:.1f}s ({elapsed_total/60:.1f} min)")
    print(f"Total Completed: {len(prog['completed'])}/{len(target_chapters)}")
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
