"""Provider-agnostic LLM interface.

Two capabilities, deliberately narrow:

    describe(images, prompt) -> dict    vision: panels in, structured JSON out
    write_script(payload, prompt) -> dict   text: context in, structured JSON out

Every provider implements the same two methods and is responsible for its own
JSON-mode enforcement, so callers never think about which vendor is in use.
`extract_json` and `RetryPolicy` are shared because bad JSON and transient 429s
happen everywhere.
"""

from __future__ import annotations

import json
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# Errors worth retrying: rate limits, overloads, dropped connections.
RETRYABLE_MARKERS = (
    "rate limit",
    "rate_limit",
    "429",
    "overloaded",
    "503",
    "502",
    "500",
    "timeout",
    "timed out",
    "connection",
    "temporarily unavailable",
    "too many requests",
)

# Signals that a retry is pointless, so we fail fast and cheaply.
FATAL_MARKERS = (
    "invalid api key",
    "unauthorized",
    "authentication",
    "permission denied",
    "not found",
    "invalid_request_error",
    "model not found",
)


class LLMError(RuntimeError):
    """A provider call failed in a way the caller should see."""


class LLMResponseError(LLMError):
    """The provider replied, but not with the JSON we asked for."""


class LLMQuotaError(LLMError):
    """The account is out of quota, or out of daily request allowance.

    Distinct from a rate limit because the two need opposite responses. A rate
    limit clears in seconds and a retry is the correct answer. An exhausted
    quota does not clear on any timescale this process's retry ladder can wait
    out, so six retries turn a five-second answer into a four-minute one and
    change nothing except the number in the log.

    `retry_after` is the provider's own estimate of when the allowance comes
    back, in seconds, when it supplies one. It is what lets a long job wait out
    a closed window instead of aborting: Google answers a free-tier daily
    overrun with a `RetryInfo.retryDelay` measured in hours, and that number is
    the difference between sleeping and guessing.
    """

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


# Phrases that mean "come back next billing period", not "come back in a moment".
QUOTA_MARKERS = (
    "quota exceeded",
    "resource_exhausted",
    "free_tier",
    "exceeded your current quota",
    "billing",
)


def is_quota_exhausted(message: str) -> bool:
    """Does this error body describe an exhausted quota rather than a rate limit?"""
    text = message.lower()
    if "429" in text or "too many requests" in text:
        # 429 covers both, so only the wording can tell them apart.
        return any(marker in text for marker in QUOTA_MARKERS)
    return any(marker in text for marker in ("resource_exhausted", "quota exceeded"))


class RatePacer:
    """Spaces outgoing requests so a free tier's per-minute ceiling is never hit.

    A free key allows as little as 10 requests a minute. A chapter is 12
    requests, and the pipeline fires them as fast as the network returns, which
    is comfortably faster than that. Retrying a 429 fixes the symptom after the
    fact; pacing avoids the failure entirely and makes a run take minutes
    instead of stalling and retrying.

    Deliberately a leaky bucket with a floor, not a strict rate: the point is a
    minimum interval between calls, so two calls never land inside the same
    window no matter how the previous one was paced.
    """

    def __init__(self, requests_per_minute: float) -> None:
        self.interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0.0
        self.last = 0.0

    def wait(self) -> None:
        if self.interval <= 0:
            return
        gap = time.monotonic() - self.last
        if self.last and gap < self.interval:
            time.sleep(self.interval - gap)
        self.last = time.monotonic()


