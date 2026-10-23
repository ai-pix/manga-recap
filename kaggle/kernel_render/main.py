"""Kaggle kernel B: turn the timeline into the final video.

Runs on Kaggle, mostly CPU. Reads the panels, the storyboard and the timeline
from the input datasets, and writes `07_final.mp4` plus a render manifest to
/kaggle/working.

Visual style lives in `manga_recap.render.kenburns`, the ffmpeg graph in
`manga_recap.render.ffmpeg`. Neither change touches this file.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

WORKING = Path("/kaggle/working")
# /kaggle/input is mounted read-only, so the payload cannot be unpacked there.
# Everything the kernel reads after the download lives under /kaggle/working.
INPUT_ROOT = WORKING / "payload"
VIDEO_NAME = "07_final.mp4"
MANIFEST_NAME = "07_render_manifest.json"
SYNC_NAME = "07_sync_report.json"
LOG_NAME = "render_log.txt"


class LogTee:
    """Tee stdout to both the console and a persistent log file in /kaggle/working."""

    def __init__(self, filepath: Path):
        self.file = filepath.open("w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, data: str) -> int:
        self.stdout.write(data)
        self.stdout.flush()
        self.file.write(data)
        self.file.flush()
        return len(data)

    def flush(self) -> None:
        self.stdout.flush()
        self.file.flush()

    def close(self) -> None:
        self.file.close()

CHUNK_BYTES = 1024 * 1024

# Some free file hosts refuse a bare urllib request and close the connection
# without a response. They serve the file fine to anything that identifies
# itself as a browser, so the download says so. Verified against catbox:
# the default agent gets RemoteDisconnected, this one gets the zip.
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    )
}

# Replaced with the real URL by the stage when it stages a push. It cannot live
# in a neighbouring file: Kaggle runs a script kernel as `/kaggle/src/script.py`,
# so nothing the push put beside main.py is next to the running code.
#
# The sentinel is a separate constant on purpose. The stage rewrites only the
# right-hand side of the assignment below, and if the token also appeared in the
# comparison that detects an unset URL, that comparison would be rewritten too
# and the kernel would never see a URL as set.
PAYLOAD_UNSET = "__PAYLOAD_URL__"
PAYLOAD_URL = PAYLOAD_UNSET

SEARCH_NAMES = ("job.json", "script.json", "timeline.json", "narration.wav", "panel_index.json")


def _payload_url() -> str:
    """Where this run's inputs are hosted. See the TTS kernel for the rationale."""
    if PAYLOAD_URL != PAYLOAD_UNSET and PAYLOAD_URL:
        return PAYLOAD_URL.strip()

    for candidate in (
        Path(__file__).resolve().parent / "payload_url.txt",
        Path("/kaggle/src/payload_url.txt"),
        Path("/kaggle/working/payload_url.txt"),
    ):
        if candidate.exists():
            value = candidate.read_text(encoding="utf-8").strip()
            if value:
                return value

    raise FileNotFoundError(
        "This kernel has no payload URL. `manga render` writes one into the "
        "kernel it pushes; pushing this directory by hand will not work."
    )


def _download(request, attempts: int = 4):
    """Open a URL, retrying a few times. See the TTS kernel for the rationale."""
    delay = 5
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return urllib.request.urlopen(request, timeout=900)
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  download attempt {attempt}/{attempts} failed: {exc}", flush=True)
            if attempt < attempts:
                time.sleep(delay)
                delay = min(delay * 2, 60)
    raise RuntimeError(f"could not download the payload after {attempts} attempts: {last}")


def fetch_payload() -> Path:
    """Download the payload archive and unpack it.

    Everything stage 5 needs — the panels, the script, the narration audio, the
    timeline — arrives in one zip at a URL. The previous design attached two
    Kaggle Datasets and searched both mounts for each file, which meant guessing
    which mount a given file lived in. One archive removes the guess.

    The URL is compiled into PAYLOAD_URL by the stage at push time, because a
    Kaggle script kernel runs as /kaggle/src/script.py and a file placed beside
    main.py is not next to the running code.
    """
    url = _payload_url()

    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    archive = INPUT_ROOT / "payload.zip"

    headers = {"User-Agent": "curl/7.88.1"} if "filebin.net" in url else FETCH_HEADERS
    print(f"downloading payload from {url}", flush=True)
    request = urllib.request.Request(url, headers=headers)
    with _download(request) as response, archive.open("wb") as out:
        shutil.copyfileobj(response, out, CHUNK_BYTES)
    print(f"payload is {archive.stat().st_size / 1_000_000:.1f} MB, unpacking", flush=True)

    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(INPUT_ROOT)
    archive.unlink()
    return INPUT_ROOT


def find(name: str) -> Path:
    """Locate a file anywhere under INPUT_ROOT, in a stable order."""
    for candidate in sorted(INPUT_ROOT.rglob(name)):
        if candidate.is_file():
            return candidate
    for candidate in sorted(INPUT_ROOT.rglob(f"*{name}")):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"{name} not found anywhere under {INPUT_ROOT}")


def find_panels_dir() -> Path:
    """The directory holding panel_*.png or panel_*.jpg."""
    for directory in sorted(INPUT_ROOT.rglob("panels")):
        if directory.is_dir() and (any(directory.glob("panel_*.png")) or any(directory.glob("panel_*.jpg"))):
            return directory
    for candidate in sorted(list(INPUT_ROOT.rglob("panel_*.png")) + list(INPUT_ROOT.rglob("panel_*.jpg"))):
        return candidate.parent
    raise FileNotFoundError(
        f"No panel_* images found under {INPUT_ROOT}. The render payload carries the "
        "chapter's panel crops."
    )


