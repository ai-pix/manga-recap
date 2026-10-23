import time
import sys
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s4_speech import run as run_speech

sys.stdout.reconfigure(encoding="utf-8")
cfg = load_config()

start_ch = int(sys.argv[1]) if len(sys.argv) > 1 else 7
end_ch = int(sys.argv[2]) if len(sys.argv) > 2 else 40

print(f"============================================================")
print(f"BATCH FISH AUDIO SYNTHESIS: Chapters {start_ch:02d} to {end_ch:02d}")
print(f"Model: s2.1-pro-free | Voice: Barbarian (802e3bc2b27e49c2995d23ef70e6ac89)")
print(f"============================================================")

t_all = time.time()
completed = 0
failed = []

for i in range(start_ch, end_ch + 1):
    ch_id = f"revival_hunter_ch{i:02d}"
    paths = ChapterPaths.create(ch_id)
    
    if (paths.narration_file.exists() and paths.timeline_file.exists()):
        print(f"[{i:02d}/{end_ch:02d}] {ch_id}: Already synthesized, skipping.")
        completed += 1
        continue
        
    print(f"\n[{i:02d}/{end_ch:02d}] Synthesizing {ch_id}...")
    t0 = time.time()
    try:
        timeline = run_speech(paths, cfg, force=True)
        dur = timeline.duration
        num_blocks = len(timeline.blocks)
        elapsed = time.time() - t0
        print(f"  -> SUCCESS in {elapsed:.1f}s: {dur:.1f}s audio ({dur/60:.2f}m), {num_blocks} blocks")
        completed += 1
    except Exception as exc:
        print(f"  -> FAILED: {exc}")
        failed.append((ch_id, str(exc)))

print(f"\n============================================================")
print(f"BATCH SYNTHESIS FINISHED in {time.time() - t_all:.1f}s!")
print(f"Successfully synthesized: {completed}/{end_ch - start_ch + 1}")
if failed:
    print(f"Failed chapters: {failed}")
print(f"============================================================")
