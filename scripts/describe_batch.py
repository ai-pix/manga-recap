"""Describe many chapters under a hard daily request budget.

Why this exists rather than a shell loop: the Gemini free tier allows 20
`generateContent` requests per day per model
(`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, which the 429 body spells
out along with a `retryDelay` measured in hours). A chapter needs one describe
call plus one transcription call, so a plain `for` loop over eight chapters
looks fine and then dies on the ninth request of the day with a ten-hour wait
attached.

Four things keep it inside the allowance:

* Every request is counted at the single point where one is issued, so the
  budget covers retries and failed batches and not just chapters.
* A chapter that fails for a recoverable reason is retried with a halved batch
  size rather than abandoned, because a whole-chapter request that trips
  MAX_TOKENS or loses one panel is a size problem, not a model problem. The
  stage already caches after every batch, so the successful part of a halved
  retry is kept.
* When the day's allowance runs out, the run sleeps for exactly as long as
  Google's `retryDelay` says and then carries on from the same chapter, because
  the alternative is a human having to come back in ten hours and reissue the
  command. The budget is re-based after each wait, since a new day is a new
  allowance.
* Per-minute pacing is left to the provider's `RatePacer`, so two calls never
  land inside the same short window even after a reset.

Usage:

    python scripts/describe_batch.py --chapters ch008 ch009 ch016
    python scripts/describe_batch.py --chapters ch016 --budget 4 --dry-run
    python scripts/describe_batch.py --chapters ch016 --no-wait   # stop instead
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from manga_recap.core.config import load_config  # noqa: E402
from manga_recap.core.logging import setup_logging  # noqa: E402
from manga_recap.core.paths import ChapterPaths  # noqa: E402
from manga_recap.core.schema import PanelIndexFile, load_model  # noqa: E402
from manga_recap.llm.base import LLMError, LLMQuotaError  # noqa: E402
from manga_recap.stages import s2_describe  # noqa: E402

# The free tier allows 20/day. Two are held back so the run cannot consume the
# last of the day and leave a chapter that was one call from finished.
DEFAULT_BUDGET = 18

# How many times a chapter may be retried with a smaller batch before it is
# left for the next day. Each retry costs a request out of the same budget.
MAX_ATTEMPTS = 3

# How long to sleep when the provider names no retry delay of its own. A daily
# free-tier window is measured in hours, so this is deliberately blunt.
FALLBACK_QUOTA_WAIT = 3600.0


def stamp() -> str:
    return time.strftime("%H:%M:%S")


def wait_out_quota(exc: LLMQuotaError, *, max_waits: int) -> bool:
    """Sleep until the allowance returns, or give up if the delay is unusable.

    The provider's own `retryDelay` is trusted, and a little extra is added
    because a request fired exactly on the boundary is the one that gets
    rejected, and a rejected request is a wasted round trip. Google reports a
    daily window as a plain count of seconds, so there is nothing to guess at.
    """
    delay = exc.retry_after
    if delay is None or delay <= 0:
        delay = FALLBACK_QUOTA_WAIT
    delay = min(delay, 24 * 3600) + 60.0
    if max_waits <= 0:
        print(f"{stamp()} {exc}", flush=True)
        return False
    hours = delay / 3600
    when = time.strftime("%H:%M:%S", time.localtime(time.time() + delay))
    print(
        f"{stamp()} quota exhausted, waiting {hours:.1f}h for the window to "
        f"reopen at {when} ({max_waits} wait(s) left)",
        flush=True,
    )
    for remaining in range(int(delay), 0, -60):
        time.sleep(min(60, remaining))
    print(f"{stamp()} window should be open again, resuming", flush=True)
    return True


class BudgetExhausted(RuntimeError):
    """Raised instead of issuing a request the day cannot afford."""


class RequestMeter:
    """Counts real API requests and refuses to exceed the budget."""

    def __init__(self, budget: int) -> None:
        self.budget = budget
        self.spent = 0
        self.windows = 1

    def charge(self) -> None:
        if self.spent >= self.budget:
            raise BudgetExhausted(
                f"{self.spent} of {self.budget} daily requests spent. "
                "Stopping before the allowance runs out; re-run tomorrow to "
                "continue from the cache."
            )
        self.spent += 1

    @property
    def left(self) -> int:
        return self.budget - self.spent

    def reset(self, window: int) -> None:
        """Start a new day's allowance, keeping the running total for the log.

        Reaching the budget is a scheduling event, not a failure, so the counter
        is rebased rather than raised. The window number is tracked so the log
        shows how many resets the run survived, which is the number that says
        whether this will finish today or tomorrow.
        """
        self.spent = 0
        self.windows = window


def wait_out_quota_budget(meter: RequestMeter, waits_left: int, enabled: bool) -> bool:
    """Sleep to the next day when the run has spent its own request budget.

    This is the runner's own ceiling firing rather than the provider's, so
    there is no `retryDelay` to read. A daily window is long, and pacing to the
    ceiling is what keeps the rest of the day's allowance in reserve.
    """
    if not enabled or waits_left <= 0:
        print(
            f"{stamp()} spent the {meter.budget}-request budget and not waiting; "
            "re-run tomorrow to continue",
            flush=True,
        )
        return False
    when = time.strftime("%H:%M:%S", time.localtime(time.time() + FALLBACK_QUOTA_WAIT))
    print(
        f"{stamp()} budget spent, sleeping until {when} to leave the rest of "
        "today's allowance alone",
        flush=True,
    )
    time.sleep(FALLBACK_QUOTA_WAIT)
    return True


def install_meter(meter: RequestMeter) -> None:
    """Charge every Gemini request against the meter.

    `_generate` is the one place a request leaves for the API, so counting there
    covers the describe pass, the transcription pass, the retry pass, and
    anything a provider does internally, without touching stage code.
    """
    from manga_recap.llm.gemini import GeminiProvider

    original = GeminiProvider._generate

    def metered(self, **kwargs):
        meter.charge()
        try:
            return original(self, **kwargs)
        except LLMQuotaError:
            # A rejected request is not an earned one, so give the slot back.
            # The error is re-raised as itself rather than rebuilt from its
            # message, which would quietly drop `retry_after`: that number is
            # the only thing that says how long the window is shut for, and a
            # runner that cannot see it falls back to a one-hour guess.
            meter.spent -= 1
            raise

    GeminiProvider._generate = metered  # type: ignore[method-assign]


def set_batch_size(config, size: int) -> None:
    config._data.setdefault("llm", {}).setdefault("vision", {})["batch_size"] = size
    describe = config._data.setdefault("describe", {})
    describe["transcribe_batch_size"] = size
    # max_tokens has to shrink with the batch or a small batch pays for a
    # large response allowance it will not use.
    tokens = min(65536, max(8192, int(size / 200 * 65536)))
    config._data["llm"]["vision"]["max_tokens"] = tokens
    describe["transcribe_max_tokens"] = min(65536, max(4096, tokens // 2))


def panel_count(paths: ChapterPaths) -> int:
    index = load_model(paths.panels_dir / "panel_index.json", PanelIndexFile)
    return index.panel_count


def described_count(paths: ChapterPaths) -> int:
    path = paths.descriptions_file
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    return len(data.get("panels", []))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chapters", nargs="+", required=True)
    parser.add_argument(
        "--budget",
        type=int,
        default=DEFAULT_BUDGET,
        help=f"max API requests for this run (default {DEFAULT_BUDGET})",
    )
    parser.add_argument(
        "--first-batch",
        type=int,
        default=0,
        help="override llm.vision.batch_size for the first attempt",
    )
    parser.add_argument(
        "--max-waits",
        type=int,
        default=4,
        help="how many closed quota windows to sleep through (default 4)",
    )
    parser.add_argument(
        "--no-wait",
        dest="wait",
        action="store_false",
        help="stop on quota exhaustion instead of sleeping until the window reopens",
    )
    parser.add_argument("--dry-run", action="store_true", help="report and exit")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    setup_logging(args.log_level)
    config = load_config()
    meter = RequestMeter(args.budget)

    base_size = args.first_batch or int(config.get("llm.vision.batch_size", 200))
    plans: list[tuple[str, int, int, int]] = []
    for chapter in args.chapters:
        paths = ChapterPaths.create(chapter)
        total = panel_count(paths)
        have = described_count(paths)
        plans.append((chapter, total, have, total - have))

    print("chapters (request estimate at one request per pass):")
    for chapter, total, have, missing in plans:
        state = "complete" if missing == 0 else f"{missing} panel(s) to describe"
        passes = 0 if missing == 0 else (1 if missing <= base_size else -missing // base_size or 1)
        calls = 0 if missing == 0 else passes + 1
        print(
            f"  {chapter}: {have}/{total} described, {state}, "
            f"~{calls} request(s), {meter.left} left"
        )
    if args.dry_run:
        return 0

    install_meter(meter)

    finished: list[str] = []
    stopped = False
    waits_left = args.max_waits if args.wait else 0
    windows = 1
    for chapter, _total, _have, missing in plans:
        if missing == 0:
            print(f"{chapter}: already complete, skipping", flush=True)
            continue
        paths = ChapterPaths.create(chapter)

        attempt = 0
        size = base_size
        while True:
            attempt += 1
            if attempt > MAX_ATTEMPTS:
                print(
                    f"{chapter}: still failing after {MAX_ATTEMPTS} attempts, "
                    "leaving it for the next window",
                    flush=True,
                )
                stopped = True
                break
            if meter.left < 2:
                if not wait_out_quota_budget(meter, waits_left, args.wait):
                    stopped = True
                    break
                meter.reset(windows)
                windows += 1
            set_batch_size(config, size)
            print(
                f"{stamp()} {chapter}: attempt {attempt}/{MAX_ATTEMPTS} at "
                f"batch_size {size} (day {windows}, {meter.spent}/{meter.budget} "
                "requests spent)",
                flush=True,
            )
            try:
                result = s2_describe.run(paths, config, force=False)
            except BudgetExhausted as exc:
                print(f"{stamp()} {chapter}: {exc}", flush=True)
                stopped = True
                break
            except LLMQuotaError as exc:
                if not wait_out_quota(exc, max_waits=waits_left):
                    print(f"{stamp()} {chapter}: {exc}", flush=True)
                    stopped = True
                    break
                waits_left -= 1
                meter.reset(windows)
                windows += 1
                attempt -= 1  # the same request, retried, not a second try
                continue
            except LLMError as exc:
                # A whole-chapter call that came back short is a size problem.
                # Halve it and let the cache carry over what already worked.
                print(f"{stamp()} {chapter}: {type(exc).__name__}: {exc}", flush=True)
                size = max(20, size // 2)
                print(f"{stamp()} {chapter}: retrying at batch_size {size}", flush=True)
                continue
            else:
                text_panels = sum(1 for p in result.panels if p.has_detected_text)
                gaps = [p.panel_id for p in result.panels if p.is_untranscribed()]
                print(
                    f"{stamp()} {chapter}: {result.panel_count} panels described, "
                    f"{len(gaps)} untranscribed of {text_panels} text panels",
                    flush=True,
                )
                finished.append(chapter)
                break

    print(f"\nspent {meter.spent} of {meter.budget} requests on day {windows}")
    print(f"finished: {', '.join(finished) if finished else 'none'}")
    if stopped:
        print("stopped early; re-run this command to continue from the cache")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