def has_nvenc(executable: str | None = None) -> bool:
    """Check if FFmpeg supports and can run h264_nvenc hardware acceleration."""
    exe = executable or shutil.which("ffmpeg")
    if exe is None:
        return False

    cuda_dirs = [
        "/usr/local/nvidia/lib64",
        "/usr/local/nvidia/lib",
        "/usr/local/cuda/compat",
        "/usr/local/cuda/lib64",
        "/usr/lib/x86_64-linux-gnu",
    ]
    env = os.environ.copy()
    current_ld = env.get("LD_LIBRARY_PATH", "")
    new_dirs = [d for d in cuda_dirs if Path(d).is_dir()]
    if new_dirs:
        env["LD_LIBRARY_PATH"] = ":".join(new_dirs + ([current_ld] if current_ld else []))

    try:
        res = subprocess.run(
            [
                exe, "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc=duration=0.5:size=256x256:rate=30",
                "-pix_fmt", "yuv420p",
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
            print(f"[nvenc_probe] NVENC check note ({exe}): {res.stderr.strip()}", flush=True)
        return False
    except Exception as exc:  # noqa: BLE001
        print(f"[nvenc_probe] NVENC check exception ({exe}): {exc}", flush=True)
        return False


def get_gpu_count() -> int:
    """Detect available NVIDIA GPUs via nvidia-smi."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return 1
    try:
        res = subprocess.run(
            [smi, "--query-gpu=count", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if res.returncode == 0:
            lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
            if lines:
                return max(1, int(lines[0]))
    except Exception:  # noqa: BLE001
        pass
    return 1


_CUDA_DEVICE_CACHE: dict[tuple[str, int], bool] = {}


def has_cuda_device(executable: str | None = None, gpu_id: int = 0) -> bool:
    """Check if FFmpeg supports CUDA hardware device initialization and hwupload_cuda."""
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
        if not ok and res.stderr:
            print(f"[cuda_probe] CUDA check note ({exe}): {res.stderr.strip()}", flush=True)
        _CUDA_DEVICE_CACHE[cache_key] = ok
        return ok
    except Exception as exc:  # noqa: BLE001
        print(f"[cuda_probe] CUDA check exception ({exe}) on GPU {gpu_id}: {exc}", flush=True)
        _CUDA_DEVICE_CACHE[cache_key] = False
        return False


def ensure_nvenc_ffmpeg() -> str:
    """Ensure an FFmpeg binary with NVENC and CUDA filter support is available on Kaggle."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        raise RuntimeError(
            "[FATAL MANDATE VIOLATION] No NVIDIA GPU detected on Kaggle! "
            "CPU execution is strictly prohibited by project mandate."
        )

    system_exe = shutil.which("ffmpeg") or "ffmpeg"
    system_has_nvenc = has_nvenc(system_exe)
    system_has_cuda = system_has_nvenc and has_cuda_device(system_exe, 0)

    if system_has_cuda:
        print(f"[kernel] Existing ffmpeg supports both NVENC and CUDA filters: {system_exe}", flush=True)
        return system_exe

    print(
        f"[kernel] Existing ffmpeg ({system_exe}) NVENC={system_has_nvenc}, CUDA={system_has_cuda}. "
        "Searching for CUDA-enabled build...",
        flush=True,
    )

    # 1. Check permanent Kaggle storage dataset (/kaggle/input/manga-recap-render-bin)
    candidate_mount_dirs = [
        Path("/kaggle/input/manga-recap-render-bin"),
    ] + [p for p in Path("/kaggle/input").glob("*render-bin*") if p.is_dir()]

    for mount_dir in candidate_mount_dirs:
        if not mount_dir.exists():
            continue
        for found_exe in sorted(mount_dir.rglob("ffmpeg")):
            if found_exe.is_file():
                print(f"[kernel] Found permanent storage FFmpeg at: {found_exe}", flush=True)
                target_dir = WORKING / "bin"
                target_dir.mkdir(parents=True, exist_ok=True)
                target_exe = target_dir / "ffmpeg"
                try:
                    shutil.copy2(found_exe, target_exe)
                    # Also copy ffprobe if present beside it
                    probe_candidate = found_exe.parent / "ffprobe"
                    if probe_candidate.is_file():
                        shutil.copy2(probe_candidate, target_dir / "ffprobe")
                        (target_dir / "ffprobe").chmod(0o755)
                    target_exe.chmod(0o755)

                    if has_nvenc(str(target_exe)) and has_cuda_device(str(target_exe), 0):
                        os.environ["PATH"] = f"{target_dir}:{os.environ.get('PATH', '')}"
                        print(
                            f"[kernel] SUCCESS: Mounted permanent CUDA+NVENC FFmpeg instantly from {mount_dir.name}!",
                            flush=True,
                        )
                        return str(target_exe)
                    print(f"[kernel] Permanent binary at {target_exe} did not pass has_cuda_device()", flush=True)
                except Exception as exc:
                    print(f"[kernel] Note: could not initialize permanent FFmpeg from {found_exe}: {exc}", flush=True)

    print("[kernel] Probing driver-compatible CUDA+NVENC FFmpeg builds for Kaggle T4...", flush=True)
    ffmpeg_dir = WORKING / "ffmpeg_static"
    for candidate in ffmpeg_dir.rglob("ffmpeg"):
        if candidate.is_file():
            if has_nvenc(str(candidate)) and has_cuda_device(str(candidate), 0):
                os.environ["PATH"] = f"{candidate.parent}:{os.environ.get('PATH', '')}"
                print(f"[kernel] Using cached CUDA+NVENC ffmpeg: {candidate}", flush=True)
                return str(candidate)

    candidate_urls = [
        # Driver 550+ / CUDA 12.4 compatible (Jellyfin 7.1.4):
        "https://github.com/jellyfin/jellyfin-ffmpeg/releases/download/v7.1.4-3/jellyfin-ffmpeg_7.1.4-3_portable_linux64-gpl.tar.xz",
        # Driver 535+ / CUDA 12.2 compatible (Jellyfin 6.0.1):
        "https://github.com/jellyfin/jellyfin-ffmpeg/releases/download/v6.0.1-7/jellyfin-ffmpeg_6.0.1-7_portable_linux64-gpl.tar.xz",
    ]

    tar_path = WORKING / "ffmpeg_static.tar.xz"
    for url in candidate_urls:
        try:
            print(f"[kernel] Fetching CUDA+NVENC FFmpeg from {url}...", flush=True)
            req = urllib.request.Request(url, headers=FETCH_HEADERS)
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=120) as resp, tar_path.open("wb") as out:
                shutil.copyfileobj(resp, out, CHUNK_BYTES)
            dl_time = time.time() - t0
            print(
                f"[kernel] Downloaded ({tar_path.stat().st_size / 1_000_000:.1f} MB in {dl_time:.1f}s)",
                flush=True,
            )

            shutil.rmtree(ffmpeg_dir, ignore_errors=True)
            ffmpeg_dir.mkdir(parents=True, exist_ok=True)
            t1 = time.time()
            res = subprocess.run(
                ["tar", "-xf", str(tar_path), "-C", str(ffmpeg_dir)],
                capture_output=True,
                text=True,
            )
            if res.returncode != 0:
                print(f"[kernel] tar extraction note: {res.stderr}", flush=True)
            tar_path.unlink(missing_ok=True)
            print(f"[kernel] Extracted build in {time.time() - t1:.1f}s", flush=True)

            ffmpeg_bins = list(ffmpeg_dir.rglob("ffmpeg"))
            if ffmpeg_bins:
                found_bin = [b for b in ffmpeg_bins if b.is_file()][0]
                new_exe = str(found_bin)
                if has_nvenc(new_exe) and has_cuda_device(new_exe, 0):
                    os.environ["PATH"] = f"{found_bin.parent}:{os.environ.get('PATH', '')}"
                    print("[kernel] SUCCESS: CUDA filters + NVENC hardware encoding are now ACTIVE on Kaggle T4 GPU!", flush=True)
                    return str(new_exe)
                print(f"[kernel] Build at {found_bin} did not pass has_cuda_device(), trying next candidate...", flush=True)
        except Exception as exc:
            print(f"[kernel] Attempt failed: {exc}", flush=True)

    if system_has_nvenc:
        print("[kernel] Note: Using verified system NVENC FFmpeg (without CUDA filters)", flush=True)
        return system_exe

    raise RuntimeError(
        "[FATAL MANDATE VIOLATION] Hardware NVENC could not be initialized on Kaggle GPU! "
        "CPU software encoding (libx264) is strictly prohibited by project mandate. "
        "Ensure GPU accelerator is attached and driver is compatible."
    )


