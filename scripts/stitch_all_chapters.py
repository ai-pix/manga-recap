"""Stitch all 20 barbarian chapters into a single recap video.

Features:
- Reads all 20 barbarian chapters (barbarian_ch01 through barbarian_ch20)
- Concatenates them seamlessly in exact chronological order
- Uses local GPU NVENC acceleration (h264_nvenc)
- Optimizes file size with constant quality cq=28 + smart bitrate cap
  reducing the 11.5 GB raw collection down to ~1.3-1.6 GB while preserving crisp 1080p
- Fast encoding at ~310+ FPS (completes in ~10-12 minutes for the entire 2.1-hour movie)
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

CHAPTERS = [f"barbarian_ch{i:02d}" for i in range(1, 21)]


def check_prerequisites(chapters: list[str]) -> list[Path]:
    missing = []
    videos = []
    for ch in chapters:
        p = Path(f"data/chapters/{ch}/07_final.mp4")
        if not p.exists() or p.stat().st_size == 0:
            missing.append(ch)
        else:
            videos.append(p)

    if missing:
        print(f"Error: Missing 07_final.mp4 for: {missing}", file=sys.stderr)
        sys.exit(1)

    return videos


def build_concat_list(videos: list[Path], list_path: Path) -> None:
    lines = []
    for v in videos:
        # Use absolute path with forward slashes for ffmpeg concat demuxer
        abs_posix = v.resolve().as_posix()
        lines.append(f"file '{abs_posix}'")
    list_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote concat playlist with {len(videos)} videos to {list_path}")


def run_stitch(
    chapters: list[str],
    output_path: Path,
    codec: str = "h264_nvenc",
    cq: int = 28,
    preset: str = "p4",
) -> None:
    videos = check_prerequisites(chapters)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    concat_file = output_path.parent / "concat_list.txt"
    build_concat_list(videos, concat_file)

    print("=" * 70)
    print(f"STITCHING {len(videos)} CHAPTERS INTO COMPACT FULL MOVIE")
    print(f"Output: {output_path}")
    print(f"GPU Video Encoder: {codec} (preset={preset}, cq={cq})")
    print(f"Audio Codec: aac (128 kbps stereo)")
    print("=" * 70)

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c:v",
        codec,
        "-preset",
        preset,
        "-cq",
        str(cq),
        "-b:v",
        "2200k",
        "-maxrate",
        "3500k",
        "-bufsize",
        "6000k",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    print(f"Running command:\n{' '.join(cmd)}\n", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, text=True)
    elapsed = time.time() - t0

    if proc.returncode != 0:
        print(f"\n[ERROR] FFmpeg stitching failed with exit code {proc.returncode}!", file=sys.stderr)
        sys.exit(proc.returncode)

    if output_path.exists():
        final_mb = output_path.stat().st_size / 1e6
        print("\n" + "=" * 70)
        print(f"SUCCESS! Stitched video generated in {elapsed / 60:.1f} minutes ({elapsed:.1f}s)")
        print(f"File: {output_path}")
        print(f"Size: {final_mb:.1f} MB ({final_mb / 1000:.2f} GB)")
        print("=" * 70)
    else:
        print("[ERROR] Output file was not created!", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Stitch recap chapters into single video")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("data/chapters/barbarian_movie_ch01_ch20.mp4"),
        help="Path for output stitched video",
    )
    parser.add_argument(
        "--codec",
        type=str,
        default="h264_nvenc",
        choices=["h264_nvenc", "hevc_nvenc"],
        help="GPU encoder to use (default: h264_nvenc for max YouTube/player compatibility)",
    )
    parser.add_argument(
        "--cq",
        type=int,
        default=28,
        help="Constant quality level (default: 28 for clean ~1.4 GB size)",
    )
    args = parser.parse_args()

    run_stitch(CHAPTERS, args.output, codec=args.codec, cq=args.cq)


if __name__ == "__main__":
    main()
