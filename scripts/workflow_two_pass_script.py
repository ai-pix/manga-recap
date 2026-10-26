"""Workflow script for Two-Pass Scripting:
Pass 1: Mercury-3 (Inception Labs) generates deep narrative summary, key plot beats, character arcs, and big-picture context.
Pass 2: Google Gemini (OpenRouter: google/gemini-2.5-flash) uses the Mercury summary + series bible + panel descriptions
        to write the storyboarded recap script with strict 1:1 clause-to-panel sync.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from manga_recap.core.schema import (
    DescriptionFile,
    ScriptFile,
    load_model,
    save_model,
)
from manga_recap.stages.s3_script.validate import validate

REPO_ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters" / "overgeared"
SERIES_BIBLE_PATH = REPO_ROOT / "data" / "series" / "overgeared" / "series.md"

load_dotenv()

MERCURY_API_KEY = os.getenv("MERCURY_AI_API_KEY")
MERCURY_BASE_URL = os.getenv("MERCURY_AI_BASE_URL", "https://api.inceptionlabs.ai/v1")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def call_mercury(prompt: str, system_prompt: str = "") -> str:
    """Call Mercury-3 for deep big-picture analysis and narrative summary."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "mercury-3",
        "messages": messages,
        "max_tokens": 1200,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{MERCURY_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {MERCURY_API_KEY}",
            "Content-Type": "application/json",
        }
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


def call_gemini(prompt: str, system_prompt: str = "") -> str:
    """Call Gemini 2.5 Flash on OpenRouter for JSON storyboard recap script."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "google/gemini-2.5-flash",
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": 0.4,
    }
    req = urllib.request.Request(
        f"{OPENROUTER_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


def process_chapter(ch_name: str) -> bool:
    ch_dir = CHAPTERS_ROOT / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    script_path = ch_dir / "04_script.json"
    summary_path = ch_dir / "04_summary_mercury.md"

    if not desc_path.exists():
        print(f"[{ch_name}] Error: {desc_path} missing.")
        return False

    desc_file: DescriptionFile = load_model(desc_path, DescriptionFile)
    series_bible = SERIES_BIBLE_PATH.read_text(encoding="utf-8") if SERIES_BIBLE_PATH.exists() else ""

    print("\n=======================================================")
    print(f"PROCESSING {ch_name.upper()} ({desc_file.panel_count} panels)")
    print("=======================================================")

    # Compact panel list for LLM context
    panel_contexts = []
    for p in desc_file.panels:
        who = ", ".join(p.characters) if p.characters else "nobody"
        line = f"[{p.panel_id}] {who} | Setting: {p.setting or 'N/A'} | Action: {p.action}"
        if p.speech_bubbles:
            line += f" | Dialogue: {' // '.join(p.speech_bubbles)}"
        panel_contexts.append(line)

    panels_text = "\n".join(panel_contexts)

    # ------------------------------------------------------------------
    # PASS 1: Mercury-3 Summary (The Big Picture)
    # ------------------------------------------------------------------
    print(f"[{ch_name}] Step 1: Generating big-picture summary via Mercury-3...")
    mercury_system = (
        "You are a master story analyst and narrative architect for manga/manhwa recaps. "
        "Analyze the scene sequence, character motivations, comedic subtext, twists, and pacing."
    )
    mercury_prompt = f"""You are analyzing {desc_file.title} of the manhwa Overgeared.

### SERIES CONTEXT:
{series_bible}

### PANEL SEQUENCE ({desc_file.panel_count} panels):
{panels_text}