def test_pynvvideocodec_benchmark() -> None:
    """Benchmark PyNvVideoCodec zero-copy encoding directly from PyTorch CUDA tensors in VRAM."""
    print("=" * 70, flush=True)
    print("[benchmark] PROBING PYNVVIDEOCODEC HARDWARE ENCODING IN VRAM", flush=True)
    try:
        print("[benchmark] Installing PyNvVideoCodec...", flush=True)
        t_inst = time.time()
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "PyNvVideoCodec"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        print(f"[benchmark] pip install took {time.time() - t_inst:.1f}s", flush=True)
        if res.returncode != 0:
            print(f"[benchmark] pip install note: {res.stderr.strip()[:300]}", flush=True)
            print("=" * 70, flush=True)
            return

        import PyNvVideoCodec as nvc
        import torch

        if not torch.cuda.is_available():
            print("[benchmark] PyTorch CUDA not available!", flush=True)
            print("=" * 70, flush=True)
            return

        # Bridge PyTorch DLPack positional stream mismatch for PyNvVideoCodec C++
        orig_dlpack = torch.Tensor.__dlpack__

        def patched_dlpack(self, stream=None, *args, **kwargs):
            if stream is not None:
                try:
                    return orig_dlpack(self, stream=stream)
                except Exception:
                    pass
            return orig_dlpack(self)

        torch.Tensor.__dlpack__ = patched_dlpack

        ver = getattr(nvc, "__version__", "unknown")
        print(f"[benchmark] Successfully imported PyNvVideoCodec! Version: {ver}", flush=True)
        apis = [a for a in dir(nvc) if not a.startswith("_")]
        print(f"[benchmark] Available APIs in nvc: {apis}", flush=True)

        w, h = 1920, 1080
        test_frames = 30
        print(f"[benchmark] Initializing hardware encoder for {w}x{h} NV12 on GPU 0...", flush=True)

        encoder = None
        if hasattr(nvc, "CreateEncoder"):
            try:
                encoder = nvc.CreateEncoder(w, h, "NV12", True)
            except Exception as e:  # noqa: BLE001
                print(f"[benchmark] CreateEncoder with 4 args failed: {e}", flush=True)

        if encoder is None and hasattr(nvc, "PyNvEncoder"):
            try:
                encoder = nvc.PyNvEncoder(w, h, "NV12", 0)
            except Exception as e:  # noqa: BLE001
                print(f"[benchmark] PyNvEncoder failed: {e}", flush=True)

        if encoder is None:
            print("[benchmark] Could not create encoder with standard signatures", flush=True)
            print("=" * 70, flush=True)
            return

        nv12_h = int(h * 1.5)
        cuda_frame = torch.zeros((nv12_h, w), dtype=torch.uint8, device="cuda:0")

        print(f"[benchmark] Encoding {test_frames} 1080p frames directly from PyTorch VRAM...", flush=True)
        t0 = time.time()
        total_bytes = 0
        from manga_recap.render.pynv_renderer import _extract_packet_bytes

        for i in range(test_frames):
            cuda_frame[0, 0] = i % 255
            bs = encoder.Encode(cuda_frame) if hasattr(encoder, "Encode") else None
            if bs:
                total_bytes += len(_extract_packet_bytes(bs))

        elapsed = time.time() - t0
        fps = test_frames / max(0.001, elapsed)
        print(
            f"[benchmark] SUCCESS: {test_frames} 1080p frames encoded in {elapsed:.3f}s ({fps:.1f} FPS) -> "
            f"{total_bytes / 1_000_000:.2f} MB bitstream!",
            flush=True,
        )
        print("=" * 70, flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[benchmark] PyNvVideoCodec probe exception: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        print("=" * 70, flush=True)


def _smootherstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _rgb_to_nv12(rgb_tensor):
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


def _slice_subpixel_nv12(rgb_strip, y_float: float, height: int):
    import torch

    strip_h = rgb_strip.shape[0]
    max_y0 = strip_h - height
    if max_y0 <= 0:
        return _rgb_to_nv12(rgb_strip[:height, :, :])

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

    return _rgb_to_nv12(sub_rgb)


def _cubic_bezier(p1x: float, p1y: float, p2x: float, p2y: float, t: float) -> float:
    """Exact cubic bezier curve evaluator (identical to After Effects Graph Editor)."""
    t = max(0.0, min(1.0, t))
    cur_t = t
    for _ in range(12):
        u = cur_t
        om = 1.0 - u
        x = 3.0 * om * om * u * p1x + 3.0 * om * u * u * p2x + u * u * u
        dx = 3.0 * (1.0 - 4.0 * u + 3.0 * u * u) * p1x + 3.0 * (2.0 * u - 3.0 * u * u) * p2x + 3.0 * u * u
        if abs(dx) < 1e-7:
            break
        diff = x - t
        cur_t -= diff / dx
        cur_t = max(0.0, min(1.0, cur_t))
    u = cur_t
    om = 1.0 - u
    return 3.0 * om * om * u * p1y + 3.0 * om * u * u * p2y + u * u * u


def _ae_easy_ease_in_out(t: float) -> float:
    """After Effects F9 Easy Ease (0.33, 0.0, 0.67, 1.0) with zero initial & final jerk."""
    return _cubic_bezier(0.33, 0.0, 0.67, 1.0, t)


def _ae_cinematic_ease(t: float) -> float:
    """Cinematic AE curve (0.25, 0.1, 0.25, 1.0) with silky glide and extended deceleration cushion."""
    return _cubic_bezier(0.25, 0.1, 0.25, 1.0, t)


def _gaussian_blur_2pass(tensor_bchw, sigma: float = 8.0):
    """True 2-pass separable Gaussian blur executed live on CUDA tensor cores."""
    import math

    import torch
    import torch.nn.functional as F

    device = tensor_bchw.device
    channels = tensor_bchw.shape[1]
    radius = int(math.ceil(3.0 * sigma))
    x = torch.arange(-radius, radius + 1, dtype=torch.float32, device=device)
    k = torch.exp(-0.5 * (x / sigma) ** 2)
    kernel = (k / k.sum()).view(1, 1, -1)
    weight_x = kernel.repeat(channels, 1, 1).unsqueeze(2)
    weight_y = kernel.repeat(channels, 1, 1).unsqueeze(3)
    pad = radius
    h = F.conv2d(tensor_bchw, weight_x, padding=(0, pad), groups=channels)
    return F.conv2d(h, weight_y, padding=(pad, 0), groups=channels)


def _generate_cinematic_backdrop(raw_batch, out_h: int = 1080, out_w: int = 1920, sigma: float = 8.5):
    """Compute high-quality professional blurred backdrop on-the-fly during rendering."""
    import torch
    import torch.nn.functional as F

    # 1. Scaled down to proxy resolution (640x360) for velvety smooth wide-radius blur
    proxy_w, proxy_h = 640, 360
    proxy = F.interpolate(raw_batch, size=(proxy_h, proxy_w), mode="bilinear", align_corners=False)
    blurred_proxy = _gaussian_blur_2pass(proxy, sigma=sigma)

    # 2. Rescale back up to 1080p canvas with bicubic interpolation
    bg = F.interpolate(blurred_proxy, size=(out_h, out_w), mode="bicubic", align_corners=False)

    # 3. Apply subtle darkening and cinematic radial vignette
    device = raw_batch.device
    yy = torch.linspace(-1.0, 1.0, out_h, device=device).view(-1, 1).repeat(1, out_w)
    xx = torch.linspace(-1.0, 1.0, out_w, device=device).view(1, -1).repeat(out_h, 1)
    vignette = 1.0 - 0.22 * (xx ** 2 + yy ** 2).clamp(0.0, 1.0)
    bg = bg * vignette.unsqueeze(0).unsqueeze(0) * 0.82
    return bg


def _blit_card_subpixel(
    canvas,  # (1, 3, H, W) float
    card,    # (1, 3, Hc, Wc) float
    cx: float,
    cy: float,
    opacity: float = 1.0,
    shadow: bool = False,
) -> None:
    """Blit card onto canvas with floating-point subpixel positioning and continuous anti-aliased edge alpha."""
    import torch
    import torch.nn.functional as F

    if opacity <= 0.001:
        return

    _, _, H, W = canvas.shape
    _, _, Hc, Wc = card.shape
    device = canvas.device

    x_min = cx - Wc / 2.0
    x_max = cx + Wc / 2.0
    y_min = cy - Hc / 2.0
    y_max = cy + Hc / 2.0

    x0 = max(0, int(torch.floor(torch.tensor(x_min)).item()))
    x1 = min(W, int(torch.ceil(torch.tensor(x_max)).item()) + 1)
    y0 = max(0, int(torch.floor(torch.tensor(y_min)).item()))
    y1 = min(H, int(torch.ceil(torch.tensor(y_max)).item()) + 1)

    box_w = x1 - x0
    box_h = y1 - y0
    if box_w <= 1 or box_h <= 1:
        return

    if shadow and opacity > 0.1:
        sx0 = max(0, x0 + 12)
        sx1 = min(W, x1 + 12)
        sy0 = max(0, y0 + 16)
        sy1 = min(H, y1 + 16)
        sw = sx1 - sx0
        sh = sy1 - sy0
        if sw > 1 and sh > 1:
            canvas[:, :, sy0:sy1, sx0:sx1] = canvas[:, :, sy0:sy1, sx0:sx1] * 0.35

    yy = torch.arange(y0, y1, device=device).view(-1, 1).repeat(1, box_w).float()
    xx = torch.arange(x0, x1, device=device).view(1, -1).repeat(box_h, 1).float()

    card_x = xx - x_min
    card_y = yy - y_min

    norm_x = 2.0 * card_x / max(1.0, float(Wc - 1)) - 1.0
    norm_y = 2.0 * card_y / max(1.0, float(Hc - 1)) - 1.0
    grid = torch.stack([norm_x, norm_y], dim=-1).unsqueeze(0)

    patch = F.grid_sample(card, grid, mode="bilinear", padding_mode="zeros", align_corners=False)

    # Continuous subpixel anti-aliasing on the card perimeter
    edge_alpha_x = torch.clamp(card_x + 0.5, 0.0, 1.0) * torch.clamp((float(Wc) - card_x) + 0.5, 0.0, 1.0)
    edge_alpha_y = torch.clamp(card_y + 0.5, 0.0, 1.0) * torch.clamp((float(Hc) - card_y) + 0.5, 0.0, 1.0)
    subpixel_alpha = (edge_alpha_x * edge_alpha_y).unsqueeze(0).unsqueeze(0)

    alpha = subpixel_alpha * opacity
    canvas[:, :, y0:y1, x0:x1] = canvas[:, :, y0:y1, x0:x1] * (1.0 - alpha) + patch * alpha


def _create_card_with_border(crop_tensor, target_h: int, target_w: int, border_w: int = 4):
    import torch
    import torch.nn.functional as F

    device = crop_tensor.device
    raw_batch = crop_tensor.unsqueeze(0)
    resized = F.interpolate(raw_batch, size=(target_h, target_w), mode="bilinear", align_corners=False)[0]

    H_tot = target_h + 2 * border_w
    W_tot = target_w + 2 * border_w
    framed = torch.full((1, 3, H_tot, W_tot), 18.0, dtype=torch.float32, device=device)
    framed[:, :, 1 : H_tot - 1, 1 : W_tot - 1] = 55.0
    framed[:, :, border_w : border_w + target_h, border_w : border_w + target_w] = resized
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
    import numpy as np
    import PyNvVideoCodec as nvc
    import torch
    from PIL import Image

    from manga_recap.render.pynv_renderer import _extract_packet_bytes

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

    clip_audio = working_dir / f"{output_prefix}_audio.wav"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(audio_path),
            "-ss", f"{start_sec:.3f}",
            "-t", f"{dur_sec:.3f}",
            str(clip_audio),
        ],
        check=True,
    )

    with Image.open(panel_path) as img:
        arr = np.array(img.convert("RGB"), dtype=np.uint8)
    raw = torch.from_numpy(arr).permute(2, 0, 1).to(device=device, dtype=torch.float32)
    _, src_h, src_w = raw.shape
    raw_batch = raw.unsqueeze(0)

    # Compute professional high-quality Gaussian blurred backdrop on-the-fly during render
    bg_batch = _generate_cinematic_backdrop(raw_batch, out_h=height, out_w=width, sigma=8.5)

    results = {}

    card_h = 960
    card_w = 560
    sec_len = min(src_h, int(round(src_w * 1.85)))
    top_crop = raw[:, :sec_len, :]
    bot_crop = raw[:, max(0, src_h - sec_len) :, :]
    card1 = _create_card_with_border(top_crop, card_h, card_w, border_w=4)
    card2 = _create_card_with_border(bot_crop, card_h, card_w, border_w=4)

    target_x1 = 656.0
    target_x2 = 1264.0
    target_y = 540.0

    # =========================================================================
    # VARIANT 2A: Buttery F9 Easy Ease (0.33, 0.0, 0.67, 1.0)
    # Natural 36-frame slide with zero initial jerk and seamless cushion
    # =========================================================================
    print(f"[sample_variants] [{output_prefix}] Rendering Variant 2A (Buttery F9 Easy Ease)...", flush=True)
    encoder = nvc.CreateEncoder(width, height, "NV12", True)
    raw_h264_2a = working_dir / f"{output_prefix}_2a.h264"
    with raw_h264_2a.open("wb") as f_out:
        for f in range(total_frames):
            canvas = bg_batch.clone()
            if f < split_frame:
                u = min(1.0, f / 24.0)
                e = _ae_easy_ease_in_out(u)
                cx1 = (960.0 - 40.0) + e * 40.0
                op1 = min(1.0, f / 14.0)
                _blit_card_subpixel(canvas, card1, cx1, target_y, opacity=op1)
            else:
                u = min(1.0, (f - split_frame) / 36.0)
                e = _ae_easy_ease_in_out(u)
                cx1 = 960.0 - e * (960.0 - target_x1)
                cx2 = (target_x2 + 80.0) - e * 80.0
                op2 = min(1.0, (f - split_frame) / 16.0)
                _blit_card_subpixel(canvas, card1, cx1, target_y, opacity=1.0)
                _blit_card_subpixel(canvas, card2, cx2, target_y, opacity=op2)

            rgb_canvas = canvas[0].clamp(0, 255).to(torch.uint8).permute(1, 2, 0).contiguous()
            nv12 = _rgb_to_nv12(rgb_canvas)
            packet = encoder.Encode(nv12)
            if packet:
                f_out.write(_extract_packet_bytes(packet))

        for flush_attr in ("EndEncode", "Flush", "flush"):
            if hasattr(encoder, flush_attr):
                try:
                    f_out.write(_extract_packet_bytes(getattr(encoder, flush_attr)()))
                    break
                except Exception:
                    pass

    s2a_mp4 = working_dir / f"{output_prefix}_style2A_f9_easy_ease.mp4"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-r", str(fps), "-i", str(raw_h264_2a),
            "-i", str(clip_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(s2a_mp4),
        ],
        check=True,
    )
    results["style2a"] = s2a_mp4

    # =========================================================================
    # VARIANT 2B: Cinematic Flow (0.25, 0.1, 0.25, 1.0) with 40-Frame Deceleration Cushion
    # Card 1 glides effortlessly; Card 2 enters with a 4-frame stagger
    # =========================================================================
    print(f"[sample_variants] [{output_prefix}] Rendering Variant 2B (Cinematic Flow Cushion)...", flush=True)
    encoder = nvc.CreateEncoder(width, height, "NV12", True)
    raw_h264_2b = working_dir / f"{output_prefix}_2b.h264"
    with raw_h264_2b.open("wb") as f_out:
        for f in range(total_frames):
            canvas = bg_batch.clone()
            if f < split_frame:
                u = min(1.0, f / 24.0)
                e = _ae_cinematic_ease(u)
                cx1 = (960.0 - 50.0) + e * 50.0
                op1 = min(1.0, f / 14.0)
                _blit_card_subpixel(canvas, card1, cx1, target_y, opacity=op1)
            else:
                # Card 1 slides left over 38 frames
                u1 = min(1.0, (f - split_frame) / 38.0)
                e1 = _ae_cinematic_ease(u1)
                cx1 = 960.0 - e1 * (960.0 - target_x1)

                # Card 2 has a subtle 3-frame staggered follow-through entrance
                f_rel2 = max(0, f - split_frame - 3)
                u2 = min(1.0, f_rel2 / 36.0)
                e2 = _ae_cinematic_ease(u2)
                cx2 = (target_x2 + 70.0) - e2 * 70.0
                op2 = 0.0 if (f - split_frame) < 3 else min(1.0, f_rel2 / 16.0)

                _blit_card_subpixel(canvas, card1, cx1, target_y, opacity=1.0)
                if op2 > 0.001:
                    _blit_card_subpixel(canvas, card2, cx2, target_y, opacity=op2)

            rgb_canvas = canvas[0].clamp(0, 255).to(torch.uint8).permute(1, 2, 0).contiguous()
            nv12 = _rgb_to_nv12(rgb_canvas)
            packet = encoder.Encode(nv12)
            if packet:
                f_out.write(_extract_packet_bytes(packet))

        for flush_attr in ("EndEncode", "Flush", "flush"):
            if hasattr(encoder, flush_attr):
                try:
                    f_out.write(_extract_packet_bytes(getattr(encoder, flush_attr)()))
                    break
                except Exception:
                    pass

    s2b_mp4 = working_dir / f"{output_prefix}_style2B_cinematic_flow.mp4"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-r", str(fps), "-i", str(raw_h264_2b),
            "-i", str(clip_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(s2b_mp4),
        ],
        check=True,
    )
    results["style2b"] = s2b_mp4

    # =========================================================================
    # VARIANT 2C: Gentle S-Curve Glide with Overlapping Depth
    # Card 1 slides gracefully; Card 2 slides with soft depth elevation
    # =========================================================================
    print(f"[sample_variants] [{output_prefix}] Rendering Variant 2C (Gentle Depth Glide)...", flush=True)
    encoder = nvc.CreateEncoder(width, height, "NV12", True)
    raw_h264_2c = working_dir / f"{output_prefix}_2c.h264"
    with raw_h264_2c.open("wb") as f_out:
        for f in range(total_frames):
            canvas = bg_batch.clone()
            if f < split_frame:
                u = min(1.0, f / 24.0)
                e = _ae_easy_ease_in_out(u)
                cx1 = (960.0 - 45.0) + e * 45.0
                op1 = min(1.0, f / 14.0)
                _blit_card_subpixel(canvas, card1, cx1, target_y, opacity=op1)
            else:
                u = min(1.0, (f - split_frame) / 36.0)
                e = _ae_easy_ease_in_out(u)
                cx1 = 960.0 - e * (960.0 - target_x1)
                cx2 = (target_x2 + 75.0) - e * 75.0
                op2 = min(1.0, (f - split_frame) / 16.0)
                _blit_card_subpixel(canvas, card1, cx1, target_y, opacity=1.0)
                _blit_card_subpixel(canvas, card2, cx2, target_y, opacity=op2, shadow=True)

            rgb_canvas = canvas[0].clamp(0, 255).to(torch.uint8).permute(1, 2, 0).contiguous()
            nv12 = _rgb_to_nv12(rgb_canvas)
            packet = encoder.Encode(nv12)
            if packet:
                f_out.write(_extract_packet_bytes(packet))

        for flush_attr in ("EndEncode", "Flush", "flush"):
            if hasattr(encoder, flush_attr):
                try:
                    f_out.write(_extract_packet_bytes(getattr(encoder, flush_attr)()))
                    break
                except Exception:
                    pass

    s2c_mp4 = working_dir / f"{output_prefix}_style2C_gentle_depth.mp4"
    subprocess.run(
        [
            exe, "-y", "-hide_banner", "-loglevel", "error",
            "-r", str(fps), "-i", str(raw_h264_2c),
            "-i", str(clip_audio),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(s2c_mp4),
        ],
        check=True,
    )
    results["style2c"] = s2c_mp4

    # Generate 3-in-1 Side-by-Side Comparison of the 3 buttery smooth motions
    print(f"[sample_variants] [{output_prefix}] Rendering 3-in-1 Comparison Video...", flush=True)
    comp_mp4 = working_dir / f"{output_prefix}_comparison_buttery_smooth.mp4"
    try:
        subprocess.run(
            [
                exe, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(s2a_mp4),
                "-i", str(s2b_mp4),
                "-i", str(s2c_mp4),
                "-filter_complex",
                "[0:v]scale=640:360[v0]; [1:v]scale=640:360[v1]; [2:v]scale=640:360[v2]; "
                "[v0][v1][v2]hstack=inputs=3,pad=1920:1080:0:(oh-ih)/2:color=0x0d0d12[outv]",
                "-map", "[outv]", "-map", "0:a",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "copy",
                str(comp_mp4),
            ],
            check=True,
        )
        results["comparison"] = comp_mp4
    except Exception as exc:  # noqa: BLE001
        print(f"[sample_variants] Note: comparison mux exception ({exc})", flush=True)

    print(f"[sample_variants] Finished all buttery smooth styles for {output_prefix}!", flush=True)
    return results


