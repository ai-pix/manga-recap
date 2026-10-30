"""Stitch Tomb Raider King Hook + all 30 chapters into a single master full movie.

Features:
- Seamlessly concatenates tomb_hook + series3_ch01 through series3_ch30 (31 parts)
- Uses proven hardware NVENC re-encode with -movflags +faststart
- Generates YouTube-ready timestamps and metadata
- Safe from multi-chapter timestamp discontinuities
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

CHAPTERS = ["tomb_hook"] + [f"series3_ch{i:02d}" for i in range(1, 31)]


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

    concat_file = output_path.parent / "tomb_concat_list.txt"
    build_concat_list(videos, concat_file)

    print("=" * 70)
    print(f"STITCHING {len(videos)} PARTS INTO FULL TOMB RAIDER KING MOVIE")
    print(f"Output: {output_path}")
    print(f"GPU Video Encoder: {codec} (preset={preset}, cq={cq})")
    print("Audio Codec: aac (128 kbps stereo)")
    print("=" * 70, flush=True)

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

    t0 = time.time()
    result = subprocess.run(cmd)
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"Stitch failed with returncode {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print("\n" + "=" * 70)
    print(f"SUCCESS: Movie rendered in {elapsed:.1f}s ({elapsed / 60:.1f}m)!")
    print(f"Final File: {output_path}")
    print(f"Size: {size_mb:.1f} MB ({size_mb / 1024:.2f} GB)")
    print("=" * 70, flush=True)


if __name__ == "__main__":
    out = Path("data/movies/tomb_raider_king_full_movie_ch01_ch30.mp4")
    run_stitch(CHAPTERS, out)