### YOUR TASK:
Provide a comprehensive, high-level narrative summary of this chapter.
Break down:
1. Core Plot & Turning Points: What happens from beginning to end?
2. Character Dynamics & Subtext: Grid's mindset, greed, determination, and comedic reactions.
3. Key Climax & Emotional / Hype Beats: What is the most exciting or hilarious moment?
4. Storytelling Angle for Recapper: How should the YouTube recapper frame this chapter to hook viewers?
"""

    summary_text = call_mercury(mercury_prompt, mercury_system)
    summary_path.write_text(summary_text, encoding="utf-8")
    print(f"[{ch_name}] Mercury-3 summary saved -> {summary_path.name} ({len(summary_text.split())} words)")

    # ------------------------------------------------------------------
    # PASS 2: Gemini 2.5 Flash Storyboard Script (The Synced Recapper Script)
    # ------------------------------------------------------------------
    print(f"[{ch_name}] Step 2: Generating storyboarded recap script via Gemini 2.5 Flash...")
    gemini_system = """You are an elite YouTube manhwa recap scriptwriter (in the style of Mamoru Manhwa).
You write energetic, hilarious, punchy, and high-retention recap narration.

STRICT RULES:
1. ZERO BANNED WORDS: NEVER use the words 'panel', 'panels', 'page', 'pages', 'chapter', 'manga', 'manhwa', 'author', 'artist', 'drawing', 'illustration', 'reader', 'viewers'.
2. AUDIO-VISUAL SYNC (1 CLAUSE = 1 PANEL):
   - Every panel bound in `panel_ids` MUST have a matching spoken clause describing what is visually on screen in that panel!
   - If a block has multiple panels in `panel_ids`, you MUST provide `beats` matching each clause to its panel.
   - Target 8 to 14 words per clause/panel.
3. HIGH RETENTION PACING:
   - Total chapter script should be ~1,200 to 1,600 words.
   - Paraphrase dialogue into punchy recapper commentary. Never read raw lines like an audiobook.
4. VALID JSON ONLY: Output a valid JSON object matching the ScriptFile schema:
{
  "chapter_id": "chXX",
  "title": "Title",
  "series": "overgeared",
  "word_count": 0,
  "blocks": [
    {
      "block_id": "b001",
      "panel_ids": ["panel_0001"],
      "narration": "Narration text describing panel 1."
    },
    {
      "block_id": "b002",
      "panel_ids": ["panel_0002", "panel_0003"],
      "narration": "First clause for panel 2. Second clause for panel 3.",
      "beats": [
        {"beat_id": "b002_b00", "text": "First clause for panel 2.", "panel_id": "panel_0002"},
        {"beat_id": "b002_b01", "text": "Second clause for panel 3.", "panel_id": "panel_0003"}
      ]
    }
  ]
}
"""

    gemini_prompt = f"""Write the complete recap script for {desc_file.title}.

### BIG-PICTURE SUMMARY (From Mercury-3):
{summary_text}

### PANELS LIST TO COVER ({desc_file.panel_count} panels):
{panels_text}

Cover the story panels in order. Ensure every panel in your blocks has a matching narration clause.
Output strictly valid JSON.
"""

    raw_json = call_gemini(gemini_prompt, gemini_system)

    # Clean potential markdown fences
    clean_json = raw_json.strip()
    if clean_json.startswith("```json"):
        clean_json = clean_json[7:]
    if clean_json.startswith("```"):
        clean_json = clean_json[3:]
    if clean_json.endswith("```"):
        clean_json = clean_json[:-3]
    clean_json = clean_json.strip()

    parsed = json.loads(clean_json)

    # Recalculate word count
    total_words = sum(len(b.get("narration", "").split()) for b in parsed.get("blocks", []))
    parsed["word_count"] = total_words
    parsed["chapter_id"] = ch_name
    parsed["series"] = "overgeared"

    script_obj = ScriptFile.model_validate(parsed)
    save_model(script_obj, script_path)
    print(f"[{ch_name}] Script generated -> {script_path.name} ({len(script_obj.blocks)} blocks, {script_obj.word_count} words)")

    # Validate against pipeline invariants
    print(f"[{ch_name}] Validating script invariants...")
    errors = validate(script_obj, desc_file)
    if errors:
        print(f"[{ch_name}] Validation warnings/errors found ({len(errors)}):")
        for err in errors[:5]:
            print(f"  - {err}")
    else:
        print(f"[{ch_name}] SUCCESS: Script passed all validator checks with 0 errors!")

    return True


if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "ch01"
    process_chapter(ch)