def run_all_sample_variants(panels_dir: Path, audio: Path, exe: str, working_dir: Path) -> dict:
    import torch
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    targets = [
        {
            "panel_id": "panel_0057",
            "start": 313.80,
            "end": 320.25,
            "split": 315.66,
        },
        {
            "panel_id": "panel_0034",
            "start": 187.38,
            "end": 193.60,
            "split": 190.37,
        },
    ]

    all_results = {}
    for t in targets:
        pid = t["panel_id"]
        p_path = panels_dir / f"{pid}.jpg"
        if not p_path.exists():
            p_path = panels_dir / f"{pid}.png"
        if not p_path.exists():
            print(f"[sample_variants] Warning: {pid} not found in {panels_dir}, skipping", flush=True)
            continue

        res = render_sample_variants_for_panel(
            panel_path=p_path,
            audio_path=audio,
            start_sec=t["start"],
            end_sec=t["end"],
            split_sec=t["split"],
            output_prefix=pid,
            exe=exe,
            working_dir=working_dir,
            device=device,
        )
        all_results[pid] = res

    manifest_data = {
        "targets": targets,
        "results": {k: {name: str(p.name) for name, p in res.items()} for k, res in all_results.items()},
    }
    (working_dir / "samples_manifest.json").write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
    return all_results


