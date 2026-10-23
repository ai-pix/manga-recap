from pathlib import Path

pynv_py = Path("src/manga_recap/render/pynv_renderer.py")
content = pynv_py.read_text(encoding="utf-8")

# 1. Update encoder initialization
old_init = """    # Initialize PyNvVideoCodec encoder
    print(f"[pynv] Initializing hardware NVENC encoder for {width}x{height} NV12...", flush=True)
    encoder = nvc.CreateEncoder(width, height, "NV12", True)"""

new_init = """    # Initialize PyNvVideoCodec encoder with target bitrate
    video_bitrate = int(settings.get("video_bitrate", 3_200_000))
    print(
        f"[pynv] Initializing hardware NVENC encoder for {width}x{height} NV12 (target: {video_bitrate/1_000_000:.1f} Mbps)...",
        flush=True,
    )
    encoder = None
    try:
        encoder = nvc.CreateEncoder(
            width,
            height,
            "NV12",
            True,
            codec="h264",
            preset="p4",
            bitrate=video_bitrate,
            rc="vbr",
            fps=fps,
        )
    except Exception as exc:
        print(f"[pynv] Note: CreateEncoder kwargs rejected ({exc}), using standard signature...", flush=True)

    if encoder is None:
        encoder = nvc.CreateEncoder(width, height, "NV12", True)"""

if old_init in content:
    content = content.replace(old_init, new_init, 1)
    print("Updated pynv encoder initialization")
else:
    print("pynv encoder init target not found (might already be patched)")

# 2. Update FFmpeg muxing
old_mux = """    # Instant mux using FFmpeg stream-copy
    exe = check_ffmpeg()
    print("[pynv] Stream-copy muxing audio into MP4...", flush=True)
    t_mux = time.time()
    mux_cmd = [
        exe,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-r",
        str(fps),
        "-i",
        str(raw_h264_path.resolve()),
        "-i",
        str(audio_path.resolve()),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-movflags",
        "+faststart",
        str(output_path.resolve()),
    ]"""

new_mux = """    # Pure GPU NVENC muxing with optimal compact bitstream
    exe = check_ffmpeg()
    raw_size = raw_h264_path.stat().st_size
    dur_sec = max(1.0, float(audio_duration))
    raw_rate_bps = (raw_size * 8) / dur_sec
    print(f"[pynv] Raw bitstream: {raw_size / 1_000_000:.1f} MB ({raw_rate_bps / 1_000_000:.2f} Mbps)", flush=True)

    if raw_rate_bps > 4_500_000:
        print(
            f"[pynv] Bitstream exceeds target rate; applying pure GPU NVENC hardware compression to {video_bitrate / 1_000_000:.1f} Mbps...",
            flush=True,
        )
        video_enc_args = [
            "-c:v",
            "h264_nvenc",
            "-preset",
            "p4",
            "-b:v",
            f"{video_bitrate}",
            "-maxrate",
            f"{int(video_bitrate * 1.35)}",
            "-bufsize",
            f"{int(video_bitrate * 2)}",
        ]
    else:
        video_enc_args = ["-c:v", "copy"]

    print("[pynv] Muxing audio into MP4...", flush=True)
    t_mux = time.time()
    mux_cmd = [
        exe,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-r",
        str(fps),
        "-i",
        str(raw_h264_path.resolve()),
        "-i",
        str(audio_path.resolve()),
        *video_enc_args,
        "-c:a",
        "aac",
        "-b:a",
        audio_bitrate,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-movflags",
        "+faststart",
        str(output_path.resolve()),
    ]"""

if old_mux in content:
    content = content.replace(old_mux, new_mux, 1)
    print("Updated pynv muxing with compact GPU rate control")
else:
    print("pynv mux target not found (might already be patched)")

pynv_py.write_text(content, encoding="utf-8")
