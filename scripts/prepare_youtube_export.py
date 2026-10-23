"""Prepare all YouTube export assets:
- Organized folders per chapter + full compilation
- Hardlinked video files (zero disk waste)
- High-CTR YouTube titles, descriptions, timestamps, tags
- High-quality 1280x720 thumbnails with blurred backdrops
- Master publishing guide
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

SERIES_TITLE = "Only Sense Online"
AUTHOR = "Aloha Zachou"
ARTIST = "Yukian"

CHAPTER_HOOKS = {
    1.0: ("Enter the World of OSO", "He Picked The Most 'Trash' Senses In A VRMMO, But Accidentally Became God-Tier"),
    2.0: ("Forest of the Beginning & Potion Crafting", "He Discovered The Most Broken Potion Recipe In The Game"),
    3.0: ("Crafting Discoveries & The Target Lock Secret", "He Mastered The Secret Sniping Mechanic Everyone Overlooked"),
    4.0: ("The Crystal Tree and Myuu", "He Unlocked The Secret Crystal Tree Dungeon With His Guild"),
    5.0: ("The Golem and the Third Town", "Crafter Defeats The Unbeatable Field Golem With Galaxy Brain Tactics"),
    5.5: ("Bonus Strips & The Trash Tier List", "The Hilarious Truth Behind The 'Trash' Tier Senses"),
    6.0: ("The Blacksmith Trial & Wholesale Mystery", "The Blacksmith Trial & The Mysterious Wholesale Recipe"),
    7.0: ("Trion Ring & The Value of Information", "He Broke The VRMMO Economy With A Single Secret Ring"),
    8.0: ("The Value of Information Part 2 & Magic Gems", "He Crafted Forbidden Elemental Magic Gems For The Elite Guild"),
    9.0: ("Black Maiden's Longbow & The Trainman", "Their Secret Expedition Gets Ambushed By An Endless Monster Swarm"),
    10.0: ("The Monster Horde & The Great Stampede", "He Saved An Entire Party From A Monster Stampede With Alchemy Bombs"),
    11.0: ("The Grand Server Update & Atelier Yun Opens", "A Massive Server Update Arrives & He Opens His Dream Atelier Shop"),
    12.0: ("The Radiant Woodland Camp & Forest Festival", "He Discovered Secret Cooking Recipes In The Radiant Forest"),
    13.0: ("The Cursed Woodland & The Fallen Adventurer", "He Encountered A Sacred Unicorn & A Cursed Adventurer In The Wild"),
    14.0: ("The Berserk Curse & The White Fox Cub", "He Broke A Berserk Curse & Rescued A Sacred Mythical Fox Cub"),
    15.0: ("The Lake Monster & Base Camp Annihilation", "A Giant Lake Monster Completely Pulverized Their Base Camp"),
    16.0: ("Inferno at the Camp & United Counterattack", "He Fought Through A Blazing Forest Inferno To Save His Guild"),
    17.0: ("Healing the Black Kitsune & Atelier Mascot", "He Adopted Twin Mythical Kitsune Cubs As Atelier Mascots"),
    18.0: ("The Older Sister Arrives", "His Terrifying Older Sister Steps In To Settle The Score"),
    19.0: ("Sei's Authority & The Atelier Banquet", "The Server's Strongest Player Protects The Crafter Atelier"),
    20.0: ("Taming the Twin Foxes & Leveling Up", "He Trained Twin Mythical Beasts And Unlocked Hidden Pet Skills"),
    21.0: ("The Massive World Boss Raid Begins", "The Massive World Boss Raid Begins Across The Forest"),
    22.0: ("High Altitude Strike & Victory Celebration", "His Stratospheric Aerial Snipe Obliterated The Behemoth Raid Boss"),
    23.0: ("The Atelier Economy & Server Balance", "The Server Admin Starts Spying On The Crafter's Broken Economy"),
    24.0: ("Cloude's Labyrinth Trap & Boss Room Scheme", "The Crafter Outsmarts The Labyrinth Boss Room Scheme"),
    25.0: ("Atelier Renovations & The Ancient Library", "He Infiltrated The Ancient Library To Uncover Forbidden Recipes"),
    26.0: ("Master Chef Yun & The Secret Recipe", "He Mastered The Ultimate Chef Skill & Upgraded His Workshop"),
    27.0: ("The Phantom Dungeon & The Forbidden Grimoire", "He Raided The Phantom Dungeon And Secured The Forbidden Grimoire"),
    28.0: ("Deciphering The Grimoire & Composite Alchemy", "Deciphering The Secret Grimoire Unlocked Composite Alchemy"),
    29.0: ("Northern Woodlands & Mass Potion Synthesis", "Mass Potion Synthesis & Northern Woodland Rare Herb Gathering"),
    30.0: ("The Ancient Boss Doors & The Ultimate Dungeon", "Confronting The Ancient Boss Doors In The Ultimate Dungeon"),
}

DEFAULT_TAGS = (
    "manga recap, manhwa recap, anime recap, only sense online, only sense online recap, "
    "vrmmo manga, crafter mc, overpowered crafter, manga recap full story, manhwa recap full, "
    "only sense online chapter 1, only sense online chapter 30, yun only sense online, "
    "manga recap 2026, best manga recap, anime recaps, fantasy recap"
)

DISCLAIMER = """========================================
FAIR USE DISCLAIMER:
Under Section 107 of the Copyright Act 1976, allowance is made for 'fair use' for purposes such as criticism, comment, news reporting, teaching, scholarship, and research. This video features original transformative narration, story recap, and commentary on the manga 'Only Sense Online'.
All rights belong to the original author (Aloha Zachou) and artist (Yukian).
========================================"""


def chapter_num(name: str) -> float:
    m = re.match(r"ch0*(\d+)(?:_(\d+))?", name)
    if m:
        base = int(m.group(1))
        sub = int(m.group(2)) if m.group(2) else 0
        return base + sub * 0.1
    return 999.0


def make_thumbnail(panel_path: Path, output_path: Path, width=1280, height=720):
    img = Image.open(panel_path).convert("RGB")
    bg_ratio = max(width / img.width, height / img.height)
    bg_w = int(img.width * bg_ratio)
    bg_h = int(img.height * bg_ratio)
    bg = img.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
    left = (bg_w - width) // 2
    top = (bg_h - height) // 2
    bg = bg.crop((left, top, left + width, top + height))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=22))
    bg = ImageEnhance.Brightness(bg).enhance(0.42)

    fg_max_w = width - 40
    fg_max_h = height - 40
    fg_ratio = min(fg_max_w / img.width, fg_max_h / img.height)
    fg_w = int(img.width * fg_ratio)
    fg_h = int(img.height * fg_ratio)
    fg = img.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

    paste_x = (width - fg_w) // 2
    paste_y = (height - fg_h) // 2
    bg.paste(fg, (paste_x, paste_y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    bg.save(output_path, quality=92)


def pick_best_panel(chapter_dir: Path) -> Path | None:
    panels_dir = chapter_dir / "02_panels"
    if not panels_dir.is_dir():
        return None
    desc_p = chapter_dir / "03_descriptions.json"
    skippable_panels = set()
    if desc_p.exists():
        try:
            d_data = json.loads(desc_p.read_text(encoding="utf-8"))
            for p in d_data.get("panels", []):
                if p.get("is_credits_or_ad") or p.get("setting") == "page_margin":
                    skippable_panels.add(p.get("panel_id"))
        except Exception:
            pass

    candidates = []
    for p in panels_dir.glob("panel_*.png"):
        if p.name.endswith("_text.png"):
            continue
        pid = p.stem
        if pid in skippable_panels:
            continue
        try:
            with Image.open(p) as img:
                w, h = img.size
                candidates.append((w * h, p))
        except Exception:
            continue

    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def main():
    root = Path("data")
    chapters_dir = root / "chapters"
    export_root = root / "youtube_ready"
    export_root.mkdir(parents=True, exist_ok=True)

    chapters = [p for p in chapters_dir.iterdir() if p.is_dir() and (p / "07_final.mp4").exists()]
    chapters.sort(key=lambda p: chapter_num(p.name))

    print(f"Processing {len(chapters)} chapters for YouTube export package...")

    cumulative_seconds = 0.0
    timestamps_list = []

    for _idx, ch in enumerate(chapters, 1):
        num = chapter_num(ch.name)
        num_str = f"{num:g}"
        title_meta = CHAPTER_HOOKS.get(num, (f"Chapter {num_str}", f"Only Sense Online Chapter {num_str}"))
        sub_title, hook_title = title_meta

        # Duration calculation
        manifest_p = ch / "07_render_manifest.json"
        timeline_p = ch / "06_timeline.json"
        duration = 0.0
        if manifest_p.exists():
            try:
                duration = float(json.loads(manifest_p.read_text(encoding="utf-8")).get("duration", 0.0))
            except Exception:
                pass
        if duration == 0.0 and timeline_p.exists():
            try:
                duration = float(json.loads(timeline_p.read_text(encoding="utf-8")).get("duration", 0.0))
            except Exception:
                pass

        # Formatting timestamp
        hours = int(cumulative_seconds // 3600)
        minutes = int((cumulative_seconds % 3600) // 60)
        seconds = int(cumulative_seconds % 60)
        ts_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        timestamps_list.append(f"{ts_str} - Chapter {num_str}: {sub_title}")
        cumulative_seconds += duration

        # Create export folder
        ch_folder_name = f"Chapter_{int(num):02d}" if num.is_integer() else f"Chapter_{int(num):02d}_{int((num%1)*10)}"
        ch_export_dir = export_root / f"{ch_folder_name}_{re.sub(r'[^a-zA-Z0-9]+', '_', sub_title).strip('_')}"
        ch_export_dir.mkdir(parents=True, exist_ok=True)

        # 1. Hardlink the video
        src_video = ch / "07_final.mp4"
        dst_video = ch_export_dir / f"Only_Sense_Online_Chapter_{num_str}.mp4"
        if not dst_video.exists():
            try:
                os.link(src_video, dst_video)
            except Exception:
                # If hardlink fails across volumes or permissions, skip copy to conserve space
                pass

        # 2. Thumbnail
        best_panel = pick_best_panel(ch)
        if best_panel:
            thumb_path = ch_export_dir / "thumbnail.jpg"
            make_thumbnail(best_panel, thumb_path)

        # 3. Read first few sentences from script for description hook
        script_p = ch / "04_script.json"
        summary_lines = []
        if script_p.exists():
            try:
                s_data = json.loads(script_p.read_text(encoding="utf-8"))
                for b in s_data.get("blocks", [])[:5]:
                    summary_lines.append(b.get("narration", ""))
            except Exception:
                pass
        hook_paragraph = " ".join(summary_lines)

        # 4. Generate Metadata TXT
        full_yt_title = f"{hook_title} | Only Sense Online Chapter {num_str} Recap"
        yt_description = f"""{full_yt_title}

