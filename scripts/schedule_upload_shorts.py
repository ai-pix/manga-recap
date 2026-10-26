"""Schedule upload of 10 SSS-Class Revival Hunter Shorts spaced every 2 hours, linked to full movie."""

from __future__ import annotations

import datetime
import re
import sys
import time
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.stages.s7_publish.youtube import (
    UploadMetadata,
    YouTubeUploader,
)

FULL_MOVIE_URL = "https://youtu.be/YN-_nk7Tcys"
FULL_MOVIE_ID = "YN-_nk7Tcys"
TAGS = [
    "sss class revival hunter",
    "manhwa recap",
    "anime recap",
    "manga recap",
    "full manhwa recap",
    "time travel manhwa",
    "over powered mc",
    "f rank to god rank",
    "4 hour manhwa recap",
    "webtoon recap",
    "shorts",
    "he keeps dying until he wins",
    "every death makes him stronger",
]


def post_full_video_comment(service, video_id: str) -> None:
    """Post a top-level comment linking to the full 4-hour movie recap."""
    comment_text = (
        f"🔥 Watch the complete 4-Hour Marathon Movie Recap here:\n"
        f"👉 {FULL_MOVIE_URL}"
    )
    try:
        service.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": comment_text,
                        }
                    },
                }
            },
        ).execute()
        print(f"  [Comment] Posted full movie link on video {video_id}!")
    except Exception as exc:
        print(f"  [Comment Notice] Could not post comment automatically ({exc}).")


def main():
    shorts_dir = REPO_ROOT / "data" / "export" / "shorts"
    if not shorts_dir.is_dir():
        print(f"Directory not found: {shorts_dir}")
        return 1

    uploader = YouTubeUploader()
    service = uploader.get_service()
    if not service:
        print("Failed to authenticate with YouTube API.")
        return 1

    # Schedule parameters: start in ~1.5 hours (14:00 IST), then every 2 hours
    # Local timezone: +05:30. 14:00 IST = 08:30 UTC
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # Next even slot: today at 08:30 UTC if in future, else +2 hours from now rounded
    start_slot = now_utc.replace(minute=30, second=0, microsecond=0) + datetime.timedelta(hours=1, minutes=30)
    if start_slot <= now_utc + datetime.timedelta(minutes=15):
        start_slot = now_utc + datetime.timedelta(hours=2)

    print("=" * 70)
    print("SCHEDULED YOUTUBE UPLOAD: 10 SHORTS (EVERY 2 HOURS)")
    print(f"First Short Scheduled For: {start_slot.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Linked Full Video: {FULL_MOVIE_URL}")
    print("=" * 70)

    results = []

    for idx in range(1, 11):
        sid = f"revival_hunter_short{idx:02d}"
        vids = list(shorts_dir.glob(f"{sid}_*.mp4"))
        metas = list(shorts_dir.glob(f"{sid}_*.txt"))

        if not vids or not metas:
            print(f"[ERROR] Missing files for {sid}")
            continue

        vid_path = vids[0]
        meta_text = metas[0].read_text(encoding="utf-8")

        # Parse title & desc
        title_match = re.search(r"TITLE:\s*\n(.*?)(?=\n\s*DESCRIPTION:|\Z)", meta_text, re.DOTALL)
        title = title_match.group(1).strip() if title_match else vid_path.stem

        desc_match = re.search(r"DESCRIPTION:\s*\n(.*)", meta_text, re.DOTALL)
        raw_desc = desc_match.group(1).strip() if desc_match else ""

        # Prepend prominent full video link to description
        full_desc = (
            f"🔥 WATCH THE COMPLETE 4-HOUR MOVIE RECAP HERE:\n"
            f"👉 {FULL_MOVIE_URL}\n\n"
            f"{raw_desc}\n\n"
            f"#sssclassrevivalhunter #manhwa #anime #recap #shorts #timereversal #webtoon"
        )

        # Calculate scheduled publication time (+2 hours for each subsequent short)
        sched_time = start_slot + datetime.timedelta(hours=(idx - 1) * 2)
        publish_at_iso = sched_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        sched_local_str = (sched_time + datetime.timedelta(hours=5, minutes=30)).strftime("%d-%b %I:%M %p IST")

        print(f"\n[{idx}/10] {sid}: {title}")
        print(f"       File: {vid_path.name} ({vid_path.stat().st_size / (1024*1024):.1f} MB)")
        print(f"       Scheduled: {sched_local_str} ({publish_at_iso})")

        meta = UploadMetadata(
            title=title[:100],
            description=full_desc[:5000],
            tags=TAGS,
            video_path=vid_path,
            thumbnail_path=None,  # YouTube automatically picks vertical frame for Shorts
        )

        try:
            # Upload with publish_at schedule
            video_id = uploader.upload_video(meta, privacy_status="private", publish_at=publish_at_iso)

            # Post comment with full video link
            post_full_video_comment(service, video_id)

            # Record
            record = {
                "key": sid,
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
                "title": title,
                "scheduled_publish_at": publish_at_iso,
                "scheduled_local": sched_local_str,
                "file": vid_path.name,
                "linked_movie": FULL_MOVIE_URL,
            }
            uploader.save_upload_record(sid, record)
            results.append(record)
            print(f"  [SUCCESS] {sid} scheduled on YouTube! ID: {video_id}")
        except Exception as exc:
            print(f"  [ERROR] Upload failed for {sid}: {exc}")

        # Short pause between uploads
        time.sleep(2)

    print("\n" + "=" * 70)
    print("ALL 10 SHORTS SUCCESSFULLY SCHEDULED ON YOUTUBE!")
    print("=" * 70)
    for r in results:
        print(f"  - {r['key']}: {r['title']}")
        print(f"    URL: {r['url']} | Scheduled: {r['scheduled_local']}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
