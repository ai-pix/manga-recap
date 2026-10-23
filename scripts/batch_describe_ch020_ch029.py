"""Parallel Batch processor for Stage 2 (describe) on chapters 20-29.
Uses Top Tools AI with MiniMax-M3 and MAX_WORKERS = 3 (proven safe under 5-connection ceiling).
Fallbacks to Kimi-K2.6 on retry.
Saves incrementally to disk per panel.
"""

from __future__ import annotations

import base64
import concurrent.futures
import io
import json
import random
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from manga_recap.core.config import load_config
from manga_recap.core.env import get as env_get
from manga_recap.core.logging import get_logger, write_stage_status
from manga_recap.core.paths import REPO_ROOT, ChapterPaths
from manga_recap.core.schema import (
    BodyLanguageEntry,
    DescriptionFile,
    PanelDescription,
    PanelIndex,
    save_model,
)
from manga_recap.stages.s1_crop import load_index

_log = get_logger("batch_describe")

API_KEY = (
    env_get("TOP_TOOLS_AI_API_KEY")
    or os.getenv("TOP_TOOLS_AI_API_KEY", "")
)
BASE_URL = env_get("TOP_TOOLS_AI_BASE_URL") or "https://top-tools-ai.com/api/v1"
PRIMARY_MODEL = "MiniMax-M3"
FALLBACK_MODEL = "Kimi-K2.6"
MAX_WORKERS = 5
API_SEMAPHORE = threading.Semaphore(4)
TARGET_CHAPTERS = [f"ch{i:03d}" for i in range(20, 30)]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_prompt() -> str:
    prompt_path = REPO_ROOT / "config" / "prompts" / "panel_description.md"
    return prompt_path.read_text(encoding="utf-8")


def _downscaled_data_url(image_path: Path, max_edge: int = 800) -> str:
    """Downscale panel on-the-fly to max 800px WebP using Lanczos for crisp, small payloads."""
    with Image.open(image_path) as img:
        orig_w, orig_h = img.size
        ratio = min(max_edge / orig_w, max_edge / orig_h)
        if ratio < 1.0:
            new_w, new_h = max(1, int(orig_w * ratio)), max(1, int(orig_h * ratio))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=85)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/webp;base64,{encoded}"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        value = [value]
    return [str(v).strip() for v in value if str(v).strip()]


def _call_api_with_retry(payload: dict, max_retries: int = 5) -> dict:
    url = f"{BASE_URL}/chat/completions"
    backoff = 2.0
    current_payload = dict(payload)

    for attempt in range(1, max_retries + 1):
        if attempt >= 3:
            current_payload["model"] = FALLBACK_MODEL

        data_bytes = json.dumps(current_payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=55) as resp:
                data = json.loads(resp.read().decode())
                content = data["choices"][0]["message"]["content"]
                text = content.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                return json.loads(text)
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode()[:200]
            if attempt == max_retries:
                raise RuntimeError(f"HTTP {e.code} after {max_retries} attempts: {err_msg}") from e
            jitter = random.uniform(1.0, 3.5)
            sleep_sec = backoff + jitter
            print(f"[RETRY {attempt}/{max_retries}] HTTP {e.code} ({err_msg}). Backing off {sleep_sec:.1f}s...", flush=True)
            time.sleep(sleep_sec)
            backoff *= 1.8
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(f"Error after {max_retries} attempts: {e}") from e
            print(f"[RETRY {attempt}/{max_retries}] Exception ({e}). Backing off {backoff:.1f}s...", flush=True)
            time.sleep(backoff)
            backoff *= 1.8


def _build_description(raw: dict, panel: PanelIndex) -> PanelDescription:
    # Handle wrapping if model placed dict inside a list or under 'panels'
    if isinstance(raw, dict) and "panels" in raw and isinstance(raw["panels"], list) and raw["panels"]:
        raw = raw["panels"][0]

    body_language = []
    for entry in raw.get("body_language") or []:
        if isinstance(entry, dict):
            body_language.append(
                BodyLanguageEntry(
                    character=str(entry.get("character", "unknown")).strip() or "unknown",
                    pose=str(entry.get("pose", "")).strip(),
                    action=str(entry.get("action", "")).strip(),
                    expression_detail=str(entry.get("expression_detail", "")).strip(),
                )
            )

    speech = _as_list(raw.get("speech_bubbles"))
    sfx = _as_list(raw.get("sfx_text"))
    return PanelDescription(
        panel_id=panel.panel_id,
        page_number=panel.page_number,
        reading_order=panel.reading_order,
        image_path=panel.image_path,
        characters=_as_list(raw.get("characters")),
        setting=str(raw.get("setting", "")).strip(),
        action=str(raw.get("action", "")).strip() or "Undescribed panel.",
        expression=str(raw.get("expression", "")).strip(),
        body_language=body_language,
        props=_as_list(raw.get("props")),
        sfx_text=sfx,
        speech_bubbles=speech,
        ambient_mood=str(raw.get("ambient_mood", "")).strip(),
        is_sfx_only=bool(raw.get("is_sfx_only", False)),
        is_color_splash=bool(raw.get("is_color_splash", False)),
        is_credits_or_ad=bool(raw.get("is_credits_or_ad", False)),
        has_detected_text=panel.has_text,
        transcription_source="panel" if panel.has_text and (speech or sfx) else "none",
    )


