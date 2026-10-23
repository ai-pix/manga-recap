"""Google Gemini provider (vision + script).

Notable difference from the others: Gemini takes whole chapter page images in
one request far more cheaply than per-panel calls do. That makes it a good
`vision` role when the script role stays on Claude.
"""

from __future__ import annotations

import base64
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from .base import (
    LLMError,
    LLMQuotaError,
    LLMResponseError,
    RatePacer,
    RetryPolicy,
    extract_json,
    is_quota_exhausted,
    normalise_panels,
    normalise_transcripts,
)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

PANEL_SCHEMA = {
    "type": "object",
    "properties": {
        "panels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "panel_id": {"type": "string"},
                    "characters": {"type": "array", "items": {"type": "string"}},
                    "setting": {"type": "string"},
                    "action": {"type": "string"},
                    "expression": {"type": "string"},
                    "body_language": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "character": {"type": "string"},
                                "pose": {"type": "string"},
                                "action": {"type": "string"},
                                "expression_detail": {"type": "string"},
                            },
                            "required": ["character", "pose", "action", "expression_detail"],
                        },
                    },
                    "props": {"type": "array", "items": {"type": "string"}},
                    "sfx_text": {"type": "array", "items": {"type": "string"}},
                    "speech_bubbles": {"type": "array", "items": {"type": "string"}},
                    "ambient_mood": {"type": "string"},
                    "is_sfx_only": {"type": "boolean"},
                    "is_color_splash": {"type": "boolean"},
                    "is_credits_or_ad": {"type": "boolean"},
                },
                "required": [
                    "panel_id",
                    "characters",
                    "setting",
                    "action",
                    "expression",
                    "body_language",
                    "props",
                    "sfx_text",
                    "speech_bubbles",
                    "ambient_mood",
                    "is_sfx_only",
                    "is_color_splash",
                    "is_credits_or_ad",
                ],
            },
        }
    },
    "required": ["panels"],
}

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "blocks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "block_id": {"type": "string"},
                    "panel_ids": {"type": "array", "items": {"type": "string"}},
                    "narration": {"type": "string"},
                    "direction": {"type": "string"},
                },
                "required": ["block_id", "panel_ids", "narration", "direction"],
            },
        },
    },
    "required": ["title", "blocks"],
}

# Deliberately narrow. A transcription call that is allowed to describe will
# describe, and a described bubble costs tokens and invites invention. The only
# escape hatch is `illegible`, which is the honest answer for text too small to
# read and is what lets the stage-3 gate see the gap.
TRANSCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "panels": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "panel_id": {"type": "string"},
                    "speech_bubbles": {"type": "array", "items": {"type": "string"}},
                    "sfx_text": {"type": "array", "items": {"type": "string"}},
                    "illegible": {"type": "boolean"},
                },
                "required": ["panel_id", "speech_bubbles", "sfx_text", "illegible"],
            },
        }
    },
    "required": ["panels"],
}


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry: RetryPolicy | None = None,
        pacer: RatePacer | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.retry = retry or RetryPolicy(max_retries=max_retries)
        self.pacer = pacer or RatePacer(0.0)
        self._client = httpx.Client(base_url=BASE_URL, timeout=timeout)

    # -- public API -------------------------------------------------------

    def describe(self, images: list[Path], prompt: str, **kwargs: Any) -> dict:
        parts: list[dict] = list(self._panel_parts(images))
        parts.extend(self._context_parts(kwargs.get("context_images")))
        payload = self._generate(
            system=prompt,
            parts=parts,
            response_schema=PANEL_SCHEMA,
            max_tokens=int(kwargs.get("max_tokens", 8000)),
            temperature=float(kwargs.get("temperature", 0.2)),
        )
        return {"panels": normalise_panels(payload)}

    def transcribe(self, images: list[Path], prompt: str, **kwargs: Any) -> dict:
        parts: list[dict] = list(self._panel_parts(images))
        payload = self._generate(
            system=prompt,
            parts=parts,
            response_schema=TRANSCRIPT_SCHEMA,
            max_tokens=int(kwargs.get("max_tokens", 4000)),
            temperature=float(kwargs.get("temperature", 0.0)),
        )
        return {"panels": normalise_transcripts(payload)}

    def write_script(self, payload: dict, prompt: str, **kwargs: Any) -> dict:
        from .anthropic import _render_script_payload

        return self._generate(
            system=prompt,
            parts=[{"text": _render_script_payload(payload)}],
            response_schema=SCRIPT_SCHEMA,
            max_tokens=int(kwargs.get("max_tokens", 16000)),
            temperature=float(kwargs.get("temperature", 0.9)),
        )

    # -- internals --------------------------------------------------------

    def _panel_parts(self, images: list[Path]) -> Iterator[dict]:
        """A text label then the image, for each panel.

        The label carries the panel_id because the model has to echo it back,
        and a bare list of images gives it no way to know which description
        belongs to which panel.
        """
        for image in images:
            yield {"text": f"panel_id: {Path(image).stem}"}
            yield _inline_data(image)

    def _context_parts(self, images: Any) -> Iterator[dict]:
        """Reference images appended after the panels.

        Labelled explicitly so the model does not describe them. The full page
        a batch was cut from is worth one image per call: without it the model
        cannot tell that two panels are the two halves of a spread.
        """
        for image in images or []:
            yield {
                "text": (
                    f"layout reference for the panels above, not a panel to "
                    f"describe: {Path(image).stem}"
                )
            }
            yield _inline_data(image)

    def _generate(
        self,
        *,
        system: str,
        parts: list[dict],
        response_schema: dict,
        max_tokens: int,
        temperature: float,
    ) -> dict:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"},
            ],
        }

        def operation() -> dict:
            self.pacer.wait()
            response = self._client.post(
                f"/models/{self.model}:generateContent",
                params={"key": self.api_key},
                json=body,
            )
            if response.status_code != 200:
                detail = response.text[:2000]
                if response.status_code in (429, 403) and is_quota_exhausted(detail):
                    retry_after = _retry_after_seconds(detail)
                    raise LLMQuotaError(
                        f"Gemini quota exhausted: {_quota_hint(detail)}\n"
                        "A free-tier key gets a fixed number of generateContent "
                        "requests per day per model, so a chapter of panel batches "
                        "does not fit inside it. Wait for the window to reset, or "
                        "enable billing on the key, or raise llm.vision.batch_size "
                        "so the chapter needs fewer requests.",
                        retry_after=retry_after,
                    )
                raise LLMError(f"Gemini API returned {response.status_code}: {detail}")
            return _parse_candidates(response.json())

        return self.retry.run(operation, description=f"gemini {self.model}")

    def close(self) -> None:
        self._client.close()


