"""Batch generate high-retention recap storyboard scripts using Official Google Gemini API.

Covers Chapters 02 to 30:
- Reads the chapter's Mercury-3 summary (04_summary_mercury.md).
- Reads previous chapter's summary for narrative continuity and callbacks.
- Reads next chapter's summary for cliffhangers and foreshadowing.
- Generates 04_script.json with strict 1:1 clause-to-panel sync (8-14 words/beat).
- Validates against Pydantic schema and pipeline invariants.
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from manga_recap.core.config import load_config
from manga_recap.core.panelcontent import clean_descriptions, rebind_skippable_panels
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model, save_model
from manga_recap.stages.s3_script.validate import validate

REPO_ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters" / "overgeared"
SERIES_BIBLE_PATH = REPO_ROOT / "data" / "series" / "overgeared" / "series.md"

load_dotenv()
load_dotenv(REPO_ROOT / "config" / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def call_gemini(prompt: str, system_prompt: str = "") -> str:
    """Call official Google Gemini API (gemini-3.1-flash-lite) for JSON storyboard recap script."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set in config/.env or the environment.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={GEMINI_API_KEY}"
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": full_prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.3,
            "maxOutputTokens": 8192,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            if attempt == 3:
                raise
            print(f"  [Gemini retry {attempt}/3]: {e}")
            time.sleep(3.0 * attempt)


