"""Config loading, dotted access, provider resolution, and API key handling."""

from __future__ import annotations

import pytest

from manga_recap.core.config import KNOWN_PROVIDERS, Config, ConfigError, load_config


@pytest.fixture
def config():
    return load_config()


def test_default_config_loads(config):
    assert config.get("render.fps") == 30
    assert config.get("crop.detector") in ("yolo", "opencv")


def test_dotted_access_returns_nested_values(config):
    assert config.get("render.kenburns.zoom_end") == pytest.approx(1.06)
    assert config.get("render.background_mode") == "blurred"


def test_the_blur_is_configured_to_run_on_a_small_copy(config):
    """The downscale is what makes a blurred backdrop affordable.

    A `boxblur` at full output resolution is the most expensive thing this
    renderer can be asked to do, so the width it actually blurs is a setting
    worth asserting on rather than a detail buried in a filter string.
    """
    assert config.get("render.blur_width") == 512
    assert config.get("render.blur_radius") > 0
    assert config.get("render.blur_darken") > 0


def test_the_beat_length_that_controls_cut_frequency_is_configurable(config):
    """`max_words_per_beat` is the dial behind visual tracking of the script.

    Lower it and the renderer cuts more often, so the picture changes more
    often within a sentence. It has to be a config value rather than a constant
    because the right density is a taste call, not a technical one.
    """
    assert config.get("render.max_words_per_beat") > 0
    assert config.get("render.min_shot_seconds") > 0


def test_missing_key_returns_default(config):
    assert config.get("does.not.exist", "fallback") == "fallback"
    assert config.get("render.nonexistent") is None


def test_require_raises_for_a_missing_key(config):
    with pytest.raises(ConfigError, match="Missing required config key"):
        config.require("definitely.not.here")


def test_require_returns_an_existing_value(config):
    assert config.require("render.width") == 1920


def test_section_returns_a_mapping(config):
    section = config.section("render")
    assert isinstance(section, dict)
    assert "width" in section


def test_unknown_provider_names_the_alternatives():
    data = {
        "llm": {
            "vision": {"provider": "notarealprovider", "model": "x"},
            "script": {"provider": "anthropic", "model": "y"},
        },
        "crop": {"detector": "opencv"},
    }
    with pytest.raises(ConfigError) as exc:
        Config(data)
    message = str(exc.value)
    for name in KNOWN_PROVIDERS:
        assert name in message


def test_missing_provider_is_reported():
    data = {
        "llm": {"vision": {"model": "x"}, "script": {"provider": "anthropic", "model": "y"}},
        "crop": {"detector": "opencv"},
    }
    with pytest.raises(ConfigError, match="llm.vision.provider"):
        Config(data)


def test_missing_model_is_reported():
    data = {
        "llm": {
            "vision": {"provider": "anthropic"},
            "script": {"provider": "anthropic", "model": "y"},
        },
        "crop": {"detector": "opencv"},
    }
    with pytest.raises(ConfigError, match="llm.vision.model"):
        Config(data)


def test_invalid_detector_is_rejected():
    data = {
        "llm": {
            "vision": {"provider": "anthropic", "model": "x"},
            "script": {"provider": "anthropic", "model": "y"},
        },
        "crop": {"detector": "magic"},
    }
    with pytest.raises(ConfigError, match="crop.detector"):
        Config(data)


def test_non_positive_fps_is_rejected():
    data = {
        "llm": {
            "vision": {"provider": "anthropic", "model": "x"},
            "script": {"provider": "anthropic", "model": "y"},
        },
        "crop": {"detector": "opencv"},
        "render": {"fps": 0},
    }
    with pytest.raises(ConfigError, match="fps"):
        Config(data)


def test_missing_api_key_explains_where_to_put_it(set_env):
    data = {
        "llm": {
            "vision": {"provider": "anthropic", "model": "x"},
            "script": {"provider": "anthropic", "model": "y"},
        },
        "crop": {"detector": "opencv"},
    }
    set_env({})
    cfg = Config(data)

    assert cfg.api_key_for("anthropic") is None
    with pytest.raises(ConfigError) as exc:
        cfg.require_api_key("anthropic")
    assert "ANTHROPIC_API_KEY" in str(exc.value)
    assert ".env" in str(exc.value)


def test_api_key_is_read_from_the_environment(set_env):
    set_env({"ANTHROPIC_API_KEY": "sk-test"})
    data = {
        "llm": {
            "vision": {"provider": "anthropic", "model": "x"},
            "script": {"provider": "anthropic", "model": "y"},
        },
        "crop": {"detector": "opencv"},
    }
    assert Config(data).require_api_key("anthropic") == "sk-test"


def test_gemini_accepts_google_api_key_alias(set_env):
    set_env({"GOOGLE_API_KEY": "g-test"})
    data = {
        "llm": {
            "vision": {"provider": "gemini", "model": "x"},
            "script": {"provider": "gemini", "model": "y"},
        },
        "crop": {"detector": "opencv"},
    }
    assert Config(data).api_key_for("gemini") == "g-test"


def test_api_key_for_unknown_provider_raises(config):
    with pytest.raises(ConfigError, match="Unknown provider"):
        config.api_key_for("nope")


def test_malformed_yaml_is_reported(tmp_path):
    bad = tmp_path / "config.yaml"
    bad.write_text("llm: [unclosed\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_config(bad, reload=True)


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "absent.yaml", reload=True)


def test_top_level_must_be_a_mapping(tmp_path):
    bad = tmp_path / "config.yaml"
    bad.write_text("- just\n- a\n- list\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="top-level mapping"):
        load_config(bad, reload=True)


def test_shipped_config_is_valid_and_complete():
    """The checked-in config must load, or nothing else works."""
    cfg = load_config()
    for key in (
        "llm.vision.provider",
        "llm.vision.model",
        "llm.script.provider",
        "llm.script.model",
        "script.target_words",
        "tts.kernel_slug",
        "align.whisper_model",
        "render.kernel_slug",
        "render.width",
        "render.height",
    ):
        assert cfg.get(key) is not None, f"{key} missing from config.yaml"