@dataclass
class RetryPolicy:
    """Exponential backoff with jitter, for transient upstream failures."""

    max_retries: int = 3
    initial_backoff: float = 2.0
    max_backoff: float = 60.0
    multiplier: float = 2.0

    def delay_for(self, attempt: int) -> float:
        raw = self.initial_backoff * (self.multiplier**attempt)
        capped = min(raw, self.max_backoff)
        # Jitter avoids retry storms when several batches fail at once.
        return capped * (0.5 + random.random() * 0.5)

    def run(self, operation, *, description: str = "LLM call", on_retry=None) -> Any:
        """Call `operation` until it succeeds or the retries run out."""
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                return operation()
            except Exception as exc:  # noqa: BLE001 - re-raised below when fatal
                last_error = exc
                message = str(exc).lower()

                if isinstance(exc, LLMQuotaError):
                    # Reported as a 429 like a rate limit, but the allowance does
                    # not come back within this process's lifetime, so retrying
                    # only converts a clear answer into a slow one.
                    raise

                if any(marker in message for marker in FATAL_MARKERS):
                    raise LLMError(f"{description} failed and is not retryable: {exc}") from exc

                if attempt >= self.max_retries:
                    break

                # Non-retryable, non-fatal: treat as a bad response and try again.
                if not any(marker in message for marker in RETRYABLE_MARKERS):
                    if not isinstance(exc, LLMResponseError):
                        raise

                delay = self.delay_for(attempt)
                if on_retry:
                    on_retry(attempt + 1, delay, exc)
                else:
                    print(f"  {description}: retry {attempt + 1}/{self.max_retries} in {delay:.1f}s")
                time.sleep(delay)

        raise LLMError(
            f"{description} failed after {self.max_retries + 1} attempts: {last_error}"
        ) from last_error


@runtime_checkable
class LLMProvider(Protocol):
    """What every provider must implement."""

    name: str

    def describe(
        self, images: list[Path], prompt: str, **kwargs: Any
    ) -> dict:
        """Read panel images and return structured JSON matching the panel schema.

        `context_images` is an optional list of reference images appended after
        the panels, such as the full page a batch was cut from. They are not
        panels to describe, and the prompt is responsible for saying so.
        """
        ...

    def transcribe(
        self, images: list[Path], prompt: str, **kwargs: Any
    ) -> dict:
        """Read native-resolution text crops and return the text found in each.

        Separate from `describe` because the job is different in kind: no
        interpretation, no characters, no setting, just the words. Splitting it
        out also means a failed read costs one cheap call rather than a whole
        expensive description batch.
        """
        ...

    def write_script(self, payload: dict, prompt: str, **kwargs: Any) -> dict:
        """Return the storyboard JSON for a chapter."""
        ...


def normalise_transcripts(payload: dict) -> list[dict]:
    """Accept the several shapes a model may use for a list of transcripts.

    Shares `normalise_panels`' key list because the shapes are the same one:
    a bare list, a list under a named key, or a list nested one level deeper.
    """
    for key in ("panels", "items", "results", "transcripts", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    for value in payload.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    raise LLMResponseError(
        f"Could not find a list of transcripts in the response. "
        f"Top-level keys: {list(payload)}"
    )


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict:
    """Pull a JSON object out of a model reply.

    Providers asked for JSON usually comply, but fences and stray prose around
    the object are common enough to be worth handling rather than failing on.
    """
    if not text or not text.strip():
        raise LLMResponseError("Empty response from provider")

    candidate = text.strip()

    # Strip a markdown code fence if present.
    fence = _FENCE_RE.search(candidate)
    if fence:
        candidate = fence.group(1).strip()

    # Try the whole thing first, then the outermost braces.
    for attempt in (candidate, _outermost_object(candidate)):
        if not attempt:
            continue
        try:
            parsed = json.loads(attempt)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
        if isinstance(parsed, list):
            return {"items": parsed}

    preview = candidate[:300].replace("\n", " ")
    raise LLMResponseError(
        f"Could not parse JSON from provider response. First 300 chars: {preview!r}"
    )


def _outermost_object(text: str) -> str | None:
    """Return the span from the first '{' to its matching '}'."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def normalise_panels(payload: dict) -> list[dict]:
    """Accept the several shapes a model may use for a list of panels.

    Some return `{"panels": [...]}`, some return a bare list wrapped by
    `extract_json` as `{"items": [...]}`, some nest one level deeper.
    """
    for key in ("panels", "items", "results", "descriptions", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if isinstance(payload.get("panels"), dict):
        return []
    for value in payload.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    raise LLMResponseError(
        f"Could not find a list of panels in the response. Top-level keys: {list(payload)}"
    )
