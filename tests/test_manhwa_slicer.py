"""Test suite for the next-generation Smart Manhwa Panel Slicer."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from manga_recap.core.schema import PanelIndexFile, load_model
from manga_recap.stages.s1_crop.manhwa_slicer import (
    ContinuousCanvas,
    ManhwaSliceConfig,
    PanelSegment,
    classify_segment,
    detect_gutters,
    find_tight_horizontal_bounds,
    merge_floating_bubbles,
    prune_segments,
    slice_manhwa,
)


def make_gutter(width: int, height: int, color: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    """Create a uniform gutter image with zero edges."""
    return Image.new("RGB", (width, height), color)


def make_story_panel(
    width: int,
    height: int,
    art_color: tuple[int, int, int] = (220, 60, 60),
    margin_x: int = 0,
) -> Image.Image:
    """Create a story panel with rich color artwork and distinct edges spanning 0 to height."""
    im = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    x1 = margin_x
    x2 = width - margin_x
    # Draw outline to boundaries so edge/art detection marks 0 to height as panel
    draw.rectangle([x1, 0, x2 - 1, height - 1], fill=art_color, outline=(0, 0, 0), width=2)
    # Add contrasting interior elements to guarantee edges and saturation
    draw.ellipse([x1 + 40, 10, x2 - 40, height - 10], fill=(60, 180, 240), outline=(0, 0, 0), width=2)
    draw.line([x1 + 20, 5, x2 - 20, height - 5], fill=(255, 255, 0), width=3)
    return im


def make_dark_scene_panel(width: int, height: int) -> Image.Image:
    """Create a dark night scene with low average luminance (<25) but containing art edges."""
    im = Image.new("RGB", (width, height), (12, 12, 16))
    draw = ImageDraw.Draw(im)
    # Outline & contrast strokes: stars, weapon edge, character silhouette lines
    draw.rectangle([0, 0, width - 1, height - 1], outline=(150, 150, 180), width=2)
    draw.line([0, 0, width - 1, height - 1], fill=(240, 240, 255), width=2)
    draw.line([width - 1, 0, 0, height - 1], fill=(200, 200, 220), width=2)
    draw.rectangle([width // 4, height // 4, width * 3 // 4, height * 3 // 4], outline=(220, 220, 240), width=2)
    return im


def make_bright_sky_panel(width: int, height: int) -> Image.Image:
    """Create a bright sky scene with high luminance (>235) but containing cloud/art edges."""
    im = Image.new("RGB", (width, height), (242, 242, 245))
    draw = ImageDraw.Draw(im)
    # Outline & cloud outlines, bird silhouettes
    draw.rectangle([0, 0, width - 1, height - 1], outline=(20, 20, 20), width=2)
    draw.line([0, height // 2, width - 1, height // 2], fill=(20, 20, 20), width=3)
    draw.ellipse([width // 3, 0, width * 2 // 3, height - 1], outline=(15, 15, 15), width=2)
    return im


def make_floating_bubble_panel(width: int, height: int) -> Image.Image:
    """Create an isolated speech bubble in the middle of a plain white background."""
    im = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    # Compact oval speech bubble in center with black text glyph lines
    bx1 = width // 3
    by1 = height // 4
    bx2 = width * 2 // 3
    by2 = height * 3 // 4
    draw.ellipse([bx1, by1, bx2, by2], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
    draw.line([bx1 + 15, (by1 + by2) // 2 - 5, bx2 - 15, (by1 + by2) // 2 - 5], fill=(0, 0, 0), width=2)
    draw.line([bx1 + 25, (by1 + by2) // 2 + 8, bx2 - 25, (by1 + by2) // 2 + 8], fill=(0, 0, 0), width=2)
    return im


def make_credit_banner(width: int, height: int = 100) -> Image.Image:
    """Create a scanlation credit banner with high white uniform area and monochrome credit text."""
    im = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(im)
    # A small black icon / discord logo / credit text box in center
    cx, cy = width // 2, height // 2
    draw.rectangle([cx - 100, cy - 20, cx + 100, cy + 20], outline=(0, 0, 0), width=2)
    draw.line([cx - 80, cy, cx + 80, cy], fill=(0, 0, 0), width=2)
    return im


def test_continuous_canvas_split_image_stitching(tmp_path: Path):
    """Test Requirement 1: Canvas stitches panels crossing split image boundaries with zero decapitation."""
    w = 600
    # Split 1:
    # - Top Gutter: 40px
    # - Story Panel 1: 200px
    # - Mid Gutter: 50px
    # - Story Panel 2 (Top Half): 250px (Total height 540)
    split1_parts = [
        make_gutter(w, 40),
        make_story_panel(w, 200, art_color=(200, 50, 50)),
        make_gutter(w, 50),
        make_story_panel(w, 250, art_color=(50, 180, 50)),
    ]
    im1 = Image.new("RGB", (w, sum(p.height for p in split1_parts)))
    cy = 0
    for p in split1_parts:
        im1.paste(p, (0, cy))
        cy += p.height

    # Split 2:
    # - Story Panel 2 (Bottom Half): 150px (Continues directly with no gutter!)
    # - Mid Gutter: 40px
    # - Story Panel 3: 220px
    # - Bottom Gutter: 40px (Total height 450)
    split2_parts = [
        make_story_panel(w, 150, art_color=(50, 180, 50)),
        make_gutter(w, 40),
        make_story_panel(w, 220, art_color=(50, 50, 200)),
        make_gutter(w, 40),
    ]
    im2 = Image.new("RGB", (w, sum(p.height for p in split2_parts)))
    cy = 0
    for p in split2_parts:
        im2.paste(p, (0, cy))
        cy += p.height

    p1 = tmp_path / "001.jpg"
    p2 = tmp_path / "002.jpg"
    im1.save(p1)
    im2.save(p2)

    out_dir = tmp_path / "output"
    index = slice_manhwa([p1, p2], out_dir, chapter_id="test_split")

    # Panel 2 spans across the split boundary between file 1 and file 2.
    # Total expected panels: 3 (Panel 1, Panel 2 intact, Panel 3).
    assert index.panel_count == 3
    assert len(index.panels) == 3

    panel2 = index.panels[1]
    # Panel 2 height should be approximately 250 + 150 = 400px (within JPEG compression edge tolerance)
    assert abs(panel2.bbox.height - 400) <= 5
    # Crucially, panel2 starts well inside file 1 (y < 540) and ends well inside file 2 (y > 540)
    assert panel2.bbox.y1 < 540
    assert panel2.bbox.y2 > 540

    # Verify the stitched file exists as .webp and matches dimensions
    p2_path = out_dir / panel2.image_path
    assert p2_path.exists()
    assert p2_path.suffix == ".webp"
    with Image.open(p2_path) as p2_im:
        assert abs(p2_im.height - 400) <= 5


def test_semantic_gutter_detection_white_and_black():
    """Test Requirement 2: Detects white gutters, black gutters, grey gutters, and protects dark/bright scenes."""
    w = 500
    parts = [
        # 1. White gutter (lum > 235, zero edges)
        make_gutter(w, 40, (255, 255, 255)),
        # 2. Dark scene panel (lum < 25, but art edges -> NOT a gutter)
        make_dark_scene_panel(w, 180),
        # 3. Black gutter (lum < 25, zero edges -> TRUE gutter)
        make_gutter(w, 35, (0, 0, 0)),
        # 4. Bright sky panel (lum > 235, but art edges -> NOT a gutter)
        make_bright_sky_panel(w, 160),
        # 5. Grey gutter (flat neutral grey, zero edges -> TRUE gutter)
        make_gutter(w, 30, (128, 128, 128)),
        # 6. Standard story panel
        make_story_panel(w, 150),
        # 7. Ending white gutter
        make_gutter(w, 30, (255, 255, 255)),
    ]

    canvas_im = Image.new("RGB", (w, sum(p.height for p in parts)))
    cy = 0
    for p in parts:
        canvas_im.paste(p, (0, cy))
        cy += p.height

    canvas = ContinuousCanvas([canvas_im])
    config = ManhwaSliceConfig(min_gutter_height=25)
    metrics = canvas.compute_row_metrics()
    _, blocks = detect_gutters(metrics, config)

    # We expect 3 distinct story blocks:
    # Block 1: Dark scene panel (180px)
    # Block 2: Bright sky panel (160px)
    # Block 3: Standard story panel (150px)
    assert len(blocks) == 3

    # Check that dark scene was recognized as story content
    dark_y1, dark_y2 = blocks[0]
    assert abs((dark_y2 - dark_y1) - 180) <= 3

    # Check that bright sky was recognized as story content
    sky_y1, sky_y2 = blocks[1]
    assert abs((sky_y2 - sky_y1) - 160) <= 3

    # Check standard story panel
    story_y1, story_y2 = blocks[2]
    assert abs((story_y2 - story_y1) - 150) <= 5


def test_minimum_gutter_height_enforcement():
    """Test Requirement 2: Gutter segments smaller than 25px are rejected."""
    w = 500
    # Two story sections separated by only a 12px white line
    parts = [
        make_story_panel(w, 100),
        make_gutter(w, 12, (255, 255, 255)),  # Sub-threshold gap (< 25px)
        make_story_panel(w, 100),
    ]
    canvas_im = Image.new("RGB", (w, sum(p.height for p in parts)))
    cy = 0
    for p in parts:
        canvas_im.paste(p, (0, cy))
        cy += p.height

    canvas = ContinuousCanvas([canvas_im])
    config = ManhwaSliceConfig(min_gutter_height=25)
    metrics = canvas.compute_row_metrics()
    _, blocks = detect_gutters(metrics, config)

    # Because 12px < 25px, it is not split; both parts remain unified as one 212px panel
    assert len(blocks) == 1
    assert (blocks[0][1] - blocks[0][0]) == 212


def test_floating_speech_bubble_elimination_and_merge():
    """Test Requirement 3: Floating speech bubbles on plain backgrounds are merged into closest story panel."""
    w = 500
    # Layout:
    # 0..150: Story Panel 1
    # 150..230: Gutter (80px)
    # 230..350: Floating Speech Bubble (120px)
    # 350..550: Gutter (200px)
    # 550..750: Story Panel 2
    # 750..790: Gutter (40px)
    # The bubble is closer to Panel 1 (gap 80px) than Panel 2 (gap 200px).
    parts = [
        make_story_panel(w, 150, art_color=(200, 40, 40)),
        make_gutter(w, 80),
        make_floating_bubble_panel(w, 120),
        make_gutter(w, 200),
        make_story_panel(w, 200, art_color=(40, 40, 200)),
        make_gutter(w, 40),
    ]

    canvas_im = Image.new("RGB", (w, sum(p.height for p in parts)))
    cy = 0
    for p in parts:
        canvas_im.paste(p, (0, cy))
        cy += p.height

    canvas = ContinuousCanvas([canvas_im])
    config = ManhwaSliceConfig()

    metrics = canvas.compute_row_metrics()
    _, blocks = detect_gutters(metrics, config)

    # Blocks find: Story 1, Bubble, Story 2
    assert len(blocks) == 3

    classified = []
    for sy, ey in blocks:
        stype, _ = classify_segment(canvas, sy, ey, config)
        classified.append(PanelSegment(y_start=sy, y_end=ey, segment_type=stype))

    assert classified[0].segment_type == "STORY"
    assert classified[1].segment_type == "FLOATING_BUBBLE"
    assert classified[2].segment_type == "STORY"

    merged = merge_floating_bubbles(classified)
    # Floating bubble was absorbed; only 2 story panels remain
    assert len(merged) == 2
    # Panel 1 absorbed the bubble: starts at 0, extends to cover the bubble
    assert merged[0].y_start == 0
    assert merged[0].y_end == classified[1].y_end
    assert len(merged[0].merged_bubbles) == 1
    assert merged[1].y_start == classified[2].y_start


def test_floating_bubble_merge_following():
    """Test Requirement 3: Floating bubble merges into following story panel when closer to it."""
    w = 500
    # Layout:
    # 0..150: Story Panel 1
    # 150..350: Gutter (200px)
    # 350..470: Floating Speech Bubble (120px)
    # 470..550: Gutter (80px)
    # 550..750: Story Panel 2
    # 750..790: Gutter (40px)
    # The bubble is closer to Panel 2 (gap 80px vs 200px).
    parts = [
        make_story_panel(w, 150),
        make_gutter(w, 200),
        make_floating_bubble_panel(w, 120),
        make_gutter(w, 80),
        make_story_panel(w, 200),
        make_gutter(w, 40),
    ]
    canvas_im = Image.new("RGB", (w, sum(p.height for p in parts)))
    cy = 0
    for p in parts:
        canvas_im.paste(p, (0, cy))
        cy += p.height

    canvas = ContinuousCanvas([canvas_im])
    config = ManhwaSliceConfig()

    _, blocks = detect_gutters(canvas.compute_row_metrics(), config)
    classified = [
        PanelSegment(y_start=sy, y_end=ey, segment_type=classify_segment(canvas, sy, ey, config)[0])
        for sy, ey in blocks
    ]

    merged = merge_floating_bubbles(classified)
    assert len(merged) == 2
    # Panel 1 remains at [0, ~150]
    assert merged[0].y_start == 0
    assert abs(merged[0].y_end - 150) <= 4
    # Panel 2 absorbed the preceding bubble: starts at the bubble's y_start
    assert merged[1].y_start == classified[1].y_start
    assert merged[1].y_end == classified[2].y_end
    assert len(merged[1].merged_bubbles) == 1


def test_clean_pruning_slivers_and_aspect_ratios():
    """Test Requirement 4: Slivers (< 70px) and extreme aspect ratios (>15:1) are pruned."""
    config = ManhwaSliceConfig(min_panel_height=70, max_aspect_ratio=15.0)

    segments = [
        # Valid story panel
        PanelSegment(y_start=0, y_end=200, segment_type="STORY", x1=0, x2=600),
        # Tiny sliver (height 40px < 70px)
        PanelSegment(y_start=250, y_end=290, segment_type="STORY", x1=0, x2=600),
        # Extreme aspect ratio (width 600, height 30 -> 20:1)
        PanelSegment(y_start=330, y_end=360, segment_type="STORY", x1=0, x2=600),
        # Valid second panel
        PanelSegment(y_start=400, y_end=600, segment_type="STORY", x1=0, x2=600),
    ]

    kept = prune_segments(segments, canvas_width=600, config=config)
    assert len(kept) == 2
    assert kept[0].y_end == 200
    assert kept[1].y_start == 400


def test_isolated_scanlation_credit_filter():
    """Test Requirement 4: Obvious scanlation credit banner at boundary is filtered out."""
    w = 600
    parts = [
        make_story_panel(w, 200),
        make_gutter(w, 40),
        make_story_panel(w, 200),
        make_gutter(w, 40),
        # Credit banner at chapter end
        make_credit_banner(w, 90),
    ]
    canvas_im = Image.new("RGB", (w, sum(p.height for p in parts)))
    cy = 0
    for p in parts:
        canvas_im.paste(p, (0, cy))
        cy += p.height

    canvas = ContinuousCanvas([canvas_im])
    config = ManhwaSliceConfig(filter_credits=True)

    _, blocks = detect_gutters(canvas.compute_row_metrics(), config)
    total_cand = len(blocks)

    classified = []
    for i, (sy, ey) in enumerate(blocks):
        is_bound = (i == 0 or i == total_cand - 1)
        stype, _ = classify_segment(canvas, sy, ey, config, is_boundary=is_bound)
        classified.append(PanelSegment(y_start=sy, y_end=ey, segment_type=stype))

    # The end banner is classified as CREDIT
    assert classified[-1].segment_type == "CREDIT"

    pruned = prune_segments(classified, canvas_width=w, config=config)
    # The credit banner was pruned, only 2 story panels remain
    assert len(pruned) == 2


def test_tight_content_bounding_box_side_margins():
    """Test Requirement 5: Empty side margins are trimmed to ink content with 10px safe margin."""
    w = 800
    h = 300
    # Artwork drawn between x=200 and x=600
    panel = make_story_panel(w, h, margin_x=200)

    config = ManhwaSliceConfig(side_margin_px=10, snap_edge_tolerance=20)
    x1, x2 = find_tight_horizontal_bounds(panel, config)

    # Ink extends from ~200 to ~600.
    # With 10px safe margin: x1 should be approx 190, x2 should be approx 610.
    assert 185 <= x1 <= 205
    assert 595 <= x2 <= 615
    assert (x2 - x1) < w  # Confirms excessive side margins were trimmed


def test_full_bleed_snaps_to_canvas_edges():
    """Test Requirement 5: Artwork extending near edges snaps to full canvas width."""
    w = 800
    h = 300
    # Artwork goes to within 5px of canvas edges
    panel = make_story_panel(w, h, margin_x=5)

    config = ManhwaSliceConfig(side_margin_px=10, snap_edge_tolerance=20)
    x1, x2 = find_tight_horizontal_bounds(panel, config)

    assert x1 == 0
    assert x2 == w


def test_100_percent_webp_and_schema_compliance(tmp_path: Path):
    """Test Requirement 6: Panels saved strictly as .webp (quality 90) and panel_index.json is schema compliant."""
    w = 600
    parts = [
        make_gutter(w, 30),
        make_story_panel(w, 200, art_color=(200, 50, 50)),
        make_gutter(w, 40),
        make_story_panel(w, 250, art_color=(50, 150, 200)),
        make_gutter(w, 30),
    ]
    canvas_im = Image.new("RGB", (w, sum(p.height for p in parts)))
    cy = 0
    for p in parts:
        canvas_im.paste(p, (0, cy))
        cy += p.height

    src_img = tmp_path / "chapter.jpg"
    canvas_im.save(src_img)

    out_dir = tmp_path / "chapter_out"
    index = slice_manhwa(src_img, out_dir, chapter_id="ch01_test")

    # Verify panel count
    assert index.panel_count == 2
    assert index.chapter_id == "ch01_test"
    assert index.page_count == 1

    # Verify panel files on disk
    panels_dir = out_dir / "02_panels"
    index_json_path = panels_dir / "panel_index.json"
    assert index_json_path.exists()

    # Load and validate with Pydantic schema
    loaded_index = load_model(index_json_path, PanelIndexFile)
    assert loaded_index.panel_count == 2
    assert len(loaded_index.panels) == 2

    for panel in loaded_index.panels:
        # Check source is manhwa
        assert panel.source == "manhwa"

        # Check image file format is strictly WEBP
        p_file = out_dir / panel.image_path
        assert p_file.exists()
        assert p_file.suffix == ".webp"
        with Image.open(p_file) as im:
            assert im.format == "WEBP"
