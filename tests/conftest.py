"""Shared fixtures and synthetic-page builders for the test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "kaggle" / "kernel_tts_align"))
sys.path.insert(0, str(REPO_ROOT))

# A conventional 3-row manga page: 3 panels, then 2, then 1 full-width panel.
GUTTER = 30
MARGIN = 24
PAGE_W, PAGE_H = 1000, 800

LAYOUTS = [
    [
        (MARGIN, MARGIN, 316, 244),
        (316 + GUTTER, MARGIN, 632, 244),
        (632 + 2 * GUTTER, MARGIN, PAGE_W - MARGIN, 244),
    ],
    [
        (MARGIN, 274, 482, 532),
        (482 + GUTTER, 274, PAGE_W - MARGIN, 532),
    ],
    [
        (MARGIN, 562, PAGE_W - MARGIN, PAGE_H - MARGIN),
    ],
]


def make_page(layout, seed: int = 11) -> Image.Image:
    """Draw a page with dense line art and screentone, like a real comic page.

    Artwork is clipped to its panel. Letting strokes bleed into the gutters
    would test this generator rather than the detector.
    """
    rng = np.random.default_rng(seed)
    image = Image.new("RGB", (PAGE_W, PAGE_H), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    for x1, y1, x2, y2 in layout:
        draw.rectangle([x1, y1, x2, y2], outline=(0, 0, 0), width=2)
        w, h = x2 - x1, y2 - y1

        for py in range(y1 + 6, y2 - 3, 6):
            for px in range(x1 + 6, x2 - 3, 6):
                if rng.random() < 0.30:
                    draw.point((px, py), fill=(90, 90, 90))

        for _ in range(int(w * h / 900)):
            px = int(rng.integers(x1 + 10, x2 - 10))
            py = int(rng.integers(y1 + 10, y2 - 10))
            ex = int(np.clip(px + int(rng.integers(10, 45)), x1 + 3, x2 - 3))
            ey = int(np.clip(py + int(rng.integers(-30, 30)), y1 + 3, y2 - 3))
            draw.line([px, py, ex, ey], fill=(0, 0, 0), width=2)

    return image


@pytest.fixture
def page_image():
    return make_page(LAYOUTS[0])


@pytest.fixture
def set_env(monkeypatch):
    """Set environment variables for a test, isolated from the real .env file.

    Without this, a test asserting that a key is missing would fail on a
    developer machine that has one configured, and pass on a fresh clone. The
    provider keys are also cleared outright rather than left alone, because a
    real `GEMINI_API_KEY` in the process environment otherwise leaks past a
    test that expected no credentials and the test starts making live API calls.
    """
    from manga_recap.core import env as env_module

    monkeypatch.setattr(env_module, "ENV_FILES", ())
    env_module._load.cache_clear()

    credential_names = (
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "OPENROUTER_API_KEY",
    )
    for name in credential_names:
        monkeypatch.delenv(name, raising=False)

    def setter(values: dict[str, str]) -> None:
        for name, value in values.items():
            monkeypatch.setenv(name, value)
        env_module._load.cache_clear()

    setter({})
    return setter


@pytest.fixture
def full_page_layouts():
    return LAYOUTS


def iou(a, b) -> float:
    inter = max(0, min(a.x2, b.x2) - max(a.x1, b.x1)) * max(
        0, min(a.y2, b.y2) - max(a.y1, b.y1)
    )
    if inter == 0:
        return 0.0
    return inter / (a.area + b.area - inter)
