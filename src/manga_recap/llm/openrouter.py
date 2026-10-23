"""OpenRouter provider (vision + script).

One API key, many models. Useful when you want to try a different model for
the script without changing providers, or as a fallback when a direct vendor key
is unavailable. JSON mode is requested via `response_format`, which most
OpenRouter models honour.
"""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

import httpx

from .base import (
    LLMError,
    LLMResponseError,
    RatePacer,
    RetryPolicy,
    extract_json,
    normalise_panels,
    normalise_transcripts,
)

API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider:
    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = 300.0,
        max_retries: int = 3,
        retry: RetryPolicy | None = None,
        pacer: RatePacer | None = None,
        app_url: str | None = None,
        app_name: str = "manga-recap",
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.retry = retry or RetryPolicy(max_retries=max_retries)
        self.pacer = pacer or RatePacer(0.0)
        headers = {
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }
        if app_url:
            headers["HTTP-Referer"] = app_url
            headers["X-Title"] = app_name
        self._client = httpx.Client(timeout=timeout, headers=headers)

    # -- public API -------------------------------------------------------

    def describe(self, images: list[Path], prompt: str, **kwargs: Any) -> dict:
        content: list[dict] = [{"type": "text", "text": prompt}]
        for image in images:
            content.append({"type": "text", "text": f"panel_id: {Path(image).stem}"})
            content.append(
                {"type": "image_url", "image_url": {"url": _data_url(image)}}
            )
        for image in kwargs.get("context_images") or []:
            content.append(
                {
                    "type": "text",
                    "text": (
                        f"layout reference for the panels above, not a panel to "
                        f"describe: {Path(image).stem}"
                    ),
                }
            )
            content.append({"type": "image_url", "image_url": {"url": _data_url(image)}})
        payload = self._chat(
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": content}],
            max_tokens=int(kwargs.get("max_tokens", 8000)),
            temperature=float(kwargs.get("temperature", 0.2)),
        )
        return {"panels": normalise_panels(payload)}

    def transcribe(self, images: list[Path], prompt: str, **kwargs: Any) -> dict:
        content: list[dict] = []
        for image in images:
            content.append({"type": "text", "text": f"panel_id: {Path(image).stem}"})
            content.append({"type": "image_url", "image_url": {"url": _data_url(image)}})
        payload = self._chat(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content},
            ],
            max_tokens=int(kwargs.get("max_tokens", 4000)),
            temperature=float(kwargs.get("temperature", 0.0)),
        )
        return {"panels": normalise_transcripts(payload)}

    def write_script(self, payload: dict, prompt: str, **kwargs: Any) -> dict:
        from .anthropic import _render_script_payload

        return self._chat(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": _render_script_payload(payload)},
            ],
            max_tokens=int(kwargs.get("max_tokens", 16000)),
            temperature=float(kwargs.get("temperature", 0.9)),
        )

    # -- internals --------------------------------------------------------

    def _chat(
        self, *, messages: list[dict], max_tokens: int, temperature: float
    ) -> dict:
        self.pacer.wait()
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }

        def operation() -> dict:
            response = self._client.post(API_URL, json=body)
            if response.status_code != 200:
                raise LLMError(
                    f"OpenRouter returned {response.status_code}: {response.text[:600]}"
                )
            return _parse_chat(response.json())

        return self.retry.run(operation, description=f"openrouter {self.model}")

    def close(self) -> None:
        self._client.close()


def _data_url(image: Path) -> str:
    image = Path(image)
    mime, _ = mimetypes.guess_type(str(image))
    if mime not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        mime = "image/png"
    encoded = base64.standard_b64encode(image.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _parse_chat(data: dict) -> dict:
    choices = data.get("choices") or []
    if not choices:
        raise LLMResponseError(f"OpenRouter returned no choices: {json.dumps(data)[:400]}")
    choice = choices[0]
    finish_reason = choice.get("finish_reason")
    if finish_reason == "length":
        raise LLMResponseError(
            "OpenRouter response hit the token limit. Raise max_tokens for this "
            "role and retry."
        )
    content = (choice.get("message") or {}).get("content")
    if not content:
        raise LLMResponseError(f"OpenRouter response had no content: {choice}")
    if isinstance(content, list):
        content = "\n".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return extract_json(content)
