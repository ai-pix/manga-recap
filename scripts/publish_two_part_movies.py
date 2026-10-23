"""Publish Part 1 (Public Live) and Part 2 (Scheduled for Wednesday) to YouTube."""

import datetime
import json
import sys
from pathlib import Path

from manga_recap.core.paths import repo_path
from manga_recap.stages.s7_publish.youtube import (
    UploadMetadata,
    YouTubeUploader,
)

TAGS = [
    "manhwa recap",
    "manga recap",
    "anime recap",
    "only sense online",
    "overpowered mc",
    "trash to god",
    "vrmmo recap",
    "full series recap",
    "9 hour recap",
    "anime marathon",
    "isekai recap",
    "leveling up",
    "crafter class",
    "hidden class",
    "zero to hero",
    "manhwa summary",
    "manga summary",
    "anime binge",
    "anime full movie",
]


def load_timestamps(ts_path: Path) -> str:
    if ts_path.exists():
        return ts_path.read_text(encoding="utf-8").strip()
    return ""


def build_part1_description() -> str:
    ts_text = load_timestamps(repo_path("data/Only_Sense_Online_Part_1_Timestamps.txt"))
    return f"""While everyone chose flashy swords and overpowered combat magic, one boy made the biggest mistake in gaming history—accidentally registering under a girl's name and picking the server's most useless 'trash' abilities: Potion Making and Bow Archery. But what the top guilds didn't know was the terrifying hidden synergy behind his rejected skills. From soloing impossible dungeon bosses to turning the entire VRMMO market upside down, witness the complete 9-hour journey of how a rejected crafter became an untouchable god.

🔥 PART 2 (THE 9-HOUR GRAND FINALE) RELEASES THIS WEDNESDAY AT 1:00 PM EST!
Make sure to Subscribe and turn on the 🔔 Notification Bell so you don't miss the conclusion!

⏱️ CHAPTER TIMESTAMPS:
{ts_text}

📖 Series: Only Sense Online (Chapters 01 to 55)
🎭 Genre: Action, Fantasy, VRMMO, Comedy, Adventure, Crafting
🎙️ Narrator: Anime Fusion
⚡ Visual & Audio: Full HD 1080p 60FPS Remastered

--------------------------------------------------------------------------------
⚠️ FAIR USE DISCLAIMER:
This video is a transformative recap and analytical review created under the Fair Use doctrine (Section 107 of the US Copyright Act). All manga panels, imagery, and intellectual property belong to their respective authors, artists, and publishers. Our content features original transformative narration, story restructuring, comedic commentary, and educational analysis.
--------------------------------------------------------------------------------
#manhwarecap #mangarecap #animerecap #onlysenseonline #fullrecap
"""


def build_part2_description() -> str:
    ts_text = load_timestamps(repo_path("data/Only_Sense_Online_Part_2_Timestamps.txt"))
    return f"""The definitive 9-Hour Grand Finale of Only Sense Online!
What happens when a crafter pushes game mechanics past what the developers ever programmed? In Part 2, Yun crosses into the deadly uncharted frontier, unlocking taboo companion evolutions, forbidden alchemical recipes, and masterwork elemental archery. When ancient titan raid bosses and collosal leviathans descend to wipe out entire server alliances, the boy who started with a wooden bow takes his stand on the frontlines to balance the battlefield and conquer the game once and for all.

🎬 WATCH PART 1 HERE:
https://youtu.be/PLACEHOLDER_PART1_ID

⏱️ CHAPTER TIMESTAMPS:
{ts_text}

📖 Series: Only Sense Online (Chapters 56 to 112 - Complete Conclusion)
🎭 Genre: Action, Fantasy, VRMMO, Comedy, Adventure, Crafting, Raid Bosses
🎙️ Narrator: Anime Fusion
⚡ Visual & Audio: Full HD 1080p Remastered

--------------------------------------------------------------------------------
⚠️ FAIR USE DISCLAIMER:
This video is a transformative recap and analytical review created under the Fair Use doctrine (Section 107 of the US Copyright Act). All manga panels, imagery, and intellectual property belong to their respective authors, artists, and publishers. Our content features original transformative narration, story restructuring, comedic commentary, and educational analysis.
--------------------------------------------------------------------------------
#manhwarecap #mangarecap #animerecap #onlysenseonline #fullrecap
"""


