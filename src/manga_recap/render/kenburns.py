"""Visual style for the render.

Kept separate from the ffmpeg plumbing in `manga_recap.render.ffmpeg` so that
changing how a video looks is a one-file edit. The renderer also runs inside the
Kaggle kernel, so this module is imported from `src/` on the kernel path.

Nothing here decides *when* a panel appears. That belongs to
`manga_recap.render.sync`, which is the single owner of shot timing; this module
only describes how a shot is drawn.
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class StyleSettings:
    """Resolved visual style, read from the job description."""

    width: int = 1920
    height: int = 1080
    fps: int = 30
    crf: int = 20
    preset: str = "medium"
    audio_bitrate: str = "192k"
    background_color: str = "0x0d0d12"
    background_mode: str = "blurred"
    blur_width: int = 512
    blur_radius: int = 16
    blur_darken: float = 0.12
    min_shot_seconds: float = 0.7
    max_clip_seconds: float = 60.0
    zoom_end: float = 1.06
    pan_cycle: str = "in,left,up,right"
    kenburns_enabled: bool = True
    bgm_enabled: bool = False
    bgm_directory: str = "assets/bgm"
    bgm_mode: str = "random"
    bgm_fixed_file: str = ""
    music_db: float = -22.0
    fade_seconds: float = 2.0
    seed: int = 7

    @classmethod
    def from_job(cls, job: dict) -> StyleSettings:
        render = job.get("render", {})
        kenburns = render.get("kenburns", {})
        bgm = job.get("bgm", {})
        return cls(
            width=int(render.get("width", 1920)),
            height=int(render.get("height", 1080)),
            fps=int(render.get("fps", 30)),
            crf=int(render.get("crf", 20)),
            preset=str(render.get("preset", "veryfast")),
            audio_bitrate=str(render.get("audio_bitrate", "192k")),
            background_color=str(render.get("background_color", "0x0d0d12")),
            background_mode=str(render.get("background_mode", "blurred")),
            blur_width=int(render.get("blur_width", 512)),
            blur_radius=int(render.get("blur_radius", 16)),
            blur_darken=float(render.get("blur_darken", 0.12)),
            min_shot_seconds=float(render.get("min_shot_seconds", 0.7)),
            max_clip_seconds=float(render.get("max_clip_seconds", 60.0)),
            kenburns_enabled=bool(kenburns.get("enabled", True)),
            zoom_end=float(kenburns.get("zoom_end", 1.06)),
            pan_cycle=str(render.get("pan_cycle", "in,left,up,right")),
            bgm_enabled=bool(bgm.get("enabled", False)),
            bgm_directory=str(bgm.get("directory", "assets/bgm")),
            bgm_mode=str(bgm.get("mode", "random")),
            bgm_fixed_file=str(bgm.get("fixed_file", "")),
            music_db=float(bgm.get("music_db", -22.0)),
            fade_seconds=float(bgm.get("fade_seconds", 2.0)),
        )

    def as_render_kwargs(self) -> dict:
        return {
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "crf": self.crf,
            "preset": self.preset,
            "audio_bitrate": self.audio_bitrate,
            "background_color": self.background_color,
            "background_mode": self.background_mode,
            "blur_width": self.blur_width,
            "blur_radius": self.blur_radius,
            "blur_darken": self.blur_darken,
            "min_shot_seconds": self.min_shot_seconds,
            "max_clip_seconds": self.max_clip_seconds,
            "max_words_per_beat": 14,
            "zoom_end": self.zoom_end if self.kenburns_enabled else 1.0,
            "pan_cycle": self.pan_cycle if self.kenburns_enabled else "in",
            "seed": self.seed,
        }


def pick_bgm(style: StyleSettings, bgm_root) -> str | None:
    """Choose a background track, if BGM is enabled and any exist.

    Returns None when BGM is off or the directory is empty, which is the normal
    v1 case. The wiring is here so turning BGM on is a config change, not a code
    change.
    """
    if not style.bgm_enabled:
        return None

    from pathlib import Path

    root = Path(bgm_root)
    if not root.is_absolute():
        root = Path.cwd() / root
    if not root.exists():
        print(f"[render] BGM enabled but {root} does not exist; continuing without music")
        return None

    tracks = sorted(p for p in root.iterdir() if p.suffix.lower() in (".mp3", ".wav", ".m4a", ".flac"))
    if not tracks:
        print(f"[render] BGM enabled but {root} has no audio files; continuing without music")
        return None

    if style.bgm_mode == "fixed" and style.bgm_fixed_file:
        for track in tracks:
            if track.name == style.bgm_fixed_file:
                return str(track)
        print(f"[render] fixed BGM {style.bgm_fixed_file} not found; picking at random")

    return str(random.Random(style.seed).choice(tracks))
