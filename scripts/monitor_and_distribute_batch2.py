"""Monitor currently running Super-Batch 2 and auto-chain Super-Batch 3."""

import shutil
import sys

from manga_recap.core import payload
from manga_recap.core.kaggle_io import (
    STATUS_DONE,
    KaggleClient,
)
from manga_recap.core.paths import repo_path

sys.path.insert(0, str(repo_path("scripts")))
from run_dual_render_batch import distribute_outputs, monitor_dual_kernels

KERNEL_DIR = repo_path("kaggle/kernel_render")
BUILD_DIR = repo_path("build/render_batches")

# Currently running on Kaggle:
BATCH_2 = {
    "k1": {
        "slug": "manga-recap-render",
        "chapters": ["ch061", "ch062", "ch063", "ch064", "ch065", "ch066", "ch067", "ch068", "ch069", "ch070"],
    },
    "k2": {
        "slug": "manga-recap-render-2",
        "chapters": ["ch071", "ch072", "ch073", "ch074", "ch075", "ch076", "ch077", "ch078", "ch079", "ch080"],
    },
}

# Next up (already uploaded on sendit.sh):
BATCH_3 = {
    "k1": {
        "slug": "manga-recap-render",
        "url": "https://sendit.sh/vv8d6/hGsx1.zip",
        "chapters": ["ch081", "ch082", "ch083", "ch084", "ch085", "ch086", "ch087", "ch088", "ch089", "ch090"],
    },
    "k2": {
        "slug": "manga-recap-render-2",
        "url": "https://sendit.sh/SfXoc/XZ4fG.zip",
        "chapters": ["ch091", "ch092", "ch093", "ch094", "ch095", "ch096", "ch097", "ch098", "ch099", "ch100"],
    },
}

# Final batch (Ch 101 to 112, already uploaded on sendit.sh):
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


def main():
    client = KaggleClient()
    clean_temp_staging()

    # 1. Monitor currently running Batch 2
    kernel_ids = [f"{client.username}/{binfo['slug']}" for binfo in BATCH_2.values()]
    print(f"\n[monitor] Monitoring running Super-Batch 2: {kernel_ids}", flush=True)
    statuses = monitor_dual_kernels(client, kernel_ids, poll_interval=20)

    for kid, st in statuses.items():
        if st not in STATUS_DONE:
            print(f"[error] Kernel {kid} did not succeed (status: {st})", flush=True)
            return 1

    # 2. Distribute Batch 2 outputs
    print("\n" + "=" * 70, flush=True)
    print("SUPER-BATCH 2 COMPLETE! Distributing outputs...", flush=True)
    print("=" * 70, flush=True)
    for _bkey, binfo in BATCH_2.items():
        distribute_outputs(client, binfo["slug"], binfo["chapters"])

    clean_temp_staging()

    # 3. Immediately Push Super-Batch 3 with pre-uploaded URLs
    print("\n" + "=" * 70, flush=True)
    print("SUPER-BATCH 3: Instantly pushing pre-uploaded payloads to Kaggle...", flush=True)
    print("=" * 70, flush=True)

    for _bkey, binfo in BATCH_3.items():
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

    # 4. Monitor Super-Batch 3
    print(f"\n[monitor] Monitoring Super-Batch 3: {kernel_ids}", flush=True)
    statuses_3 = monitor_dual_kernels(client, kernel_ids, poll_interval=20)
    for kid, st in statuses_3.items():
        if st not in STATUS_DONE:
            print(f"[error] Kernel {kid} did not succeed in Batch 3 ({st})", flush=True)
            return 1

    # 5. Distribute Super-Batch 3 outputs
    print("\n" + "=" * 70, flush=True)
    print("SUPER-BATCH 3 COMPLETE! Distributing outputs...", flush=True)
    print("=" * 70, flush=True)
    for _bkey, binfo in BATCH_3.items():
        distribute_outputs(client, binfo["slug"], binfo["chapters"])

    clean_temp_staging()

    # 6. Immediately Push Super-Batch 4 with pre-uploaded URLs
    print("\n" + "=" * 70, flush=True)
    print("SUPER-BATCH 4: Instantly pushing final batch to Kaggle...", flush=True)
    print("=" * 70, flush=True)

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

    # 7. Monitor Super-Batch 4
    print(f"\n[monitor] Monitoring Super-Batch 4: {kernel_ids}", flush=True)
    statuses_4 = monitor_dual_kernels(client, kernel_ids, poll_interval=20)
    for kid, st in statuses_4.items():
        if st not in STATUS_DONE:
            print(f"[error] Kernel {kid} did not succeed in Batch 4 ({st})", flush=True)
            return 1

    # 8. Distribute Super-Batch 4 outputs
    print("\n" + "=" * 70, flush=True)
    print("SUPER-BATCH 4 COMPLETE! Distributing outputs...", flush=True)
    print("=" * 70, flush=True)
    for _bkey, binfo in BATCH_4.items():
        distribute_outputs(client, binfo["slug"], binfo["chapters"])

    clean_temp_staging()
    print("\n[SUCCESS] ENTIRE SERIES THROUGH CHAPTER 112 FULLY RENDERED AND VERIFIED!", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
