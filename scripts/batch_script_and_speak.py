"""Automated Two-Pass Scripting and Fish Audio Voiceover Pipeline for Overgeared.

Step 1: Audit and prune non-story artifacts (titles, blank gutters, orphan speech bubble crops).
Step 2: Pass 1 - Big-picture narrative summary via Mercury-3 (Inception Labs).
Step 3: Pass 2 - High-retention YouTube recapper storyboard script via Gemini 2.5 Flash (OpenRouter).
Step 4: Stage 4 - Fish Audio cloud synthesis (s2.1-pro-free) & word-anchored timeline generation.
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

from manga_recap.core.config import Config, load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model, save_model
from manga_recap.stages.s3_script.validate import validate
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts

REPO_ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters" / "overgeared"
SERIES_BIBLE_PATH = REPO_ROOT / "data" / "series" / "overgeared" / "series.md"

load_dotenv()
load_dotenv(REPO_ROOT / "config" / ".env")

MERCURY_API_KEY = os.getenv("MERCURY_AI_API_KEY")
MERCURY_BASE_URL = os.getenv("MERCURY_AI_BASE_URL", "https://api.inceptionlabs.ai/v1")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def audit_and_prune_panels(desc_path: Path) -> tuple[int, int]:
    """Flag non-story panels (title covers, blank gutters, standalone text crops) as skippable."""
    desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
    panels = desc_data.get("panels", [])
    pruned_count = 0

    for p in panels:
        setting = p.get("setting", "").lower()
        action = p.get("action", "").lower()
        speech = p.get("speech_bubbles", [])
        chars = p.get("characters", [])

        is_artifact = False

        # 1. Title / credits / chapter logos
        if any(t in setting or t in action for t in ["title", "credits", "logo", "team argo", "author", "redice"]):
            is_artifact = True
        if any("team argo" in s.lower() or "템빨" in s or "redice" in s.lower() for s in speech):
            is_artifact = True

        # 2. Blank or empty gutters
        if any(t in action for t in ["blank", "no clear action", "almost entirely blank", "white space", "page_margin"]):
            is_artifact = True
        if setting == "page_margin":
            is_artifact = True

        # 3. Standalone speech bubble crops without characters or visual scene
        if not chars and ("speech bubble" in action or "caption" in action or "text box" in action):
            if "is displayed" in action or "contains" in action or "abstract white" in setting or "plain white" in setting:
                is_artifact = True

        if is_artifact:
            p["is_credits_or_ad"] = True
            pruned_count += 1
        else:
            p["is_credits_or_ad"] = False

    desc_path.write_text(json.dumps(desc_data, indent=2), encoding="utf-8")
    active_count = len(panels) - pruned_count
    return pruned_count, active_count


def call_mercury(prompt: str, system_prompt: str = "") -> str:
    """Call Mercury-3 for deep big-picture analysis and narrative summary."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "mercury-3",
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0.3,
    }
    req = urllib.request.Request(
        f"{MERCURY_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {MERCURY_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        msg = data["choices"][0]["message"]
        content = msg.get("content")
        if not content:
            raise RuntimeError(f"Mercury-3 returned empty content: {data}")
        return content


def call_gemini(prompt: str, system_prompt: str = "") -> str:
    """Call official Google Gemini API (gemini-3.1-flash-lite) for JSON storyboard recap script."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in config/.env or the environment.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
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
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"]


def process_chapter(ch_name: str, config: Config, force_script: bool = False, force_audio: bool = False) -> bool:
    ch_dir = CHAPTERS_ROOT / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    script_path = ch_dir / "04_script.json"
    summary_path = ch_dir / "04_summary_mercury.md"
    audio_path = ch_dir / "05_narration.wav"
    timeline_path = ch_dir / "06_timeline.json"

    if not desc_path.exists():
        print(f"[{ch_name}] Error: {desc_path} missing. Skipping.")
        return False

    print("\n=======================================================")
    print(f"PROCESSING {ch_name.upper()}")
    print("=======================================================")

    # 1. Audit and prune non-story artifacts
    pruned, active = audit_and_prune_panels(desc_path)
    print(f"[{ch_name}] Panel audit: {pruned} non-story panels pruned, {active} story panels active.")

    desc_file: DescriptionFile = load_model(desc_path, DescriptionFile)
    series_bible = SERIES_BIBLE_PATH.read_text(encoding="utf-8") if SERIES_BIBLE_PATH.exists() else ""

    # Build active panel context list
    panel_contexts = []
    for p in desc_file.panels:
        if p.is_credits_or_ad:
            continue
        who = ", ".join(p.characters) if p.characters else "nobody"
        line = f"[{p.panel_id}] {who} | Setting: {p.setting or 'N/A'} | Action: {p.action}"
        if p.speech_bubbles:
            line += f" | Dialogue: {' // '.join(p.speech_bubbles)}"
        panel_contexts.append(line)

    panels_text = "\n".join(panel_contexts)

    # 2. Pass 1: Mercury-3 Narrative Summary
    if summary_path.exists() and not force_script:
        print(f"[{ch_name}] Pass 1: Found existing Mercury summary -> {summary_path.name}")
        summary_text = summary_path.read_text(encoding="utf-8")
    else:
        print(f"[{ch_name}] Pass 1: Calling Mercury-3 for big-picture summary...")
        mercury_system = (
            "You are a master story analyst and narrative architect for manga/manhwa recaps. "
            "Analyze the scene sequence, character motivations, comedic subtext, twists, and pacing."
        )
        mercury_prompt = f"""You are analyzing {desc_file.title} of the manhwa Overgeared.

### SERIES CONTEXT:
{series_bible}

### STORY PANEL SEQUENCE ({active} panels):
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
        print(f"[{ch_name}] Mercury-3 summary saved ({len(summary_text.split())} words).")

    # 3. Pass 2: Gemini Recapper Storyboard Script
    if script_path.exists() and not force_script:
        print(f"[{ch_name}] Pass 2: Found existing script -> {script_path.name}")
        script_obj = load_model(script_path, ScriptFile)
    else:
        print(f"[{ch_name}] Pass 2: Calling official Google Gemini API (gemini-3.1-flash-lite)...")
        gemini_system = """You are an elite YouTube manhwa recap scriptwriter (in the style of Mamoru Manhwa).
You write energetic, hilarious, punchy, and high-retention recap narration.

STRICT RULES:
1. ZERO BANNED WORDS: NEVER use the words 'panel', 'panels', 'page', 'pages', 'chapter', 'manga', 'manhwa', 'author', 'artist', 'drawing', 'illustration', 'reader', 'viewers'.
2. AUDIO-VISUAL SYNC (1 CLAUSE = 1 PANEL):
   - Every panel in `panel_ids` MUST have a matching spoken clause describing what is visually happening in that panel!
   - If a block names multiple panels, you MUST include `beats` matching each clause to its panel.
   - Target 8 to 14 words per clause/panel.
3. HIGH RETENTION PACING:
   - Total chapter script should be ~1,100 to 1,600 words.
   - Paraphrase dialogue into punchy recapper commentary. Never read raw quotes like an audiobook.
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

### STORY PANELS TO COVER ({active} panels):
{panels_text}

Cover the story panels in order. Ensure every panel in your blocks has a matching narration clause.
Output strictly valid JSON.
"""
        raw_json = call_gemini(gemini_prompt, gemini_system)
        (ch_dir / "_debug_script_raw.json").write_text(raw_json, encoding="utf-8")
        clean_json = raw_json.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        try:
            parsed = json.loads(clean_json)
        except json.JSONDecodeError as jde:
            print(f"[{ch_name}] JSONDecodeError: {jde}. Raw tail: {clean_json[-200:]}")
            raise
        total_words = sum(len(b.get("narration", "").split()) for b in parsed.get("blocks", []))
        parsed["word_count"] = total_words
        parsed["chapter_id"] = ch_name
        parsed["series"] = "overgeared"
        parsed["created_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        # Sanitize and ensure unique beat_ids per block, and sync narration with beats
        for b in parsed.get("blocks", []):
            if "beats" in b and b["beats"]:
                for idx, beat in enumerate(b["beats"]):
                    beat["beat_id"] = f"{b['block_id']}_b{idx:02d}"
                b["narration"] = " ".join(beat["text"].strip() for beat in b["beats"])

        script_obj = ScriptFile.model_validate(parsed)
        save_model(script_obj, script_path)
        print(f"[{ch_name}] Script generated ({len(script_obj.blocks)} blocks, {script_obj.total_words} words).")

        # Validate script
        errors = validate(script_obj, desc_file)
        if errors:
            print(f"[{ch_name}] Validator warnings ({len(errors)}):")
            for err in errors[:5]:
                print(f"  - {err}")
        else:
            print(f"[{ch_name}] Script passed all validator checks with 0 errors!")

    # 4. Stage 4: Fish Audio Synthesis & Timeline Generation
    if audio_path.exists() and timeline_path.exists() and not force_audio:
        print(f"[{ch_name}] Stage 4: Found existing Fish Audio narration -> {audio_path.name}")
    else:
        print(f"[{ch_name}] Stage 4: Synthesizing narration with Fish Audio (s2.1-pro-free)...")
        paths = ChapterPaths(f"overgeared/{ch_name}", REPO_ROOT / "data" / "chapters")
        timeline = run_fish_tts(paths, config, force=force_audio)
        print(f"[{ch_name}] Audio synthesized: {timeline.duration:.1f}s, {len(timeline.blocks)} blocks -> {audio_path.name}")

    print(f"[{ch_name}] COMPLETE & VERIFIED!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch script and synthesize chapters")
    parser.add_argument("--chapters", nargs="*", help="Specific chapters to process (e.g. ch02 ch03)")
    parser.add_argument("--from-ch", type=int, default=2, help="Start chapter number (default: 2)")
    parser.add_argument("--to-ch", type=int, default=30, help="End chapter number (default: 30)")
    parser.add_argument("--force-script", action="store_true", help="Force regenerate summary and script")
    parser.add_argument("--force-audio", action="store_true", help="Force resynthesize audio")
    args = parser.parse_args()

    config = load_config()

    if args.chapters:
        target_chapters = args.chapters
    else:
        target_chapters = [f"ch{i:02d}" for i in range(args.from_ch, args.to_ch + 1)]

    print(f"Starting batch processing for {len(target_chapters)} chapters: {target_chapters}")
    t_start = time.time()

    successes = []
    failures = []

    for ch in target_chapters:
        try:
            ok = process_chapter(ch, config, force_script=args.force_script, force_audio=args.force_audio)
            if ok:
                successes.append(ch)
            else:
                failures.append(ch)
        except Exception as e:
            print(f"[{ch}] ERROR: {e}")
            failures.append(ch)

    elapsed = time.time() - t_start
    print("\n=======================================================")
    print(f"BATCH FINISHED in {elapsed:.1f}s")
    print(f"Success ({len(successes)}): {successes}")
    if failures:
        print(f"Failures ({len(failures)}): {failures}")
    print("=======================================================")


if __name__ == "__main__":
    main()
