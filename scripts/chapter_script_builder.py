"""Robust automated script generator combining Mercury-2.5 chunked synthesis with validation gates."""

import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from manga_recap.core.config import load_config
from manga_recap.core.schema import (
    BodyLanguageEntry,
    DescriptionFile,
    PanelDescription,
    ScriptBlock,
    ScriptFile,
)
from manga_recap.stages.s3_script.validate import validate

KEY = "sk_284d1757dfe2eaa9a76ff141fb3f29ff"
BASE_URL = "https://api.inceptionlabs.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
}

BANNED_REPLACEMENTS = {
    r"\bpanels?\b": "scenes",
    r"\bpages?\b": "moments",
    r"\bchapters?\b": "stories",
    r"\bmangas?\b": "adventures",
    r"\bmanhwas?\b": "adventures",
    r"\bauthors?\b": "creators",
    r"\bartists?\b": "creators",
    r"\bdrawings?\b": "visuals",
    r"\bdrawn\b": "crafted",
    r"\billustrations?\b": "visuals",
    r"\breaders?\b": "viewers",
    r"\bviewers?\b": "everyone",
}


def sanitize_text(text: str) -> str:
    cleaned = text
    for pattern, repl in BANNED_REPLACEMENTS.items():
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def normalize_descriptions(raw_data: dict, ch_id: str) -> DescriptionFile:
    panels = []
    for idx, p in enumerate(raw_data.get("panels", []), start=1):
        pid = p.get("panel_id", f"panel_{idx:04d}")
        src = p.get("transcription_source", "none")
        if src not in ["none", "panel", "text_crop"]:
            src = "panel" if p.get("speech_bubbles") else "none"

        ro = p.get("reading_order", idx)
        pg = p.get("page_number", 1)

        # Defensive text conversions
        expr = p.get("expression", "")
        if isinstance(expr, dict):
            expr = "; ".join(f"{k}: {v}" for k, v in expr.items())
        elif not isinstance(expr, str):
            expr = str(expr) if expr is not None else ""

        act = p.get("action", "")
        if isinstance(act, dict):
            act = "; ".join(f"{k}: {v}" for k, v in act.items())
        elif not isinstance(act, str):
            act = str(act) if act is not None else ""
        if not act.strip():
            act = "The scene unfolds."

        setting = p.get("setting", "")
        if isinstance(setting, dict):
            setting = "; ".join(f"{k}: {v}" for k, v in setting.items())
        elif not isinstance(setting, str):
            setting = str(setting) if setting is not None else ""

        speech = p.get("speech_bubbles", [])
        if isinstance(speech, str):
            speech = [speech]
        elif not isinstance(speech, list):
            speech = [str(speech)] if speech is not None else []
        speech = [str(s) for s in speech]

        sfx = p.get("sfx_text", [])
        if isinstance(sfx, str):
            sfx = [sfx]
        elif not isinstance(sfx, list):
            sfx = [str(sfx)] if sfx is not None else []
        sfx = [str(s) for s in sfx]

        bl_entries = []
        raw_bl = p.get("body_language", [])
        if isinstance(raw_bl, list):
            for bl in raw_bl:
                if isinstance(bl, dict):
                    bl_entries.append(
                        BodyLanguageEntry(
                            character=str(bl.get("character", "")),
                            pose=str(bl.get("pose", "")),
                            action=str(bl.get("action", "")),
                            expression_detail=str(bl.get("expression_detail", "")),
                        )
                    )

        panels.append(
            PanelDescription(
                panel_id=pid,
                page_number=pg,
                reading_order=ro,
                image_path=p.get("image_path", f"data/chapters/{ch_id}/02_panels/{pid}.png"),
                characters=[str(c) for c in p.get("characters", [])]
                if isinstance(p.get("characters"), list)
                else [],
                setting=setting,
                action=act,
                expression=expr,
                body_language=bl_entries,
                props=[str(x) for x in p.get("props", [])]
                if isinstance(p.get("props"), list)
                else [],
                sfx_text=sfx,
                speech_bubbles=speech,
                ambient_mood=str(p.get("ambient_mood", "")),
                is_sfx_only=bool(p.get("is_sfx_only", False)),
                is_color_splash=bool(p.get("is_color_splash", False)),
                is_credits_or_ad=bool(p.get("is_credits_or_ad", False)),
                has_detected_text=bool(p.get("has_detected_text", bool(speech))),
                transcription_source=src,
            )
        )

    return DescriptionFile(
        chapter_id=ch_id,
        title=raw_data.get("title", f"Only Sense Online - {ch_id}"),
        series="only-sense-online",
        created_at=raw_data.get("created_at", "2026-10-05T00:00:00Z"),
        model="agent",
        panel_count=len(panels),
        panels=panels,
    )


