"""Background script to stage, zip, and pre-upload upcoming render batches to cloud storage.

This runs concurrently while Kaggle renders the current batch, so future batches
can be submitted to Kaggle with zero staging/upload delay.
"""

from __future__ import annotations

import json
import sys

from manga_recap.core.paths import repo_path

sys.path.insert(0, str(repo_path("scripts")))
from run_dual_render_batch import stage_batch, upload_archive

BUILD_DIR = repo_path("build/render_batches")
CACHE_FILE = BUILD_DIR / "preuploaded_urls.json"

UPCOMING_BATCHES = [
    # Super-Batch 2
    ("batch_ch061_ch070", ["ch061", "ch062", "ch063", "ch064", "ch065", "ch066", "ch067", "ch068", "ch069", "ch070"]),
    ("batch_ch071_ch080", ["ch071", "ch072", "ch073", "ch074", "ch075", "ch076", "ch077", "ch078", "ch079", "ch080"]),
    # Super-Batch 3
    ("batch_ch081_ch090", ["ch081", "ch082", "ch083", "ch084", "ch085", "ch086", "ch087", "ch088", "ch089", "ch090"]),
    ("batch_ch091_ch100", ["ch091", "ch092", "ch093", "ch094", "ch095", "ch096", "ch097", "ch098", "ch099", "ch100"]),
    # Super-Batch 4
    ("batch_ch101_ch106", ["ch101", "ch102", "ch103", "ch103_5", "ch104", "ch105", "ch106"]),
    ("batch_ch107_ch112", ["ch107", "ch108", "ch109", "ch110", "ch111", "ch112"]),
]


def main():
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    cache = {}
    if CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    print("=" * 70, flush=True)
    print("PRE-UPLOADER: Preparing and uploading all upcoming batches in background", flush=True)
    print("=" * 70, flush=True)

    for bname, chs in UPCOMING_BATCHES:
        if bname in cache and cache[bname]:
            print(f"[pre-upload] {bname} already cached: {cache[bname]}", flush=True)
            continue

        print(f"\n[pre-upload] >>> Staging {bname} ({len(chs)} chapters)...", flush=True)
        arc = stage_batch(bname, chs, BUILD_DIR)
        print(f"[pre-upload] >>> Uploading {arc.name} to cloud storage...", flush=True)
        url = upload_archive(arc)
        cache[bname] = url
        CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[pre-upload] SUCCESS {bname} -> {url}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("ALL UPCOMING BATCHES PRE-STAGED AND PRE-UPLOADED!", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
