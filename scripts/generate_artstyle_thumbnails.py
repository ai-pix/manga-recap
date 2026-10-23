"""Generate and organize distinct art style thumbnail packages."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.make_clickbait_thumbnail import create_clickbait_thumbnail

OUT_DIR = Path("data/youtube_ready/thumbnail_artstyles")
OUT_DIR.mkdir(parents=True, exist_ok=True)

MANHWA_IMG = Path(r"C:\Users\ravih\.gemini\antigravity-cli\brain\5ec274e6-8f03-4197-9d9b-65cfad957695\manhwa_recap_thumbnail_1791106336972.jpg")
TRIGGER_IMG = Path(r"C:\Users\ravih\.gemini\antigravity-cli\brain\5ec274e6-8f03-4197-9d9b-65cfad957695\trigger_style_thumbnail_1791106338230.jpg")
CINEMATIC_IMG = Path(r"C:\Users\ravih\.gemini\antigravity-cli\brain\5ec274e6-8f03-4197-9d9b-65cfad957695\fantasy_crafter_bow_thumbnail_1791106341951.jpg")

# 1. Dark Action Manhwa Style (Solo Leveling style)
shutil.copy2(MANHWA_IMG, OUT_DIR / "Style_1_Dark_Manhwa_Raw.jpg")
create_clickbait_thumbnail(
    MANHWA_IMG,
    OUT_DIR / "Style_1_Dark_Manhwa_Clickbait.jpg",
    top_text="SHADOW CRAFTER?!",
    bottom_text="THE WEAKEST AWAKENED!",
    badge_text="SSS-RANK SENSE"
)

# 2. Studio Trigger / Graphic Pop Anime Style (Cyberpunk Edgerunners / Kill la Kill)
shutil.copy2(TRIGGER_IMG, OUT_DIR / "Style_2_Trigger_Pop_Anime_Raw.jpg")
create_clickbait_thumbnail(
    TRIGGER_IMG,
    OUT_DIR / "Style_2_Trigger_Pop_Anime_Clickbait.jpg",
    top_text="CRAZY ALCHEMY?!",
    bottom_text="HE BROKE THE SYSTEM!",
    badge_text="MAX LEVEL CRAFTER"
)

# 3. Semi-Realistic Cinematic 3D Fantasy Style (UE5 / League of Legends / Genshin Cinematic)
shutil.copy2(CINEMATIC_IMG, OUT_DIR / "Style_3_Cinematic_3D_Fantasy_Raw.jpg")
create_clickbait_thumbnail(
    CINEMATIC_IMG,
    OUT_DIR / "Style_3_Cinematic_3D_Fantasy_Clickbait.jpg",
    top_text="TRASH SENSES?!",
    bottom_text="THE ULTIMATE CRAFTER!",
    badge_text="5 HOUR FULL STORY"
)

print(f"All 3 new art styles generated successfully in: {OUT_DIR.resolve()}")