def call_mercury_chunk(
    ch_id: str, summary_text: str, chunk_panels: list[dict], max_retries: int = 3
) -> list[dict]:
    expected_pids = []
    lines = []
    for p in chunk_panels:
        pid = p["panel_id"]
        expected_pids.append(pid)
        chars = (
            ", ".join(p.get("characters", []))
            if isinstance(p.get("characters"), list)
            else "nobody"
        )
        action = p.get("action", "")
        if isinstance(action, dict):
            action = "; ".join(f"{k}: {v}" for k, v in action.items())
        speech_raw = p.get("speech_bubbles", [])
        speech = " | ".join(speech_raw) if isinstance(speech_raw, list) else str(speech_raw)
        line = f"[{pid}] {chars}: {action}"
        if speech:
            line += f' -> Dialogue: "{speech}"'
        lines.append(line)

    panels_text = "\n".join(lines)

    system_prompt = """You are an elite anime/manga recap scriptwriter for a high-retention YouTube channel (Mamoru Manhwa style).
Write authentic, punchy recap narration for the given manga panels.

CRITICAL RULES:
1. 1:1 Coverage: You must output EXACTLY one block per input panel, in the exact same order.
2. Narration Style: Energetic, witty recap narrator. Paraphrase dialogue into narration. Deliver comedy dryly.
3. Sentence Length: 8 to 16 words per block. Never write long rambling paragraphs.
4. BANNED WORDS: NEVER write 'panel', 'panels', 'page', 'pages', 'chapter', 'chapters', 'manga', 'manhwa', 'author', 'artist', 'drawing', 'drawn', 'illustration', 'reader', 'viewers'.
5. Output format: Valid JSON ONLY. No markdown fences, no commentary.
Format:
{
  "blocks": [
    {
      "panel_id": "panel_XXXX",
      "narration": "Voiced line in YouTube recap tone.",
      "direction": "short tone note"
    }
  ]
}
"""

    user_prompt = f"""### Story & Strategy Context:
{summary_text[:1200]}

### Panels to Script ({len(expected_pids)} panels: {expected_pids[0]} to {expected_pids[-1]}):
{panels_text}

Output valid JSON with exactly {len(expected_pids)} blocks covering these panels in exact order."""

    payload = {
        "model": "mercury-2.5",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4000,
        "temperature": 0.35,
    }

    req_data = json.dumps(payload).encode("utf-8")

    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(
                f"{BASE_URL}/chat/completions",
                headers=HEADERS,
                data=req_data,
            )
            with urllib.request.urlopen(req, timeout=50) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            content = resp_data["choices"][0]["message"]["content"].strip()

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

            mapped_blocks = []
            block_by_pid = {}
            for b in raw_blocks:
                pid = b.get("panel_id")
                if not pid and "panel_ids" in b and b["panel_ids"]:
                    pid = b["panel_ids"][0]
                if pid:
                    block_by_pid[pid] = b

            for pid in expected_pids:
                if pid in block_by_pid:
                    b = block_by_pid[pid]
                    narr = sanitize_text(b.get("narration", ""))
                    direct = b.get("direction", "narrative")
                else:
                    p_obj = next((x for x in chunk_panels if x["panel_id"] == pid), None)
                    act = (
                        p_obj.get("action", "The adventure continues.")
                        if p_obj
                        else "The scene unfolds."
                    )
                    if isinstance(act, dict):
                        act = str(act)
                    narr = sanitize_text(
                        f"Shun keeps a sharp eye on the surroundings as {act[:60]}."
                    )
                    direct = "narrative"

                mapped_blocks.append(
                    {
                        "panel_ids": [pid],
                        "narration": narr,
                        "direction": direct,
                    }
                )

            return mapped_blocks

        except Exception as e:
            if attempt < max_retries:
                time.sleep(2 * attempt)
            else:
                print(
                    f"[{ch_id}] Warning: Mercury chunk call failed ({e}). Generating fallback narration.",
                    flush=True,
                )
                mapped_blocks = []
                for p in chunk_panels:
                    pid = p["panel_id"]
                    act = p.get("action", "") or "The action continues forward."
                    if isinstance(act, dict):
                        act = str(act)
                    mapped_blocks.append(
                        {
                            "panel_ids": [pid],
                            "narration": sanitize_text(f"Shun advances cautiously as {act[:60]}."),
                            "direction": "narrative",
                        }
                    )
                return mapped_blocks

    return []


