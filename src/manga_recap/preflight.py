"""Preflight check: is everything this chapter needs actually configured?

Worth running before a long pipeline. The expensive stages are a paid API call
per panel and a multi-minute Kaggle TTS pass, and finding a missing credential
after those have started is the most annoying way to lose time.
"""

from __future__ import annotations

from dataclasses import dataclass

from .core import env
from .core.config import KNOWN_PROVIDERS, Config
from .core.kaggle_io import KAGGLE_CONFIG_PATH, find_executable
from .core.paths import repo_path

OK = "ok"
WARN = "warn"
FAIL = "fail"


@dataclass
class Check:
    name: str
    status: str
    detail: str


def run_checks(config: Config) -> list[Check]:
    """Every configuration dependency, as a pass, warn or fail."""
    checks: list[Check] = []

    # -- LLM provider and key ---------------------------------------------
    for role in ("vision", "script"):
        provider = config.get(f"llm.{role}.provider")
        model = config.get(f"llm.{role}.model")
        key = config.api_key_for(provider) if provider in KNOWN_PROVIDERS else None
        if not provider:
            checks.append(Check(f"llm.{role}.provider", FAIL, "not set"))
        elif not key:
            checks.append(
                Check(
                    f"llm.{role} key",
                    FAIL,
                    f"no key for '{provider}'. Set it in config/.env",
                )
            )
        else:
            masked = f"{key[:6]}...{key[-4:]}" if len(key) > 12 else "set"
            checks.append(
                Check(f"llm.{role}", OK, f"{provider} / {model} (key {masked})")
            )

    # -- prompts ----------------------------------------------------------
    for relative in ("panel_description.md", "storyboard.md"):
        path = repo_path(f"config/prompts/{relative}")
        size = path.stat().st_size if path.exists() else 0
        checks.append(
            Check(
                f"prompt {relative}",
                OK if size > 0 else FAIL,
                f"{size} bytes" if size else "missing",
            )
        )

    # -- series bible -----------------------------------------------------
    series = str(config.get("project.series_name", "default"))
    bible = repo_path(f"data/series/{series}/series.md")
    if bible.exists():
        checks.append(Check(f"series bible ({series})", OK, "present"))
    else:
        checks.append(
            Check(
                f"series bible ({series})",
                WARN,
                "absent, the narrator will have no character names or running gags",
            )
        )

    # -- panel detector ---------------------------------------------------
    detector = str(config.get("crop.detector", "opencv"))
    if detector == "yolo":
        weights = repo_path(str(config.get("crop.weights_path", "")))
        checks.append(
            Check(
                "panel detector",
                OK if weights.exists() else FAIL,
                f"yolo weights at {weights.name}" if weights.exists()
                else f"missing {weights}, run `manga fetch-models`",
            )
        )
    else:
        checks.append(Check("panel detector", OK, "opencv xy-cut (no weights needed)"))

    # -- Kaggle -----------------------------------------------------------
    if KAGGLE_CONFIG_PATH.exists() or env.get("KAGGLE_USERNAME"):
        checks.append(Check("kaggle credentials", OK, "found"))
    else:
        checks.append(
            Check(
                "kaggle credentials",
                FAIL,
                f"no {KAGGLE_CONFIG_PATH.name} and no KAGGLE_USERNAME in config/.env",
            )
        )

    cli = find_executable("kaggle")
    checks.append(
        Check(
            "kaggle cli",
            OK if cli else FAIL,
            cli or "not found, `pip install kaggle` into this environment",
        )
    )

    # -- model weights for the Kaggle kernels ------------------------------
    kernel_dir = repo_path("kaggle")
    for kernel in ("kernel_tts_align", "kernel_render"):
        path = kernel_dir / kernel / "main.py"
        checks.append(
            Check(
                f"kernel {kernel}",
                OK if path.exists() else FAIL,
                "present" if path.exists() else "missing",
            )
        )

    return checks


def render(checks: list[Check]) -> bool:
    """Print the checks and return True when nothing failed."""
    symbols = {OK: "[green]ok  [/green]", WARN: "[yellow]warn[/yellow]", FAIL: "[red]FAIL[/red]"}
    width = max(len(c.name) for c in checks) if checks else 0

    for check in checks:
        print(f"{symbols[check.status]}  {check.name.ljust(width)}  {check.detail}")

    failed = [c for c in checks if c.status == FAIL]
    warned = [c for c in checks if c.status == WARN]
    print()
    if failed:
        print(f"[red]{len(failed)} check(s) failed. Fix these before running.[/red]")
    elif warned:
        print(f"[yellow]Ready, with {len(warned)} warning(s).[/yellow]")
    else:
        print("[green]Everything is configured.[/green]")
    return not failed
