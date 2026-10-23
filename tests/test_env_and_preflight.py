"""Environment loading, credential checks, and the preflight report."""

from __future__ import annotations

import json

import pytest

from manga_recap.core import env
from manga_recap.core.config import load_config
from manga_recap.preflight import FAIL, OK, run_checks

# -- env file parsing -------------------------------------------------------


def write_env(tmp_path, body: str):
    path = tmp_path / ".env"
    path.write_text(body, encoding="utf-8")
    return path


def parse(monkeypatch, path):
    monkeypatch.setattr(env, "ENV_FILES", (path,))
    env._load.cache_clear()
    return env._load()


def test_simple_assignment(monkeypatch, tmp_path):
    parsed = parse(monkeypatch, write_env(tmp_path, "FOO=bar\n"))
    assert parsed["FOO"] == "bar"


def test_comments_and_blank_lines_are_ignored(monkeypatch, tmp_path):
    body = "# a comment\n\n   \nFOO=bar\n# trailing\n"
    parsed = parse(monkeypatch, write_env(tmp_path, body))
    assert parsed["FOO"] == "bar"
    assert "a comment" not in parsed


def test_export_prefix_is_accepted(monkeypatch, tmp_path):
    parsed = parse(monkeypatch, write_env(tmp_path, "export FOO=bar\n"))
    assert parsed["FOO"] == "bar"


def test_double_quotes_are_stripped(monkeypatch, tmp_path):
    parsed = parse(monkeypatch, write_env(tmp_path, 'FOO="bar baz"\n'))
    assert parsed["FOO"] == "bar baz"


def test_single_quotes_are_stripped(monkeypatch, tmp_path):
    parsed = parse(monkeypatch, write_env(tmp_path, "FOO='bar baz'\n"))
    assert parsed["FOO"] == "bar baz"


def test_value_containing_a_hash_is_kept(monkeypatch, tmp_path):
    parsed = parse(monkeypatch, write_env(tmp_path, "FOO=abc#def\n"))
    assert parsed["FOO"] == "abc#def"


def test_value_containing_an_equals_sign_is_kept(monkeypatch, tmp_path):
    parsed = parse(monkeypatch, write_env(tmp_path, "FOO=a=b=c\n"))
    assert parsed["FOO"] == "a=b=c"


def test_empty_value_reads_as_unset(monkeypatch, tmp_path):
    parse(monkeypatch, write_env(tmp_path, "FOO=\n"))
    env._load.cache_clear()
    assert env.get("FOO") is None


def test_line_without_equals_is_skipped(monkeypatch, tmp_path):
    parsed = parse(monkeypatch, write_env(tmp_path, "JUST_A_WORD\nFOO=bar\n"))
    assert parsed["FOO"] == "bar"
    assert "JUST_A_WORD" not in parsed


def test_later_files_do_not_override_earlier_ones(monkeypatch, tmp_path):
    first = write_env(tmp_path, "FOO=first\n")
    second = tmp_path / "b.env"
    second.write_text("FOO=second\n", encoding="utf-8")

    monkeypatch.setattr(env, "ENV_FILES", (first, second))
    env._load.cache_clear()
    assert env._load()["FOO"] == "first"


def test_real_environment_wins_over_the_file(monkeypatch, tmp_path):
    monkeypatch.setenv("FOO", "from_shell")
    parsed = parse(monkeypatch, write_env(tmp_path, "FOO=from_file\n"))
    assert parsed["FOO"] == "from_shell"


def test_get_any_takes_the_first_present(monkeypatch, tmp_path):
    parse(monkeypatch, write_env(tmp_path, "SECOND=two\nTHIRD=three\n"))
    assert env.get_any("FIRST", "SECOND", "THIRD") == "two"
    assert env.get_any("FIRST", "MISSING") is None


# -- shipped .env -----------------------------------------------------------


def test_shipped_env_file_is_gitignored():
    from manga_recap.core.paths import REPO_ROOT

    ignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "config/.env" in ignore


def test_shipped_env_file_exists_and_is_readable():
    from manga_recap.core.paths import REPO_ROOT

    path = REPO_ROOT / "config" / ".env"
    assert path.exists(), "config/.env should exist for pasting keys into"
    text = path.read_text(encoding="utf-8")
    for name in ("GEMINI_API_KEY", "KAGGLE_USERNAME", "KAGGLE_KEY"):
        assert name in text, f"{name} missing from config/.env"


