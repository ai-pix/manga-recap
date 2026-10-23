"""Automated YouTube Upload Pipeline CLI.

Upload individual chapters or the master compilation marathon to YouTube with:
- Full Title & Description (including clickable chapter timestamps)
- 16:9 Custom Thumbnail
- Tags, Category, and Privacy / Scheduling controls
- Resumable upload with progress bar
- Upload tracking in data/youtube_uploads.json

Examples:
    # 1. Preview what will be uploaded (no credentials or network calls needed):
    python scripts/upload_to_youtube.py --dry-run ch01

    # 2. Upload the 5-hour master marathon compilation:
    python scripts/upload_to_youtube.py --compilation

    # 3. Upload a single chapter (defaults to unlisted):
    python scripts/upload_to_youtube.py ch01

    # 4. Upload as public immediately:
    python scripts/upload_to_youtube.py ch01 --privacy public

    # 5. Schedule video release:
    python scripts/upload_to_youtube.py ch01 --publish-at 2026-10-06T12:00:00Z

    # 6. Upload all 31 chapters:
    python scripts/upload_to_youtube.py --all
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.stages.s7_publish.youtube import (  # noqa: E402
    YouTubeUploader,
    find_package_assets,
)


def find_chapter_folder(export_dir: Path, chapter_id: str) -> Path | None:
    """Match ch01 -> Chapter_01_*, ch005_5 -> Chapter_05_5_*, etc."""
    import re
    m = re.match(r"ch0*(\d+)(?:_(\d+))?", chapter_id.lower())
    if not m:
        return None
    base = int(m.group(1))
    sub = int(m.group(2)) if m.group(2) else None

    pattern = rf"^chapter_{base:02d}_{sub}_" if sub is not None else rf"^chapter_{base:02d}_(?!\d)"
    for d in export_dir.iterdir():
        if d.is_dir() and re.match(pattern, d.name.lower()):
            return d
    return None


def print_dry_run(package_dir: Path, key: str, privacy: str, publish_at: str | None):
    meta = find_package_assets(package_dir)
    print("=" * 70)
    print(f"DRY RUN PREVIEW: {key} ({package_dir.name})")
    print("=" * 70)
    print(f"Video File:     {meta.video_path} ({meta.video_path.stat().st_size / (1024*1024):.2f} MB)")
    print(f"Thumbnail File: {meta.thumbnail_path}")
    print(f"Privacy Status: {privacy}" + (f" (Scheduled for {publish_at})" if publish_at else ""))
    print(f"\nTITLE:\n{meta.title}")
    print(f"\nDESCRIPTION (First 350 chars):\n{meta.description[:350]}...\n[truncated: total {len(meta.description)} chars]")
    print(f"\nTAGS ({len(meta.tags)}):\n{', '.join(meta.tags)}")
    print("=" * 70 + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Automated YouTube Upload Pipeline for Manga Recap videos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("chapters", nargs="*", help="Chapter IDs to upload (e.g. ch01, ch02)")
    parser.add_argument("--compilation", action="store_true", help="Upload the master 5-hour compilation marathon")
    parser.add_argument("--all", action="store_true", help="Upload all 31 chapters in sequence")
    parser.add_argument(
        "--privacy",
        choices=("unlisted", "private", "public"),
        default="unlisted",
        help="Privacy status on YouTube (default: unlisted)",
    )
    parser.add_argument(
        "--publish-at",
        help="Schedule publish time in UTC ISO 8601 format (e.g. 2026-10-06T12:00:00Z)",
    )
    parser.add_argument(
        "--credentials",
        help="Path to Google Cloud client_secrets.json (default: searches project root)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-upload even if recorded as already uploaded in data/youtube_uploads.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate assets, metadata, and thumbnails without connecting to YouTube API",
    )

    args = parser.parse_args(argv)

    export_dir = REPO_ROOT / "data" / "youtube_ready"
    if not export_dir.is_dir():
        print(f"Export directory not found at: {export_dir}")
        print("Please run scripts/prepare_youtube_export.py first.")
        return 1

    targets: list[tuple[str, Path]] = []

    if args.compilation:
        comp_dir = export_dir / "00_FULL_SERIES_COMPILATION"
        if not comp_dir.is_dir():
            print(f"Compilation directory not found at: {comp_dir}")
            return 1
        targets.append(("full_compilation", comp_dir))

    if args.all:
        for d in sorted(export_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("00_"):
                ch_key = d.name.split("_")[0] + "_" + d.name.split("_")[1]
                targets.append((ch_key, d))

    for ch_id in args.chapters:
        folder = find_chapter_folder(export_dir, ch_id)
        if not folder:
            print(f"Could not find export package folder for '{ch_id}' in {export_dir}")
            return 1
        targets.append((ch_id, folder))

    if not targets:
        print("No target specified. Use chapter IDs (e.g. 'ch01'), '--compilation', or '--all'.")
        print("Run with '--help' for usage examples.")
        return 1

    if args.dry_run:
        print(f"\n[DRY RUN] Validating {len(targets)} package(s)...\n")
        for key, folder in targets:
            print_dry_run(folder, key, args.privacy, args.publish_at)
        print(f"[SUCCESS] All {len(targets)} package(s) verified valid for YouTube upload!")
        return 0

    creds_path = Path(args.credentials) if args.credentials else None
    uploader = YouTubeUploader(credentials_path=creds_path)

    print(f"\n[YouTube Pipeline] Preparing upload for {len(targets)} target(s)...")
    for idx, (key, folder) in enumerate(targets, 1):
        print(f"\n--- [{idx}/{len(targets)}] Processing: {key} ---")
        try:
            uploader.upload_package(
                package_dir=folder,
                key=key,
                privacy_status=args.privacy,
                publish_at=args.publish_at,
                force=args.force,
            )
        except Exception as exc:
            print(f"\n[ERROR] Upload failed for {key}: {exc}")
            print("To resume later, re-run the command; completed uploads are automatically skipped.")
            return 1

    print("\n[COMPLETE] All requested uploads finished successfully!")
    print(f"Upload records saved in: {uploader.state_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
