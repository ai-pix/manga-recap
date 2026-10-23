"""Anthropic provider (vision + script).

Uses the Messages API with a tool definition to force structured output, rather
than just asking for JSON in prose. That is meaningfully more reliable: the
model cannot drift out of the schema mid-chapter, which matters when the script
stage must emit hundreds of block objects with correct panel references.
"""

from __future__ import annotations

import base64
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

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# Tool schemas. Anthropic's tool-use gives us a hard guarantee on shape.
PANEL_TOOL = {
    "name": "record_panels",
    "description": "Record the structured description of each manga panel that was shown.",
    "input_schema": {
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
}

SCRIPT_TOOL = {
    "name": "record_storyboard",
    "description": "Record the finished storyboard: narration blocks and the panels each plays over.",
    "input_schema": {
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
}


TRANSCRIPT_TOOL = {
    "name": "record_text",
    "description": (
        "Record only the text visible in each manga text crop. No description, "
        "no interpretation, no characters."
    ),
    "input_schema": {
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
    },
}


class AnthropicProvider:
    name = "anthropic"

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
        self._client = httpx.Client(
            base_url="https://api.anthropic.com",
            timeout=timeout,
            headers={
                "x-api-key": api_key,
                "anthropic-version": API_VERSION,
                "content-type": "application/json",
            },
        )

    # -- public API -------------------------------------------------------

    def describe(self, images: list[Path], prompt: str, **kwargs: Any) -> dict:
        """Describe a batch of panel images.

        Every image carries its panel_id in a text block immediately before it,
        because the model must echo that id back and a bare list of images gives
        it no way to know which description belongs to which panel.
        """
        content: list[dict] = []
        for image in images:
            content.append(_text_block(f"panel_id: {image.stem}"))
            content.append(_image_block(image))

        for image in kwargs.get("context_images") or []:
            content.append(
                _text_block(
                    f"layout reference for the panels above, not a panel to "
                    f"describe: {image.stem}"
                )
            )
            content.append(_image_block(image))

        return self._call_with_tool(
            system=prompt,
            content=content,
            tool=PANEL_TOOL,
            max_tokens=int(kwargs.get("max_tokens", 8000)),
            temperature=float(kwargs.get("temperature", 0.2)),
        )

    def transcribe(self, images: list[Path], prompt: str, **kwargs: Any) -> dict:
        content: list[dict] = []
        for image in images:
            content.append(_text_block(f"panel_id: {image.stem}"))
            content.append(_image_block(image))

        result = self._call_with_tool(
            system=prompt,
            content=content,
            tool=TRANSCRIPT_TOOL,
            max_tokens=int(kwargs.get("max_tokens", 4000)),
            temperature=float(kwargs.get("temperature", 0.0)),
        )
        return {"panels": normalise_transcripts(result)}

    def write_script(self, payload: dict, prompt: str, **kwargs: Any) -> dict:
        """Generate the storyboard from the chapter context payload."""
        return self._call_with_tool(
            system=prompt,
            content=[_text_block(_render_script_payload(payload))],
            tool=SCRIPT_TOOL,
            max_tokens=int(kwargs.get("max_tokens", 16000)),
            temperature=float(kwargs.get("temperature", 0.9)),
        )

    # -- internals --------------------------------------------------------

    def _call_with_tool(
        self,
        *,
        system: str,
        content: list[dict],
        tool: dict,
        max_tokens: int,
        temperature: float,
    ) -> dict:
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": content}],
            "tools": [tool],
            # Force the model to answer with the tool call, not prose.
            "tool_choice": {"type": "tool", "name": tool["name"]},
        }

        def operation() -> dict:
            self.pacer.wait()
            response = self._client.post("/v1/messages", json=body)
            if response.status_code != 200:
                detail = response.text[:600]
                raise LLMError(
                    f"Anthropic API returned {response.status_code}: {detail}"
                )
            return _extract_tool_input(response.json(), tool["name"])

        return self.retry.run(
            operation, description=f"anthropic {self.model} {tool['name']}"
        )

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _text_block(text: str) -> dict:
    return {"type": "text", "text": text}


def _image_block(image: Path) -> dict:
    """Encode a panel as a base64 image block."""
    image = Path(image)
    mime, _ = mimetypes.guess_type(str(image))
    if mime not in ("image/png", "image/jpeg", "image/webp", "image/gif"):
        mime = "image/png"
    data = base64.standard_b64encode(image.read_bytes()).decode("ascii")
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": mime, "data": data},
    }


def _extract_tool_input(response: dict, tool_name: str) -> dict:
    """Pull the tool_use block's input out of a Messages API response."""
    for block in response.get("content", []):
        if block.get("type") == "tool_use" and block.get("name") == tool_name:
            input_data = block.get("input")
            if isinstance(input_data, dict):
                if tool_name in ("record_panels", "record_text"):
                    return {"panels": normalise_panels(input_data)}
                return input_data

    # stop_reason == max_tokens means the output was cut off, which is a real
    # risk for a long storyboard. Say so rather than reporting a vague failure.
    if response.get("stop_reason") == "max_tokens":
        raise LLMResponseError(
            "Response hit the max_tokens limit before completing. Raise "
            "llm.script.max_tokens (currently the configured value) and retry."
        )

    # Some responses arrive as text anyway; fall back to lenient parsing.
    text_parts = [b.get("text", "") for b in response.get("content", []) if b.get("type") == "text"]
    if text_parts:
        return extract_json("\n".join(text_parts))

    raise LLMResponseError(
        f"No tool_use block for '{tool_name}' in response. "
        f"stop_reason: {response.get('stop_reason')}"
    )


def _render_script_payload(payload: dict) -> str:
    """Flatten the chapter context into the user message for the script stage.

    Labels are explicit so the model always knows where the series background
    stops and the panel list begins.
    """
    sections: list[str] = []

    if payload.get("series_bible"):
        sections.append(
            "<series_bible>\n" + payload["series_bible"].strip() + "\n</series_bible>"
        )

    if payload.get("chapter_title"):
        sections.append(f"<chapter_title>{payload['chapter_title']}</chapter_title>")

    if payload.get("known_characters"):
        known = "\n".join(f"- {c}" for c in payload["known_characters"])
        sections.append(f"<known_characters>\n{known}\n</known_characters>")

    if payload.get("panel_lines"):
        lines = "\n".join(payload["panel_lines"])
        sections.append(
            "<panels>\n"
            f"Total panels: {payload.get('panel_count', len(payload['panel_lines']))}\n"
            f"{lines}\n"
            "</panels>"
        )

    instructions = [
        f"<target_words>{payload.get('target_words', 4000)}</target_words>",
    ]
    if payload.get("coverage_requirements"):
        instructions.append(
            "<coverage>\n" + payload["coverage_requirements"].strip() + "\n</coverage>"
        )
    sections.append("\n".join(instructions))

    return "\n\n".join(sections)
