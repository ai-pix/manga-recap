"""Upload the 4-Hour SSS-Class Revival Hunter Marathon Movie to YouTube as Unlisted."""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.stages.s7_publish.youtube import (
    YouTubeUploader,
    find_package_assets,
)


def main():
    package_dir = REPO_ROOT / "data" / "export" / "revival_hunter_movie_package"
    if not package_dir.is_dir():
        print(f"Package directory not found: {package_dir}")
        return 1

    print("[YouTube Publish] Locating package assets...")
    meta = find_package_assets(package_dir)
    print(f"  Title: {meta.title}")
    print(f"  Video: {meta.video_path.name} ({meta.video_path.stat().st_size / (1024**3):.2f} GB)")
    print(f"  Thumbnail: {meta.thumbnail_path.name if meta.thumbnail_path else 'None'}")
    print(f"  Tags: {len(meta.tags)} tags")
    print("  Privacy: unlisted (Ready for user to set Premiere)")

    uploader = YouTubeUploader()
    # Authenticate
    service = uploader.get_service()
    if not service:
        print("Failed to authenticate with YouTube API.")
        return 1

    print("\n[YouTube Publish] Launching resumable 10GB video upload...")
    video_id = uploader.upload_video(meta, privacy_status="unlisted")

    if meta.thumbnail_path and meta.thumbnail_path.exists():
        print("[YouTube Publish] Uploading 16:9 custom thumbnail...")
        uploader.set_thumbnail(video_id, meta.thumbnail_path)

    # Save record
    uploader.save_upload_record(
        "revival_hunter_4hour_movie",
        {
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}",
            "title": meta.title,
            "privacy": "unlisted",
            "file": str(meta.video_path),
            "size_gb": round(meta.video_path.stat().st_size / (1024**3), 2),
        },
    )

    print("\n" + "=" * 60)
    print(f"SUCCESS: Video published to YouTube as UNLISTED!")
    print(f"Video URL: https://youtu.be/{video_id}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
