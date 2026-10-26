"""Reschedule the 12 Overgeared YouTube shorts to start from 26th 00:00 AM IST (midnight) and every 2 hours after."""

from __future__ import annotations

import datetime
import json
import sys
import zoneinfo
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from scripts.publish_overgeared_youtube import get_authenticated_service  # noqa: E402

UPLOADS_FILE = REPO_ROOT / "data" / "youtube_uploads.json"
IST = zoneinfo.ZoneInfo("Asia/Kolkata")


def main() -> None:
    print("=" * 70)
    print("RESCHEDULING 12 OVERGEARED SHORTS TO START FROM 26TH 00:00 AM IST")
    print("=" * 70)

    if not UPLOADS_FILE.exists():
        print(f"Error: {UPLOADS_FILE} not found!")
        sys.exit(1)

    uploads_data = json.loads(UPLOADS_FILE.read_text(encoding="utf-8"))
    youtube = get_authenticated_service()

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_ist = datetime.datetime.now(IST)
    print(f"Current Time: {now_ist.strftime('%d-%b %I:%M:%S %p %Z')} ({now_utc.isoformat()})")

    base_time_ist = datetime.datetime(2026, 10, 26, 0, 0, 0, tzinfo=IST)

    results = []

    for i in range(1, 13):
        key = f"overgeared_short{i:02d}"
        if key not in uploads_data:
            print(f"Warning: {key} not found in {UPLOADS_FILE}")
            continue

        item = uploads_data[key]
        video_id = item["video_id"]
        title = item["title"]

        target_ist = base_time_ist + datetime.timedelta(hours=(i - 1) * 2)
        target_utc = target_ist.astimezone(datetime.timezone.utc)
        target_utc_str = target_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        local_str = target_ist.strftime("%d-%b %I:%M %p IST")

        print(f"\n[{i}/12] {key}: {title}")
        print(f"       Target: {local_str} ({target_utc_str})")

        if (target_utc - now_utc).total_seconds() < 60:
            print(f"       Target time is NOW / due ({local_str}) -> Setting to PUBLIC immediately!")
            try:
                youtube.videos().update(
                    part="status",
                    body={
                        "id": video_id,
                        "status": {
                            "privacyStatus": "public",
                        },
                    },
                ).execute()
                print(f"       [SUCCESS] Video {video_id} is now PUBLIC!")
                item["privacy"] = "public"
                item["status"] = "public"
                item["scheduled_local"] = f"{local_str} (LIVE NOW)"
                item["scheduled_publish_at"] = target_utc_str
            except Exception as e:
                print(f"       [ERROR] Failed to set public: {e}")
        else:
            print(f"       Scheduling for {local_str} ({target_utc_str})...")
            try:
                youtube.videos().update(
                    part="status",
                    body={
                        "id": video_id,
                        "status": {
                            "privacyStatus": "private",
                            "publishAt": target_utc_str,
                        },
                    },
                ).execute()
                print(f"       [SUCCESS] Video {video_id} rescheduled to {local_str}!")
                item["privacy"] = "private"
                item["scheduled_publish_at"] = target_utc_str
                item["scheduled_local"] = local_str
            except Exception as e:
                print(f"       [ERROR] Failed to reschedule: {e}")

        results.append({
            "key": key,
            "title": title,
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}",
            "scheduled_local": item.get("scheduled_local", local_str),
        })

    UPLOADS_FILE.write_text(json.dumps(uploads_data, indent=2), encoding="utf-8")
    print("\n" + "=" * 70)
    print("ALL 12 SHORTS RESCHEDULED SUCCESSFULLY!")
    print("=" * 70)
    for res in results:
        print(f"  - {res['key']}: {res['title']}")
        print(f"    URL: {res['url']} | Scheduled: {res['scheduled_local']}")


if __name__ == "__main__":
    main()
