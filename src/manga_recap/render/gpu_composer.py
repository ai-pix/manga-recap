"""Ultra-fast, GPU-accelerated panel image compositing.

Replaces the legacy subprocess-heavy FFmpeg filtergraph for still preparation.
Supports:
1. Pure CUDA GPU tensor compositing via PyTorch when CUDA is available.
2. Fast multithreaded Pillow C-extension compositing when on CPU.
3. 100% in-memory processing without intermediate subprocess startup overhead.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageEnhance, ImageFilter

if TYPE_CHECKING:
    from .ffmpeg import Clip

# Global cache to check CUDA availability without re-querying
_CUDA_AVAILABLE: bool | None = None


def is_cuda_available() -> bool:
    global _CUDA_AVAILABLE
    if _CUDA_AVAILABLE is None:
        try:
            import torch
            _CUDA_AVAILABLE = bool(torch.cuda.is_available())
        except ImportError:
            _CUDA_AVAILABLE = False
    return _CUDA_AVAILABLE


def _even(value: float) -> int:
    """Round to an even integer for codec compatibility."""
    rounded = int(round(value))
    return rounded if rounded % 2 == 0 else rounded + 1


def _overscan_for(zoom_end: float) -> float:
    if zoom_end <= 1.001:
        return 1.0
    return zoom_end + 0.01


def _color_tuple(value: str) -> tuple[int, int, int]:
    val = value.strip().lstrip("#")
    if val.startswith("0x"):
        val = val[2:]
    if len(val) == 6:
        return (int(val[0:2], 16), int(val[2:4], 16), int(val[4:6], 16))
    return (13, 13, 18)


def compose_still_pillow(
    input_path: Path,
    output_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    background: str = "blurred",
    zoom_end: float = 1.0,
    blur_width: int = 128,
    blur_radius: int = 12,
    darken: float = 0.12,
) -> Path:
    """Compose one panel into a single finished frame using Pillow C-extensions."""
    overscan = _overscan_for(zoom_end)
    target_w = _even(width * overscan)
    target_h = _even(height * overscan)

    img = Image.open(input_path).convert("RGB")
    src_w, src_h = img.size

    # Fit foreground inside target canvas
    scale_fg = min(target_w / src_w, target_h / src_h)
    fg_w = max(1, int(round(src_w * scale_fg)))
    fg_h = max(1, int(round(src_h * scale_fg)))
    fg = img.resize((fg_w, fg_h), Image.Resampling.BILINEAR)

    x_off = (target_w - fg_w) // 2
    y_off = (target_h - fg_h) // 2

    if background != "blurred":
        # Solid background
        color = _color_tuple(background)
        canvas = Image.new("RGB", (target_w, target_h), color)
        canvas.paste(fg, (x_off, y_off))
    else:
        # Blurred background: scale down to blur_width, boxblur, scale to target, darken
        bw = max(16, min(blur_width, 256))
        bh = max(16, int(round(bw * src_h / src_w)))
        bg = img.resize((bw, bh), Image.Resampling.BILINEAR)
        bg = bg.filter(ImageFilter.BoxBlur(blur_radius))
        bg = bg.resize((target_w, target_h), Image.Resampling.BILINEAR)

        if darken > 0.001:
            bg = ImageEnhance.Brightness(bg).enhance(max(0.0, 1.0 - darken))

        bg.paste(fg, (x_off, y_off))
        canvas = bg

    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG", compress_level=1)
    return output_path


def compose_still_cuda(
    input_path: Path,
    output_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    background: str = "blurred",
    zoom_end: float = 1.0,
    blur_width: int = 128,
    blur_radius: int = 12,
    darken: float = 0.12,
) -> Path:
    """Compose one panel into a finished frame directly in GPU VRAM using PyTorch CUDA."""
    import numpy as np
    import torch
    import torch.nn.functional as F

    if not torch.cuda.is_available():
        raise RuntimeError(
            "[FATAL MANDATE VIOLATION] CUDA GPU is required for PyTorch video compositing!"
        )

    overscan = _overscan_for(zoom_end)
    target_w = _even(width * overscan)
    target_h = _even(height * overscan)

    # 1. Read image directly into PyTorch CUDA tensor [3, H, W] in float32
    img = Image.open(input_path).convert("RGB")
    arr = np.array(img, dtype=np.uint8)
    raw = torch.from_numpy(arr).permute(2, 0, 1).cuda().float()

    c, src_h, src_w = raw.shape
    raw_batch = raw.unsqueeze(0)  # [1, 3, H, W]

    # 2. Foreground fitting on CUDA
    scale_fg = min(target_w / src_w, target_h / src_h)
    fg_w = max(1, int(round(src_w * scale_fg)))
    fg_h = max(1, int(round(src_h * scale_fg)))
    fg_tensor = F.interpolate(
        raw_batch, size=(fg_h, fg_w), mode="bilinear", align_corners=False
    )[0]

    x_off = (target_w - fg_w) // 2
    y_off = (target_h - fg_h) // 2

    if background != "blurred":
        col = _color_tuple(background)
        canvas = (
            torch.tensor(col, dtype=torch.float32, device="cuda")
            .view(3, 1, 1)
            .repeat(1, target_h, target_w)
        )
    else:
        # 3. Blurred background 100% on CUDA GPU
        bw = max(16, min(blur_width, 256))
        bh = max(16, int(round(bw * src_h / src_w)))
        small = F.interpolate(raw_batch, size=(bh, bw), mode="bilinear", align_corners=False)

        # Fast separable 1D box blur kernel on CUDA
        k_size = max(3, blur_radius * 2 + 1)
        kernel = torch.ones(1, 1, k_size, device="cuda") / k_size
        blurred = F.conv1d(small.view(-1, 1, bw), kernel, padding=k_size // 2).view(1, 3, bh, bw)
        blurred = F.conv1d(
            blurred.permute(0, 1, 3, 2).reshape(-1, 1, bh), kernel, padding=k_size // 2
        )
        blurred = blurred.view(1, 3, bw, bh).permute(0, 1, 3, 2).contiguous()

        bg_tensor = F.interpolate(
            blurred, size=(target_h, target_w), mode="bilinear", align_corners=False
        )[0]
        if darken > 0.001:
            bg_tensor *= 1.0 - darken
        canvas = bg_tensor

    # 4. Overlay foreground on CUDA
    canvas[:, y_off : y_off + fg_h, x_off : x_off + fg_w] = fg_tensor
    canvas = canvas.clamp(0, 255).byte().permute(1, 2, 0).cpu().numpy()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(canvas).save(output_path, "PNG", compress_level=1)
    return output_path


def compose_still(
    input_path: Path,
    output_path: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    background: str = "blurred",
    zoom_end: float = 1.0,
    blur_width: int = 128,
    blur_radius: int = 12,
    darken: float = 0.12,
) -> Path:
    """Unified entry point: uses pure PyTorch CUDA on GPU, otherwise Pillow on local test."""
    if is_cuda_available():
        return compose_still_cuda(
            input_path,
            output_path,
            width=width,
            height=height,
            background=background,
            zoom_end=zoom_end,
            blur_width=blur_width,
            blur_radius=blur_radius,
            darken=darken,
        )
    return compose_still_pillow(
        input_path,
        output_path,
        width=width,
        height=height,
        background=background,
        zoom_end=zoom_end,
        blur_width=blur_width,
        blur_radius=blur_radius,
        darken=darken,
    )


def prepare_stills_fast(
    clips: list[Clip],
    stills_dir: Path,
    *,
    width: int = 1920,
    height: int = 1080,
    background: str = "blurred",
    zoom_end: float = 1.0,
    blur_width: int = 128,
    blur_radius: int = 12,
    darken: float = 0.12,
    workers: int = 16,
) -> dict[str, Path]:
    """Prepare all unique panel stills in parallel with pure in-memory execution."""
    stills_dir.mkdir(parents=True, exist_ok=True)
    wanted: dict[str, Clip] = {}
    for clip in clips:
        if clip.panel_id not in wanted:
            wanted[clip.panel_id] = clip

    total = len(wanted)
    print(f"[render] preparing {total} stills (pure GPU/in-memory, {workers} workers)...", flush=True)
    t0 = time.time()

    def process(item: tuple[str, Clip]) -> tuple[str, Path]:
        panel_id, clip = item
        target = stills_dir / f"{panel_id}.png"
        compose_still(
            clip.path,
            target,
            width=width,
            height=height,
            background=background,
            zoom_end=zoom_end,
            blur_width=blur_width,
            blur_radius=blur_radius,
            darken=darken,
        )
        return (panel_id, target)

    results: dict[str, Path] = {}
    max_w = min(total, max(1, workers))
    with ThreadPoolExecutor(max_workers=max_w) as pool:
        for pid, path in pool.map(process, wanted.items()):
            results[pid] = path

    print(f"[render] all {total} stills prepared in {time.time() - t0:.2f}s!", flush=True)
    return results
