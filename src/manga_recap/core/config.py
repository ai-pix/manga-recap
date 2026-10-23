"""Config loading: YAML file plus .env overlay, validated on access.

Deliberately thin. Pydantic models already validate the data contracts, and
over-validating config would just make iteration annoying. What this module
does guarantee is that a missing file or a malformed provider name fails with a
message that tells you what to fix.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from . import env
from .paths import REPO_ROOT

DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"
KNOWN_PROVIDERS = ("anthropic", "gemini", "openrouter")


class ConfigError(RuntimeError):
    """Raised for any configuration problem the user can fix."""


class Config:
    """Dotted-path config access with an .env overlay.

    `cfg.get("render.fps")` returns 30. `cfg.get("llm.vision.api_key")` reads
    from the environment, with a per-provider key name.
    """

    def __init__(self, data: dict[str, Any], config_path: Path | None = None) -> None:
        self._data = data
        self._config_path = config_path
        self._validate()

    # -- access -----------------------------------------------------------

    def get(self, dotted_key: str, default: Any = None) -> Any:
        """Read a value by dotted path. Raises on an unknown provider."""
        parts = dotted_key.split(".")
        node: Any = self._data
        for part in parts[:-1]:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]

        leaf = parts[-1]
        if leaf == "api_key":
            provider = parts[-3] if len(parts) >= 3 else ""
            return self.api_key_for(provider)
        if not isinstance(node, dict) or leaf not in node:
            return default
        return node[leaf]

    def require(self, dotted_key: str) -> Any:
        """Read a value that must exist. Fails loudly when it does not."""
        sentinel = object()
        value = self.get(dotted_key, sentinel)
        if value is sentinel or value is None:
            where = f" in {self._config_path}" if self._config_path else ""
            raise ConfigError(f"Missing required config key: {dotted_key}{where}")
        return value

    def section(self, name: str) -> dict[str, Any]:
        value = self.get(name, {})
        if not isinstance(value, dict):
            raise ConfigError(f"Config section '{name}' is not a mapping")
        return value

    def as_dict(self) -> dict[str, Any]:
        return self._data

    # -- secrets ----------------------------------------------------------

    def api_key_for(self, provider: str) -> str | None:
        """Look up a provider's API key from the environment."""
        if provider not in KNOWN_PROVIDERS:
            raise ConfigError(
                f"Unknown provider '{provider}'. Available: {', '.join(KNOWN_PROVIDERS)}"
            )
        return env.get_any(*self._env_names_for(provider))

    def _env_names_for(self, provider: str) -> tuple[str, ...]:
        if provider == "anthropic":
            return ("ANTHROPIC_API_KEY",)
        if provider == "gemini":
            return ("GEMINI_API_KEY", "GOOGLE_API_KEY")
        return ("OPENROUTER_API_KEY",)

    def require_api_key(self, provider: str) -> str:
        key = self.api_key_for(provider)
        if not key:
            names = " or ".join(self._env_names_for(provider))
            raise ConfigError(
                f"No API key for provider '{provider}'. Set {names} in "
                f"{REPO_ROOT / 'config' / '.env'} (copy config/.env.example to start)."
            )
        return key

    # -- validation -------------------------------------------------------

    def _validate(self) -> None:
        for role in ("vision", "script"):
            provider = self.get(f"llm.{role}.provider")
            if provider is None:
                raise ConfigError(f"Missing config key: llm.{role}.provider")
            if provider not in KNOWN_PROVIDERS:
                raise ConfigError(
                    f"llm.{role}.provider is '{provider}'. "
                    f"Available: {', '.join(KNOWN_PROVIDERS)}"
                )
            if not self.get(f"llm.{role}.model"):
                raise ConfigError(f"Missing config key: llm.{role}.model")

        detector = self.get("crop.detector", "yolo")
        if detector not in ("yolo", "opencv"):
            raise ConfigError(f"crop.detector must be 'yolo' or 'opencv', got '{detector}'")

        if self.get("render.fps", 30) <= 0:
            raise ConfigError("render.fps must be a positive number")


def load_config(path: Path | str | None = None, *, reload: bool = False) -> Config:
    """Load config.yaml. Cached, since it is read on nearly every call.

    `reload` discards the cache first, which is what the tests need when they
    point at temporary config files.
    """
    if reload:
        _load_config.cache_clear()
    return _load_config(str(path) if path else str(DEFAULT_CONFIG_PATH))


@lru_cache(maxsize=8)
def _load_config(config_path: str) -> Config:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(
            f"Config file not found: {path}\n"
            f"Expected the default at {DEFAULT_CONFIG_PATH}"
        )
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Config file {path} is not valid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config file {path} must contain a top-level mapping")
    return Config(data, path)