def test_shipped_env_example_matches_the_real_one():
    from manga_recap.core.paths import REPO_ROOT

    root = REPO_ROOT / "config"
    real = set()
    for line in (root / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            real.add(line.split("=")[0].strip())
    example = set()
    for line in (root / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            example.add(line.split("=")[0].strip())
    assert real <= example, f"variables not documented: {real - example}"


# -- kaggle credentials -----------------------------------------------------


def test_kaggle_username_falls_back_to_the_environment(monkeypatch, set_env):
    from manga_recap.core import kaggle_io

    monkeypatch.setattr(kaggle_io, "_read_credentials_file", lambda: None)
    set_env({"KAGGLE_USERNAME": "someone"})
    assert kaggle_io.kaggle_username() == "someone"


def test_kaggle_credentials_file_is_preferred(monkeypatch, set_env):
    from manga_recap.core import kaggle_io

    monkeypatch.setattr(
        kaggle_io, "_read_credentials_file", lambda: {"username": "from_file", "key": "k"}
    )
    set_env({"KAGGLE_USERNAME": "from_env"})
    assert kaggle_io.kaggle_username() == "from_file"


def test_kaggle_writes_credentials_file_from_env(monkeypatch, set_env, tmp_path):
    from manga_recap.core import kaggle_io

    target = tmp_path / "kaggle.json"
    monkeypatch.setattr(kaggle_io, "KAGGLE_CONFIG_PATH", target)
    monkeypatch.setattr(kaggle_io, "_read_credentials_file", lambda: None)
    set_env({"KAGGLE_USERNAME": "someone", "KAGGLE_KEY": "secret"})

    assert kaggle_io.ensure_kaggle_credentials() == "someone"
    assert json.loads(target.read_text(encoding="utf-8")) == {
        "username": "someone",
        "key": "secret",
    }


def test_kaggle_never_overwrites_an_existing_file(monkeypatch, set_env, tmp_path):
    from manga_recap.core import kaggle_io

    target = tmp_path / "kaggle.json"
    target.write_text(json.dumps({"username": "original", "key": "old"}), encoding="utf-8")
    monkeypatch.setattr(kaggle_io, "KAGGLE_CONFIG_PATH", target)
    set_env({"KAGGLE_USERNAME": "someone", "KAGGLE_KEY": "new"})

    assert kaggle_io.ensure_kaggle_credentials() == "original"
    assert json.loads(target.read_text(encoding="utf-8"))["username"] == "original"


def test_kaggle_error_names_both_options(monkeypatch, set_env, tmp_path):
    from manga_recap.core import kaggle_io

    monkeypatch.setattr(kaggle_io, "KAGGLE_CONFIG_PATH", tmp_path / "absent.json")
    monkeypatch.setattr(kaggle_io, "_read_credentials_file", lambda: None)
    set_env({})

    with pytest.raises(kaggle_io.KaggleError) as exc:
        kaggle_io.ensure_kaggle_credentials()
    message = str(exc.value)
    assert "KAGGLE_USERNAME" in message
    assert "KAGGLE_KEY" in message
    # It must point at the file it checked, by full path.
    assert str(tmp_path / "absent.json") in message


# -- preflight --------------------------------------------------------------


def test_preflight_flags_missing_keys(monkeypatch, set_env):
    from manga_recap.core import kaggle_io

    set_env({})
    monkeypatch.setattr(kaggle_io, "_read_credentials_file", lambda: None)
    config = load_config()

    checks = {c.name: c for c in run_checks(config)}
    assert checks["llm.vision key"].status == FAIL
    assert checks["llm.script key"].status == FAIL


def test_preflight_passes_with_credentials(set_env):
    config = load_config()
    set_env({"GEMINI_API_KEY": "test-key-value"})

    checks = {c.name: c for c in run_checks(config)}
    assert checks["llm.vision"].status == OK
    assert checks["llm.script"].status == OK
    # The key must not be printed in full.
    assert "test-key-value" not in checks["llm.vision"].detail


def test_preflight_masks_the_key(set_env):
    set_env({"GEMINI_API_KEY": "AIzaSyABCDEFGHIJKLMNOP"})
    checks = {c.name: c for c in run_checks(load_config())}
    detail = checks["llm.vision"].detail
    assert "AIzaSyABCDEFGHIJKLMNOP" not in detail
    assert "AIzaSy" in detail and "MNOP" in detail
