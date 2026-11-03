"""Tests for panel content classification, description cleaning, and script rebinding."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from manga_recap.core.config import load_config
from manga_recap.core.panelcontent import (
    analyse_panel,
    clean_descriptions,
    rebind_skippable_panels,
)
from manga_recap.core.schema import (
    DescriptionFile,
    PanelDescription,
    ScriptBlock,
    ScriptFile,
)


@pytest.fixture
def tmp_panels_dir(tmp_path):
    panels_dir = tmp_path / "02_panels"
    panels_dir.mkdir(parents=True, exist_ok=True)
    return panels_dir


def _create_test_image(path, kind: str, size=(200, 200)):
    """Generate synthetic panel images for testing."""
    if kind == "white_void":
        arr = np.full((size[1], size[0]), 255, dtype=np.uint8)
    elif kind == "black_void":
        arr = np.zeros((size[1], size[0]), dtype=np.uint8)
    elif kind == "sliver":
        arr = np.full((30, 200), 200, dtype=np.uint8)
    elif kind == "text_card":
        # White background with black text stripes
        arr = np.full((size[1], size[0]), 255, dtype=np.uint8)
        arr[80:90, 20:180] = 0
        arr[110:120, 20:180] = 0
    else:  # kind == "art"
        # Rich mid-tones, line art, gradients
        y, x = np.mgrid[0:size[1], 0:size[0]]
        arr = ((np.sin(x / 10.0) + np.cos(y / 10.0) + 2.0) * 60).astype(np.uint8)
    img = Image.fromarray(arr)
    img.save(path)


def test_analyse_panel_detects_void_and_sliver(tmp_panels_dir):
    white_path = tmp_panels_dir / "white.png"
    black_path = tmp_panels_dir / "black.png"
    sliver_path = tmp_panels_dir / "sliver.png"
    art_path = tmp_panels_dir / "art.png"

    _create_test_image(white_path, "white_void")
    _create_test_image(black_path, "black_void")
    _create_test_image(sliver_path, "sliver", size=(200, 30))
    _create_test_image(art_path, "art")

    res_white = analyse_panel("p_white", white_path)
    assert res_white.is_text_only
    assert "void" in res_white.reason

    res_black = analyse_panel("p_black", black_path)
    assert res_black.is_text_only
    assert "void" in res_black.reason

    res_sliver = analyse_panel("p_sliver", sliver_path)
    assert res_sliver.is_text_only
    assert "sliver" in res_sliver.reason

    res_art = analyse_panel("p_art", art_path)
    assert not res_art.is_text_only


def test_clean_descriptions_migrates_dialogue(tmp_path, tmp_panels_dir):
    p1_img = tmp_panels_dir / "panel_0001.png"
    p2_img = tmp_panels_dir / "panel_0002.png"
    p3_img = tmp_panels_dir / "panel_0003.png"

    _create_test_image(p1_img, "art")
    _create_test_image(p2_img, "white_void")  # text card
    _create_test_image(p3_img, "art")

    desc = DescriptionFile(
        chapter_id="test_ch",
        created_at="now",
        panel_count=3,
        panels=[
            PanelDescription(
                panel_id="panel_0001",
                page_number=1,
                reading_order=1,
                image_path="02_panels/panel_0001.png",
                action="Hero stares ahead",
                characters=["Hero"],
            ),
            PanelDescription(
                panel_id="panel_0002",
                page_number=1,
                reading_order=2,
                image_path="02_panels/panel_0002.png",
                setting="caption_boxes",
                action="A black caption box",
                speech_bubbles=["The end has arrived."],
            ),
            PanelDescription(
                panel_id="panel_0003",
                page_number=1,
                reading_order=3,
                image_path="02_panels/panel_0003.png",
                action="Hero draws sword",
                characters=["Hero"],
                speech_bubbles=["I will fight."],
            ),
        ],
    )

    cleaned_desc, pruned_cnt = clean_descriptions(desc, tmp_path)
    assert pruned_cnt == 1

    p2 = [p for p in cleaned_desc.panels if p.panel_id == "panel_0002"][0]
    p3 = [p for p in cleaned_desc.panels if p.panel_id == "panel_0003"][0]

    assert p2.is_credits_or_ad
    assert p2.is_text_only
    # Dialogue migrated to p3
    assert "The end has arrived." in p3.speech_bubbles
    assert "I will fight." in p3.speech_bubbles


def test_rebind_skippable_panels_updates_script():
    cfg = load_config()
    desc = DescriptionFile(
        chapter_id="test_ch",
        created_at="now",
        panel_count=3,
        panels=[
            PanelDescription(
                panel_id="panel_0001", page_number=1, reading_order=1,
                image_path="p1.png", action="Hero smiles", characters=["Hero"]
            ),
            PanelDescription(
                panel_id="panel_0002", page_number=1, reading_order=2,
                image_path="p2.png", action="Text card", is_credits_or_ad=True, is_text_only=True
            ),
            PanelDescription(
                panel_id="panel_0003", page_number=1, reading_order=3,
                image_path="p3.png", action="Hero jumps", characters=["Hero"]
            ),
        ],
    )

    script = ScriptFile(
        chapter_id="test_ch",
        created_at="now",
        target_words=100,
        blocks=[
            ScriptBlock(
                block_id="b001",
                panel_ids=["panel_0001", "panel_0002"],
                narration="Hero smiles as text appears.",
            ),
            ScriptBlock(
                block_id="b002",
                panel_ids=["panel_0002", "panel_0003"],
                narration="Reading the text, hero jumps.",
            ),
        ],
    )

    rebound_script, cnt = rebind_skippable_panels(script, desc, cfg)
    assert cnt > 0
    # b001 should only reference panel_0001 (panel_0002 rebound and deduped)
    assert rebound_script.blocks[0].panel_ids == ["panel_0001"]
    # b002 should only reference panel_0003
    assert rebound_script.blocks[1].panel_ids == ["panel_0003"]
