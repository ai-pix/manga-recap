"""Dispatch sample variant rendering to Kaggle GPU."""

from __future__ import annotations

import shutil

from manga_recap.core import payload
from manga_recap.core.kaggle_io import KaggleClient
from manga_recap.core.paths import repo_path


def main():
    kernel_dir = repo_path("kaggle/kernel_render")
    payload_url = "https://filebin.net/mr-cbde1b8501/barbarian_ch01-render.zip"
    client = KaggleClient()
    kernel_slug = "manga-recap-render"
    kernel_id = f"{client.username}/{kernel_slug}"

    work_dir = repo_path("data/chapters/barbarian_ch01/_kaggle_kernel_samples")
    print(f"[dispatch] Staging kernel at {work_dir}...", flush=True)
    staged = payload.stage_from_url(
        kernel_dir=kernel_dir,
        url=payload_url,
        work_dir=work_dir,
        metadata={
            "id": kernel_id,
            "title": kernel_slug,
            "enable_gpu": True,
            "dataset_sources": ["wampireai/manga-recap-render-bin"],
        },
    )

    print(f"[dispatch] Pushing kernel {kernel_id} to Kaggle GPU...", flush=True)
    client.push_kernel(staged)

    print(f"[dispatch] Waiting for {kernel_id} to complete execution on Tesla T4...", flush=True)
    run_info = client.wait_for_kernel(kernel_id, poll_interval=10, max_wait=1200)
    print(
        f"[dispatch] Kernel finished: total={run_info.total_seconds:.1f}s, "
        f"queue={run_info.queue_seconds:.1f}s",
        flush=True,
    )

    out_dir = repo_path("data/chapters/barbarian_ch01/samples")
    out_dir.mkdir(parents=True, exist_ok=True)
    download_dir = client.download_kernel_output(
        kernel_id, repo_path("data/chapters/barbarian_ch01/_kaggle_output_samples")
    )
    print(f"[dispatch] Downloaded outputs from Kaggle to {download_dir}:", flush=True)
    for f in download_dir.glob("*"):
        if f.is_file():
            print(f"  -> {f.name} ({f.stat().st_size / 1_000_000:.2f} MB)", flush=True)
            shutil.copy2(f, out_dir / f.name)

    print(f"\n[dispatch] All samples successfully placed in {out_dir}!", flush=True)


if __name__ == "__main__":
    main()
