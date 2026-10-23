"""Upload the 2-hour stitched movie recap to YouTube with custom thumbnail and SEO."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from googleapiclient.http import MediaFileUpload

from manga_recap.stages.s7_publish.youtube import YouTubeUploader

VIDEO_PATH = Path("data/chapters/barbarian_movie_ch01_ch20.mp4")
DEFAULT_THUMB_PATH = Path(r"c:\Users\ravih\Downloads\Crystal Dungeon Escape.png")

TITLE = "He Was Trapped in a Hell-Mode RPG as a Barbarian... Until He Broke the System! (Ch 1-20 Recap)"

DESCRIPTION = """After spending 9 grueling years trying to beat the impossible 2D dark fantasy RPG "Dungeon and Stone", veteran gamer Hansoo Lee finally reaches the final boss room... only to wake up inside the game itself as Bjorn, a muscle-headed barbarian warrior facing immediate execution!

In this brutal roguelike world, permadeath is real, party members backstab for loot, and low-tier barbarians are treated like cannon fodder. Watch Hansoo use his encyclopedic game knowledge, stat min-maxing, and sheer survival instincts to outsmart traps, monster ambushes, and greedy player-killers.

Enjoy this complete 2-Hour Movie Recap of Chapters 1 to 20!

TIMESTAMPS:
00:00 - Chapter 01: Awakening in the Labyrinth
06:03 - Chapter 02: Trial of the Barbarians
13:24 - Chapter 03: The Bloodstained Floor
19:45 - Chapter 04: The First Monster Hunt
25:49 - Chapter 05: Crystal Cavern Secrets
32:00 - Chapter 06: Traitor's Ambush
38:05 - Chapter 07: Meeting Erwin the Elf
43:37 - Chapter 08: Tactical Alliance
48:59 - Chapter 09: The Goblin Forest
54:25 - Chapter 10: Counterattack
59:52 - Chapter 11: Claiming the Essence
01:05:13 - Chapter 12: Return to the City
01:12:44 - Chapter 13: Blood Money & Upgrades
01:18:48 - Chapter 14: Guild Registration
01:24:19 - Chapter 15: Tavern Brawl & Bounty
01:30:28 - Chapter 16: Safe Haven Secrets
01:36:29 - Chapter 17: Preparing for Floor Two
01:43:53 - Chapter 18: The Dungeon Gate Opens
01:52:03 - Chapter 19: The Undead Swarm
01:58:45 - Chapter 20: Battle of the Monument

Series: Survive as a Barbarian in the Game (게임 속 바바리안으로 살아남기)
Chapters: 1 - 20 (Full Movie Edition)

#manhwarecap #mangarecap #animerecap #isekai #actionmanhwa #manhwa
"""

TAGS = [
    "survive as a barbarian in the game",
    "manhwa recap",
    "manga recap",
    "anime recap",
    "manhwa recap movie",
    "isekai manhwa recap",
    "action manhwa",
    "full movie recap",
    "overpowered mc",
    "game recap",
    "dungeon and stone",
    "manhwa summary",
    "manhwa full story",
]


def upload_movie(
    video_path: Path,
    thumb_path: Path,
    privacy: str = "public",
) -> None:
    if not video_path.exists():
        print(f"Error: Video file not found at {video_path}", file=sys.stderr)
        sys.exit(1)

    if not thumb_path.exists():
        print(f"Error: Thumbnail file not found at {thumb_path}", file=sys.stderr)
        sys.exit(1)

    uploader = YouTubeUploader()
    service = uploader.get_service()

    print("=" * 70)
    print("UPLOADING 2-HOUR MOVIE RECAP TO YOUTUBE")
    print("=" * 70)
    print(f"Video File:     {video_path} ({video_path.stat().st_size / 1e6:.1f} MB)")
    print(f"Thumbnail File: {thumb_path}")
    print(f"Privacy Status: {privacy} (PUBLIC LIVE)")
    print(f"Title:          {TITLE}")
    print(f"Tags Count:     {len(TAGS)}")
    print("=" * 70, flush=True)

    body = {
        "snippet": {
            "title": TITLE,
            "description": DESCRIPTION,
            "tags": TAGS,
            "categoryId": "24",  # Entertainment
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        chunksize=1024 * 1024 * 16,  # 16 MB chunks
        resumable=True,
    )

    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    print("\nStarting resumable video upload...", flush=True)
    response = None
    t0 = time.time()
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            elapsed = time.time() - t0
            speed_mb = (status.progress() * video_path.stat().st_size) / (elapsed * 1e6) if elapsed > 0 else 0
            print(f"Upload progress: {pct}% ({status.resumable_progress / 1e6:.1f} MB / {video_path.stat().st_size / 1e6:.1f} MB) @ {speed_mb:.1f} MB/s", flush=True)

    video_id = response.get("id")
    print(f"\n[SUCCESS] Video uploaded successfully! Video ID: {video_id}")
    video_url = f"https://youtu.be/{video_id}"
    print(f"Watch URL: {video_url}", flush=True)

    # Set Custom Thumbnail
    print(f"\nSetting custom thumbnail from {thumb_path}...", flush=True)
    try:
        thumb_media = MediaFileUpload(str(thumb_path), mimetype="image/png")
        service.thumbnails().set(
            videoId=video_id,
            media_body=thumb_media,
        ).execute()
        print("[SUCCESS] Custom thumbnail applied successfully!", flush=True)
    except Exception as exc:
        print(f"[WARNING] Could not set thumbnail via API: {exc}", file=sys.stderr)

    print("\n" + "=" * 70)
    print("VIDEO IS NOW LIVE ON YOUTUBE!")
    print(f"URL: {video_url}")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Upload movie recap to YouTube")
    parser.add_argument("--video", type=Path, default=VIDEO_PATH, help="Video file path")
    parser.add_argument("--thumb", type=Path, default=DEFAULT_THUMB_PATH, help="Thumbnail file path")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"], help="Privacy status")
    args = parser.parse_args()

    upload_movie(args.video, args.thumb, privacy=args.privacy)


if __name__ == "__main__":
    main()
