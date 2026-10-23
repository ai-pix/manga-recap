"""Create high-CTR, clickbaity YouTube thumbnails with bold text overlays and badges."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

IMPACT_FONT = Path("C:/Windows/Fonts/impact.ttf")
ARIAL_BD = Path("C:/Windows/Fonts/arialbd.ttf")


def draw_text_with_outline(
    draw: ImageDraw.ImageDraw,
    text: str,
    pos: tuple[int, int],
    font: ImageFont.FreeTypeFont,
    fill_color: tuple[int, int, int],
    outline_color: tuple[int, int, int] = (0, 0, 0),
    outline_width: int = 6,
):
    x, y = pos
    # Draw thick stroke around text for high readability
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                draw.text((x + dx, y + dy), text, font=font, fill=outline_color)
    # Inner fill
    draw.text((x, y), text, font=font, fill=fill_color)


def create_clickbait_thumbnail(
    base_image_path: Path,
    output_path: Path,
    top_text: str = "TRASH SKILLS?!",
    bottom_text: str = "HE BROKE THE GAME!",
    badge_text: str = "5 HOUR MARATHON",
    target_width: int = 1280,
    target_height: int = 720,
):
    # 1. Load and scale base image to 1280x720 16:9
    base = Image.open(base_image_path).convert("RGB")
    ratio = max(target_width / base.width, target_height / base.height)
    new_w = int(base.width * ratio)
    new_h = int(base.height * ratio)
    base = base.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_width) // 2
    top = (new_h - target_height) // 2
    base = base.crop((left, top, left + target_width, top + target_height))

    # 2. Boost saturation and contrast for high click-through-rate pop
    base = ImageEnhance.Color(base).enhance(1.25)
    base = ImageEnhance.Contrast(base).enhance(1.15)

    # 3. Create text overlay layer
    overlay = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    font_path = str(IMPACT_FONT) if IMPACT_FONT.exists() else "arial.ttf"
    top_font = ImageFont.truetype(font_path, 88)
    bottom_font = ImageFont.truetype(font_path, 98)
    badge_font = ImageFont.truetype(str(ARIAL_BD) if ARIAL_BD.exists() else font_path, 34)

    # 4. Badge (Top Left, e.g. "5 HOUR MARATHON")
    if badge_text:
        badge_bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
        bw = badge_bbox[2] - badge_bbox[0] + 30
        bh = badge_bbox[3] - badge_bbox[1] + 16
        bx, by = 40, 40
        # Draw red badge rectangle with rounded corners
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8, fill=(230, 20, 20, 240), outline=(255, 255, 255, 220), width=3)
        draw.text((bx + 15, by + 6), badge_text, font=badge_font, fill=(255, 255, 255))

    # 5. Top Text (e.g. "TRASH SKILLS?!")
    if top_text:
        bbox_top = draw.textbbox((0, 0), top_text, font=top_font)
        tw = bbox_top[2] - bbox_top[0]
        # Position top right / center-right
        tx = target_width - tw - 50
        ty = 50
        draw_text_with_outline(draw, top_text, (tx, ty), top_font, fill_color=(255, 235, 50), outline_color=(0, 0, 0), outline_width=8)

    # 6. Bottom Banner & Text (e.g. "HE BROKE THE GAME!")
    if bottom_text:
        bbox_bot = draw.textbbox((0, 0), bottom_text, font=bottom_font)
        bw = bbox_bot[2] - bbox_bot[0]
        bx = (target_width - bw) // 2
        by = target_height - 150

        # Dark gradient under bottom text for punchy contrast
        shadow_rect = Image.new("RGBA", (target_width, 180), (0, 0, 0, 160))
        overlay.paste(shadow_rect, (0, target_height - 180), mask=shadow_rect)

        # Draw red/orange glowing bottom text
        draw_text_with_outline(draw, bottom_text, (bx, by), bottom_font, fill_color=(255, 60, 60), outline_color=(0, 0, 0), outline_width=9)

    # 7. Merge overlay onto base
    result = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path, quality=95)
    print(f"Generated clickbait thumbnail: {output_path} ({target_width}x{target_height})")
    return output_path


if __name__ == "__main__":
    import sys
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("scratch/test_thumbnail.jpg")
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("scratch/clickbait_test.jpg")
    create_clickbait_thumbnail(src, dst)