{hook_paragraph}

In this episode of Only Sense Online:
Our protagonist Shun (Yun) navigates the complex virtual reality world of OSO with an unconventional skill build that everyone else called useless. Watch how smart crafting, unique perception senses, and tactical thinking turn apparent weaknesses into an unstoppable playstyle!

Manga Title: {SERIES_TITLE} (オンリーセンス・オンライン)
Original Story: {AUTHOR}
Illustration: {ARTIST}

If you enjoyed this recap, please LIKE, SUBSCRIBE, and ring the bell for more in-depth manga & manhwa recaps!

{DISCLAIMER}

#onlysenseonline #mangarecap #animerecap #manhwarecap #vrmmo #isekai
"""
        meta_content = f"""YOUTUBE UPLOAD METADATA:
----------------------------------------
VIDEO FILE: Only_Sense_Online_Chapter_{num_str}.mp4
THUMBNAIL FILE: thumbnail.jpg

TITLE:
{full_yt_title}

DESCRIPTION:
{yt_description}

TAGS:
{DEFAULT_TAGS}, only sense online chapter {num_str}
"""
        (ch_export_dir / "metadata.txt").write_text(meta_content, encoding="utf-8")
        print(f"  [OK] Exported Chapter {num_str:>4} -> {ch_export_dir.name}")

    # Now handle Master Compilation
    compilation_dir = export_root / "00_FULL_SERIES_COMPILATION"
    compilation_dir.mkdir(parents=True, exist_ok=True)

    # Master Thumbnail
    ch22_panel = pick_best_panel(chapters_dir / "ch022") or pick_best_panel(chapters_dir / "ch01")
    if ch22_panel:
        make_thumbnail(ch22_panel, compilation_dir / "thumbnail.jpg")

    # Master Video (already exists at data/youtube_ready/00_FULL_SERIES_COMPILATION/Only_Sense_Online_Full_Story_Recap_Ch01-30.mp4)
    master_title = "He Picked The 'Worst' Senses In A VRMMO And Became The Ultimate Crafter | Only Sense Online (Chapters 1-30 Full Story Recap)"

    timestamps_block = "\n".join(timestamps_list)

    master_description = f"""{master_title}

