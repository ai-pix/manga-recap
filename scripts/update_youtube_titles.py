"""Update YouTube video titles for high CTR and synergy with thumbnails."""

import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

NEW_TITLES = {
    "ch01": "He Picked The Most \"Trash\" Skills, But Accidentally Broke The Entire Game [Part 1]",
    "ch02": "He Created A Potion So Broken That Top Guilds Started A War For It [Part 2]",
    "ch03": "Everyone Laughed At His Useless Bow... Until He One-Shot The World Boss [Part 3]",
    "ch04": "He Discovered A Secret Exploit That Shattered The Game's Physics [Part 4]",
    "ch05": "The Boss Was Immune To All Weapons, So He Melted Its Armor In 5 Seconds [Part 5]",
    "ch06": "Assassins Ambushed A \"Weak Crafter\", But Ended Up Begging For Mercy [Part 6]",
    "ch07": "He Crafted A Forbidden Ring That Broke The Entire VRMMO Economy [Part 7]",
    "ch08": "When A Level 1 Crafter Accidentally Nukes The Entire Battlefield [Part 8]",
    "ch09": "He Unlocked A Cursed Bow That Top Guilds Were Terrified To Touch [Part 9]",
    "ch10": "When The Elite Guild Wipes Out, The \"Trash Crafter\" Solo Carries [Part 10]",
}


def apply_titles():
    token_path = Path("config/youtube_token.json")
    if not token_path.exists():
        raise FileNotFoundError(f"Missing {token_path}")

    creds = Credentials.from_authorized_user_file(str(token_path))
    youtube = build("youtube", "v3", credentials=creds)

    uploads_file = Path("data/youtube_uploads.json")
    uploads = json.loads(uploads_file.read_text(encoding="utf-8"))

    print("Updating YouTube Video Titles...")
    for ch_key, new_title in NEW_TITLES.items():
        if ch_key not in uploads:
            print(f"Skipping {ch_key}: not found in uploads")
            continue

        item = uploads[ch_key]
        vid = item["video_id"]

        # Fetch current snippet to avoid overwriting description/tags/category
        vid_res = youtube.videos().list(part="snippet", id=vid).execute()
        if not vid_res.get("items"):
            print(f"Video {vid} not found on YouTube!")
            continue

        snippet = vid_res["items"][0]["snippet"]
        old_title = snippet["title"]
        snippet["title"] = new_title

        # Update video snippet
        youtube.videos().update(
            part="snippet",
            body={
                "id": vid,
                "snippet": snippet,
            },
        ).execute()

        item["title"] = new_title
        print(f"[{ch_key}] Updated {vid}:")
        print(f"  Old: {old_title}")
        print(f"  New: {new_title} (len: {len(new_title)})")

    uploads_file.write_text(json.dumps(uploads, indent=2), encoding="utf-8")
    print("\nSaved updated titles to data/youtube_uploads.json!")


if __name__ == "__main__":
    apply_titles()
