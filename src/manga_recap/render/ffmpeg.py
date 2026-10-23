"""Build the ffmpeg commands that turn a shot list into a video.

The visual style and the scheduling are deliberately separate. `sync.py` decides
*what* is on screen and *when*; this module only decides how to get pixels out
of it. Two consequences worth stating, because both were bugs:

- **Times are absolute.** Every segment gets its frames from the shot list's
  own timestamps. The old design chained all panels through one `xfade` graph
  and derived each cut from the sum of the durations before it, which silently
  discarded the silence between narration blocks. The video ran 30 seconds
  ahead of the audio by the end of chapter 1 and finished early. Cutting on
  absolute time makes that failure impossible.

- **One still, one segment.** Each panel is scaled to the output size exactly
  once, then held as a still. No per-frame scale, blur, overlay or `zoompan`.
  A `zoompan` over 101 panels was the single most expensive thing in the
  render; a moving crop over an already-oversized still looks the same and
  costs a fraction of it. The blurred letterbox backdrop, which ran
  `boxblur` over two megapixels on every frame, is now opt-in and off.

Segments are encoded independently and joined with a stream copy, so the work
parallelises across cores and GPUs and the join itself is instant.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from .sync import Shot, read_field


@dataclass
class Clip:
    """One panel on screen for a span of time.

    `frames` is the authoritative length. It is derived from the shot's
    absolute timestamps once, at the end, so no later rounding can move a cut.
    """

    panel_id: str
    path: Path
    start: float
    end: float
    direction: str = ""
    beat_id: str = ""
    block_id: str = ""
    frames: int = 0

    def __post_init__(self) -> None:
        if self.end < self.start:
            self.end = self.start

    @property
    def duration(self) -> float:
        return max(0.05, self.end - self.start)


def check_ffmpeg() -> str:
    """Locate ffmpeg, or explain how to fix it. Kaggle images ship with it."""
    executable = shutil.which("ffmpeg")
    if executable is None:
        raise FileNotFoundError(
            "ffmpeg is not on PATH. On Kaggle it is preinstalled; this stage is "
            "meant to run there. To run it locally, install ffmpeg and put it on PATH."
        )
    return executable


# ---------------------------------------------------------------------------
# Clips
# ---------------------------------------------------------------------------


def build_clips(
    script,
    timeline,
    panels_dir: Path,
    *,
    min_seconds: float = 0.7,
    max_seconds: float = 60.0,
    max_words_per_beat: int = 14,
    fps: int = 30,
) -> list[Clip]:
    """Expand the script and timeline into frame-exact clips.

    Delegates the timing to `sync.plan_shots`, which is the only place in the
    pipeline allowed to decide when a panel is on screen. Keeping one owner for
    that decision is what stops the renderer and the aligner disagreeing.

    Frame counts are assigned from cumulative absolute timestamps, so the
    segments sum to exactly `round(audio_duration * fps)` frames with no gap
    and no overlap between them.
    """
    from .sync import coverage_gaps, merge_repeats, plan_shots

    panels_dir = Path(panels_dir)
    audio_duration = float(timeline.get("duration", 0.0) or 0.0)
    words = timeline.get("words") or []

    report = plan_shots(
        read_field(script, "blocks", []),
        words,
        audio_duration=audio_duration,
        max_words_per_beat=max_words_per_beat,
        min_shot_seconds=min_seconds,
    )
    for problem in report.problems:
        print(f"[render] sync problem: {problem}")
    for warning in report.warnings:
        print(f"[render] sync warning: {warning}")
    if report.warning_summary():
        print(f"[render] sync warnings: {report.warning_summary()}")

    shots = merge_repeats(report.shots)
    shots = _clamp_durations(shots, min_seconds=min_seconds, max_seconds=max_seconds)

    gaps = coverage_gaps(shots, audio_duration)
    if gaps:
        print(
            f"[render] {len(gaps)} gap(s) in the shot list, e.g. "
            f"{gaps[0][0]:.2f}-{gaps[0][1]:.2f}s of {audio_duration:.2f}s total"
        )

    clips: list[Clip] = []
    for shot in shots:
        path = panels_dir / f"{shot.panel_id}.png"
        if not path.exists():
            path = panels_dir / f"{shot.panel_id}.jpg"
        if not path.exists():
            print(f"[render] panel image missing, skipping its shot: {path}")
            continue
        clips.append(
            Clip(
                panel_id=shot.panel_id,
                path=path,
                start=shot.start,
                end=shot.end,
                beat_id=shot.beat_id,
                block_id=shot.block_id,
            )
        )

    _assign_frames(clips, audio_duration=audio_duration, fps=fps)
    return clips


def _assign_frames(clips: list[Clip], *, audio_duration: float, fps: int) -> None:
    """Give every clip a whole number of frames, without gaps or overlap.

    Boundaries are rounded once, from absolute time, and each clip runs from
    its own start frame to the next one's. Computing a length per clip and
    adding them up instead would let rounding errors accumulate into a visible
    drift at the end of a long chapter.
    """
    if not clips:
        return

    total_frames = max(1, int(round(audio_duration * fps))) if audio_duration > 0 else 0
    boundaries: list[int] = [0]
    for clip in clips[:-1]:
        boundaries.append(max(boundaries[-1], int(round(clip.end * fps))))
    if total_frames:
        boundaries.append(max(boundaries[-1], total_frames))
    else:
        boundaries.append(max(boundaries[-1], int(round(clips[-1].end * fps))))

    for clip, start_frame, end_frame in zip(clips, boundaries, boundaries[1:], strict=False):
        clip.frames = max(1, end_frame - start_frame)


def _clamp_durations(shots: list[Shot], *, min_seconds: float, max_seconds: float) -> list[Shot]:
    """Keep shots inside the readable window without moving any cut.

    `sync` already guarantees coverage and monotonicity, so this only trims the
    extremes: a shot longer than `max_seconds` gives its tail to the shot that
    follows, and the last one is left alone because there is nothing after it
    to hand the time to.
    """
    if max_seconds <= 0:
        return shots

    for index, shot in enumerate(shots[:-1]):
        if shot.duration <= max_seconds:
            continue
        following = shots[index + 1]
        room = shot.end - max(shot.start + min_seconds, shot.end - max_seconds)
        take = min(room, following.duration - min_seconds)
        if take > 0:
            following.start -= take
            shot.end -= take

    return shots


# ---------------------------------------------------------------------------
# Per-shot stills
# ---------------------------------------------------------------------------


def _even(value: float, minimum: int = 2) -> int:
    """Round to a whole even number of pixels.

    `yuv420p` needs even dimensions, and the overscan factor does not land on
    them: 180 * 1.07 is 192.6. Rounding to even once here means no downstream
    filter ever has to reject the frame.
    """
    rounded = int(round(value))
    return max(minimum, rounded - (rounded % 2))


def fit_filter(
    *,
    width: int,
    height: int,
    mode: str = "fit",
    background: str = "0x0d0d12",
    overscan: float = 1.0,
) -> str:
    """The scale/crop chain that turns one panel into one output-sized frame.

    `overscan` scales the still larger than the frame so a moving crop has
    somewhere to travel. Without it a Ken Burns move has to resample every
    frame, which is exactly the cost this module exists to avoid.
    """
    target_w = _even(width * overscan)
    target_h = _even(height * overscan)

    if mode == "crop":
        # Fill the frame, discarding the overflow. One scale, one crop.
        return (
            f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h}"
        )

    # `fit` keeps the whole panel and pads the remainder. Cheapest of the two
    # and the only one that never hides part of the art.
    return (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=decrease,"
        f"pad={target_w}:{target_h}:(ow-iw)/2:(oh-ih)/2:color={background}"
    )


def blurred_backdrop_filter(
    *,
    width: int,
    height: int,
    overscan: float = 1.0,
    blur_width: int = 512,
    blur_radius: int = 16,
    darken: float = 0.12,
) -> str:
    """A blurred, darkened copy of the panel, filling the frame.

    The panel is scaled down to `blur_width` pixels, blurred there, and scaled
    back up. That is not a shortcut that happens to look similar: a blurred
    backdrop carries no detail by definition, so the downscale destroys nothing
    a full-resolution blur would have kept, and the blur runs on a few thousand
    pixels instead of two million.

    Returned as a single-input chain with an `overlay` at the end, ready to be
    composed against the sharp panel by `compose_filter`.
    """
    target_w = _even(width * overscan)
    target_h = _even(height * overscan)
    small = _even(blur_width)

    return (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},"
        f"scale={small}:-2,boxblur={blur_radius}:1,"
        f"scale={target_w}:{target_h}:flags=bicubic,"
        f"eq=brightness=-{darken:.3f}"
    )


def compose_filter(
    *,
    width: int,
    height: int,
    background: str = "0x0d0d12",
    overscan: float = 1.0,
    blur_width: int = 512,
    blur_radius: int = 16,
    darken: float = 0.12,
) -> str:
    """One input panel to one finished frame, background included.

    `blurred` puts a soft, darkened copy of the panel behind it so the frame is
    filled edge to edge and the sharp art sits on top. `solid` pads with a flat
    colour, which is cheaper and draws more attention to the art.

    The whole composition happens here, on a single frame. That is the point:
    the segment encoder then holds a finished still, so nothing in this chain
    ever runs per frame.
    """
    if background != "blurred":
        return fit_filter(
            width=width,
            height=height,
            mode=background,
            background=_color(background),
            overscan=overscan,
        )

    target_w = _even(width * overscan)
    target_h = _even(height * overscan)

    backdrop = blurred_backdrop_filter(
        width=width,
        height=height,
        overscan=overscan,
        blur_width=blur_width,
        blur_radius=blur_radius,
        darken=darken,
    )
    # The foreground is deliberately left unpadded. Padded to the full frame it
    # covers the backdrop with the pad colour, which is exactly the black bars
    # this mode exists to remove. At its fitted size, overlay centres it over the
    # backdrop and the blurred margins show through.
    return (
        f"split=2[bgsrc][fgsrc];"
        f"[bgsrc]{backdrop}[bg];"
        f"[fgsrc]scale={target_w}:{target_h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2:format=auto,setsar=1,format=yuv420p"
    )


def _color(value: str) -> str:
    """A background name that is not a layout mode is a colour."""
    return value if value.startswith("0x") or value.startswith("#") else "0x0d0d12"


def build_still_command(
    clip: Clip,
    output: Path,
    *,
    width: int,
    height: int,
    background: str = "blurred",
    zoom_end: float = 1.0,
    blur_width: int = 512,
    blur_radius: int = 16,
    darken: float = 0.12,
    executable: str | None = None,
) -> list[str]:
    """Compose one panel into a single finished frame.

    One output frame, so this costs the same whether the panel ends up on
    screen for half a second or ten. The frame is oversized when a Ken Burns
    move is configured, giving the crop somewhere to travel.
    """
    chain = compose_filter(
        width=width,
        height=height,
        background=background,
        overscan=_overscan_for(zoom_end),
        blur_width=blur_width,
        blur_radius=blur_radius,
        darken=darken,
    )
    command = [executable or check_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"]
    command += ["-i", str(clip.path), "-vf", chain, "-frames:v", "1", str(output)]
    return command


def _overscan_for(zoom_end: float) -> float:
    """How much larger than the frame a still should be.

    Exactly 1.0 when there is no move. Adding headroom unconditionally would
    make every static shot render at 1% oversized, and with no crop to trim it
    back the encoder would emit a video in the wrong resolution.
    """
    if zoom_end <= 1.001:
        return 1.0
    return zoom_end + 0.01


def build_segment_command(
    still: Path,
    output: Path,
    frames: int,
    *,
    width: int,
    height: int,
    fps: int = 30,
    zoom_end: float = 1.0,
    pan: str = "in",
    crf: int = 20,
    preset: str = "veryfast",
    executable: str | None = None,
) -> list[str]:
    """Hold one already-sized still for `frames` frames.

    With no motion this is a loop and an encode: no filter runs against the
    pixels at all. With motion it is a single `crop` whose window slides across
    the oversized still, which is a cheap per-frame operation compared to
    resampling the whole frame.

    The move is expressed against `t`, the frame's timestamp, rather than a
    frame counter, so it runs at the same speed whatever frame rate the render
    is configured at.
    """
    command = [executable or check_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error"]
    command += ["-loop", "1", "-framerate", str(fps), "-i", str(still)]

    if zoom_end > 1.001:
        span = max(1e-3, (frames - 1) / float(fps)) if frames > 1 else 1.0
        step = f"min(1,t/{span:.4f})"
        if pan == "left":
            x_expr, y_expr = f"(iw-ow)*(1-{step})", "(ih-oh)/2"
        elif pan == "right":
            x_expr, y_expr = f"(iw-ow)*{step}", "(ih-oh)/2"
        elif pan == "up":
            x_expr, y_expr = "(iw-ow)/2", f"(ih-oh)*(1-{step})"
        else:
            x_expr, y_expr = "(iw-ow)/2", f"(ih-oh)*{step}"
        command += ["-vf", f"crop={width}:{height}:x='{x_expr}':y='{y_expr}'"]

    x264_preset = preset if not (preset.startswith("p") and len(preset) == 2) else "veryfast"
    command += [
        "-frames:v", str(frames),
        "-c:v", "libx264",
        "-preset", x264_preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        "-an",
        str(output),
    ]
    return command


def build_concat_command(
    segments: list[Path],
    audio_path: Path,
    output_path: Path,
    *,
    audio_bitrate: str = "192k",
    executable: str | None = None,
) -> list[str]:
    """Join the encoded segments and mux the narration.

    The video is stream-copied, so this is a remux rather than a re-encode and
    takes well under a second regardless of chapter length.
    """
    if not segments:
        raise ValueError("No segments to concatenate.")

    listing = output_path.parent / "concat_list.txt"
    listing.parent.mkdir(parents=True, exist_ok=True)
    listing.write_text(
        "".join(f"file '{s.resolve().as_posix()}'\n" for s in segments), encoding="utf-8"
    )

    return [
        executable or check_ffmpeg(),
        "-y", "-hide_banner", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(listing),
        "-i", str(audio_path),
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ]


# ---------------------------------------------------------------------------
# Encoder probing
# ---------------------------------------------------------------------------


def has_nvenc(executable: str | None = None) -> bool:
    """Check if FFmpeg supports and can run h264_nvenc hardware acceleration."""
    exe = executable or shutil.which("ffmpeg")
    if exe is None:
        return False

    cuda_dirs = [
        "/usr/local/nvidia/lib64",
        "/usr/local/nvidia/lib",
        "/usr/lib/x86_64-linux-gnu",
        "/usr/local/cuda/lib64",
        "/usr/local/cuda/compat",
    ]
    env = os.environ.copy()
    current_ld = env.get("LD_LIBRARY_PATH", "")
    new_dirs = [d for d in cuda_dirs if Path(d).is_dir() and d not in current_ld]
    if new_dirs:
        env["LD_LIBRARY_PATH"] = ":".join(new_dirs + ([current_ld] if current_ld else []))

    try:
        res = subprocess.run(
            [
                exe, "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc=duration=0.5:size=256x256:rate=30",
                "-c:v", "h264_nvenc", "-f", "null", "-",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if res.returncode == 0:
            if new_dirs:
                os.environ["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH"]
            return True
        if res.stderr:
            print(f"[nvenc_probe] NVENC check note: {res.stderr.strip()}", flush=True)
        return False
    except Exception as exc:  # noqa: BLE001 - a probe must never break a render
        print(f"[nvenc_probe] NVENC check exception: {exc}", flush=True)
        return False


def get_gpu_count() -> int:
    """Detect available NVIDIA GPUs via nvidia-smi."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return 1
    try:
        res = subprocess.run([smi, "-L"], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            lines = [line for line in res.stdout.strip().splitlines() if "GPU " in line]
            return max(1, len(lines))
    except Exception:  # noqa: BLE001
        pass
    return 1


_CUDA_DEVICE_CACHE: dict[tuple[str, int], bool] = {}


def has_cuda_device(executable: str | None = None, gpu_id: int = 0) -> bool:
    """Check if FFmpeg supports CUDA hardware device initialization and hwupload_cuda on a specific GPU."""
    exe = executable or shutil.which("ffmpeg")
    if exe is None:
        return False
    cache_key = (exe, gpu_id)
    if cache_key in _CUDA_DEVICE_CACHE:
        return _CUDA_DEVICE_CACHE[cache_key]

    cuda_dirs = [
        "/usr/local/nvidia/lib64",
        "/usr/local/nvidia/lib",
        "/usr/lib/x86_64-linux-gnu",
        "/usr/local/cuda/lib64",
        "/usr/local/cuda/compat",
    ]
    env = os.environ.copy()
    current_ld = env.get("LD_LIBRARY_PATH", "")
    new_dirs = [d for d in cuda_dirs if Path(d).is_dir() and d not in current_ld]
    if new_dirs:
        env["LD_LIBRARY_PATH"] = ":".join(new_dirs + ([current_ld] if current_ld else []))

    try:
        res = subprocess.run(
            [
                exe,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-init_hw_device",
                f"cuda=cuda_{gpu_id}:{gpu_id}",
                "-filter_hw_device",
                f"cuda_{gpu_id}",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=0.1:size=256x256:rate=30",
                "-vf",
                "format=nv12,hwupload_cuda",
                "-c:v",
                "h264_nvenc",
                "-gpu",
                str(gpu_id),
                "-pix_fmt",
                "cuda",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        ok = res.returncode == 0
        if ok and new_dirs:
            os.environ["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH"]
        _CUDA_DEVICE_CACHE[cache_key] = ok
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[cuda_probe] CUDA check exception on GPU {gpu_id}: {exc}", flush=True)
        _CUDA_DEVICE_CACHE[cache_key] = False
        return False


def resolve_encoder(preference: str = "auto") -> str:
    """`auto` means NVENC when it works and libx264 when it does not."""
    if preference != "auto":
        return preference
    return "h264_nvenc" if has_nvenc() else "libx264"


def _segment_codec_args(
    encoder: str, crf: int, preset: str, gpu_id: int | None = None
) -> list[str]:
    if encoder == "h264_nvenc":
        nvenc_preset = preset if preset.startswith("p") and len(preset) == 2 else "p1"
        args = ["-c:v", "h264_nvenc"]
        if gpu_id is not None:
            args += ["-gpu", str(gpu_id)]
        args += ["-preset", nvenc_preset, "-tune", "ull", "-bf", "0", "-cq", str(crf)]
        return args
    x264_preset = preset if not (preset.startswith("p") and len(preset) == 2) else "veryfast"
    return ["-c:v", "libx264", "-preset", x264_preset, "-crf", str(crf)]



# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render(
    script,
    timeline,
    panels_dir: Path,
    audio_path: Path,
    output_path: Path,
    settings: dict,
) -> dict:
    """Render the chapter and return a manifest describing what was produced.

    Supports ultra-fast direct streaming with dual-GPU split-half concurrency,
    with automatic fallback to multi-worker segmented NVENC encoding.
    """
    engine = str(settings.get("engine", "segmented"))
    if engine == "pynv":
        try:
            from .pynv_renderer import render_pynv

            return render_pynv(
                script=script,
                timeline=timeline,
                panels_dir=panels_dir,
                audio_path=audio_path,
                output_path=output_path,
                settings=settings,
            )
        except Exception as exc:
            # On Kaggle or pure GPU environments, fail immediately if pynv was mandated
            if Path("/kaggle").is_dir() or bool(os.environ.get("KAGGLE_KERNEL_RUN_TYPE")):
                raise
            print(
                f"[render] Note: pynv engine failed ({exc}), "
                "falling back to direct_stream / segmented render",
                flush=True,
            )
    if engine == "direct_stream":
        try:
            from .direct_stream import render_direct_stream
            return render_direct_stream(
                script=script,
                timeline=timeline,
                panels_dir=panels_dir,
                audio_path=audio_path,
                output_path=output_path,
                settings=settings,
            )
        except Exception as exc:
            print(
                f"[render] Note: direct_stream engine failed ({exc}), "
                "falling back to segmented NVENC render",
                flush=True,
            )

    width = int(settings.get("width", 1920))
    height = int(settings.get("height", 1080))
    fps = int(settings.get("fps", 30))
    crf = int(settings.get("crf", 20))
    preset = str(settings.get("preset", "veryfast"))
    encoder = str(settings.get("encoder", "auto"))
    background_mode = str(settings.get("background_mode", "blurred"))
    background_color = str(settings.get("background_color", "0x0d0d12"))
    zoom_end = float(settings.get("zoom_end", 1.0))
    blur_width = int(settings.get("blur_width", 512))
    blur_radius = int(settings.get("blur_radius", 16))
    darken = float(settings.get("blur_darken", 0.12))
    background = background_color if background_mode == "solid" else background_mode
    max_words = int(settings.get("max_words_per_beat", 14))
    min_shot = float(settings.get("min_shot_seconds", 0.7))
    max_shot = float(settings.get("max_clip_seconds", 60.0))
    pan_cycle = str(settings.get("pan_cycle", "in,left,up,right"))

    clips = build_clips(
        script,
        timeline,
        panels_dir,
        min_seconds=min_shot,
        max_seconds=max_shot,
        max_words_per_beat=max_words,
        fps=fps,
    )
    if not clips:
        raise ValueError(
            "No renderable clips. Check that the script binds panels to its narration "
            "and that the panel images exist."
        )

    audio_duration = float(timeline.get("duration", 0.0) or 0.0)
    print(
        f"[render] {len(clips)} shots covering {audio_duration:.2f}s "
        f"({sum(c.frames for c in clips)} frames at {fps}fps)"
    )

    shm_dir = Path("/dev/shm")
    if shm_dir.is_dir() and os.access(shm_dir, os.W_OK):
        work_dir = shm_dir / f"manga_render_{output_path.stem}_{os.getpid()}"
    else:
        work_dir = output_path.parent / "_render_segments"
    shutil.rmtree(work_dir, ignore_errors=True)
    stills_dir = work_dir / "stills"
    segments_dir = work_dir / "segments"
    stills_dir.mkdir(parents=True, exist_ok=True)
    segments_dir.mkdir(parents=True, exist_ok=True)


    executable = check_ffmpeg()
    use_encoder = resolve_encoder(encoder)
    print(
        f"[render] encoder: {use_encoder}, background: {background_mode}, "
        f"zoom_end: {zoom_end}"
    )

    pans = [p.strip() for p in pan_cycle.split(",") if p.strip()] or ["in"]

    try:
        _prepare_stills(
            clips,
            stills_dir,
            executable=executable,
            width=width,
            height=height,
            background=background,
            zoom_end=zoom_end,
            blur_width=blur_width,
            blur_radius=blur_radius,
            darken=darken,
            workers=int(settings.get("max_workers", 0) or 0),
        )

        segments = _encode_segments(
            clips,
            stills_dir,
            segments_dir,
            executable=executable,
            width=width,
            height=height,
            fps=fps,
            zoom_end=zoom_end,
            pans=pans,
            encoder=use_encoder,
            crf=crf,
            preset=preset,
            workers=int(settings.get("max_workers", 0) or 0),
        )

        print(f"[render] joining {len(segments)} segments and muxing audio", flush=True)
        command = build_concat_command(
            segments,
            audio_path,
            output_path,
            audio_bitrate=str(settings.get("audio_bitrate", "192k")),
            executable=executable,
        )
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg failed joining the segments (code {result.returncode}):\n"
                f"{result.stderr[-3000:]}"
            )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return {
        "clip_count": len(clips),
        "duration": sum(c.frames for c in clips) / float(fps),
        "frames": sum(c.frames for c in clips),
        "panels_shown": sorted({c.panel_id for c in clips}),
        "output": str(output_path),
        "shots": [
            {
                "panel_id": c.panel_id,
                "start": round(c.start, 3),
                "end": round(c.end, 3),
                "frames": c.frames,
            }
            for c in clips
        ],
    }


def _prepare_stills(
    clips: list[Clip],
    stills_dir: Path,
    *,
    executable: str,
    width: int,
    height: int,
    background: str,
    zoom_end: float,
    blur_width: int,
    blur_radius: int,
    darken: float,
    workers: int,
) -> None:
    """Compose every panel into one finished frame in parallel.

    Uses pure in-memory/GPU compositing for blazing speed, with graceful fallback.
    """
    try:
        from .gpu_composer import prepare_stills_fast
        prepare_stills_fast(
            clips,
            stills_dir,
            width=width,
            height=height,
            background=background,
            zoom_end=zoom_end,
            blur_width=blur_width,
            blur_radius=blur_radius,
            darken=darken,
            workers=workers if workers > 0 else 16,
        )
        return
    except Exception as exc:
        print(f"[render] Note: fast still composer exception: {exc}, using FFmpeg fallback", flush=True)

    wanted: dict[str, Clip] = {}
    for clip in clips:
        wanted.setdefault(clip.panel_id, clip)

    print(
        f"[render] preparing {len(wanted)} panel stills at {width}x{height} "
        f"(background: {background})",
        flush=True,
    )
    started = time.time()

    def prepare(item: tuple[str, Clip]) -> Path:
        panel_id, clip = item
        target = stills_dir / f"{panel_id}.png"
        command = build_still_command(
            clip,
            target,
            width=width,
            height=height,
            background=background,
            zoom_end=zoom_end,
            blur_width=blur_width,
            blur_radius=blur_radius,
            darken=darken,
            executable=executable,
        )
        res = subprocess.run(command, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(
                f"could not compose {panel_id} ({clip.path.name}):\n{res.stderr[-1500:]}"
            )
        return target

    _run_pool(prepare, list(wanted.items()), workers, label="stills")
    print(f"[render] stills ready in {time.time() - started:.1f}s", flush=True)


def _encode_segments(
    clips: list[Clip],
    stills_dir: Path,
    segments_dir: Path,
    *,
    executable: str,
    width: int,
    height: int,
    fps: int,
    zoom_end: float,
    pans: list[str],
    encoder: str,
    crf: int,
    preset: str,
    workers: int,
) -> list[Path]:
    """Hold each still for its frames, then join. Parallelized across all available GPUs."""
    print(f"[render] encoding {len(clips)} segments", flush=True)
    started = time.time()
    is_nvenc = encoder == "h264_nvenc"
    num_gpus = get_gpu_count() if is_nvenc else 1

    def encode(item: tuple[int, Clip]) -> Path:
        index, clip = item
        target = segments_dir / f"seg_{index:04d}.mp4"
        command = build_segment_command(
            stills_dir / f"{clip.panel_id}.png",
            target,
            clip.frames,
            width=width,
            height=height,
            fps=fps,
            zoom_end=zoom_end,
            pan=pans[index % len(pans)],
            crf=crf,
            preset=preset,
            executable=executable,
        )
        if is_nvenc:
            gpu_id = (index % num_gpus) if num_gpus > 1 else 0
            command = _swap_encoder(command, encoder, crf, preset, gpu_id=gpu_id)
        elif encoder != "libx264":
            command = _swap_encoder(command, encoder, crf, preset)

        res = subprocess.run(command, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(
                f"segment {index} ({clip.panel_id}) failed (code {res.returncode}):\n"
                f"{res.stderr[-1500:]}"
            )
        return target

    try:
        segments = _run_pool(
            encode,
            list(enumerate(clips)),
            workers,
            label="segments",
            is_nvenc=is_nvenc,
        )
    finally:
        print(f"[render] segments encoded in {time.time() - started:.1f}s", flush=True)
    return segments


def _swap_encoder(
    command: list[str],
    encoder: str,
    crf: int,
    preset: str,
    gpu_id: int | None = None,
) -> list[str]:
    """Swap libx264 for a hardware encoder in an already-built command."""
    out: list[str] = []
    index = 0
    while index < len(command):
        token = command[index]
        if token == "-c:v":
            out += _segment_codec_args(encoder, crf, preset, gpu_id=gpu_id)
            index += 2
            continue
        if token == "-preset":
            index += 2
            continue
        if token == "-crf":
            index += 2
            continue
        out.append(token)
        index += 1
    return out


def _run_pool(
    work,
    items: list,
    workers: int,
    *,
    label: str,
    is_nvenc: bool = False,
) -> list:
    """Run `work` over `items`, using maximum GPU concurrency across all GPUs."""
    total = len(items)
    if total == 0:
        return []

    num_gpus = get_gpu_count() if is_nvenc else 1
    cpu_count = os.cpu_count() or 4
    if workers > 0:
        count = min(total, workers)
    elif is_nvenc:
        # 16 parallel workers per GPU (32 workers across 2x GPUs!)
        count = min(total, max(16, 16 * num_gpus))
    else:
        count = min(total, cpu_count)

    print(f"[render] {label}: {total} jobs across {count} workers (detected {num_gpus} GPU(s))", flush=True)
    completed = 0
    results: list = [None] * total

    def run(item):
        nonlocal completed
        index, payload = item
        results[index] = work(payload)
        completed += 1
        if completed % 10 == 0 or completed == total:
            print(f"[render] {label}: {completed}/{total} ({completed / total * 100:.1f}%)", flush=True)

    with ThreadPoolExecutor(max_workers=count) as pool:
        list(pool.map(run, enumerate(items)))
    return results

