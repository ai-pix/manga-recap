"""Batch processing pipeline for Manga Recap chapters (barbarian_ch02 to barbarian_ch20).

Stages supported:
1. describe: Vision model panel descriptions via Gemini 3.5 Flash Lite
2. summary: Narrative arc summary via Mercury 2.5 (OpenRouter)
3. script: 1:1 panel-to-block recap script via Mercury 2.5 (OpenRouter)
4. speak: Narration generation via Fish Audio + Whisper alignment (05_narration.wav, 06_timeline.json)
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def run_describe(chapter_id: str) -> bool:
    """Run Stage 2: Vision panel descriptions."""
    desc_path = Path(f"data/chapters/{chapter_id}/03_descriptions.json")
    index_path = Path(f"data/chapters/{chapter_id}/02_panels/panel_index.json")
    if desc_path.exists() and index_path.exists():
        try:
            d = json.loads(desc_path.read_text(encoding="utf-8"))
            idx = json.loads(index_path.read_text(encoding="utf-8"))
            if len(d.get("panels", [])) >= len(idx.get("panels", [])):
                print(f"[{chapter_id}] Descriptions already complete ({len(d['panels'])} panels). Skipping.", flush=True)
                return True
        except Exception:
            pass

    print(f"[{chapter_id}] Running describe stage (Gemini 3.5 Flash Lite)...", flush=True)
    cmd = [sys.executable, "-m", "manga_recap", "describe", chapter_id]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[{chapter_id}] Describe failed:\n{res.stderr}\n{res.stdout}", flush=True)
        return False
    print(f"[{chapter_id}] Describe stage complete!", flush=True)
    return True


def run_mercury_summary(chapter_id: str) -> bool:
    """Run Mercury 2.5 narrative summary."""
    summary_path = Path(f"data/chapters/{chapter_id}/03_summary_mercury.txt")
    if summary_path.exists() and summary_path.stat().st_size > 500:
        print(f"[{chapter_id}] Summary already exists ({summary_path.stat().st_size} bytes). Skipping.")
        return True

    desc_path = Path(f"data/chapters/{chapter_id}/03_descriptions.json")
    if not desc_path.exists():
        print(f"[{chapter_id}] Cannot summarize: 03_descriptions.json missing.")
        return False

    desc = json.loads(desc_path.read_text(encoding="utf-8"))
    panel_summaries = []
    for p in desc.get("panels", []):
        pid = p["panel_id"]
        act = p.get("action", "")
        speech = " | ".join(p.get("speech_bubbles", []))
        chars = ", ".join(p.get("characters", []))
        panel_summaries.append(f"[{pid}] Chars: {chars}; Action: {act}; Dialogue: {speech}")

    full_context = "\n".join(panel_summaries)
    prompt = (
        f"You are a master manhwa recap storyteller. Below are the sequential panel descriptions for "
        f"{chapter_id} of 'Surviving the Game as a Barbarian'.\n"
        f"Provide an engaging, highly detailed narrative summary of {chapter_id} that captures all story beats, "
        f"character dialogues, barbarian lore/customs, internal thoughts, and dramatic stakes.\n\n"
        f"PANEL DESCRIPTIONS:\n{full_context}\n"
    )

    payload = {
        "model": "inception/mercury-2.5",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
    }

    req = urllib.request.Request(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        data=json.dumps(payload).encode(),
    )

    print(f"[{chapter_id}] Generating Mercury 2.5 narrative summary...", flush=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                if "choices" in data and data["choices"]:
                    summary = data["choices"][0]["message"].get("content", "")
                    if summary:
                        summary_path.write_text(summary, encoding="utf-8")
                        print(f"[{chapter_id}] Summary saved ({len(summary)} chars)!", flush=True)
                        return True
            print(f"[{chapter_id}] Empty summary, retrying (attempt {attempt + 1})...", flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"[{chapter_id}] Error generating summary (attempt {attempt + 1}): {e}", flush=True)
            time.sleep(4)

    return False


def run_mercury_script(chapter_id: str) -> bool:
    """Run Mercury 2.5 1:1 script generation in chunks of 20 panels."""
    out_script_path = Path(f"data/chapters/{chapter_id}/04_script.json")
    desc_path = Path(f"data/chapters/{chapter_id}/03_descriptions.json")
    summary_path = Path(f"data/chapters/{chapter_id}/03_summary_mercury.txt")

    if not desc_path.exists() or not summary_path.exists():
        print(f"[{chapter_id}] Descriptions or summary missing.")
        return False

    desc = json.loads(desc_path.read_text(encoding="utf-8"))
    summary = summary_path.read_text(encoding="utf-8")

    # Filter out title/logo/credits panels
    valid_panels = [
        p for p in desc.get("panels", [])
        if not p.get("is_credits_or_ad", False)
        and p.get("setting") != "page_margin"
        and (chapter_id != "barbarian_ch02" or p.get("panel_id") not in ["panel_0021", "panel_0022"])
    ]

    if out_script_path.exists() and out_script_path.stat().st_size > 1000:
        try:
            from manga_recap.core.schema import ScriptFile
            sc = ScriptFile.model_validate_json(out_script_path.read_text(encoding="utf-8"))
            if len(sc.blocks) >= len(valid_panels) - 2:
                print(f"[{chapter_id}] Script already exists with {len(sc.blocks)} blocks. Skipping.", flush=True)
                return True
        except Exception:
            pass

    cache_dir = Path(f"data/chapters/{chapter_id}/.script_chunks")
    cache_dir.mkdir(parents=True, exist_ok=True)

    chunk_size = 20
    all_blocks = []
    block_counter = 1

    for chunk_idx, i in enumerate(range(0, len(valid_panels), chunk_size)):
        chunk_file = cache_dir / f"chunk_{chunk_idx:02d}.json"
        chunk = valid_panels[i : i + chunk_size]

        if chunk_file.exists():
            blocks = json.loads(chunk_file.read_text(encoding="utf-8"))
        else:
            chunk_lines = []
            for p in chunk:
                pid = p["panel_id"]
                act = p.get("action", "")
                speech = " | ".join(p.get("speech_bubbles", []))
                chars = ", ".join(p.get("characters", []))
                chunk_lines.append(f"Panel ID: {pid}\nCharacters: {chars}\nAction: {act}\nDialogue: {speech}\n")

            chunk_prompt = f"""You are an elite YouTube manhwa recap narrator (style: Mamoru Manhwa).
