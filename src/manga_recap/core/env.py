"""Environment loading, shared by the config layer and the Kaggle transport.

Both need the same view of the environment: real environment variables first,
then `config/.env` and `.env` filling in the gaps. Keeping that in one place
means the API keys and the Kaggle credentials cannot drift apart in how they are
read.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from .paths import REPO_ROOT

# Checked in order. A value already present in the real environment always wins,
# so a shell export overrides the file without anyone editing it.
ENV_FILES = (
    REPO_ROOT / "config" / ".env",
    REPO_ROOT / ".env",
)

CACHE_TTL_SECONDS = 0  # read fresh every call; the file is tiny and this runs rarely


def env_files() -> list[Path]:
    """Env files that exist, in the order they are applied."""
    return [path for path in ENV_FILES if path.exists()]


@lru_cache(maxsize=1)
def _load() -> dict[str, str]:
    values: dict[str, str] = dict(os.environ)
    for path in ENV_FILES:
        if path.exists():
            _parse_env_file(path, values)
    return values


def reload() -> None:
    """Discard the cache, so an edited .env is picked up in a long session."""
    _load.cache_clear()


def get(name: str) -> str | None:
    """Read one variable, or None when it is unset or blank."""
    value = _load().get(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def get_any(*names: str) -> str | None:
    """First non-empty value among several names, for alias support."""
    for name in names:
        value = get(name)
        if value:
            return value
    return None


def set_default(name: str, value: str) -> None:
    """Set a variable only if it is not already present.

    Used to publish .env values into the process environment for the Kaggle CLI,
    which reads the real environment and cannot be handed a Python dict.
    """
    os.environ.setdefault(name, value)


def _parse_env_file(path: Path, into: dict[str, str]) -> None:
    """Merge a .env file into `into`, without overwriting existing values.

    Handles the common .env dialect: comments, blank lines, optional `export`,
    and single or double quoted values.
    """
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip matching quotes only, so a value containing a quote survives.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in into:
            into[key] = value
