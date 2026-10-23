"""Import and wiring checks.

The stages reference each other by relative import, and a single-dot mistake
turns into a runtime failure in a stage that otherwise looks fine. This module
imports everything and asserts the wiring, so that class of bug fails here
instead of mid-pipeline.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

MODULES = [
    "manga_recap",
    "manga_recap.cli",
    "manga_recap.core.config",
    "manga_recap.core.kaggle_io",
    "manga_recap.core.logging",
    "manga_recap.core.paths",
    "manga_recap.core.schema",
    "manga_recap.llm",
    "manga_recap.llm.anthropic",
    "manga_recap.llm.base",
    "manga_recap.llm.gemini",
    "manga_recap.llm.openrouter",
    "manga_recap.llm.registry",
    "manga_recap.render.ffmpeg",
    "manga_recap.render.kenburns",
    "manga_recap.stages.s0_ingest",
    "manga_recap.stages.s1_crop",
    "manga_recap.stages.s1_crop.cropper",
    "manga_recap.stages.s1_crop.detector",
    "manga_recap.stages.s1_crop.ordering",
    "manga_recap.stages.s1_crop.validate",
    "manga_recap.stages.s2_describe",
    "manga_recap.stages.s3_script",
    "manga_recap.stages.s3_script.validate",
    "manga_recap.stages.s4_speech",
    "manga_recap.stages.s5_render",
    "manga_recap.stages.s6_pipeline",
    "manga_recap.stages.s6_pipeline.status",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    assert importlib.import_module(name) is not None


def test_every_stage_exposes_run():
    from manga_recap.stages import (
        s0_ingest,
        s1_crop,
        s2_describe,
        s3_script,
        s4_speech,
        s5_render,
    )

    for stage in (s0_ingest, s1_crop, s2_describe, s3_script, s4_speech, s5_render):
        assert callable(stage.run), f"{stage.__name__} must expose a run()"


def test_stage_dependencies_resolve():
    """s2 must reach s1's panel index, and s3 must reach s2's descriptions.

    Both are cross-stage relative imports, the easiest thing in the layout to
    get wrong by one dot.
    """
    from manga_recap.stages.s1_crop import load_index
    from manga_recap.stages.s2_describe import run as describe_run

    assert callable(load_index)
    assert callable(describe_run)

    from manga_recap.stages.s2_describe import _load_existing
    from manga_recap.stages.s3_script import run as script_run

    assert callable(_load_existing)
    assert callable(script_run)


def test_shipped_prompts_exist_and_are_substantial():
    for relative in ("panel_description.md", "storyboard.md"):
        path = REPO_ROOT / "config" / "prompts" / relative
        assert path.exists(), f"{relative} is missing"
        text = path.read_text(encoding="utf-8")
        assert len(text) > 800, f"{relative} is too short to constrain a model usefully"


def test_prompt_files_parse_as_markdown_headings():
    storyboard = (REPO_ROOT / "config" / "prompts" / "storyboard.md").read_text(encoding="utf-8")
    assert "## Voice" in storyboard
    assert "## References" in storyboard
    assert "## Structure" in storyboard


def test_shipped_config_is_valid_yaml():
    import yaml

    data = yaml.safe_load(
        (REPO_ROOT / "config" / "config.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(data, dict)
    assert data["llm"]["vision"]["provider"] in ("anthropic", "gemini", "openrouter")
    assert data["crop"]["detector"] in ("yolo", "opencv")


def test_env_example_covers_every_provider():
    text = (REPO_ROOT / "config" / ".env.example").read_text(encoding="utf-8")
    for variable in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        assert variable in text


def test_gitignore_protects_secrets_and_artifacts():
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
    assert "data/chapters/" in text


def test_folder_layout_matches_the_documented_structure():
    expected = [
        "config",
        "config/prompts",
        "data/series",
        "kaggle",
        "kaggle/kernel_tts_align",
        "kaggle/kernel_render",
        "models",
        "src/manga_recap",
        "tests",
    ]
    for relative in expected:
        assert (REPO_ROOT / relative).is_dir(), f"{relative}/ is missing"


def test_each_stage_directory_owns_its_artifact():
    """The numbered layout is the resume mechanism, so it must not drift."""
    from manga_recap.core.paths import ChapterPaths

    paths = ChapterPaths.create("ch01", Path("/tmp/data"))
    names = {
        "pages": paths.pages_dir.name,
        "panels": paths.panels_dir.name,
        "descriptions": paths.descriptions_file.name,
        "script": paths.script_file.name,
        "narration": paths.narration_file.name,
        "timeline": paths.timeline_file.name,
        "final": paths.final_file.name,
    }
    assert names == {
        "pages": "01_pages",
        "panels": "02_panels",
        "descriptions": "03_descriptions.json",
        "script": "04_script.json",
        "narration": "05_narration.wav",
        "timeline": "06_timeline.json",
        "final": "07_final.mp4",
    }
