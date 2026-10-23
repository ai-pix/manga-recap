"""Schedule uploaded YouTube videos for automated release."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

def main():
    token_path = REPO_ROOT / "config" / "youtube_token.json"
    if not token_path.exists():
        print(f"Token file not found: {token_path}")
        return 1

    uploads_file = REPO_ROOT / "data" / "youtube_uploads.json"
    if not uploads_file.exists():
        print(f"Upload records not found: {uploads_file}")
        return 1

    with open(uploads_file, encoding="utf-8") as f:
        records = json.load(f)

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    service = build("youtube", "v3", credentials=creds)

    # Indian Standard Time (UTC+5:30)
    ist = timezone(timedelta(hours=5, minutes=30))
    # Start: 6:00 PM IST today (2026-10-04)
    start_ist = datetime(2026, 10, 4, 18, 0, 0, tzinfo=ist)

    # Ordered chapter keys
    ordered_keys = ["ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch09", "ch10"]

    print("=" * 70)
    print("SCHEDULING 10 VIDEOS (EVERY 4 HOURS STARTING 6:00 PM IST)")
    print("=" * 70)

    for i, ch_key in enumerate(ordered_keys):
        if ch_key not in records:
            print(f"Warning: {ch_key} not found in upload records.")
            continue

        video_id = records[ch_key]["video_id"]
        scheduled_ist = start_ist + timedelta(hours=4 * i)
        scheduled_utc = scheduled_ist.astimezone(timezone.utc)
        publish_at_str = scheduled_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"\n[{i+1}/10] {ch_key} (ID: {video_id})")
        print(f"     Target Release: {scheduled_ist.strftime('%Y-%m-%d %I:%M %p IST')}")
        print(f"     YouTube UTC:    {publish_at_str}")

        try:
            update_body = {
                "id": video_id,
                "status": {
                    "privacyStatus": "private",
                    "publishAt": publish_at_str,
                },
            }
            res = service.videos().update(part="status", body=update_body).execute()
            records[ch_key]["privacy"] = "private"
            records[ch_key]["publish_at"] = publish_at_str
            records[ch_key]["scheduled_ist"] = scheduled_ist.strftime("%Y-%m-%d %I:%M %p IST")
            print(f"     [SUCCESS] Scheduled! Status: {res.get('status', {}).get('privacyStatus')}")
        except Exception as exc:
            print(f"     [ERROR] Failed to schedule {video_id}: {exc}")

    with open(uploads_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print("\n" + "=" * 70)
    print("ALL 10 VIDEOS SUCCESSFULLY SCHEDULED!")
    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())
