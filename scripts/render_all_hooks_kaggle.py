"""Stage, upload, render on Kaggle GPU, and distribute all 4 hook videos."""

import json
import shutil
import sys

from manga_recap.core import payload
from manga_recap.core.kaggle_io import (
    STATUS_DONE,
    KaggleClient,
)
from manga_recap.core.paths import ChapterPaths, repo_path

sys.path.insert(0, str(repo_path("scripts")))
from run_dual_render_batch import (
    distribute_outputs,
    monitor_dual_kernels,
    stage_batch,
    upload_archive,
)

KERNEL_DIR = repo_path("kaggle/kernel_render")
BUILD_DIR = repo_path("build/render_batches")
HOOKS = ["hook_part1", "hook_part2", "hook_part3", "hook_part4"]


def main():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    client = KaggleClient()

    print("=" * 70, flush=True)
    print("HOOK RENDERING: Staging and rendering all 4 hooks on Kaggle GPU...", flush=True)
    print("=" * 70, flush=True)

    # 1. Stage the 4 hooks
    batch_name = "batch_hooks"
    archive = stage_batch(batch_name, HOOKS, BUILD_DIR)

    # 2. Upload to sendit.sh
    payload_url = upload_archive(archive)
    print(f"[upload] Payload ready: {payload_url}", flush=True)

    # Clean local zip immediately
    if archive.exists():
        archive.unlink()

    # 3. Push to Kaggle GPU kernel
    slug = "manga-recap-render"
    kernel_id = f"{client.username}/{slug}"
    work_dir = repo_path(f"build/_staging_{slug}")

    print(f"\n[push] Pushing {kernel_id} to Kaggle GPU...", flush=True)
    payload.stage_from_url(
        kernel_dir=KERNEL_DIR,
        url=payload_url,
        work_dir=work_dir,
        metadata={
            "id": kernel_id,
            "title": slug,
            "enable_gpu": True,
            "enable_internet": True,
            "dataset_sources": ["wampireai/manga-recap-render-bin"],
        },
    )
    client.push_kernel(work_dir)
    print(f"[push] Pushed {kernel_id} successfully!", flush=True)

    # 4. Monitor Kaggle GPU run
    print(f"\n[monitor] Monitoring {kernel_id}...", flush=True)
    statuses = monitor_dual_kernels(client, [kernel_id], poll_interval=15)
    if statuses.get(kernel_id) not in STATUS_DONE:
        print(f"[error] Kernel {kernel_id} failed: {statuses.get(kernel_id)}", flush=True)
        return 1

    # 5. Distribute outputs
    print("\n" + "=" * 70, flush=True)
    print("RENDERING COMPLETE! Distributing hook videos...", flush=True)
    print("=" * 70, flush=True)
    distribute_outputs(client, slug, HOOKS)

    # Copy to data/hooks/
    hooks_dir = repo_path("data/hooks")
    hooks_dir.mkdir(parents=True, exist_ok=True)
    for h in HOOKS:
        src_video = ChapterPaths.create(h).final_file
        dst_video = hooks_dir / f"{h}.mp4"
        shutil.copy2(src_video, dst_video)
        manifest_file = ChapterPaths.create(h).render_manifest_file
        dur = 0.0
        if manifest_file.exists():
            dur = json.loads(manifest_file.read_text(encoding="utf-8")).get("duration", 0.0)
        size_mb = dst_video.stat().st_size / 1e6
        print(f"[distribute] [{h}] Saved {dst_video.name} ({dur:.1f}s, {size_mb:.1f} MB)", flush=True)

    # Clean temporary output dir
    out_dir = repo_path(f"build/output_{slug}")
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)

    print("\n[SUCCESS] ALL 4 HOOK VIDEOS RENDERED AND VERIFIED ON DISK!", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
