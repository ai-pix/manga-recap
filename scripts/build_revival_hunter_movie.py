"""Stitch all 40 chapters + 1-minute prologue hook into a single 4-Hour Marathon Movie using FFmpeg stream copy."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def format_timestamp(seconds: float) -> str:
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_duration(file_path: Path) -> float:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(file_path),
    ]
    res = subprocess.check_output(cmd, text=True)
    data = json.loads(res)
    return float(data["format"]["duration"])


def main():
    root = Path(".")
    output_dir = Path("C:/Users/ravih/Videos/MangaRecap")
    output_dir.mkdir(parents=True, exist_ok=True)
    package_dir = root / "data" / "export" / "revival_hunter_movie_package"
    package_dir.mkdir(parents=True, exist_ok=True)
    output_movie = package_dir / "SSS_Class_Revival_Hunter_Chapters_01_to_40_4Hours.mp4"

    hook_path = root / "data" / "chapters" / "revival_hunter_hook" / "07_final.mp4"
    if not hook_path.exists():
        raise FileNotFoundError(f"Hook not found: {hook_path}")

    clips: list[tuple[str, Path]] = [("Prologue: Dying 4,090 Times to Reverse Time", hook_path)]
    for i in range(1, 41):
        ch_path = root / "data" / "chapters" / f"revival_hunter_ch{i:02d}" / "07_final.mp4"
        if not ch_path.exists():
            raise FileNotFoundError(f"Missing chapter video: {ch_path}")
        clips.append((f"Chapter {i:02d}", ch_path))

    print(f"Gathered {len(clips)} clips (Hook + Chapters 01 to 40). Computing durations...")

    # Compute timestamps
    timestamps: list[tuple[str, str]] = []
    current_time = 0.0

    concat_lines = []
    for title, clip in clips:
        dur = get_duration(clip)
        ts_str = format_timestamp(current_time)
        timestamps.append((ts_str, title))
        posix_path = clip.resolve().as_posix()
        concat_lines.append(f"file '{posix_path}'")
        current_time += dur

    total_duration_str = format_timestamp(current_time)
    print(f"Total Compilation Duration: {total_duration_str} ({current_time / 3600:.2f} hours)")

    concat_file = package_dir / "concat_list.txt"
    concat_file.write_text("\n".join(concat_lines), encoding="utf-8")

    # Run FFmpeg concat stream copy with strict PTS/DTS regeneration and faststart
    print(f"Concatenating losslessly with FFmpeg stream copy to: {output_movie}")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        "-fflags",
        "+genpts",
        "-movflags",
        "+faststart",
        str(output_movie),
    ]
    subprocess.run(cmd, check=True)

    # Generate metadata.txt with timestamps
    metadata_file = package_dir / "metadata.txt"
    title_text = "He Broke Time With 4,090 Deaths: SSS-Class Revival Hunter (Chapters 01-40) Manhwa recap"

    desc_lines = [
        "Confucius Kim lived as a bottom-tier F-rank hunter, consuming toxic jealousy towards the world's greatest hunter: The Flame Emperor.",
        "One night, in a twisted stroke of irony, the Tower grants him an S-rank passive skill: Upon death, he copies one skill from his killer and regresses 24 hours into the past.",
        "When the Flame Emperor murders him in cold blood, Confucius copies his regression skill—and dies 4,090 times to rewind time by 11 years to eliminate the tyrant before he ever ascends.",
        "",
        "Here is the complete 4-hour epic story of SSS-Class Revival Hunter, covering Chapters 01 through 40.",
        "",
        "⏰ CHAPTER TIMESTAMPS:",
    ]
    for ts, name in timestamps:
        desc_lines.append(f"{ts} - {name}")

    desc_lines.extend([
        "",
        "🔥 Voice: Expressive Barbarian Narration (Fish Audio Studio)",
        "🎨 Pure GPU Hardware Render (PyNvVideoCodec zero-copy NVENC)",
        "",
        "#manhwarecap #manhwa #anime #recap #animerecap #sssclassrevivalhunter #timereversal #webtoon",
    ])

    tags_text = "sss class revival hunter, manhwa recap, anime recap, manga recap, full manhwa recap, time travel manhwa, over powered mc, f rank to god rank, 4 hour manhwa recap, webtoon recap"

    meta_content = f"TITLE:\n{title_text}\n\nDESCRIPTION:\n" + "\n".join(desc_lines) + f"\n\nTAGS:\n{tags_text}\n"
    metadata_file.write_text(meta_content, encoding="utf-8")

    # Copy backup to Videos folder
    backup_link = output_dir / "SSS_Class_Revival_Hunter_Chapters_01_to_40_4Hours.mp4"
    try:
        shutil.copy2(output_movie, backup_link)
    except Exception:
        pass

    print(f"SUCCESS: Compilation ready at {output_movie} ({output_movie.stat().st_size / (1024**3):.2f} GB)")
    print(f"Metadata file ready at {metadata_file}")


if __name__ == "__main__":
    main()
