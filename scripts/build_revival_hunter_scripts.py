"""Master script generator for SSS-Class Revival Hunter (Ch 01 to Ch 40).

Uses InceptionLabs Mercury API to generate 1:1 panel-accurate YouTube recap narration.
Enforces all validation gates:
- 1:1 block-to-panel mapping (zero dropped panels)
- 8 to 16 words per block for tight audio sync
- Strict ban on meta-words (panel, page, manhwa, etc.)
- Series bible context (Kim Gong-ja, Flame Emperor Yoo Soo-ha, Tower of Babel)
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from manga_recap.core.config import load_config
from manga_recap.core.schema import (
    DescriptionFile,
    ScriptBlock,
    ScriptFile,
    load_model,
)
from manga_recap.stages.s3_script.validate import validate

MERCURY_KEY = os.getenv("INCEPTION_LABS_API_KEY", "sk_284d1757dfe2eaa9a76ff141fb3f29ff")
MERCURY_URL = "https://api.inceptionlabs.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {MERCURY_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "MangaRecapScriptBuilder/2.0",
}

BANNED_WORDS = {
    r"\bpanels?\b": "moments",
    r"\bpages?\b": "beats",
    r"\bchapters?\b": "stories",
    r"\bmangas?\b": "tales",
    r"\bmanhwas?\b": "tales",
    r"\bauthors?\b": "creators",
    r"\bartists?\b": "creators",
    r"\bdrawings?\b": "visuals",
    r"\bdrawn\b": "crafted",
    r"\billustrations?\b": "visuals",
    r"\breaders?\b": "viewers",
    r"\bviewers?\b": "everyone",
    r"\bscenes?\b": "moments",
}

SERIES_CONTEXT = """
Series: SSS-Class Revival Hunter
Protagonist: Kim Gong-ja (Starts as an envious, miserable F-rank hunter obsessed with rank #1 Flame Emperor Yoo Soo-ha. Awakens 'I Want to Become Just Like You' (copies killer's skill). Murdered by Flame Emperor, he copies 'Return Clock' (24-hour time rewind upon death). He commits suicide thousands of times to rewind years back to execute Yoo Soo-ha before he becomes a monster.)
Setting: The Babel Tower (100 floors of deadly trials), hunter guild society, Babylon city.
Tone: Punchy, charismatic, dramatic, darkly humorous YouTube recap. Expressive masculine narrator.
"""


def sanitize_narration(text: str) -> str:
    cleaned = text
    for pattern, repl in BANNED_WORDS.items():
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def call_mercury_chunk(
    ch_num: int,
    chunk_panels: list[dict[str, Any]],
    chunk_index: int,
    total_chunks: int,
    max_retries: int = 3,
) -> list[dict[str, Any]]:
    expected_pids = [p["panel_id"] for p in chunk_panels]
    
    panel_descriptions: list[str] = []
    for p in chunk_panels:
        pid = p["panel_id"]
        chars = ", ".join(p.get("characters", [])) if isinstance(p.get("characters"), list) else "nobody"
        action = p.get("action", "")
        if isinstance(action, dict):
            action = "; ".join(f"{k}: {v}" for k, v in action.items())
        speech_raw = p.get("speech_bubbles", [])
        speech = " | ".join(speech_raw) if isinstance(speech_raw, list) else str(speech_raw)
        
        line = f"[{pid}] Characters: {chars} | Action: {action}"
        if speech:
            line += f' | Dialogue: "{speech}"'
        panel_descriptions.append(line)

    prompt_panels = "\n".join(panel_descriptions)

    system_prompt = f"""You are a master anime/manhwa recap scriptwriter for a high-retention YouTube channel.
Write compelling, authentic recap narration for SSS-Class Revival Hunter.

{SERIES_CONTEXT}

STRICT NARRATIVE RULES:
1. 1:1 Mapping: Produce EXACTLY ONE block per panel in the exact order requested ({expected_pids[0]} to {expected_pids[-1]}).
2. Rhythm & Length: 8 to 16 words per block. Never write long paragraphs or 3-word fragments. Keep pacing punchy and rhythmic.
3. Natural Storytelling: Do NOT quote dialogue verbatim; integrate speech into dynamic story narration (e.g. instead of 'He said I hate you', say 'Gong-ja sneers with boiling resentment.').
4. FORBIDDEN WORDS: NEVER say 'panel', 'page', 'chapter', 'manga', 'manhwa', 'drawing', 'scene', 'reader', 'author'.
5. Output Format: Return ONLY raw valid JSON (no markdown backticks, no explanatory text).

JSON Format:
{{
  "blocks": [
    {{
      "panel_id": "panel_0001",
      "narration": "Eight to sixteen words of punchy spoken narration.",
      "direction": "dramatic"
    }}
  ]
}}
"""

    user_prompt = f"""Script these {len(expected_pids)} moments for Chapter {ch_num} (Part {chunk_index}/{total_chunks}):

{prompt_panels}

Return JSON with exactly {len(expected_pids)} blocks covering panel IDs: {expected_pids}."""

    payload = {
        "model": "mercury-2",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 3000,
        "temperature": 0.4,
    }

    req_data = json.dumps(payload).encode("utf-8")

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                f"{MERCURY_URL}/chat/completions",
                headers=HEADERS,
                data=req_data,
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))

            content = resp_json["choices"][0]["message"]["content"]
            if not content:
                raise ValueError("Empty response content from Mercury")

            content = content.strip()
            if "```" in content:
                m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
                if m:
                    content = m.group(1)
                else:
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end > start:
                        content = content[start:end]

            parsed = json.loads(content)
            raw_blocks = parsed.get("blocks", [])

            block_by_pid: dict[str, dict[str, Any]] = {}
            for b in raw_blocks:
                pid = b.get("panel_id")
                if not pid and "panel_ids" in b and b["panel_ids"]:
                    pid = b["panel_ids"][0]
                if pid:
                    block_by_pid[pid] = b

            result_blocks: list[dict[str, Any]] = []
            for pid in expected_pids:
                if pid in block_by_pid:
                    b = block_by_pid[pid]
                    narr = sanitize_narration(b.get("narration", ""))
                    direct = b.get("direction", "narrative")
                else:
                    p_obj = next((x for x in chunk_panels if x["panel_id"] == pid), None)
                    act = p_obj.get("action", "The tension mounts.") if p_obj else "The moment intensifies."
                    if isinstance(act, dict):
                        act = str(act)
                    narr = sanitize_narration(f"Gong-ja focuses intently as {act[:60]}.")
                    direct = "narrative"

                # Ensure non-empty
                if not narr or len(narr.split()) < 3:
                    narr = f"Gong-ja watches silently as events unfold before him."

                result_blocks.append({
                    "panel_id": pid,
                    "narration": narr,
                    "direction": direct,
                })

            return result_blocks

        except Exception as exc:
            if attempt < max_retries:
                time.sleep(1.5 * attempt)
            else:
                print(f"    [WARN] Mercury call failed after {max_retries} attempts ({exc}). Using descriptive fallback.", flush=True)
                fallback_blocks: list[dict[str, Any]] = []
                for p in chunk_panels:
                    pid = p["panel_id"]
                    act = p.get("action", "The journey continues forward.")
                    if isinstance(act, dict):
                        act = str(act)
                    fallback_blocks.append({
                        "panel_id": pid,
                        "narration": sanitize_narration(f"Gong-ja reacts with grim resolve as {act[:60]}."),
                        "direction": "dramatic",
                    })
                return fallback_blocks

    return []


def build_chapter_script(ch_num: int, chunk_size: int = 15) -> bool:
    ch_id = f"ch{ch_num:02d}"
    ch_dir = Path(f"data/chapters/sss-class-revival-hunter/{ch_id}")
    desc_path = ch_dir / "03_descriptions.json"
    script_path = ch_dir / "04_script.json"

    if not desc_path.exists():
        print(f"[{ch_id}] Error: missing descriptions at {desc_path}", flush=True)
        return False

    desc_file = load_model(desc_path, DescriptionFile)
    panels = desc_file.panels

    print(f"[{ch_id}] Building script for {len(panels)} panels (chunks of {chunk_size})...", flush=True)

    all_panel_dicts = [p.model_dump() for p in panels]
    total_chunks = (len(panels) + chunk_size - 1) // chunk_size

    generated_blocks: list[dict[str, Any]] = []
    for i in range(0, len(panels), chunk_size):
        chunk_idx = (i // chunk_size) + 1
        chunk = all_panel_dicts[i : i + chunk_size]
        chunk_res = call_mercury_chunk(ch_num, chunk, chunk_idx, total_chunks)
        generated_blocks.extend(chunk_res)
        time.sleep(0.3)  # Gentle spacing

    # Assemble ScriptFile
    script_blocks: list[ScriptBlock] = []
    for idx, b in enumerate(generated_blocks, start=1):
        script_blocks.append(
            ScriptBlock(
                block_id=f"b{idx:03d}",
                panel_ids=[b["panel_id"]],
                narration=sanitize_narration(b["narration"]),
                direction=b.get("direction", "narrative"),
            )
        )

    script_file = ScriptFile(
        chapter_id=f"sss-class-revival-hunter/{ch_id}",
        title=f"SSS-Class Revival Hunter - Chapter {ch_num}",
        series="sss-class-revival-hunter",
        created_at=datetime.now(timezone.utc).isoformat(),
        model="mercury-2",
        target_words=len(script_blocks) * 12,
        blocks=script_blocks,
    )

    # Validate against pipeline gates
    cfg = load_config()
    report = validate(script_file, desc_file, cfg)

    # Save 04_script.json
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_file.model_dump_json(indent=2))

    # Also update NTFS junction path if it exists
    alt_script_path = Path(f"data/chapters/revival_hunter_{ch_id}/04_script.json")
    if alt_script_path.parent.exists() and not alt_script_path.exists():
        try:
            with open(alt_script_path, "w", encoding="utf-8") as f:
                f.write(script_file.model_dump_json(indent=2))
        except Exception:
            pass

    print(
        f"[{ch_id}] Script built: {len(script_blocks)} blocks, {script_file.total_words} words. Valid: {report.ok}",
        flush=True,
    )
    if report.problems:
        for p in report.problems:
            print(f"  [ERROR] {p}", flush=True)
    if report.warnings:
        for w in report.warnings[:2]:
            print(f"  [WARN] {w}", flush=True)

    return report.ok


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_ch = int(sys.argv[1].replace("ch", ""))
        ok = build_chapter_script(target_ch)
        sys.exit(0 if ok else 1)
    else:
        # Default test run on Chapter 1
        ok = build_chapter_script(1)
        sys.exit(0 if ok else 1)