def generate_script_for_chapter(ch_num: int, force: bool = False) -> bool:
    ch_name = f"ch{ch_num:02d}"
    ch_dir = CHAPTERS_ROOT / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    summary_path = ch_dir / "04_summary_mercury.md"
    script_path = ch_dir / "04_script.json"

    if not desc_path.exists() or not summary_path.exists():
        print(f"[{ch_name}] Error: Missing descriptions or summary. Skipping.")
        return False

    if script_path.exists() and not force:
        try:
            existing = load_model(script_path, ScriptFile)
            if len(existing.blocks) > 10 and existing.total_words > 400:
                print(f"[{ch_name}] Already exists -> {script_path.name} ({len(existing.blocks)} blocks, {existing.total_words} words). Skipping.")
                return True
        except Exception:
            pass

    desc_file: DescriptionFile = load_model(desc_path, DescriptionFile)
    current_summary = summary_path.read_text(encoding="utf-8")
    series_bible = SERIES_BIBLE_PATH.read_text(encoding="utf-8") if SERIES_BIBLE_PATH.exists() else ""

    # Previous chapter context for narrative continuity
    prev_context = ""
    if ch_num > 1:
        prev_summary_path = CHAPTERS_ROOT / f"ch{ch_num-1:02d}" / "04_summary_mercury.md"
        if prev_summary_path.exists():
            prev_lines = prev_summary_path.read_text(encoding="utf-8").splitlines()
            prev_context = "\n".join(prev_lines[:15])  # First 15 lines of prev summary

    # Next chapter hook for cliffhanger setup
    next_hook = ""
    if ch_num < 30:
        next_summary_path = CHAPTERS_ROOT / f"ch{ch_num+1:02d}" / "04_summary_mercury.md"
        if next_summary_path.exists():
            next_lines = next_summary_path.read_text(encoding="utf-8").splitlines()
            next_hook = "\n".join(next_lines[:12])  # Opening of next chapter

    # Clean descriptions and build active pure art panel sequence
    desc_file, _ = clean_descriptions(desc_file, ch_dir)
    active_panels = [p for p in desc_file.panels if not p.is_skippable()]
    panel_contexts = []
    for p in active_panels:
        who = ", ".join(p.characters) if p.characters else "nobody"
        line = f"[{p.panel_id}] {who} | Setting: {p.setting or 'N/A'} | Action: {p.action}"
        if p.speech_bubbles:
            line += f" | Dialogue: {' // '.join(p.speech_bubbles)}"
        panel_contexts.append(line)

    panels_text = "\n".join(panel_contexts)

    gemini_system = """You are an elite YouTube manhwa recap scriptwriter (in the style of Mamoru Manhwa).
You write energetic, hilarious, punchy, high-retention recap narration that hooks viewers and keeps them glued to the screen.

STRICT INVARIANTS:
1. ZERO BANNED WORDS: NEVER use the words 'panel', 'panels', 'page', 'pages', 'chapter', 'manga', 'manhwa', 'author', 'artist', 'drawing', 'illustration', 'reader', 'viewers', 'in this scene'.
2. AUDIO-VISUAL SYNC (1 CLAUSE = 1 PANEL):
   - Every panel in `panel_ids` MUST have a matching spoken clause describing what is visually happening in that panel!
   - Prefer 1 panel per block (1:1 mapping: block has 1 panel in `panel_ids` and 1 sentence).
   - If grouping 2 panels in a block, you MUST provide `beats` matching each clause to its panel.
   - Target 8 to 14 words per clause/panel.
3. HIGH RETENTION & CLIFFHANGER PACING:
   - Paraphrase dialogue into punchy recapper commentary. Never read raw lines like an audiobook.
   - Weave in Grid's hilarious debt obsession, laborer trauma, comedic arrogance, and running gags.
   - End with an intense, curiosity-inducing cliffhanger connecting to what comes next.
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
      "narration": "Descriptive sentence for panel 1."
    }
  ]
}
"""

    gemini_prompt = f"""Write the complete recap script for {desc_file.title}.

### SERIES LORE & CONTEXT:
{series_bible}

### PREVIOUS CHAPTER LEAD-IN:
{prev_context or "Start of the story."}

### CURRENT CHAPTER BIG-PICTURE SUMMARY (From Mercury-3):
{current_summary}

### NEXT CHAPTER TEASER (Use this to craft the ending cliffhanger!):
{next_hook or "Season finale / climax."}

### STORY PANELS TO COVER IN EXACT ORDER ({len(active_panels)} panels):
{panels_text}

Every story panel must appear in order. Make the narration punchy, exciting, and hilarious.
Output strictly valid JSON.
"""

    print(f"[{ch_name}] Generating script via Gemini ({len(active_panels)} panels)...", end="", flush=True)
    t0 = time.time()
    raw_json = call_gemini(gemini_prompt, gemini_system)
    elapsed = time.time() - t0

    clean_json = raw_json.strip()
    if clean_json.startswith("```json"):
        clean_json = clean_json[7:]
    if clean_json.startswith("```"):
        clean_json = clean_json[3:]
    if clean_json.endswith("```"):
        clean_json = clean_json[:-3]
    clean_json = clean_json.strip()

    parsed = json.loads(clean_json)

    # Sanitize and ensure unique beat_ids per block, and sync narration with beats
    for b in parsed.get("blocks", []):
        if "beats" in b and b["beats"]:
            for idx, beat in enumerate(b["beats"]):
                beat["beat_id"] = f"{b['block_id']}_b{idx:02d}"
            b["narration"] = " ".join(beat["text"].strip() for beat in b["beats"])

    total_words = sum(len(b.get("narration", "").split()) for b in parsed.get("blocks", []))
    parsed["word_count"] = total_words
    parsed["chapter_id"] = ch_name
    parsed["series"] = "overgeared"
    parsed["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

    script_obj = ScriptFile.model_validate(parsed)
    script_obj, rebound_cnt = rebind_skippable_panels(script_obj, desc_file)
    if rebound_cnt > 0:
        print(f" [rebound {rebound_cnt} text panels]", end="")
    save_model(script_obj, script_path)
    print(f" Done in {elapsed:.1f}s ({len(script_obj.blocks)} blocks, {script_obj.total_words} words) -> {script_path.name}")

    # Validate against pipeline invariants
    try:
        config = load_config()
        report = validate(script_obj, desc_file, config)
        if report.problems:
            print(f"  [{ch_name}] Validation notes ({len(report.problems)}): {report.problems[:3]}")
    except Exception as e:
        print(f"  [{ch_name}] Validation check notice: {e}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch generate Gemini storyboard scripts")
    parser.add_argument("--from-ch", type=int, default=2, help="Start chapter (default: 2)")
    parser.add_argument("--to-ch", type=int, default=30, help="End chapter (default: 30)")
    parser.add_argument("--force", action="store_true", help="Force regenerate existing scripts")
    args = parser.parse_args()

    targets = list(range(args.from_ch, args.to_ch + 1))
    print("=======================================================")
    print(f"STARTING GEMINI BATCH SCRIPTING: {len(targets)} CHAPTERS (ch{targets[0]:02d} to ch{targets[-1]:02d})")
    print("=======================================================")

    successes = []
    failures = []
    t_start = time.time()

    for idx, ch_num in enumerate(targets, 1):
        ch_name = f"ch{ch_num:02d}"
        print(f"[{idx}/{len(targets)}] ", end="")
        try:
            ok = generate_script_for_chapter(ch_num, force=args.force)
            if ok:
                successes.append(ch_name)
            else:
                failures.append(ch_name)
        except Exception as e:
            print(f"[{ch_name}] ERROR: {e}")
            failures.append(ch_name)
        time.sleep(1.0)

    total_time = time.time() - t_start
    print("\n=======================================================")
    print(f"PHASE 2 FINISHED IN {total_time:.1f}s ({total_time/60:.1f} mins)")
    print(f"Successfully generated: {len(successes)} scripts")
    if failures:
        print(f"Failed chapters: {failures}")
    print("=======================================================")


if __name__ == "__main__":
    main()
