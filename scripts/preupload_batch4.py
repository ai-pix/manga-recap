"""Pre-stage and pre-upload final Super-Batch 4 with immediate disk cleanup."""

import json
import shutil
import sys

from manga_recap.core.paths import repo_path

sys.path.insert(0, str(repo_path("scripts")))
from run_dual_render_batch import stage_batch, upload_archive

BUILD_DIR = repo_path("build/render_batches")
CACHE_FILE = BUILD_DIR / "preuploaded_urls.json"

BATCHES = [
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

    for bname, chs in BATCHES:
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

        # Immediately clean up local files to conserve disk space
        if arc.exists():
            arc.unlink()
            print(f"[pre-upload] Cleaned {arc.name}", flush=True)
        s_dir = BUILD_DIR / f"staging_{bname}"
        if s_dir.exists():
            shutil.rmtree(s_dir)
            print(f"[pre-upload] Cleaned {s_dir.name}", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("SUPER-BATCH 4 PRE-UPLOADED SUCCESSFULLY!", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
