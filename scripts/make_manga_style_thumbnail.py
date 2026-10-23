"""Create stylized manga-art thumbnail with high-contrast color toning and clickbait typography."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.make_clickbait_thumbnail import ARIAL_BD, IMPACT_FONT, draw_text_with_outline


def create_manga_splash_thumbnail(
    manga_panel_path: Path,
    output_path: Path,
    top_text: str = "1-SHOT THE WORLD BOSS?!",
    bottom_text: str = "WEAKEST ARCHER DID THIS!",
    badge_text: str = "FULL RECAP (CH 1-30)",
    target_width: int = 1280,
    target_height: int = 720,
):
    # 1. Load manga panel
    img = Image.open(manga_panel_path).convert("L")  # grayscale

    # Tone it with dynamic cyan/purple duo-tone
    colorized = ImageOps.colorize(img, black="#08081a", white="#ffffff", mid="#4070a0")

    # Background: blurred scaled copy
    bg_ratio = max(target_width / colorized.width, target_height / colorized.height)
    bg_w = int(colorized.width * bg_ratio)
    bg_h = int(colorized.height * bg_ratio)
    bg = colorized.resize((bg_w, bg_h), Image.Resampling.LANCZOS)
    left = (bg_w - target_width) // 2
    top = (bg_h - target_height) // 2
    bg = bg.crop((left, top, left + target_width, top + target_height))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=25))
    bg = ImageEnhance.Brightness(bg).enhance(0.4)

    # Foreground: fit panel nicely
    fg_h = target_height - 30
    fg_ratio = fg_h / colorized.height
    fg_w = int(colorized.width * fg_ratio)
    fg = colorized.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

    # Give foreground a thin white border
    fg_bordered = ImageOps.expand(fg, border=4, fill="#ffffff")

    # Center-right placement so left is open for badges/hooks
    paste_x = target_width - fg_bordered.width - 40
    paste_y = (target_height - fg_bordered.height) // 2
    bg.paste(fg_bordered, (paste_x, paste_y))

    # Text overlay layer
    overlay = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_path = str(IMPACT_FONT) if IMPACT_FONT.exists() else "arial.ttf"
    top_font = ImageFont.truetype(font_path, 80)
    bottom_font = ImageFont.truetype(font_path, 86)
    badge_font = ImageFont.truetype(str(ARIAL_BD) if ARIAL_BD.exists() else font_path, 34)

    # Badge
    if badge_text:
        bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw = bbox[2] - bbox[0] + 30
        bh = bbox[3] - bbox[1] + 16
        draw.rounded_rectangle([40, 40, 40 + bw, 40 + bh], radius=8, fill=(230, 20, 20, 240), outline=(255, 255, 255, 220), width=3)
        draw.text((55, 46), badge_text, font=badge_font, fill=(255, 255, 255))

    # Top Text
    if top_text:
        draw_text_with_outline(draw, top_text, (40, 115), top_font, fill_color=(255, 240, 40), outline_color=(0, 0, 0), outline_width=8)

    # Bottom Banner and text
    if bottom_text:
        shadow_rect = Image.new("RGBA", (target_width, 160), (0, 0, 0, 180))
        overlay.paste(shadow_rect, (0, target_height - 160), mask=shadow_rect)
        draw_text_with_outline(draw, bottom_text, (40, target_height - 130), bottom_font, fill_color=(255, 60, 60), outline_color=(0, 0, 0), outline_width=9)

    result = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, quality=95)
    print(f"Saved manga style thumbnail to {output_path}")
    return output_path


if __name__ == "__main__":
    p = Path("data/chapters/ch022/02_panels/panel_0081.png")
    out = Path("scratch/thumbnail_option_manga_splash.jpg")
    create_manga_splash_thumbnail(p, out)
