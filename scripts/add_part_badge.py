"""Add high-impact 'PART 1' badges to the Option B thumbnail."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

IMPACT_FONT = Path("C:/Windows/Fonts/impact.ttf")
ARIAL_BD = Path("C:/Windows/Fonts/arialbd.ttf")


def draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    text: str,
    pos: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill_color: tuple[int, int, int],
    outline_color: tuple[int, int, int] = (0, 0, 0),
    outline_width: int = 5,
):
    x, y = pos
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    draw.text((x, y), text, font=font, fill=fill_color)


def create_part1_variants(src_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    base = Image.open(src_path).convert("RGB")
    # Resize to exact 1280x720 standard YouTube thumbnail format
    base_1280 = base.resize((1280, 720), Image.Resampling.LANCZOS)

    font_path = str(IMPACT_FONT) if IMPACT_FONT.exists() else "arial.ttf"

    # =========================================================================
    # Variant 1: Top-Left Neon Red Pill Badge (Safe from YouTube duration overlay)
    # =========================================================================
    img1 = base_1280.copy()
    overlay1 = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(overlay1)
    badge_font1 = ImageFont.truetype(font_path, 46)

    text = "PART 1"
    bbox = d1.textbbox((0, 0), text, font=badge_font1)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    bx, by = 45, 35
    padding_x = 24
    padding_y = 12
    badge_w = tw + padding_x * 2
    badge_h = th + padding_y * 2

    # Drop shadow
    d1.rounded_rectangle([bx + 4, by + 4, bx + badge_w + 4, by + badge_h + 4], radius=12, fill=(0, 0, 0, 180))
    # Red background with white outline
    d1.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=12, fill=(235, 25, 25, 250), outline=(255, 255, 255, 255), width=4)
    # White text with subtle black outline
    draw_text_with_outline(d1, text, (bx + padding_x, by + padding_y - 2), badge_font1, fill_color=(255, 255, 255), outline_color=(0, 0, 0), outline_width=3)

    out1 = Image.alpha_composite(img1.convert("RGBA"), overlay1).convert("RGB")
    v1_path = out_dir / "Option_B_Part1_TopLeft_RedBadge.jpg"
    out1.save(v1_path, quality=95)
    print("Saved Variant 1:", v1_path)

    # =========================================================================
    # Variant 2: Angled Comic Burst / Gold & Black Ribbon (Anime Pop Style)
    # =========================================================================
    img2 = base_1280.copy()
    badge_img = Image.new("RGBA", (280, 120), (0, 0, 0, 0))
    bd = ImageDraw.Draw(badge_img)
    gold_font = ImageFont.truetype(font_path, 52)

    # Yellow/Gold badge with black border
    bd.rounded_rectangle([10, 10, 270, 95], radius=14, fill=(255, 215, 0, 255), outline=(0, 0, 0, 255), width=5)
    # Inner border
    bd.rounded_rectangle([15, 15, 265, 90], radius=10, fill=None, outline=(255, 255, 255, 220), width=2)
    draw_text_with_outline(bd, "★ PART 1 ★", (32, 22), gold_font, fill_color=(0, 0, 0), outline_color=(255, 255, 255), outline_width=2)

    # Rotate -8 degrees for anime kinetic flair
    badge_rotated = badge_img.rotate(8, resample=Image.Resampling.BICUBIC, expand=True)

    overlay2 = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    overlay2.paste(badge_rotated, (35, 25), mask=badge_rotated)
    out2 = Image.alpha_composite(img2.convert("RGBA"), overlay2).convert("RGB")
    v2_path = out_dir / "Option_B_Part1_GoldAnimeSticker.jpg"
    out2.save(v2_path, quality=95)
    print("Saved Variant 2:", v2_path)

    # =========================================================================
    # Variant 3: Bottom-Left Sleek Red Cyber Tag
    # =========================================================================
    img3 = base_1280.copy()
    overlay3 = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(overlay3)
    font3 = ImageFont.truetype(font_path, 54)

    t3 = "PART 1"
    b3 = d3.textbbox((0, 0), t3, font=font3)
    tw3 = b3[2] - b3[0]
    th3 = b3[3] - b3[1]
    bx3, by3 = 50, 720 - th3 - 75

    d3.rounded_rectangle([bx3 - 6, by3 - 6, bx3 + tw3 + 36, by3 + th3 + 26], radius=8, fill=(0, 0, 0, 200))
    d3.rounded_rectangle([bx3 - 10, by3 - 10, bx3 + tw3 + 30, by3 + th3 + 20], radius=8, fill=(220, 20, 40, 245), outline=(255, 255, 255, 240), width=3)
    draw_text_with_outline(d3, t3, (bx3 + 10, by3 + 2), font3, fill_color=(255, 255, 255), outline_color=(0, 0, 0), outline_width=4)

    out3 = Image.alpha_composite(img3.convert("RGBA"), overlay3).convert("RGB")
    v3_path = out_dir / "Option_B_Part1_BottomLeft_Tag.jpg"
    out3.save(v3_path, quality=95)
    print("Saved Variant 3:", v3_path)

    # Also set Variant 1 as the default active thumbnail in Chapter 1 folder
    ch1_thumb = Path("data/youtube_ready/Chapter_01_Enter_the_World_of_OSO/thumbnail.jpg")
    out1.save(ch1_thumb, quality=95)
    print("Updated Chapter 1 active thumbnail with Option B Part 1!")


if __name__ == "__main__":
    src = Path("data/youtube_ready/playful_anime_thumbnails/Option_B_Weakest_Class_Broke_The_Game.jpg")
    out = Path("data/youtube_ready/playful_anime_thumbnails")
    create_part1_variants(src, out)
