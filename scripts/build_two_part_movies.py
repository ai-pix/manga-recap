"""Assemble the complete 112-chapter series into Two 9-Hour Mega Movies.

Movie 1: Hook 1 + Chapters 01 to 55 (approx 9 hours 06 mins)
Movie 2: Hook 3 + Chapters 56 to 112 (approx 8 hours 50 mins)

Outputs:
- C:/Users/ravih/Videos/MangaRecap/Only_Sense_Online_Part_1_9Hours.mp4
- C:/Users/ravih/Videos/MangaRecap/Only_Sense_Online_Part_2_9Hours.mp4
- data/Only_Sense_Online_Part_1_Timestamps.txt
- data/Only_Sense_Online_Part_2_Timestamps.txt
"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from manga_recap.core.paths import repo_path


def ch_key(name: str) -> tuple[int, int]:
    m = re.match(r"ch0*(\d+)(?:_(\d+))?", name)
    if m:
        base = int(m.group(1))
        sub = int(m.group(2)) if m.group(2) else 0
        return (base, sub)
    return (9999, 0)


def format_ts(seconds: float) -> str:
    s = int(seconds)
    hrs = s // 3600
    mins = (s % 3600) // 60
    secs = s % 60
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def assemble_part(
    part_num: int,
    title: str,
    hook_file: Path,
    hook_label: str,
    chapters: list[str],
    output_video: Path,
    timestamps_file: Path,
):
    print("=" * 70, flush=True)
    print(f"ASSEMBLING PART {part_num}: {title}", flush=True)
    print(f"Chapters ({len(chapters)}): {chapters[0]} to {chapters[-1]}", flush=True)
    print("=" * 70, flush=True)

    concat_lines = []
    timestamps = []
    cursor = 0.0

    # 1. Add Hook
    if hook_file.exists():
        # Get hook duration via ffprobe
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(hook_file)],
            capture_output=True,
            text=True,
            check=True,
        )
        hook_dur = float(probe.stdout.strip())
        concat_lines.append(f"file '{hook_file.resolve().as_posix()}'")
        timestamps.append(f"{format_ts(cursor)} - {hook_label}")
        cursor += hook_dur
    else:
        print(f"[warning] Hook file {hook_file} not found!", flush=True)

    # 2. Add Chapters
    for c in chapters:
        ch_dir = repo_path("data/chapters") / c
        video_f = ch_dir / "07_final.mp4"
        manifest_f = ch_dir / "07_render_manifest.json"

        if not video_f.exists():
            raise FileNotFoundError(f"Missing video for chapter {c}: {video_f}")

        # Duration
        dur = 0.0
        if manifest_f.exists():
            dur = json.loads(manifest_f.read_text(encoding="utf-8")).get("duration", 0.0)
        else:
            probe = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_f)],
                capture_output=True,
                text=True,
                check=True,
            )
            dur = float(probe.stdout.strip())

        # Formatted label
        clean_name = c.replace("ch00", "Chapter ").replace("ch0", "Chapter ").replace("ch", "Chapter ")
        concat_lines.append(f"file '{video_f.resolve().as_posix()}'")
        timestamps.append(f"{format_ts(cursor)} - {clean_name}")
        cursor += dur

    # Save concat list
    list_file = repo_path(f"build/concat_part{part_num}.txt")
    list_file.parent.mkdir(parents=True, exist_ok=True)
    list_file.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")
    print(f"[list] Saved FFmpeg concat list to {list_file}", flush=True)

    # Save Timestamps
    timestamps_file.parent.mkdir(parents=True, exist_ok=True)
    timestamps_file.write_text("\n".join(timestamps) + "\n", encoding="utf-8")
    print(f"[timestamps] Saved YouTube description timestamps to {timestamps_file}", flush=True)

    # 3. Run Lossless FFmpeg Concat
    output_video.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
        str(output_video),
    ]

    print(f"[ffmpeg] Executing lossless stream copy to {output_video.name}...", flush=True)
    start_t = time.time()
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[error] FFmpeg concat failed: {res.stderr[-500:]}", flush=True)
        raise RuntimeError("FFmpeg concat failed.")

    elapsed = time.time() - start_t
    size_gb = output_video.stat().st_size / 1e9
    hrs = cursor / 3600
    print(f"[success] Part {part_num} ready in {elapsed:.1f}s!")
    print(f"  File: {output_video}")
    print(f"  Duration: {hrs:.2f} hours ({int(hrs)}h {int((hrs%1)*60)}m)")
    print(f"  Size: {size_gb:.2f} GB\n", flush=True)


def main():
    ch_dirs = sorted([d.name for d in repo_path("data/chapters").iterdir() if d.is_dir() and d.name.startswith("ch")], key=ch_key)
    if len(ch_dirs) < 112:
        print(f"[error] Expected at least 112 chapters, found {len(ch_dirs)}")
        return 1

    part1_chs = ch_dirs[:56]   # ch01 through ch055 (56 chapters)
    part2_chs = ch_dirs[56:]  # ch056 through ch112 (59 chapters)

    out_dir = Path("C:/Users/ravih/Videos/MangaRecap")
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Part 1 ---
    assemble_part(
        part_num=1,
        title="Part 1: The Trash-Skill God (Chapters 01 to 55)",
        hook_file=repo_path("data/hooks/hook_part1.mp4"),
        hook_label="Intro & Hook: The Trash-Skill God",
        chapters=part1_chs,
        output_video=out_dir / "Only_Sense_Online_Part_1_Chapters_01_to_55_9Hours.mp4",
        timestamps_file=repo_path("data/Only_Sense_Online_Part_1_Timestamps.txt"),
    )

    # --- Part 2 ---
    assemble_part(
        part_num=2,
        title="Part 2: The Uncharted Realm & Grand Finale (Chapters 56 to 112)",
        hook_file=repo_path("data/hooks/hook_part3.mp4"),
        hook_label="Intro & Hook: The Uncharted Frontier & Grand Climax",
        chapters=part2_chs,
        output_video=out_dir / "Only_Sense_Online_Part_2_Chapters_56_to_112_9Hours.mp4",
        timestamps_file=repo_path("data/Only_Sense_Online_Part_2_Timestamps.txt"),
    )

    print("=" * 70, flush=True)
    print("ALL TWO 9-HOUR MEGA MOVIES ASSEMBLED AND READY ON DISK!", flush=True)
    print("=" * 70, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
