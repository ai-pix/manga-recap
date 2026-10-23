"""Sample variant renderer for tall manga/manhwa panels on Kaggle GPU.

Renders and compares 3 camera motion variants on ultra-tall panels:
1. Variant 1 (Dynamic Split Cards): Both sections shown as cards side-by-side,
   entering on their respective spoken beats.
2. Variant 2 (Sequential Slide Cards): Full-sized cards sliding horizontally
   across the screen on the beat boundary.
3. Variant 3 (Continuous Stepped Glide): Seamless continuous vertical pan
   across the entire panel with smooth easing at key beat framings and zero skipped middle.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
from PIL import Image


def smootherstep(t: float) -> float:
    """Quintic Hermite curve with 0 first and second derivatives at both ends."""
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def rgb_to_nv12(rgb_tensor):
    """Convert an RGB uint8 tensor (H, W, 3) on CUDA to NV12 (H * 1.5, W) on CUDA."""
    import torch

    h, w, _ = rgb_tensor.shape
    r = rgb_tensor[:, :, 0].float()
    g = rgb_tensor[:, :, 1].float()
    b = rgb_tensor[:, :, 2].float()

    y = (0.257 * r + 0.504 * g + 0.098 * b + 16.0).clamp(0, 255).to(torch.uint8)
    r_sub = r[::2, ::2]
    g_sub = g[::2, ::2]
    b_sub = b[::2, ::2]
    u = (-0.148 * r_sub - 0.291 * g_sub + 0.439 * b_sub + 128.0).clamp(0, 255).to(torch.uint8)
    v = (0.439 * r_sub - 0.368 * g_sub - 0.071 * b_sub + 128.0).clamp(0, 255).to(torch.uint8)

    uv = torch.empty((h // 2, w), dtype=torch.uint8, device=rgb_tensor.device)
    uv[:, 0::2] = u
    uv[:, 1::2] = v

    return torch.cat([y, uv], dim=0).contiguous()


def slice_subpixel_nv12(rgb_strip, y_float: float, height: int):
    """Extract a height-sized NV12 frame with sub-pixel vertical bilinear interpolation on CUDA."""
    import torch

    strip_h = rgb_strip.shape[0]
    max_y0 = strip_h - height
    if max_y0 <= 0:
        return rgb_to_nv12(rgb_strip[:height, :, :])

    clamped_y = max(0.0, min(float(max_y0), y_float))
    y0 = int(clamped_y)
    alpha = clamped_y - y0

    if alpha < 0.005 or y0 >= max_y0:
        sub_rgb = rgb_strip[y0 : y0 + height, :, :]
    elif alpha > 0.995:
        sub_rgb = rgb_strip[y0 + 1 : y0 + 1 + height, :, :]
    else:
        row0 = rgb_strip[y0 : y0 + height, :, :].float()
        row1 = rgb_strip[y0 + 1 : y0 + 1 + height, :, :].float()
        sub_rgb = (row0 * (1.0 - alpha) + row1 * alpha).clamp(0, 255).to(torch.uint8)

    return rgb_to_nv12(sub_rgb)


def extract_packet_bytes(packet) -> bytes:
    if packet is None:
        return b""
    if isinstance(packet, (bytes, bytearray)):
        return bytes(packet)
    if isinstance(packet, memoryview):
        return packet.tobytes()
    if isinstance(packet, dict):
        if "data" in packet:
            return bytes(packet["data"])
        for v in packet.values():
            if isinstance(v, (bytes, bytearray, memoryview)):
                return bytes(v)
        return b""
    if isinstance(packet, (list, tuple)):
        return b"".join(extract_packet_bytes(p) for p in packet)
    if hasattr(packet, "tobytes"):
        return packet.tobytes()
    try:
        return bytes(packet)
    except Exception:
        return b""


def overlay_card_on_canvas(
    canvas,  # (3, H, W) float
    card,    # (3, Hc, Wc) float
    center_x: int,
    center_y: int,
    opacity: float = 1.0,
) -> None:
    """Blit card tensor onto canvas centered at (center_x, center_y)."""
    _, H_canv, W_canv = canvas.shape
    _, H_card, W_card = card.shape
    x0 = center_x - W_card // 2
    y0 = center_y - H_card // 2
    x1 = x0 + W_card
    y1 = y0 + H_card

    cx0 = max(0, x0)
    cy0 = max(0, y0)
    cx1 = min(W_canv, x1)
    cy1 = min(H_canv, y1)

    if cx0 >= cx1 or cy0 >= cy1:
        return

    kx0 = cx0 - x0
    ky0 = cy0 - y0
    kx1 = kx0 + (cx1 - cx0)
    ky1 = ky0 + (cy1 - cy0)

    card_crop = card[:, ky0:ky1, kx0:kx1]
    if opacity < 0.999:
        canvas[:, cy0:cy1, cx0:cx1] = canvas[:, cy0:cy1, cx0:cx1] * (1.0 - opacity) + card_crop * opacity
    else:
        canvas[:, cy0:cy1, cx0:cx1] = card_crop


def create_card_with_border(crop_tensor, target_h: int, target_w: int, border_w: int = 4):
    """Resize crop_tensor to (target_h, target_w) and add crisp border."""
    import torch
    import torch.nn.functional as F

    device = crop_tensor.device
    raw_batch = crop_tensor.unsqueeze(0)  # [1, 3, H, W]
    resized = F.interpolate(raw_batch, size=(target_h, target_w), mode="bilinear", align_corners=False)[0]

    # Card with dark outer rim + light inner stroke
    H_tot = target_h + 2 * border_w
    W_tot = target_w + 2 * border_w
    framed = torch.full((3, H_tot, W_tot), 20.0, dtype=torch.float32, device=device)
    # Subtle inner border line
    framed[:, 1:H_tot - 1, 1:W_tot - 1] = 60.0
    framed[:, border_w : border_w + target_h, border_w : border_w + target_w] = resized
    return framed


def render_sample_variants_for_panel(
    panel_path: Path,
    audio_path: Path,
    start_sec: float,
    end_sec: float,
    split_sec: float,
    output_prefix: str,
    exe: str,
    working_dir: Path,
    device,
) -> dict[str, Path]:
    """Render the 3 sample motion variants for an ultra-tall panel."""
    import PyNvVideoCodec as nvc
    import torch
    import torch.nn.functional as F

    dur_sec = end_sec - start_sec
    fps = 30
    total_frames = int(round(dur_sec * fps))
    split_frame = int(round((split_sec - start_sec) * fps))
    width, height = 1920, 1080

    print(
        f"[sample_variants] Rendering {output_prefix}: {panel_path.name} "
        f"({dur_sec:.2f}s, {total_frames} frames, split at frame {split_frame})...",
        flush=True,
    )

    # 1. Slice audio
    clip_audio = working_dir / f"{output_prefix}_audio.wav"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{start_sec:.3f}",
            "-t", f"{dur_sec:.3f}",
            "-i", str(audio_path),
            "-c", "copy",
            str(clip_audio),
        ],
        check=True,
    )

    # 2. Load panel image to GPU
    with Image.open(panel_path) as img:
        arr = np.array(img.convert("RGB"), dtype=np.uint8)
    raw = torch.from_numpy(arr).permute(2, 0, 1).to(device=device, dtype=torch.float32)
    _, src_h, src_w = raw.shape
    raw_batch = raw.unsqueeze(0)

    # 3. Create blurred background (1920x1080)
    bw = 128
    bh = max(16, int(round(bw * src_h / src_w)))
    small = F.interpolate(raw_batch, size=(bh, bw), mode="bilinear", align_corners=False)
    k_size = 25
    kernel = torch.ones(1, 1, k_size, device=device) / k_size
    blurred = F.conv1d(small.view(-1, 1, bw), kernel, padding=k_size // 2).view(1, 3, bh, bw)
    blurred = F.conv1d(
        blurred.permute(0, 1, 3, 2).reshape(-1, 1, bh), kernel, padding=k_size // 2
    ).view(1, 3, bw, bh).permute(0, 1, 3, 2).contiguous()
    bg_tensor = F.interpolate(blurred, size=(height, width), mode="bilinear", align_corners=False)[0]
    bg_tensor = bg_tensor * 0.85  # darken by 15%

    results = {}

    # -------------------------------------------------------------------------
    # VARIANT 1: Dynamic Split Cards
    # -------------------------------------------------------------------------
    print("[sample_variants] Rendering Variant 1 (Dynamic Split Cards)...", flush=True)
    card_h = 940
    card_w = 470
    sec_len = min(src_h, int(round(src_w * 2.0)))
    top_crop = raw[:, :sec_len, :]
    bot_crop = raw[:, max(0, src_h - sec_len):, :]
    card1 = create_card_with_border(top_crop, card_h, card_w, border_w=4)
    card2 = create_card_with_border(bot_crop, card_h, card_w, border_w=4)

    target_x1 = 540
    target_x2 = 1380
    target_y = 540

    encoder = nvc.CreateEncoder(width, height, "NV12", True)
    raw_h264_v1 = working_dir / f"{output_prefix}_v1.h264"
    with raw_h264_v1.open("wb") as f_out:
        for f in range(total_frames):
            canvas = bg_tensor.clone()
            if f < split_frame:
                # Beat 0: Card 1 glides in from left to target_x1, Card 2 is offscreen
                u = min(1.0, f / 18.0)
                e = smootherstep(u)
                x1 = int(round(-300 + e * (target_x1 - (-300))))
                overlay_card_on_canvas(canvas, card1, x1, target_y)
            else:
                # Beat 1: Card 1 holds, Card 2 glides in from right to target_x2
                u = min(1.0, (f - split_frame) / 22.0)
                e = smootherstep(u)
                x2 = int(round(2300 - e * (2300 - target_x2)))
                overlay_card_on_canvas(canvas, card1, target_x1, target_y)
                overlay_card_on_canvas(canvas, card2, x2, target_y)

            rgb_canvas = canvas.clamp(0, 255).to(torch.uint8).permute(1, 2, 0).contiguous()
            nv12 = rgb_to_nv12(rgb_canvas)
            packet = encoder.Encode(nv12)
            if packet:
                f_out.write(extract_packet_bytes(packet))

        for flush_attr in ("EndEncode", "Flush", "flush"):
            if hasattr(encoder, flush_attr):
                try:
                    f_out.write(extract_packet_bytes(getattr(encoder, flush_attr)()))
                    break
                except Exception:
                    pass

    v1_mp4 = working_dir / f"{output_prefix}_variant1_split_cards.mp4"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-r", str(fps), "-i", str(raw_h264_v1),
            "-i", str(clip_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            str(v1_mp4),
        ],
        check=True,
    )
    results["variant1"] = v1_mp4

    # -------------------------------------------------------------------------
    # VARIANT 2: Sequential Slide Cards
    # -------------------------------------------------------------------------
    print("[sample_variants] Rendering Variant 2 (Sequential Slide Cards)...", flush=True)
    card2_h = 980
    card2_w = 540
    card2_1 = create_card_with_border(top_crop, card2_h, card2_w, border_w=4)
    card2_2 = create_card_with_border(bot_crop, card2_h, card2_w, border_w=4)
    center_x = 960

    encoder = nvc.CreateEncoder(width, height, "NV12", True)
    raw_h264_v2 = working_dir / f"{output_prefix}_v2.h264"
    trans_len = 16
    with raw_h264_v2.open("wb") as f_out:
        for f in range(total_frames):
            canvas = bg_tensor.clone()
            if f < split_frame:
                overlay_card_on_canvas(canvas, card2_1, center_x, target_y)
            elif f < split_frame + trans_len:
                u = (f - split_frame) / float(trans_len)
                e = smootherstep(u)
                x1 = int(round(center_x - e * 1500))
                x2 = int(round(2460 - e * 1500))
                overlay_card_on_canvas(canvas, card2_1, x1, target_y)
                overlay_card_on_canvas(canvas, card2_2, x2, target_y)
            else:
                overlay_card_on_canvas(canvas, card2_2, center_x, target_y)

            rgb_canvas = canvas.clamp(0, 255).to(torch.uint8).permute(1, 2, 0).contiguous()
            nv12 = rgb_to_nv12(rgb_canvas)
            packet = encoder.Encode(nv12)
            if packet:
                f_out.write(extract_packet_bytes(packet))

        for flush_attr in ("EndEncode", "Flush", "flush"):
            if hasattr(encoder, flush_attr):
                try:
                    f_out.write(extract_packet_bytes(getattr(encoder, flush_attr)()))
                    break
                except Exception:
                    pass

    v2_mp4 = working_dir / f"{output_prefix}_variant2_slide_cards.mp4"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-r", str(fps), "-i", str(raw_h264_v2),
            "-i", str(clip_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            str(v2_mp4),
        ],
        check=True,
    )
    results["variant2"] = v2_mp4

    # -------------------------------------------------------------------------
    # VARIANT 3: Continuous Stepped Glide
    # -------------------------------------------------------------------------
    print("[sample_variants] Rendering Variant 3 (Continuous Stepped Glide)...", flush=True)
    fg_w = min(width, max(1080, int(round(src_w * 1.35))))
    scale_fg = fg_w / float(src_w)
    fg_h = int(round(src_h * scale_fg))
    travel = fg_h - height
    x_off = (width - fg_w) // 2

    bg_strip_small = F.interpolate(raw_batch, size=(bh, bw), mode="bilinear", align_corners=False)
    bg_strip_blur = F.conv1d(bg_strip_small.view(-1, 1, bw), kernel, padding=k_size // 2).view(1, 3, bh, bw)
    bg_strip_blur = F.conv1d(
        bg_strip_blur.permute(0, 1, 3, 2).reshape(-1, 1, bh), kernel, padding=k_size // 2
    ).view(1, 3, bw, bh).permute(0, 1, 3, 2).contiguous()
    bg_strip = F.interpolate(bg_strip_blur, size=(fg_h, width), mode="bilinear", align_corners=False)[0] * 0.85

    fg_tensor = F.interpolate(raw_batch, size=(fg_h, fg_w), mode="bilinear", align_corners=False)[0]
    canvas_strip = bg_strip
    canvas_strip[:, 0:fg_h, x_off:x_off + fg_w] = fg_tensor
    rgb_strip = canvas_strip.clamp(0, 255).to(torch.uint8).permute(1, 2, 0).contiguous()

    encoder = nvc.CreateEncoder(width, height, "NV12", True)
    raw_h264_v3 = working_dir / f"{output_prefix}_v3.h264"

    # Multi-beat keyframe glide curve:
    # Beat 0: holds near top (drifts gently 0 -> 400px)
    # Beat 0->1 transition: glides through middle artwork (400px -> 85% of travel)
    # Beat 1: settles and eases to the bottom explosion (85% of travel -> travel)
    y_drift_top = min(400.0, float(travel) * 0.05)
    y_trans_target = float(travel) * 0.85
    glide_start = max(10, split_frame - 15)
    glide_end = min(total_frames - 10, split_frame + 35)
    glide_len = max(1, glide_end - glide_start)

    with raw_h264_v3.open("wb") as f_out:
        for f in range(total_frames):
            if f < glide_start:
                # Subtle drift at top
                prog = f / float(max(1, glide_start))
                y_val = prog * y_drift_top
            elif f < glide_end:
                # Continuous glide through middle
                u = (f - glide_start) / float(glide_len)
                e = smootherstep(u)
                y_val = y_drift_top + e * (y_trans_target - y_drift_top)
            else:
                # Decelerate into bottom explosion
                u = (f - glide_end) / float(max(1, total_frames - glide_end - 1))
                e = smootherstep(u)
                y_val = y_trans_target + e * (float(travel) - y_trans_target)

            curr_nv12 = slice_subpixel_nv12(rgb_strip, y_val, height)
            packet = encoder.Encode(curr_nv12)
            if packet:
                f_out.write(extract_packet_bytes(packet))

        for flush_attr in ("EndEncode", "Flush", "flush"):
            if hasattr(encoder, flush_attr):
                try:
                    f_out.write(extract_packet_bytes(getattr(encoder, flush_attr)()))
                    break
                except Exception:
                    pass

    v3_mp4 = working_dir / f"{output_prefix}_variant3_stepped_glide.mp4"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-r", str(fps), "-i", str(raw_h264_v3),
            "-i", str(clip_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-shortest",
            str(v3_mp4),
        ],
        check=True,
    )
    results["variant3"] = v3_mp4

    # -------------------------------------------------------------------------
    # COMPARISON VIDEO: 3-in-1 Side-by-Side Presentation
    # -------------------------------------------------------------------------
    print("[sample_variants] Rendering 3-in-1 Side-by-Side Comparison Video...", flush=True)
    comp_mp4 = working_dir / f"{output_prefix}_comparison_all_variants.mp4"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(v1_mp4),
            "-i", str(v2_mp4),
            "-i", str(v3_mp4),
            "-filter_complex",
            "[0:v]scale=640:360[v0]; [1:v]scale=640:360[v1]; [2:v]scale=640:360[v2]; "
            "[v0][v1][v2]hstack=inputs=3,pad=1920:1080:0:(oh-ih)/2:color=0x0d0d12[outv]",
            "-map", "[outv]", "-map", "0:a",
            "-c:v", "h264_nvenc", "-preset", "p1",
            "-c:a", "copy",
            str(comp_mp4),
        ],
        check=True,
    )
    results["comparison"] = comp_mp4

    print(f"[sample_variants] Finished all sample variants for {output_prefix}!", flush=True)
    return results