def _quota_hint(detail: str) -> str:
    """Pull the limit, the window and the wait out of a quota error body.

    The body names all three, and they are the difference between "wait a
    minute" and "this key gets 20 requests a day, come back tomorrow", so they
    are worth surfacing verbatim. `quotaId` is the only place the window is
    stated in words; the metric alone does not say whether it is per minute or
    per day, and getting that wrong is how a run burns hours of retries.
    """
    import re

    limit = re.search(r"limit:\s*(\d+)", detail)
    metric = re.search(r"metric:\s*([\w./-]+)", detail)
    quota_id = re.search(r"quotaId\"?:\s*\"?([\w-]+)", detail)
    parts = []
    if limit:
        parts.append(f"limit {limit.group(1)}")
    if metric:
        parts.append(metric.group(1))
    if quota_id:
        parts.append(quota_id.group(1))
    if not parts:
        return detail.strip()[:200]
    return ", ".join(parts)


def _retry_after_seconds(detail: str) -> float | None:
    """Read `RetryInfo.retryDelay` out of a quota error body, in seconds.

    Google answers a daily free-tier overrun with a delay measured in hours,
    quoted as a decimal number of seconds. Parsing it is what lets a long job
    sleep exactly as long as the window lasts instead of giving up or polling
    a closed door.
    """
    import re

    match = re.search(r'"retryDelay"\s*:\s*"?([\d.]+)s', detail)
    if match:
        return float(match.group(1))
    # Older bodies only carry the human-readable form, e.g. "retry in 10h33m25s".
    verbose = re.search(r"retry in ([\dhms.]+)", detail)
    if not verbose:
        return None
    total = 0.0
    for value, unit in re.findall(r"([\d.]+)([dhms])", verbose.group(1)):
        total += float(value) * {"d": 86400, "h": 3600, "m": 60, "s": 1}[unit]
    return total or None


def _inline_data(image: Path) -> dict:
    """A whole image part for the generateContent payload.

    The REST API is camelCase throughout: `inlineData`, `mimeType`. The Python
    SDK silently accepts snake_case and the HTTP API rejects it with a 400 that
    names the offending field, so this is worth being explicit about.
    """
    return {
        "inlineData": {
            "mimeType": _mime_for(image),
            "data": base64.standard_b64encode(Path(image).read_bytes()).decode("ascii"),
        }
    }


def _mime_for(image: Path) -> str:
    suffix = Path(image).suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "image/png")


def _parse_candidates(data: dict) -> dict:
    """Pull the JSON payload out of a generateContent response."""
    candidates = data.get("candidates") or []
    if not candidates:
        prompt_feedback = data.get("promptFeedback", {})
        raise LLMResponseError(
            f"Gemini returned no candidates. Feedback: {prompt_feedback}"
        )

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    if finish_reason == "MAX_TOKENS":
        raise LLMResponseError(
            "Gemini hit MAX_TOKENS before completing. Raise the configured "
            "max_tokens for this role and retry."
        )

    parts = candidate.get("content", {}).get("parts", [])
    texts = [p.get("text", "") for p in parts if "text" in p]
    if not texts:
        raise LLMResponseError(f"Gemini response contained no text. Candidate: {candidate}")
    return extract_json("\n".join(texts))
