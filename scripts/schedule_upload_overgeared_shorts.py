"""Schedule upload of 12 Overgeared Shorts spaced every 2 hours, linked to the full movie recap."""

from __future__ import annotations

import argparse
import datetime
import re
import sys
import time
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.stages.s7_publish.youtube import (  # noqa: E402
    UploadMetadata,
    YouTubeUploader,
)
from scripts.publish_overgeared_youtube import get_authenticated_service  # noqa: E402

TAGS = [
    "overgeared",
    "manhwa recap",
    "anime recap",
    "manga recap",
    "full manhwa recap",
    "god grid",
    "shin youngwoo",
    "pagma successor",
    "legendary blacksmith",
    "shorts",
    "webtoon recap",
    "he broke the game",
]


def post_full_video_comment(service, video_id: str, movie_url: str) -> None:
    """Post a top-level comment linking to the full 2.5-hour movie recap."""
    comment_text = (
        f"🔥 Watch the complete 2.5-Hour Overgeared Movie Recap here:\n"
        f"👉 {movie_url}"
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
        print(f"  [Comment] Posted full movie link on video {video_id}!", flush=True)
    except Exception as exc:
        print(f"  [Comment Notice] Could not post comment automatically ({exc}).", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Schedule upload of 12 Overgeared Shorts")
    parser.add_argument("--movie-url", type=str, default="", help="Full Overgeared movie YouTube URL")
    parser.add_argument("--interval-hours", type=float, default=2.0, help="Interval between shorts in hours")
    parser.add_argument("--start-delay-hours", type=float, default=2.0, help="Hours from now to start first short")
    args = parser.parse_args()

    shorts_dir = REPO_ROOT / "data" / "export" / "shorts"
    if not shorts_dir.is_dir():
        print(f"Directory not found: {shorts_dir}", flush=True)
        return 1

    service = get_authenticated_service()
    uploader = YouTubeUploader()

    # Schedule parameters: start in `start_delay_hours`, then every `interval_hours`
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    start_slot = now_utc + datetime.timedelta(hours=args.start_delay_hours)

    movie_url = args.movie_url
    if not movie_url:
        try:
            channels = service.channels().list(mine=True, part="contentDetails").execute()
            uploads_id = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            items = service.playlistItems().list(playlistId=uploads_id, part="snippet", maxResults=10).execute()
            for itm in items.get("items", []):
                t = itm.get("snippet", {}).get("title", "").lower()
                v = itm.get("snippet", {}).get("resourceId", {}).get("videoId")
                if "overgear" in t or "broken" in t or "god-tier" in t:
                    movie_url = f"https://youtu.be/{v}"
                    print(f"Auto-detected full movie URL from channel: {movie_url}", flush=True)
                    break
            if not movie_url and items.get("items"):
                v = items["items"][0].get("snippet", {}).get("resourceId", {}).get("videoId")
                movie_url = f"https://youtu.be/{v}"
                print(f"Defaulting to latest uploaded video: {movie_url}", flush=True)
        except Exception:
            movie_url = "https://youtu.be/overgeared-full-movie"

    print("=" * 70, flush=True)
    print("SCHEDULED YOUTUBE UPLOAD: 12 OVERGEARED SHORTS (EVERY 2 HOURS)", flush=True)
    print(f"First Short Scheduled For: {start_slot.strftime('%Y-%m-%d %H:%M:%S UTC')}", flush=True)
    print(f"Linked Full Movie: {movie_url}", flush=True)
    print("=" * 70, flush=True)

    results = []

    for idx in range(1, 13):
        sid = f"overgeared_short{idx:02d}"
        vids = list(shorts_dir.glob(f"{sid}_*.mp4"))
        metas = list(shorts_dir.glob(f"{sid}_*.txt"))

        if not vids or not metas:
            print(f"[ERROR] Missing files for {sid}", flush=True)
            continue

        vid_path = vids[0]
        meta_text = metas[0].read_text(encoding="utf-8")

        # Parse title & desc
        title_match = re.search(r"TITLE:\s*\n(.*?)(?=\n\s*DESCRIPTION:|\Z)", meta_text, re.DOTALL)
        title = title_match.group(1).strip() if title_match else vid_path.stem

        desc_match = re.search(r"DESCRIPTION:\s*\n(.*)", meta_text, re.DOTALL)
        raw_desc = desc_match.group(1).strip() if desc_match else ""

        full_desc = (
            f"🔥 WATCH THE COMPLETE 2.5-HOUR OVERGEARED MOVIE RECAP HERE:\n"
            f"👉 {movie_url}\n\n"
            f"{raw_desc}\n\n"
            f"#overgeared #manhwa #anime #recap #shorts #godgrid #webtoon"
        )

        sched_time = start_slot + datetime.timedelta(hours=(idx - 1) * args.interval_hours)
        publish_at_iso = sched_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        sched_local_str = (sched_time + datetime.timedelta(hours=5, minutes=30)).strftime("%d-%b %I:%M %p IST")

        print(f"\n[{idx}/12] {sid}: {title}", flush=True)
        print(f"       File: {vid_path.name} ({vid_path.stat().st_size / (1024*1024):.1f} MB)", flush=True)
        print(f"       Scheduled: {sched_local_str} ({publish_at_iso})", flush=True)

        meta = UploadMetadata(
            title=title[:100],
            description=full_desc[:5000],
            tags=TAGS,
            video_path=vid_path,
            thumbnail_path=None,
        )

        try:
            video_id = uploader.upload_video(meta, privacy_status="private", publish_at=publish_at_iso)
            post_full_video_comment(service, video_id, movie_url)

            record = {
                "key": sid,
                "video_id": video_id,
                "url": f"https://youtu.be/{video_id}",
                "title": title,
                "scheduled_publish_at": publish_at_iso,
                "scheduled_local": sched_local_str,
                "file": vid_path.name,
                "linked_movie": movie_url,
            }
            uploader.save_upload_record(sid, record)
            results.append(record)
            print(f"  [SUCCESS] {sid} scheduled on YouTube! ID: {video_id}", flush=True)
        except Exception as exc:
            print(f"  [ERROR] Upload failed for {sid}: {exc}", flush=True)

        time.sleep(2)

    print("\n" + "=" * 70, flush=True)
    print("ALL 12 OVERGEARED SHORTS PROCESSED FOR SCHEDULING!", flush=True)
    print("=" * 70, flush=True)
    for r in results:
        print(f"  - {r['key']}: {r['title']}", flush=True)
        print(f"    URL: {r['url']} | Scheduled: {r['scheduled_local']}", flush=True)
    print("=" * 70, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