def process_chapter(chapter_id: str, prompt_base: str, series_name: str) -> str:
    paths = ChapterPaths.create(chapter_id)
    index = load_index(paths)
    if index.panel_count == 0:
        return f"[{chapter_id}] Skipped: no panels."

    described: dict[str, PanelDescription] = {}
    if paths.descriptions_file.exists():
        try:
            with open(paths.descriptions_file, encoding="utf-8") as f:
                data = json.load(f)
                for p_dict in data.get("panels", []):
                    # Only accept real descriptions
                    if p_dict.get("action") != "Panel depicted in scene.":
                        p = PanelDescription(**p_dict)
                        described[p.panel_id] = p
        except Exception as e:
            print(f"[{chapter_id}] Notice: starting fresh description ({e})", flush=True)

    ordered_panels = index.ordered()
    pending = [p for p in ordered_panels if p.panel_id not in described]

    if not pending:
        return f"[{chapter_id}] Already 100% complete ({len(described)} panels)."

    print(f"\n>>> [{chapter_id}] Starting describe: {len(pending)} pending / {index.panel_count} total panels with {MAX_WORKERS} workers ({PRIMARY_MODEL}).", flush=True)

    save_lock = threading.Lock()

    def _describe_single_panel(panel: PanelIndex) -> PanelDescription | None:
        panel_img = paths.root / panel.image_path
        data_url = _downscaled_data_url(panel_img)

        user_content = [
            {
                "type": "text",
                "text": f"Analyze manga panel {panel.panel_id} and output valid JSON following the schema precisely.",
            },
            {
                "type": "image_url",
                "image_url": {"url": data_url},
            },
        ]

        payload = {
            "model": PRIMARY_MODEL,
            "messages": [
                {"role": "system", "content": prompt_base},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 1200,
            "temperature": 0.2,
        }

        t0 = time.time()
        try:
            with API_SEMAPHORE:
                res_json = _call_api_with_retry(payload)
            desc = _build_description(res_json, panel)
            elapsed = time.time() - t0

            with save_lock:
                described[panel.panel_id] = desc
                current_ordered = [described[p.panel_id] for p in ordered_panels if p.panel_id in described]
                save_model(
                    DescriptionFile(
                        chapter_id=chapter_id,
                        title="",
                        series=series_name,
                        created_at=_now(),
                        model=PRIMARY_MODEL,
                        panel_count=len(current_ordered),
                        panels=current_ordered,
                    ),
                    paths.descriptions_file,
                )
                pct = len(current_ordered) / index.panel_count * 100
                print(f"  [{chapter_id}] {panel.panel_id} OK in {elapsed:.1f}s -> {len(current_ordered)}/{index.panel_count} ({pct:.1f}%)", flush=True)
            return desc
        except Exception as e:
            print(f"  [{chapter_id}] {panel.panel_id} FAILED ({e})", flush=True)
            return None

    # Run in parallel with MAX_WORKERS
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_describe_single_panel, p): p for p in pending}
        for future in concurrent.futures.as_completed(futures):
            future.result()

    is_complete = len(described) >= index.panel_count
    if is_complete:
        write_stage_status(
            chapter_id,
            "s2_describe",
            "completed",
            {"panel_count": len(described), "model": PRIMARY_MODEL},
        )
    return f"[{chapter_id}] Finished! {len(described)}/{index.panel_count} panels described."


def main():
    config = load_config()
    series_name = str(config.get("project.series_name", "only-sense-online"))
    prompt_base = _load_prompt()

    print("============================================================", flush=True)
    print(f"Parallel Batch Describe Starting: chapters 20-29 ({MAX_WORKERS} Workers)")
    print(f"Provider: Top Tools AI ({BASE_URL})")
    print(f"Primary: {PRIMARY_MODEL} | Fallback: {FALLBACK_MODEL}")
    print(f"Target Chapters: {', '.join(TARGET_CHAPTERS)}")
    print("============================================================\n", flush=True)

    for chapter_id in TARGET_CHAPTERS:
        try:
            summary = process_chapter(chapter_id, prompt_base, series_name)
            print(f">>> {summary}\n", flush=True)
        except Exception as e:
            print(f">>> [{chapter_id}] ERROR: {e}\n", flush=True)

    print("\n============================================================")
    print("ALL TARGET CHAPTERS PROCESSED!")
    print("============================================================")


if __name__ == "__main__":
    main()
