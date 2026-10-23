import time
import sys
import os
import subprocess
import json
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s5_render import run as run_render

sys.stdout.reconfigure(encoding="utf-8")
cfg = load_config()

start_ch = int(sys.argv[1]) if len(sys.argv) > 1 else 6
end_ch = int(sys.argv[2]) if len(sys.argv) > 2 else 40

print(f"============================================================")
print(f"KAGGLE GPU BATCH RENDER ORCHESTRATOR: Chapters {start_ch:02d} to {end_ch:02d}")
print(f"Target Kernel: manga-recap-render (Tesla T4 pure GPU)")
print(f"============================================================")

t_all = time.time()
completed = 0
failed = []

for i in range(start_ch, end_ch + 1):
    ch_id = f"revival_hunter_ch{i:02d}"
    paths = ChapterPaths.create(ch_id)
    
    if paths.final_file.exists():
        print(f"[{i:02d}/{end_ch:02d}] {ch_id}: 07_final.mp4 already exists, checking sync...")
        # Check if already verified
        probe = subprocess.check_output([
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(paths.final_file)
        ], text=True)
        data = json.loads(probe)
        vd = next((s["duration"] for s in data["streams"] if s["codec_type"] == "video"), None)
        ad = next((s["duration"] for s in data["streams"] if s["codec_type"] == "audio"), None)
        print(f"  Existing video={float(vd):.1f}s, audio={float(ad):.1f}s -> OK")
        completed += 1
        continue
        
    print(f"\n[{i:02d}/{end_ch:02d}] Preparing to render {ch_id}...")
    
    # Wait for audio to be ready if it's currently synthesizing
    wait_count = 0
    while not (paths.narration_file.exists() and paths.timeline_file.exists()):
        print(f"  Waiting for {ch_id} audio synthesis to complete... ({wait_count*10}s)", flush=True)
        time.sleep(10)
        wait_count += 1
        if wait_count > 60:  # 10 minutes timeout
            raise TimeoutError(f"Timed out waiting for audio for {ch_id}")
            
    print(f"  Audio confirmed for {ch_id}. Launching Kaggle GPU render...", flush=True)
    t0 = time.time()
    try:
        manifest = run_render(paths, cfg, force=True)
        elapsed = time.time() - t0
        print(f"  -> RENDER SUCCESS in {elapsed:.1f}s for {ch_id}!", flush=True)
        
        # Verify streams and remux if necessary
        probe = subprocess.check_output([
            "ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(paths.final_file)
        ], text=True)
        data = json.loads(probe)
        v_dur = float(next(s["duration"] for s in data["streams"] if s["codec_type"] == "video"))
        a_dur = float(next(s["duration"] for s in data["streams"] if s["codec_type"] == "audio"))
        diff = abs(v_dur - a_dur)
        
        if diff > 1.0:
            print(f"  [Auto-Sync] Audio/video diff {diff:.2f}s detected on {ch_id}, applying lossless stream remux...", flush=True)
            fixed_file = paths.root / "07_final_fixed.mp4"
            remux_cmd = [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(paths.final_file),
                "-i", str(paths.narration_file),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-movflags", "+faststart",
                str(fixed_file)
            ]
            subprocess.run(remux_cmd, check=True)
            os.replace(fixed_file, paths.final_file)
            print(f"  [Auto-Sync] Remux complete with 100% full un-truncated audio!", flush=True)
            
        completed += 1
    except Exception as exc:
        print(f"  -> RENDER FAILED for {ch_id}: {exc}", flush=True)
        failed.append((ch_id, str(exc)))

print(f"\n============================================================")
print(f"BATCH RENDER COMPLETED in {time.time() - t_all:.1f}s!")
print(f"Successfully rendered: {completed}/{end_ch - start_ch + 1}")
if failed:
    print(f"Failed chapters: {failed}")
print(f"============================================================")
