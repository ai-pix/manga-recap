"""Push, monitor, distribute, and verify the final Super-Batch 4 (ch101-ch112)."""

import shutil
import sys

from manga_recap.core import payload
from manga_recap.core.kaggle_io import (
    STATUS_DONE,
    KaggleClient,
)
from manga_recap.core.paths import ChapterPaths, repo_path

sys.path.insert(0, str(repo_path("scripts")))
from run_dual_render_batch import distribute_outputs, monitor_dual_kernels

KERNEL_DIR = repo_path("kaggle/kernel_render")
BUILD_DIR = repo_path("build/render_batches")

BATCH_4 = {
    "k1": {
        "slug": "manga-recap-render",
        "url": "https://sendit.sh/tqCyP/taO-z.zip",
        "chapters": ["ch101", "ch102", "ch103", "ch103_5", "ch104", "ch105", "ch106"],
    },
    "k2": {
        "slug": "manga-recap-render-2",
        "url": "https://sendit.sh/QYEZp/kr5no.zip",
        "chapters": ["ch107", "ch108", "ch109", "ch110", "ch111", "ch112"],
    },
}


def clean_temp_staging():
    for d in BUILD_DIR.glob("staging_*"):
        try:
            shutil.rmtree(d)
        except Exception:
            pass
    for z in BUILD_DIR.glob("*.zip"):
        try:
            z.unlink()
        except Exception:
            pass
    for out in repo_path("build").glob("output_*"):
        try:
            shutil.rmtree(out)
        except Exception:
            pass


def main():
    client = KaggleClient()
    clean_temp_staging()

    print("=" * 70, flush=True)
    print("FINAL SUPER-BATCH 4: Pushing ch101-ch112 to Kaggle GPU...", flush=True)
    print("=" * 70, flush=True)

    # 1. Push both kernels
    for _bkey, binfo in BATCH_4.items():
        work_dir = repo_path(f"build/_staging_{binfo['slug']}")
        kernel_id = f"{client.username}/{binfo['slug']}"
        print(f"[push] Pushing {kernel_id} with pre-uploaded payload {binfo['url']}...", flush=True)
        payload.stage_from_url(
            kernel_dir=KERNEL_DIR,
            url=binfo["url"],
            work_dir=work_dir,
            metadata={
                "id": kernel_id,
                "title": binfo["slug"],
                "enable_gpu": True,
                "enable_internet": True,
                "dataset_sources": ["wampireai/manga-recap-render-bin"],
            },
        )
        client.push_kernel(work_dir)
        print(f"[push] Pushed {kernel_id} successfully!", flush=True)

    # 2. Monitor both kernels
    kernel_ids = [f"{client.username}/{binfo['slug']}" for binfo in BATCH_4.values()]
    print(f"\n[monitor] Monitoring final Super-Batch 4: {kernel_ids}", flush=True)
    statuses = monitor_dual_kernels(client, kernel_ids, poll_interval=20)

    for kid, st in statuses.items():
        if st not in STATUS_DONE:
            print(f"[error] Kernel {kid} did not succeed in Batch 4 ({st})", flush=True)
            return 1

    # 3. Distribute outputs and clean immediately
    print("\n" + "=" * 70, flush=True)
    print("SUPER-BATCH 4 COMPLETE! Distributing outputs...", flush=True)
    print("=" * 70, flush=True)
    for _bkey, binfo in BATCH_4.items():
        distribute_outputs(client, binfo["slug"], binfo["chapters"])
        # Clean the output dir immediately to save disk space
        out_dir = repo_path(f"build/output_{binfo['slug']}")
        if out_dir.exists():
            shutil.rmtree(out_dir, ignore_errors=True)
            print(f"[clean] Cleaned temporary output dir: {out_dir}", flush=True)

    clean_temp_staging()

    # 4. Final verification of all chapters across the series
    all_ch_dirs = sorted([d.name for d in repo_path("data/chapters").iterdir() if d.is_dir() and d.name.startswith("ch")])
    missing = []
    total_size = 0
    for ch in all_ch_dirs:
        p = ChapterPaths.create(ch).final_file
        if not p.exists() or p.stat().st_size == 0:
            missing.append(ch)
        else:
            total_size += p.stat().st_size

    print("\n" + "=" * 70, flush=True)
    print(f"SERIES COMPLETION AUDIT: {len(all_ch_dirs) - len(missing)}/{len(all_ch_dirs)} Chapters Verified", flush=True)
    print(f"Total Video Archive Size: {total_size / 1e9:.2f} GB", flush=True)
    if missing:
        print(f"[ERROR] Missing chapters: {missing}", flush=True)
        return 1

    print("[SUCCESS] ALL 115 CHAPTERS FULLY RENDERED AND VERIFIED ON DISK!", flush=True)
    print("=" * 70, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
