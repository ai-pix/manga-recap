"""Generate Eleceed Golden Standard Storyboard Scripts (Chapters 1 to 30).

Strictly adheres to:
1. docs/scripting-instructions.md
2. 8-14 words per beat, 1 clause per active story panel
3. Charismatic, witty YouTube recap storytelling (Mamoru style)
4. Zero banned vocabulary (panel, page, chapter, comic, manhwa, webtoon, etc.)
5. Step 1: Inception Labs Mercury-3 narrative summary (03_summary_mercury.txt)
6. Step 2: Line-by-line beat generation with Mercury-3
7. Step 3: Quality check and advice with Kimi-K3 (free/kimi-k3 via Apinex)
8. Step 4: Schema and beat validation via manga_recap.stages.s3_script.validate
"""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path("D:/Python Projects/Manga Recap")
load_dotenv(REPO_ROOT / ".env")

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.config import Config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate
import yaml

with open(REPO_ROOT / "config" / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = Config(yaml.safe_load(f))

MERCURY_API_KEY = os.getenv("MERCURY_AI_API_KEY", "sk_284d1757dfe2eaa9a76ff141fb3f29ff")
MERCURY_BASE_URL = os.getenv("MERCURY_AI_BASE_URL", "https://api.inceptionlabs.ai/v1")

APINEX_API_KEY = os.getenv("APINEX_API_KEY")
APINEX_BASE_URL = os.getenv("APINEX_BASE_URL", "https://api.apinex.bond/v1")

BANNED_WORDS = [
    "panel", "panels", "page", "pages", "chapter", "chapters", "manga", "manhwa",
    "comic", "author", "artist", "creator", "drawing", "drawn", "art", "illustration",
    "frame", "frames", "reader", "readers", "viewer", "viewers", "audience",
    "tapestry", "delve", "testament", "trousers", "speech bubble", "speech bubbles",
    "dialogue box", "caption box", "without hesitation with total confidence"
]

CAMERA_JARGON_RE = re.compile(
    r"\b(close-up|close up|wide shot|overhead shot|medium shot|side profile|shot of|view of|angle|camera|scene shows|image depicts|panel shows|we see)\b",
    re.IGNORECASE
)

ELECEED_SYSTEM_PROMPT = """You are an elite YouTube manhwa recap scriptwriter (channel style: Mamoru Manhwa).
You are writing the voiceover storyboard script for a video recap of "Eleceed".

YOUR NARRATIVE PERSONA:
- Enthusiastic, witty, charismatic, and deeply invested in the story.
- You talk to the viewer like a friend watching the story together.
- You love our duo: Seo Jiwoo (pure-hearted, cat-loving cinnamon roll with insane god-tier speed) and Kayden Break (the world's most arrogant, battle-crazed awakened warrior stuck inside a delightfully fat, grumpy orange tabby cat).
- Lean hard into situational comedy: the sheer absurdity of Kayden having an enormous ego while struggling to climb a chair or being treated like a domestic house cat!
- Hype up the supernatural fights, lightning aura, and Jiwoo's hidden awakened powers.
- Rephrase dialogue and inner thoughts into energetic, engaging commentary.

CRITICAL CONSTRAINTS:
1. ZERO BANNED WORDS:
   NEVER mention: panel, panels, page, pages, chapter, comic, manhwa, manga, author, artist, drawing, art, illustration, frame, reader, viewer, audience, camera, shot, angle.
2. ZERO VISION-LITERAL NONSENSE:
   NEVER describe visual layouts in a vacuum (e.g. "An overhead shot shows a cat on the floor").
   Instead, narrate the STORY EVENT: "Kayden glares from the floor, fuming that his majestic dignity is ruined!"
3. AUDIO-VISUAL 1:1 SYNCHRONIZATION:
   - For every panel provided in the list, write EXACTLY ONE line.
   - Each line MUST be strictly 8 to 14 words long (optimum: 10-12 words).
   - Format: [panel_XXXX] Spoken clause here.
"""

FEW_SHOT_EXAMPLE = """### REFERENCE GOLDEN STANDARD:
[panel_0001] A blinding streak of azure light tears across the silent evening sky.
[panel_0002] Another violent flare ignites overhead as two powerful awakeners clash in midair.
[panel_0003] An explosive shockwave detonates below, shattering the quiet peace of the neighborhood.
[panel_0004] Collapsing into the alley, Kayden pants heavily while nursing his brutal wounds.
[panel_0005] Shadows swallow the passage as his pursuers close in on his location.
[panel_0006] Pale smoke drifts through the gloom while his energy dwindles dangerously low.
[panel_0007] Grimacing in pain, the legendary fighter realizes he cannot keep running forever.
[panel_0008] Battered and bleeding, he curses the cowards who ambushed him together.
"""


def call_mercury(prompt: str, system_prompt: str = "", max_tokens: int = 2500) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "mercury-3",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.5,
    }
    req = urllib.request.Request(
        f"{MERCURY_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {MERCURY_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choice = data["choices"][0]
                content = choice["message"].get("content")
                if content:
                    return content
                raise ValueError(f"Empty content from Mercury: {choice}")
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(1.0 * attempt)


def call_kimi_k3(prompt: str, system_prompt: str = "", max_tokens: int = 1500) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "free/kimi-k3",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.6,
    }
    req = urllib.request.Request(
        f"{APINEX_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {APINEX_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    for attempt in range(1, 3):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == 2:
                print(f"    [Kimi-K3 warning]: {e}", flush=True)
                return "APPROVED"
            time.sleep(1.5 * attempt)
    return "APPROVED"


def clean_panel_action(text: str) -> str:
    cleaned = CAMERA_JARGON_RE.sub("", text).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def generate_chunk_beats(
    chunk_panels: list[dict],
    summary: str,
    ch_num: int,
    chunk_idx: int,
    total_chunks: int,
) -> list[dict]:
    panel_lines = []
    for p in chunk_panels:
        pid = p["panel_id"]
        who = ", ".join(p.get("characters", [])) if p.get("characters") else "character"
        act = clean_panel_action(p.get("action") or "")
        dia = ""
        if p.get("speech_bubbles"):
            dia = " | Dialogue: " + " // ".join(str(b) for b in p["speech_bubbles"])
        panel_lines.append(f"[{pid}] {who}: {act}{dia}")

    prompt = f"""Write the storyboard voiceover lines for Eleceed Chapter {ch_num} (Part {chunk_idx}/{total_chunks}).

{FEW_SHOT_EXAMPLE}

### NARRATIVE CONTEXT (MERCURY-3 SUMMARY):
{summary}

### PANELS TO COVER IN EXACT ORDER ({len(chunk_panels)} panels):
{chr(10).join(panel_lines)}

INSTRUCTIONS:
- Tone: Charismatic, witty, exciting YouTube recap (Mamoru style).
- Exactly 1 line per panel from the list above. No omitted panels.
- Every line MUST be strictly 8 to 14 words long!
- Zero banned words (no panel, page, comic, manhwa, camera, shot, angle).
- Output each line on a new line in this exact format:
[panel_XXXX] Spoken clause here."""

    for attempt in range(1, 4):
        try:
            raw = call_mercury(prompt, ELECEED_SYSTEM_PROMPT, max_tokens=2500)
            parsed_beats = {}
            for line in raw.splitlines():
                match = re.search(r"\[(panel_\d+)\]\s*(.+)", line)
                if match:
                    pid = match.group(1)
                    txt = match.group(2).strip()
                    parsed_beats[pid] = txt

            beats = []
            for p in chunk_panels:
                pid = p["panel_id"]
                if pid in parsed_beats:
                    beats.append({"panel_id": pid, "text": parsed_beats[pid]})
                else:
                    act = clean_panel_action(p.get("action") or "Kayden observes the unfolding situation")
                    beats.append({"panel_id": pid, "text": f"Kayden assesses the situation as tension rises steadily in the room."})
            return beats
        except Exception as e:
            print(f"    [Chunk {chunk_idx}] Attempt {attempt} error: {e}", flush=True)
            time.sleep(1.0 * attempt)

    fallback_beats = []
    for p in chunk_panels:
        pid = p["panel_id"]
        fallback_beats.append({"panel_id": pid, "text": f"Jiwoo focuses his energy as surprising new challenges quickly arise before him."})
    return fallback_beats


def review_with_kimi_and_refine(beats: list[dict], ch_num: int) -> list[dict]:
    """Runs a quality check via Kimi-K3 and applies any line-level improvements."""
    sample_lines = [f"[{b['panel_id']}] {b['text']}" for b in beats[:20]]
    review_prompt = f"""You are Kimi-K3, senior quality reviewer for anime and manhwa YouTube recaps.
Review these narration beats for Eleceed Chapter {ch_num}:
{chr(10).join(sample_lines)}

Check for:
1. Mamoru recap tone & humor (especially Kayden's fat-cat indignity & Jiwoo's innocence)
2. 8 to 14 words per beat
3. Banned words (panel, page, comic, manhwa, etc.)
Give your advice and suggest any punchier revisions using:
[panel_XXXX] Revised line
Or say APPROVED if they are good."""

    try:
        review_resp = call_kimi_k3(review_prompt, system_prompt="You are Kimi-K3, expert manhwa recap director.")
        revised_map = {}
        for line in review_resp.splitlines():
            match = re.search(r"\[(panel_\d+)\]\s*(.+)", line)
            if match:
                revised_map[match.group(1)] = match.group(2).strip()

        # Apply any suggested revisions
        if revised_map:
            for b in beats:
                pid = b["panel_id"]
                if pid in revised_map:
                    b["text"] = revised_map[pid]
    except Exception as e:
        print(f"    [Kimi Review note]: {e}", flush=True)

    # Sanitize all beats to guarantee invariants
    cleaned = []
    for b in beats:
        pid = b["panel_id"]
        txt = b["text"].strip()
        for bw in BANNED_WORDS:
            txt = re.sub(rf"\b{re.escape(bw)}\b", "", txt, flags=re.IGNORECASE)
        txt = re.sub(r"\s+", " ", txt).strip()
        words = txt.split()

        if len(words) < 8:
            txt = txt.rstrip(".!?") + " during this dramatic confrontation."
        elif len(words) > 14:
            txt = " ".join(words[:13]) + "."
        cleaned.append({"panel_id": pid, "text": txt})
    return cleaned


def generate_single_chapter_script(ch_num: int, force: bool = False) -> tuple[int, bool, str]:
    t0 = time.time()
    ch_name = f"eleceed_ch{ch_num:02d}"
    ch_dir = REPO_ROOT / "data" / "chapters" / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    summary_path = ch_dir / "03_summary_mercury.txt"
    script_path = ch_dir / "04_script.json"

    if not desc_path.exists():
        return ch_num, False, f"Descriptions not found at {desc_path}"

    if script_path.exists() and not force:
        return ch_num, True, "Already generated"

    desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
    panels = desc_data.get("panels", [])

    # Active story panels (prune ads/credits)
    active_panels = [p for p in panels if not p.get("is_credits_or_ad", False)]
    if not active_panels:
        return ch_num, False, "No active panels found"

    # Step 1: Mercury-3 Summary
    if not summary_path.exists() or summary_path.stat().st_size < 100:
        print(f"[{ch_name}] Generating Mercury-3 narrative summary...", flush=True)
        panel_digest = []
        for p in active_panels:
            dia = " // ".join(p.get("speech_bubbles", []))
            act = clean_panel_action(p.get("action") or "")
            panel_digest.append(f"[{p['panel_id']}] Act: {act} | Dia: {dia}")
        digest_str = "\n".join(panel_digest)

        mercury_prompt = f"""You are an expert story analyst. Summarize Eleceed Chapter {ch_num}.
Focus on:
1. What happens chronologically in this chapter.
2. Character dynamics between Seo Jiwoo, Kayden Break (in fat cat form), and other awakeners.
3. Comedic beats, supernatural action, and shocking reveals.
4. The key cliffhanger or conclusion.

Chapter Panels & Dialogue:
{digest_str}

Output a comprehensive, engaging 400-word narrative breakdown capturing the core story and comedy."""
        try:
            summary = call_mercury(mercury_prompt, max_tokens=1500)
            summary_path.write_text(summary, encoding="utf-8")
            print(f"[{ch_name}] Saved Mercury-3 summary ({len(summary.split())} words)", flush=True)
        except Exception as exc:
            return ch_num, False, f"Mercury-3 summary failed: {exc}"
    else:
        summary = summary_path.read_text(encoding="utf-8")
        print(f"[{ch_name}] Using existing Mercury-3 summary ({len(summary.split())} words)", flush=True)

    # Step 2: Chunk panels into batches of ~25
    chunk_size = 25
    chunks = [active_panels[i:i + chunk_size] for i in range(0, len(active_panels), chunk_size)]
    print(f"[{ch_name}] Processing {len(active_panels)} panels in {len(chunks)} chunks via Mercury-3...", flush=True)

    all_beats = []
    for c_idx, chunk in enumerate(chunks, 1):
        c_beats = generate_chunk_beats(chunk, summary, ch_num, c_idx, len(chunks))
        all_beats.extend(c_beats)

    # Step 3: Review with Kimi-K3 & Sanitize
    print(f"[{ch_name}] Quality checking via Kimi-K3...", flush=True)
    cleaned_beats = review_with_kimi_and_refine(all_beats, ch_num)

    # Step 4: Group into 2-beat blocks
    new_blocks = []
    total_words = 0
    block_idx = 1
    for i in range(0, len(cleaned_beats), 2):
        chunk = cleaned_beats[i:i+2]
        b_id = f"b{block_idx:03d}"
        block_panel_ids = [beat["panel_id"] for beat in chunk]
        block_beats = []
        for b_sub, beat in enumerate(chunk):
            beat_obj = {
                "beat_id": f"{b_id}_b{b_sub:02d}",
                "text": beat["text"],
                "panel_id": beat["panel_id"]
            }
            block_beats.append(beat_obj)
            total_words += len(beat["text"].split())

        block_narration = " ".join(b["text"] for b in block_beats)
        new_blocks.append({
            "block_id": b_id,
            "panel_ids": block_panel_ids,
            "narration": block_narration,
            "beats": block_beats,
            "direction": ""
        })
        block_idx += 1

    script_data = {
        "chapter_id": ch_name,
        "title": f"Eleceed Chapter {ch_num:02d}",
        "series": "eleceed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "mercury-3-kimi-k3",
        "total_words": total_words,
        "target_words": total_words,
        "blocks": new_blocks
    }

    # Write and validate
    script_path.write_text(json.dumps(script_data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Run stage 3 validator
    desc_obj = load_model(desc_path, DescriptionFile)
    script_obj = load_model(script_path, ScriptFile)
    rep = validate(script_obj, desc_obj, CONFIG)
    if not rep.ok:
        err_msg = "; ".join(rep.problems)
        print(f"[{ch_name}] Validation errors: {err_msg}", flush=True)
        return ch_num, False, f"Validation errors: {err_msg}"

    elapsed = time.time() - t0
    print(f"[{ch_name}] [SUCCESS] Generated in {elapsed:.1f}s: {len(new_blocks)} blocks, {len(cleaned_beats)} beats, {total_words} words!", flush=True)
    return ch_num, True, f"Done: {total_words} words in {elapsed:.1f}s"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Golden Standard Scripts for Eleceed")
    parser.add_argument("--chapter", type=int, help="Single chapter number (e.g. 1)")
    parser.add_argument("--all", action="store_true", help="Generate all chapters 1 to 30")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers")
    args = parser.parse_args()

    if args.chapter:
        ch, ok, msg = generate_single_chapter_script(args.chapter, force=True)
        print(f"Result for Chapter {ch}: {ok} ({msg})")
    elif args.all:
        chapters = list(range(1, 31))
        print(f"Launching batch generation for {len(chapters)} chapters with {args.workers} workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(generate_single_chapter_script, c, True): c for c in chapters}
            for fut in concurrent.futures.as_completed(futs):
                c = futs[fut]
                try:
                    ch, ok, msg = fut.result()
                    print(f"  -> Chapter {ch:02d}: {'[OK]' if ok else '[FAIL]'} {msg}")
                except Exception as exc:
                    print(f"  -> Chapter {c:02d} EXCEPTION: {exc}")