RUN_SAMPLE_VARIANTS = False


def main() -> int:
    started = time.time()
    WORKING.mkdir(parents=True, exist_ok=True)
    sys.stdout = LogTee(WORKING / LOG_NAME)

    print("=" * 70, flush=True)
    print("[kernel] HARDWARE ENVIRONMENT PROBE", flush=True)
    import subprocess
    smi = shutil.which("nvidia-smi")
    if smi:
        res = subprocess.run([smi], capture_output=True, text=True)
        print(res.stdout, flush=True)
    else:
        print("[kernel] nvidia-smi not found (CPU only)", flush=True)
    print("=" * 70, flush=True)

    payload_root = fetch_payload()

    # The repo's src/ is uploaded alongside the kernel so the render modules are
    # importable, which keeps the style logic identical to the local copy. The
    # payload's lib/ carries this kernel's own helpers.
    ensure_src_on_path(payload_root)

    import manga_recap.render.ffmpeg as ffmpeg_module
    from manga_recap.render.ffmpeg import check_ffmpeg, get_gpu_count

    ffmpeg_module.has_nvenc = has_nvenc
    ffmpeg_module.has_cuda_device = has_cuda_device

    ensure_nvenc_ffmpeg()
    exe = check_ffmpeg()
    print(f"[kernel] FFmpeg executable: {exe}", flush=True)
    print(f"[kernel] NVENC hardware encoder available: {has_nvenc()}", flush=True)
    print(f"[kernel] CUDA hardware filter available (GPU 0): {has_cuda_device(exe, 0)}", flush=True)
    print(f"[kernel] Detected GPU count: {get_gpu_count()}", flush=True)

    test_pynvvideocodec_benchmark()

    job = json.loads(find("job.json").read_text(encoding="utf-8"))

    if RUN_SAMPLE_VARIANTS or job.get("mode") == "sample_variants":
        print("=" * 70, flush=True)
        print("[kernel] RUNNING SAMPLE VARIANTS PREVIEW MODE", flush=True)
        print("=" * 70, flush=True)
        panels_dir = find_panels_dir()
        audio = find("narration.wav")
        run_all_sample_variants(panels_dir, audio, exe, WORKING)
        print(f"[kernel] Sample variants finished in {time.time() - started:.1f}s!", flush=True)
        shutil.rmtree(INPUT_ROOT, ignore_errors=True)
        shutil.rmtree(WORKING / "ffmpeg_static", ignore_errors=True)
        return 0

    if job.get("mode") == "batch":
        chapters = job.get("chapters", [])
        print(f"[kernel] ===== BATCH MODE: Rendering {len(chapters)} chapters =====", flush=True)
        for idx, ch_name in enumerate(chapters, 1):
            print(f"\n[kernel] >>> [{idx}/{len(chapters)}] Starting {ch_name}...", flush=True)
            ch_dir = INPUT_ROOT / "chapters" / ch_name
            if not ch_dir.is_dir():
                print(f"[kernel] ERROR: Directory missing for {ch_name}", flush=True)
                continue

            ch_script = json.loads((ch_dir / "script.json").read_text(encoding="utf-8"))
            ch_timeline = json.loads((ch_dir / "timeline.json").read_text(encoding="utf-8"))
            ch_panels = ch_dir / "panels"
            ch_audio = ch_dir / "narration.wav"

            ch_output = WORKING / f"{ch_name}_final.mp4"
            ch_manifest = WORKING / f"{ch_name}_render_manifest.json"
            ch_sync = WORKING / f"{ch_name}_sync_report.json"

            try:
                render_chapter_core(
                    job, ch_script, ch_timeline, ch_panels, ch_audio,
                    ch_output, ch_manifest, ch_sync, exe, ch_name
                )
                print(f"[kernel] [OK] Finished {ch_name}", flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f"[kernel] [FAIL] Chapter {ch_name} failed: {exc}", flush=True)
                import traceback
                traceback.print_exc()

        shutil.rmtree(INPUT_ROOT, ignore_errors=True)
        shutil.rmtree(WORKING / "ffmpeg_static", ignore_errors=True)
        print(f"[kernel] All batch chapters finished in {time.time() - started:.0f}s", flush=True)
        return 0

    script = json.loads(find("script.json").read_text(encoding="utf-8"))
    timeline = json.loads(find("timeline.json").read_text(encoding="utf-8"))
    panels_dir = find_panels_dir()
    audio = find("narration.wav")
    output = WORKING / VIDEO_NAME
    manifest_file = WORKING / MANIFEST_NAME
    sync_file = WORKING / SYNC_NAME

    render_chapter_core(
        job, script, timeline, panels_dir, audio,
        output, manifest_file, sync_file, exe, str(job.get("chapter_id", ""))
    )

    shutil.rmtree(INPUT_ROOT, ignore_errors=True)
    shutil.rmtree(WORKING / "ffmpeg_static", ignore_errors=True)

    size_mb = output.stat().st_size / 1_000_000
    print(f"[kernel] rendered {VIDEO_NAME} ({size_mb:.1f} MB) in {time.time() - started:.0f}s", flush=True)
    print(f"[kernel] outputs: {VIDEO_NAME}, {MANIFEST_NAME}, {SYNC_NAME}", flush=True)
    return 0


