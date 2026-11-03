"""Instant, Zero-Reencode Video Stitcher for Manga Recap.

Merges pre-rendered chapter videos into a single master recap video in minutes
using pure stream-copy (-c copy). No CPU/GPU encoding, zero quality loss.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path


def get_video_duration(path: Path) -> float:
    """Read duration in seconds using sibling timeline.json (instant) or ffprobe fallback."""
    timeline_file = path.parent / "06_timeline.json"
    if timeline_file.exists():
        try:
            with timeline_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if "duration" in data and data["duration"]:
                    return float(data["duration"])
        except Exception:
            pass
    try:
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def instant_stitch(
    chapters: list[str],
    output_path: Path,
    faststart: bool = True,
) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    videos: list[Path] = []
    missing: list[str] = []
    total_expected_dur = 0.0

    print("=" * 75)
    print(f"INSTANT STREAM-COPY STITCHER: {len(chapters)} Chapters")
    print("=" * 75)

    for ch in chapters:
        v = Path(f"data/chapters/{ch}/07_final.mp4")
        if not v.exists() or v.stat().st_size < 1_000_000:
            missing.append(ch)
        else:
            videos.append(v)
            dur = get_video_duration(v)
            total_expected_dur += dur

    if missing:
        print(f"\n[ERROR] Missing or empty 07_final.mp4 in {len(missing)} chapters:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        sys.exit(1)

    print(f"Validated all {len(videos)} input videos.")
    print(f"Expected Full Movie Duration: {total_expected_dur:.1f}s ({total_expected_dur / 60:.1f} min / {total_expected_dur / 3600:.2f} hrs)")
    print(f"Target Output: {output_path}")
    print("-" * 75)

    concat_file = output_path.parent / f"_concat_{int(time.time())}.txt"
    with concat_file.open("w", encoding="utf-8") as f:
        for v in videos:
            f.write(f"file '{v.resolve().as_posix()}'\n")

    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-stats",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
    ]
    if faststart:
        cmd.extend(["-movflags", "+faststart"])

    cmd.append(str(output_path))

    print(f"Executing instant stream copy directly to external drive: {output_path}...", flush=True)
    t0 = time.time()

    # Run FFmpeg with visible output
    proc = subprocess.run(cmd)

    concat_file.unlink(missing_ok=True)
    elapsed = time.time() - t0

    if proc.returncode != 0:
        print(f"\n[ERROR] FFmpeg stream copy failed with exit code {proc.returncode}!", file=sys.stderr)
        sys.exit(proc.returncode)

    if proc.returncode != 0:
        print(f"\n[ERROR] FFmpeg stream copy failed with exit code {proc.returncode}!", file=sys.stderr)
        sys.exit(proc.returncode)

    if not output_path.exists():
        print(f"\n[ERROR] Output file {output_path} was not created!", file=sys.stderr)
        sys.exit(1)

    actual_dur = get_video_duration(output_path)
    size_mb = output_path.stat().st_size / (1024 * 1024)
    dur_diff = abs(actual_dur - total_expected_dur)

    print("\n" + "=" * 75)
    print("SUCCESS! MOVIE CREATED INSTANTLY WITHOUT RE-ENCODING")
    print(f"Time Taken:      {elapsed:.1f}s ({elapsed / 60:.2f} minutes)")
    print(f"Output File:     {output_path}")
    print(f"File Size:       {size_mb:.1f} MB ({size_mb / 1024:.2f} GB)")
    print(f"Actual Duration: {actual_dur:.1f}s ({actual_dur / 60:.1f} min)")
    print(f"Duration Drift:  {dur_diff:.2f}s vs total sum")
    print("=" * 75)


def main():
    parser = argparse.ArgumentParser(description="Instantly stitch chapter videos via stream copy")
    parser.add_argument("--prefix", type=str, default="orv_ch", help="Chapter prefix (e.g. orv_ch, series3_ch)")
    parser.add_argument("--start", type=int, default=0, help="Start chapter number")
    parser.add_argument("--end", type=int, default=30, help="End chapter number")
    parser.add_argument("--output", "-o", type=Path, default=Path("data/movies/orv_full_movie.mp4"), help="Output path")
    parser.add_argument("--no-faststart", action="store_true", help="Skip +faststart for even faster writing")
    args = parser.parse_args()

    chapters = [f"{args.prefix}{i:02d}" for i in range(args.start, args.end + 1)]
    instant_stitch(chapters, args.output, faststart=not args.no_faststart)


if __name__ == "__main__":
    main()
