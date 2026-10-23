"""Batch voice generation for Chapters 1-30 using Fish Audio s2.1-pro-free."""

import time
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts

chapters = [
    'ch01', 'ch02', 'ch003', 'ch004', 'ch005', 'ch005_5', 'ch06', 'ch007',
    'ch008', 'ch009', 'ch010', 'ch011', 'ch012', 'ch013', 'ch014', 'ch015',
    'ch016', 'ch017', 'ch018', 'ch019', 'ch020', 'ch021', 'ch022', 'ch023',
    'ch024', 'ch025', 'ch026', 'ch027', 'ch028', 'ch029', 'ch030'
]

config = load_config()
root_dir = Path("data/chapters")

print(f"==================================================", flush=True)
print(f"Batch Voice Generation: {len(chapters)} Chapters", flush=True)
print(f"Model: {config.get('tts.fish_model')}", flush=True)
print(f"Voice: {config.get('tts.fish_voice_id')} (Voice #4 - Energetic YouTube Recap)", flush=True)
print(f"==================================================", flush=True)

t_start_all = time.time()

for idx, ch in enumerate(chapters, start=1):
    paths = ChapterPaths.create(ch, root_dir)
    print(f"\n[{idx}/{len(chapters)}] Checking {ch}...", flush=True)
    t0 = time.time()
    
    try:
        timeline = run_fish_tts(paths, config, force=False)
        duration_sec = time.time() - t0
        print(f"SUCCESS: {ch} -> {timeline.duration:.1f}s audio in {duration_sec:.1f}s ({len(timeline.blocks)} blocks)", flush=True)
    except Exception as exc:
        print(f"ERROR on {ch}: {exc}", flush=True)
        time.sleep(3)

total_elapsed = time.time() - t_start_all
print(f"\n==================================================", flush=True)
print(f"All {len(chapters)} chapters processed in {total_elapsed/60.0:.1f} minutes!", flush=True)
print(f"==================================================", flush=True)