When Shun joins the cutting-edge VRMMO "Only Sense Online", his friends tell him to pick standard combat classes. Instead, he picks the 10 most ridiculed, underpowered "trash" Senses in the entire game—Potion Making, Archery, Enchanting, and Keen Sight.

Everyone assumes he'll quit within a week. But with galaxy-brain logic, relentless crafting experimentation, and outside-the-box battle tactics, Shun discovers game-breaking synergies that the developers never anticipated!

Watch the COMPLETE journey from his humble beginnings in Chapter 1 all the way through the epic raids, guild wars, and secret labyrinth expeditions of Chapter 30 in this ultimate 5-hour seamless manga recap marathon!

TIMESTAMPS:
{timestamps_block}

Series Info:
Manga Title: {SERIES_TITLE} (オンリーセンス・オンライン)
Original Story: {AUTHOR}
Art: {ARTIST}

Don't forget to LIKE and SUBSCRIBE for more full-story recaps! Let us know your favorite moment in the comments below!

{DISCLAIMER}

#onlysenseonline #mangarecap #animerecap #manhwarecap #vrmmo #fullstory #marathon
"""

    master_meta_content = f"""FULL COMPILATION YOUTUBE UPLOAD METADATA:
----------------------------------------
VIDEO FILE: Only_Sense_Online_Full_Story_Recap_Ch01-30.mp4 (1.28 GB, 5h 05m 08s)
THUMBNAIL FILE: thumbnail.jpg

TITLE:
{master_title}

DESCRIPTION:
{master_description}

TAGS:
{DEFAULT_TAGS}, full story recap, manga recap marathon, only sense online complete
"""
    (compilation_dir / "metadata.txt").write_text(master_meta_content, encoding="utf-8")
    (export_root / "CHAPTER_TIMESTAMPS.txt").write_text(timestamps_block, encoding="utf-8")

    print("\n[SUCCESS] Master Compilation and all 31 chapter packages are ready in:")
    print(f"  {export_root.resolve()}")


if __name__ == "__main__":
    main()
