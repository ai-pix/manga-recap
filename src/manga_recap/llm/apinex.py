"""Apinex provider with native tool calling (vision + script).

High-speed OpenAI-compatible provider hosted at https://api.apinex.bond/v1.
Leverages native OpenAI-format tool calling (function calling) for guaranteed
structured schema adherence on multimodal vision models like free/gemini-3.8-flash.
Configured for maximum tool calls allowed per minute (14.0 RPM against 15.0 limit).
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
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

DEFAULT_API_URL = os.getenv("APINEX_BASE_URL", "https://api.apinex.bond/v1") + "/chat/completions"

PANEL_TOOL = {
    "type": "function",
    "function": {
        "name": "record_panels",
        "description": "Record the structured description of each manga panel that was shown.",
        "parameters": {
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
        },
    },
}

TRANSCRIPT_TOOL = {
    "type": "function",
    "function": {
        "name": "record_text",
        "description": "Record text visible in each manga crop.",
        "parameters": {
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
                        "required": ["panel_id", "speech_bubbles", "sfx_text"],
                    },
                }
            },
            "required": ["panels"],
        },
    },
}

SCRIPT_TOOL = {
    "type": "function",
    "function": {
        "name": "record_storyboard",
        "description": "Record the finished storyboard: narration blocks and mapped panels.",
        "parameters": {
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
        },
    },
}


class ApinexProvider:
    name = "apinex"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout: float = 120.0,
        max_retries: int = 5,
        retry: RetryPolicy | None = None,
        pacer: RatePacer | None = None,
        base_url: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.retry = retry or RetryPolicy(max_retries=max_retries)
        self.pacer = pacer or RatePacer(14.0)  # Max tools allowed per min
        self.api_url = f"{base_url.rstrip('/')}/chat/completions" if base_url else DEFAULT_API_URL

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
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

        payload = self._chat_with_tool(
            messages=[
                {"role": "user", "content": content},
            ],
            tool=PANEL_TOOL,
            max_tokens=int(kwargs.get("max_tokens", 8000)),
            temperature=float(kwargs.get("temperature", 0.2)),
        )
        return {"panels": normalise_panels(payload)}

    def transcribe(self, images: list[Path], prompt: str, **kwargs: Any) -> dict:
        content: list[dict] = []
        for image in images:
            content.append({"type": "text", "text": f"panel_id: {Path(image).stem}"})
            content.append({"type": "image_url", "image_url": {"url": _data_url(image)}})

        payload = self._chat_with_tool(
            messages=[
                {"role": "user", "content": content},
            ],
            tool=TRANSCRIPT_TOOL,
            max_tokens=int(kwargs.get("max_tokens", 4000)),
            temperature=float(kwargs.get("temperature", 0.0)),
        )
        return {"panels": normalise_transcripts(payload)}

    def write_script(self, payload: dict, prompt: str, **kwargs: Any) -> dict:
        from .anthropic import _render_script_payload

        return self._chat_with_tool(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": _render_script_payload(payload)},
            ],
            tool=SCRIPT_TOOL,
            max_tokens=int(kwargs.get("max_tokens", 16000)),
            temperature=float(kwargs.get("temperature", 0.9)),
        )

    # -- internals --------------------------------------------------------

    def _chat_with_tool(
        self,
        *,
        messages: list[dict],
        tool: dict,
        max_tokens: int,
        temperature: float,
    ) -> dict:
        self.pacer.wait()
        tool_name = tool["function"]["name"]
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "tools": [tool],
            "tool_choice": {"type": "function", "function": {"name": tool_name}},
        }

        def operation() -> dict:
            response = self._client.post(self.api_url, json=body)
            if response.status_code != 200:
                raise LLMError(
                    f"Apinex returned {response.status_code}: {response.text[:600]}"
                )
            return _parse_tool_response(response.json())

        return self.retry.run(operation, description=f"apinex tool-call {self.model}")

    def close(self) -> None:
        self._client.close()


def _data_url(image: Path) -> str:
    image = Path(image)
    mime, _ = mimetypes.guess_type(str(image))
    if mime not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        mime = "image/webp" if image.suffix.lower() == ".webp" else "image/png"
    encoded = base64.standard_b64encode(image.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _parse_tool_response(data: dict) -> dict:
    choices = data.get("choices") or []
    if not choices:
        raise LLMResponseError(f"Apinex returned no choices: {json.dumps(data)[:400]}")
    choice = choices[0]
    msg = choice.get("message") or {}

    # 1. Native tool call arguments
    tool_calls = msg.get("tool_calls") or []
    if tool_calls:
        fn = tool_calls[0].get("function") or {}
        raw_args = fn.get("arguments", "{}")
        if isinstance(raw_args, dict):
            return raw_args
        return json.loads(raw_args)

    # 2. Content fallback
    content = msg.get("content")
    if content:
        if isinstance(content, list):
            content = "\n".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        return extract_json(content)

    raise LLMResponseError(f"Apinex response had neither tool_calls nor content: {choice}")