def main():
    uploader = YouTubeUploader()

    part1_video = Path("C:/Users/ravih/Videos/MangaRecap/Only_Sense_Online_Part_1_Chapters_01_to_55_9Hours.mp4")
    part2_video = Path("C:/Users/ravih/Videos/MangaRecap/Only_Sense_Online_Part_2_Chapters_56_to_112_9Hours.mp4")

    part1_thumb = repo_path("data/thumbnails/Only_Sense_Online_Part_1_Evolution_Thumbnail.jpg")
    part2_thumb = repo_path("data/thumbnails/Only_Sense_Online_Part_2_Thumbnail.jpg")

    if not part1_video.exists():
        print(f"[error] Part 1 video not found: {part1_video}")
        return 1
    if not part2_video.exists():
        print(f"[error] Part 2 video not found: {part2_video}")
        return 1

    print("=" * 70)
    print("YOUTUBE PUBLISHING PIPELINE")
    print("=" * 70)
    print(f"Part 1 Video: {part1_video.name} ({part1_video.stat().st_size / 1e9:.2f} GB)")
    print(f"Part 2 Video: {part2_video.name} ({part2_video.stat().st_size / 1e9:.2f} GB)")
    print(f"Part 1 Thumbnail: {part1_thumb.name}")
    print(f"Part 2 Thumbnail: {part2_thumb.name}")
    print("=" * 70 + "\n")

    # ----------------------------------------------------
    # STEP 1: Upload Part 1 (PUBLIC LIVE)
    # ----------------------------------------------------
    part1_title = "He Picked The Worst TRASH Senses, But Unlocked A Secret God Class! (Part 1) [9 HOURS] - Manga Recap"
    part1_meta = UploadMetadata(
        title=part1_title,
        description=build_part1_description(),
        tags=TAGS,
        video_path=part1_video,
        thumbnail_path=part1_thumb,
        category_id="24",  # Entertainment
    )

    print("\n>>> UPLOADING PART 1 (PUBLIC - LIVE RIGHT NOW)...")
    part1_id = uploader.upload_video(part1_meta, privacy_status="public")
    if part1_thumb.exists():
        uploader.set_thumbnail(part1_id, part1_thumb)

    print(f"\n[PART 1 LIVE]: https://youtu.be/{part1_id}")

    # ----------------------------------------------------
    # STEP 2: Upload Part 2 (SCHEDULED FOR WEDNESDAY 1:00 PM EST)
    # Wednesday Oct 7, 2026 13:00 EDT = 17:00:00Z UTC
    # ----------------------------------------------------
    wednesday_publish_utc = "2026-10-07T17:00:00Z"
    part2_title = "When The Trash Crafter Defeats The Server's #1 Titan Alliance! (Part 2) [9 HOURS] - Manga Recap"

    # Inject actual Part 1 link into Part 2 description
    part2_desc = build_part2_description().replace("PLACEHOLDER_PART1_ID", part1_id)

    part2_meta = UploadMetadata(
        title=part2_title,
        description=part2_desc,
        tags=TAGS,
        video_path=part2_video,
        thumbnail_path=part2_thumb,
        category_id="24",  # Entertainment
    )

    print(f"\n>>> UPLOADING PART 2 (SCHEDULED FOR WEDNESDAY at 1:00 PM EST: {wednesday_publish_utc})...")
    part2_id = uploader.upload_video(part2_meta, privacy_status="private", publish_at=wednesday_publish_utc)
    if part2_thumb.exists():
        uploader.set_thumbnail(part2_id, part2_thumb)

    print(f"\n[PART 2 SCHEDULED]: https://youtu.be/{part2_id}")

    # Record in history
    history_file = repo_path("data/youtube_uploads_movies.json")
    history_data = {
        "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "part1": {
            "id": part1_id,
            "url": f"https://youtu.be/{part1_id}",
            "status": "public",
            "title": part1_title,
            "duration": "9h 07m",
        },
        "part2": {
            "id": part2_id,
            "url": f"https://youtu.be/{part2_id}",
            "status": "scheduled",
            "publish_at": wednesday_publish_utc,
            "title": part2_title,
            "duration": "8h 51m",
        },
    }
    history_file.write_text(json.dumps(history_data, indent=2), encoding="utf-8")
    print(f"\n[DONE] Saved upload details to {history_file}")

    print("\n" + "=" * 70)
    print("SUCCESS: BOTH 9-HOUR MOVIES PUBLISHED TO YOUTUBE!")
    print(f"  Part 1 (LIVE):      https://youtu.be/{part1_id}")
    print(f"  Part 2 (WEDNESDAY): https://youtu.be/{part2_id}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