We are writing the synchronized recap narration for {chapter_id} of 'Surviving the Game as a Barbarian'.

NARRATIVE ARC CONTEXT:
\"\"\"
{summary}
\"\"\"

Write an individual spoken narration block for EACH panel below (1:1 mapping).
Each panel must receive its own block with:
- "block_id": "b001", ...
- "panel_ids": ["panel_XXXX"]  <-- EXACTLY ONE panel_id per block!
- "narration": 1 to 2 punchy, conversational, spoken sentences (10 to 18 words) that describe what is happening in that panel or explain character reasoning.
- "direction": "beat"
- "beats": []

STRICT VOCABULARY BANS:
NEVER say: 'panel', 'panels', 'chapter', 'page', 'manga', 'manhwa', 'author', 'artist', 'drawing', 'illustration', 'reader', 'viewers'.
Speak about Bjorn, Aynar, Erwen, the barbarian tribe, and game mechanics directly.

PANELS TO SCRIPT (Total {len(chunk)} panels):
\"\"\"
{"".join(chunk_lines)}
\"\"\"

Return ONLY a JSON array of blocks:
[
  {{
    "block_id": "...",
    "panel_ids": ["..."],
    "narration": "...",
    "direction": "beat",
    "beats": []
  }}
]
"""

            payload = {
                "model": "inception/mercury-2.5",
                "messages": [{"role": "user", "content": chunk_prompt}],
                "max_tokens": 8000,
            }

            req = urllib.request.Request(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(payload).encode(),
            )

            blocks = None
            for attempt in range(4):
                print(f"[{chapter_id}] Generating script chunk {chunk_idx + 1} ({len(chunk)} panels, attempt {attempt + 1})...", flush=True)
                try:
                    with urllib.request.urlopen(req, timeout=120) as resp:
                        data = json.loads(resp.read().decode())
                        if "choices" not in data or not data["choices"]:
                            time.sleep(3)
                            continue
                        content = data["choices"][0]["message"].get("content", "")
                        if not content:
                            time.sleep(3)
                            continue
                        if "```json" in content:
                            content = content.split("```json")[1].split("```")[0].strip()
                        elif "```" in content:
                            content = content.split("```")[1].split("```")[0].strip()
                        blocks = json.loads(content)
                        if isinstance(blocks, dict) and "blocks" in blocks:
                            blocks = blocks["blocks"]
                        chunk_file.write_text(json.dumps(blocks, indent=2), encoding="utf-8")
                        break
                except Exception as e:
                    print(f"[{chapter_id}] Chunk error on attempt {attempt + 1}: {e}", flush=True)
                    time.sleep(4)

            if not blocks:
                print(f"[{chapter_id}] Failed to generate chunk {chunk_idx + 1}")
                return False

        for b in blocks:
            b["block_id"] = f"b{block_counter:03d}"
            block_counter += 1
            all_blocks.append(b)

    full_script = {
        "chapter_id": chapter_id,
        "title": f"{chapter_id.replace('_', ' ').title()}",
        "series": "barbarian",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "model": "inception/mercury-2.5",
        "target_words": len(all_blocks) * 15,
        "blocks": all_blocks,
    }

    out_script_path.write_text(json.dumps(full_script, indent=2), encoding="utf-8")
    print(f"[{chapter_id}] Script saved to {out_script_path} with {len(all_blocks)} blocks!", flush=True)

    from manga_recap.core.config import load_config
    from manga_recap.core.schema import DescriptionFile, ScriptFile
    from manga_recap.stages.s3_script.validate import validate

    cfg = load_config()
    sc = ScriptFile.model_validate_json(out_script_path.read_text(encoding="utf-8"))
    desc_obj = DescriptionFile.model_validate_json(desc_path.read_text(encoding="utf-8"))
    rep = validate(sc, desc_obj, cfg)
    print(f"[{chapter_id}] Script validation OK: {rep.ok}", flush=True)
    if not rep.ok:
        print(f"[{chapter_id}] Validation report:\n{rep.render()}", flush=True)
        if not rep.is_passing:
            return False
    return True


def run_speak(chapter_id: str) -> bool:
    """Run Stage 4: Fish Audio TTS + Whisper alignment."""
    voice_path = Path(f"data/chapters/{chapter_id}/05_narration.wav")
    timeline_path = Path(f"data/chapters/{chapter_id}/06_timeline.json")
    if voice_path.exists() and timeline_path.exists():
        print(f"[{chapter_id}] Narration and timeline already exist. Skipping.")
        return True

    print(f"[{chapter_id}] Running speak stage (Fish Audio + Whisper)...", flush=True)
    cmd = [sys.executable, "-m", "manga_recap", "speak", chapter_id]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"[{chapter_id}] Speak stage failed with code {res.returncode}", flush=True)
        return False
    print(f"[{chapter_id}] Speak stage complete!", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch process Manga Recap chapters.")
    parser.add_argument("--start", type=int, default=2, help="Start chapter number (e.g. 2)")
    parser.add_argument("--end", type=int, default=20, help="End chapter number (e.g. 20)")
    parser.add_argument("--chapter", type=str, default=None, help="Specific chapter ID (e.g. barbarian_ch02)")
    parser.add_argument("--stage", type=str, default="all", choices=["all", "describe", "summary", "script", "speak"])
    args = parser.parse_args()

    if args.chapter:
        chapters = [args.chapter]
    else:
        chapters = [f"barbarian_ch{c:02d}" for c in range(args.start, args.end + 1)]

    print(f"Starting batch pipeline for chapters: {chapters}")
    print(f"Stage mode: {args.stage}\n" + "=" * 60)

    for cid in chapters:
        print(f"\n>>> PROCESSING {cid} <<<")
        if args.stage in ("all", "describe"):
            if not run_describe(cid):
                print(f"Failed describe for {cid}, skipping chapter.")
                continue

        if args.stage in ("all", "summary"):
            if not run_mercury_summary(cid):
                print(f"Failed summary for {cid}, skipping chapter.")
                continue

        if args.stage in ("all", "script"):
            if not run_mercury_script(cid):
                print(f"Failed script for {cid}, skipping chapter.")
                continue

        if args.stage in ("all", "speak"):
            if not run_speak(cid):
                print(f"Failed speak for {cid}, skipping chapter.")
                continue

    print("\nBatch pipeline finished!")


if __name__ == "__main__":
    main()
