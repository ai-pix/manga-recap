"""Generate and organize multiple thumbnail options with both text and raw variants."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.make_clickbait_thumbnail import create_clickbait_thumbnail
from scripts.make_manga_style_thumbnail import create_manga_splash_thumbnail

OUT_DIR = Path("data/youtube_ready/thumbnail_options")
OUT_DIR.mkdir(parents=True, exist_ok=True)

IMG1 = Path(r"C:\Users\ravih\.gemini\antigravity-cli\brain\5ec274e6-8f03-4197-9d9b-65cfad957695\vrmmo_god_tier_thumbnail_1791105986320.jpg")
IMG2 = Path(r"C:\Users\ravih\.gemini\antigravity-cli\brain\5ec274e6-8f03-4197-9d9b-65cfad957695\broken_system_anime_recap_thumbnail_1791106171486.jpg")
IMG3 = Path(r"C:\Users\ravih\.gemini\antigravity-cli\brain\5ec274e6-8f03-4197-9d9b-65cfad957695\unbeatable_raid_solo_thumbnail_1791106170993.jpg")
MANGA_SPLASH = Path("data/chapters/ch022/02_panels/panel_0081.png")

# Option 1: The Broken Senses Bow & Alchemy (Original)
shutil.copy2(IMG1, OUT_DIR / "Option_1_Trash_Senses_Raw.jpg")
create_clickbait_thumbnail(
    IMG1,
    OUT_DIR / "Option_1_Trash_Senses_Clickbait.jpg",
    top_text="TRASH SKILLS?!",
    bottom_text="HE BROKE THE GAME!",
    badge_text="5 HOUR FULL STORY"
)

# Option 2: The System Glitch & Max Alchemy
shutil.copy2(IMG2, OUT_DIR / "Option_2_System_Glitch_Raw.jpg")
create_clickbait_thumbnail(
    IMG2,
    OUT_DIR / "Option_2_System_Glitch_Clickbait.jpg",
    top_text="SYSTEM ERROR?!",
    bottom_text="LEVEL MAX CRAFTER!",
    badge_text="GAME-BREAKING BUILD"
)

# Option 3: The Colossal World Boss & Nine-Tailed Fox Raid
shutil.copy2(IMG3, OUT_DIR / "Option_3_Colossal_Raid_Raw.jpg")
create_clickbait_thumbnail(
    IMG3,
    OUT_DIR / "Option_3_Colossal_Raid_Clickbait.jpg",
    top_text="SOLO RAID BOSS?!",
    bottom_text="1-SHOT THE TITAN!",
    badge_text="MARATHON RECAP"
)

# Option 4: Dynamic Duo-Tone Manga Action Splash
create_manga_splash_thumbnail(
    MANGA_SPLASH,
    OUT_DIR / "Option_4_Manga_Action_Splash.jpg",
    top_text="1-SHOT THE WORLD BOSS?!",
    bottom_text="WEAKEST ARCHER DID THIS!",
    badge_text="FULL RECAP (CH 1-30)"
)

print("All 4 thumbnail options generated in:")
print(f"  {OUT_DIR.resolve()}")