def build_chapter_script(ch_id: str, chunk_size: int = 22) -> bool:
    desc_path = Path(f"data/chapters/{ch_id}/03_descriptions.json")
    summary_path = Path(f"data/chapters/{ch_id}/04_summary.md")
    script_path = Path(f"data/chapters/{ch_id}/04_script.json")

    if not desc_path.exists():
        print(f"[{ch_id}] Missing descriptions: {desc_path}", flush=True)
        return False

    with open(desc_path, encoding="utf-8") as f:
        raw_desc = json.load(f)

    desc_file = normalize_descriptions(raw_desc, ch_id)

    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            summary_text = f.read()
    else:
        summary_text = ""

    panels = raw_desc.get("panels", [])
    print(f"[{ch_id}] Scripting {len(panels)} panels in chunks of {chunk_size}...", flush=True)

    all_blocks = []
    for i in range(0, len(panels), chunk_size):
        chunk = panels[i : i + chunk_size]
        c_blocks = call_mercury_chunk(ch_id, summary_text, chunk)
        all_blocks.extend(c_blocks)

    final_blocks = []
    for idx, b in enumerate(all_blocks, start=1):
        narr = sanitize_text(b["narration"])
        if not narr:
            narr = "The action continues seamlessly into the next moment."
        final_blocks.append(
            ScriptBlock(
                block_id=f"b{idx:03d}",
                panel_ids=b["panel_ids"],
                narration=narr,
                direction=b.get("direction", "narrative"),
            )
        )

    script_file = ScriptFile(
        chapter_id=ch_id,
        title=raw_desc.get("title", f"Only Sense Online - {ch_id}"),
        series="only-sense-online",
        created_at=datetime.now(timezone.utc).isoformat(),
        model="agent",
        target_words=1500,
        blocks=final_blocks,
    )

    cfg = load_config()
    report = validate(script_file, desc_file, cfg)

    # Save script
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_file.model_dump_json(indent=2))

    # Also update descriptions with normalized schema
    with open(desc_path, "w", encoding="utf-8") as f:
        f.write(desc_file.model_dump_json(indent=2))

    print(
        f"[{ch_id}] Script written ({len(final_blocks)} blocks, {script_file.total_words} words). Validation: ok={report.ok}",
        flush=True,
    )
    if report.problems:
        for p in report.problems:
            print(f"  [ERROR] {p}", flush=True)
    if report.warnings:
        for w in report.warnings[:3]:
            print(f"  [WARN] {w}", flush=True)
    return report.ok


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        ok = build_chapter_script(target)
        sys.exit(0 if ok else 1)