def render_chapter_core(
    job: dict,
    script: dict,
    timeline: dict,
    panels_dir: Path,
    audio: Path,
    output: Path,
    manifest_file: Path,
    sync_file: Path,
    exe: str,
    chapter_id: str,
) -> dict:
    from manga_recap.render.ffmpeg import render
    from manga_recap.render.kenburns import StyleSettings, pick_bgm
    from manga_recap.render.sync import coverage_gaps, plan_shots

    render_config = job.get("render", {})
    test_duration = float(render_config.get("test_duration_seconds", 0.0) or 0.0)
    if test_duration > 0:
        print(f"[kernel] TEST MODE ENABLED: slicing to first {test_duration:.1f}s", flush=True)
        timeline["blocks"] = [
            b for b in timeline.get("blocks", []) if float(b["start"]) < test_duration
        ]
        for b in timeline["blocks"]:
            if float(b["end"]) > test_duration:
                b["end"] = test_duration
        timeline["duration"] = min(float(timeline.get("duration", test_duration)), test_duration)

        trimmed_audio = WORKING / f"narration_{chapter_id}_{int(test_duration)}s.wav"
        subprocess.run(
            [
                exe,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(audio),
                "-t",
                str(test_duration),
                "-c",
                "copy",
                str(trimmed_audio),
            ],
            check=True,
        )
        audio = trimmed_audio
        print(f"[kernel] trimmed narration audio to {test_duration:.1f}s: {audio.name}", flush=True)

    bw = int(render_config.get("blur_width", 128))
    br = int(render_config.get("blur_radius", 12))
    style = StyleSettings.from_job(job)
    style.blur_width = bw
    style.blur_radius = br

    use_nvenc = has_nvenc(exe)
    if not use_nvenc:
        raise RuntimeError(
            "[FATAL MANDATE VIOLATION] Hardware NVENC is not available on this kernel! "
            "Pure GPU rendering is strictly mandated; CPU rendering is prohibited."
        )
    num_gpus = get_gpu_count()
    default_workers = max(16, 16 * num_gpus)
    workers = int(render_config.get("max_workers", 0) or default_workers)
    preset = str(render_config.get("preset", "p1"))

    print(
        f"[kernel] render job for {chapter_id}: panels={panels_dir.name}, "
        f"audio={audio.name}, blur={bw}px, workers={workers} ({num_gpus} GPU(s)), preset={preset}",
        flush=True,
    )

    render_kwargs = {
        **style.as_render_kwargs(),
        "blur_width": bw,
        "blur_radius": br,
        "encoder": "h264_nvenc",
        "preset": preset,
        "max_workers": workers,
        "engine": render_config.get("engine", "pynv"),
        "pan_tall": render_config.get("pan_tall", True),
        "subtle_motion": render_config.get("subtle_motion", True),
        "video_bitrate": render_config.get("video_bitrate", 3200000),
    }


    report = plan_shots(
        script.get("blocks", []),
        timeline.get("words", []),
        audio_duration=float(timeline.get("duration", 0.0) or 0.0),
        max_words_per_beat=int(render_config.get("max_words_per_beat", 14)),
        min_shot_seconds=style.min_shot_seconds,
    )
    print(f"[kernel] SYNC REPORT [{chapter_id}]: {len(report.shots)} shots, drift {report.drift:+.3f}s")
    print(f"[kernel] problems: {report.problems}", flush=True)
    for warning in report.warnings:
        print(f"[kernel] sync warning: {warning}", flush=True)
    if report.warning_summary():
        print(f"[kernel] sync warnings: {report.warning_summary()}", flush=True)

    sync_file.write_text(
        json.dumps(
            {
                "audio_duration": report.audio_duration,
                "covered_duration": report.covered_duration,
                "drift": report.drift,
                "gaps": coverage_gaps(report.shots, report.audio_duration),
                "problems": report.problems,
                "warnings": report.warnings,
                "suppressed_warnings": report.warning_summary(),
                "shots": [
                    {
                        "panel_id": s.panel_id,
                        "block_id": s.block_id,
                        "beat_id": s.beat_id,
                        "start": round(s.start, 3),
                        "end": round(s.end, 3),
                        "anchored": s.anchored,
                        "text": s.text,
                    }
                    for s in report.shots
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = render(script, timeline, panels_dir, audio, output, render_kwargs)

    track = pick_bgm(style, Path.cwd())
    if track:
        print(f"[kernel] BGM selected: {track} (mixing is applied in a later stage)", flush=True)

    manifest = {
        "chapter_id": chapter_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "width": style.width,
        "height": style.height,
        "fps": style.fps,
        "duration": round(float(timeline.get("duration", 0.0)), 3),
        "clip_count": summary["clip_count"],
        "bgm_track": track,
        "output_file": output.name,
        "frames": summary.get("frames", 0),
        "clips": summary.get("shots", []),
    }
    manifest_file.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ffprobe = shutil.which("ffprobe")
    if ffprobe and output.exists():
        probe_res = subprocess.run(
            [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(output)],
            capture_output=True,
            text=True,
        )
        print(f"[kernel] FFPROBE VERIFICATION [{chapter_id}]:", flush=True)
        try:
            probe_data = json.loads(probe_res.stdout)
            fmt = probe_data.get("format", {})
            print(
                f"  Duration: {fmt.get('duration')}s, Size: {fmt.get('size')} bytes",
                flush=True,
            )
            expected = float(timeline.get("duration", 0.0) or 0.0)
            actual = float(fmt.get("duration", 0.0) or 0.0)
            if expected > 0:
                gap = actual - expected
                verdict = "OK" if abs(gap) <= 0.5 else "MISMATCH"
                print(f"  Audio {expected:.3f}s vs video {actual:.3f}s -> {verdict} ({gap:+.3f}s)", flush=True)
        except Exception:  # noqa: BLE001
            pass

    return summary


def ensure_src_on_path(root: Path | None = None) -> None:
    """Make the render modules importable inside the kernel.

    The kernel's own helper modules ride in the payload under `lib/`, because
    Kaggle does not put files that sat beside main.py on the path. The repo's
    `src/` is uploaded with the kernel too and carries the shared render code.
    """
    if root is not None:
        lib_dir = root / "lib"
        if lib_dir.is_dir() and str(lib_dir) not in sys.path:
            sys.path.insert(0, str(lib_dir))
            print(f"[kernel] helper modules from {lib_dir}/", flush=True)

        src_dir = root / "src"
        if src_dir.is_dir() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
            print(f"[kernel] using src from payload {src_dir}", flush=True)

    for candidate in (Path.cwd(), Path.cwd() / "repo", WORKING):
        src = candidate / "src"
        if src.is_dir() and str(src) not in sys.path:
            sys.path.insert(0, str(src))
            print(f"[kernel] using src from {src}")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as exc:
        if exc.code != 0:
            import traceback
            detail = traceback.format_exc()
            print(detail, flush=True)
            try:
                (WORKING / "failure.txt").write_text(detail, encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
        shutil.rmtree(INPUT_ROOT, ignore_errors=True)
        shutil.rmtree(WORKING / "ffmpeg_static", ignore_errors=True)
        raise
    except BaseException:
        import traceback

        detail = traceback.format_exc()
        print(detail, flush=True)
        try:
            (WORKING / "failure.txt").write_text(detail, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        shutil.rmtree(INPUT_ROOT, ignore_errors=True)
        shutil.rmtree(WORKING / "ffmpeg_static", ignore_errors=True)
        raise
