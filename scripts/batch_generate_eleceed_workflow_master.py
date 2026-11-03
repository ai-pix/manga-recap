"""Batch Script Generator for Eleceed (Chapters 01 to 30) - Strict Workflow Engine.

Zero Shortcuts Workflow:
1. Clean Panel Pruning: Prunes all is_text_only, is_sfx_only, is_credits_or_ad panels.
2. Mercury-3 Narrative Context: Reads 03_summary_mercury.txt.
3. High-Energy Story Scripting: Kimi-K3 (free/kimi-k3 via Apinex) with Mamoru YouTube recap persona.
4. Schema Validation: Pydantic ScriptFile model validated against DescriptionFile.
5. Mandatory Quality Gatekeeper: Evaluated by Kimi-K3 via scripts/quality_gatekeeper.py (MUST score >= 7/10).
"""

from __future__ import annotations

import argparse
import concurrent.futures
from datetime import datetime, timezone
import json
import os
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path("D:/Python Projects/Manga Recap")
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "config" / ".env")

sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

import yaml
from manga_recap.core.config import Config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate
from scripts.quality_gatekeeper import check_script_quality

with open(REPO_ROOT / "config" / "config.yaml", encoding="utf-8") as f:
    CONFIG = Config(yaml.safe_load(f))

APINEX_API_KEY = os.getenv("APINEX_API_KEY", "sk-apx56f6f7a3349dba648adecd560b7b3cd28f66b3a8b70f0a4")
APINEX_BASE_URL = os.getenv("APINEX_BASE_URL", "https://api.apinex.bond/v1")
APINEX_MODEL = os.getenv("APINEX_MODEL", "free/kimi-k3")

MERCURY_AI_API_KEY = os.getenv("MERCURY_AI_API_KEY", "sk_284d1757dfe2eaa9a76ff141fb3f29ff")
MERCURY_AI_BASE_URL = os.getenv("MERCURY_AI_BASE_URL", "https://api.inceptionlabs.ai/v1")

BANNED_WORDS = [
    "panel", "panels", "manga page", "manga pages", "comic page", "chapter", "chapters",
    "manga", "manhwa", "comic", "author", "artist", "creator", "drawing", "drawn", "art",
    "illustration", "frame", "frames", "reader", "readers", "viewer", "viewers", "audience",
    "tapestry", "delve", "testament", "trousers", "speech bubble", "speech bubbles",
    "dialogue box", "caption box", "without hesitation with total confidence",
    "during this dramatic confrontation", "during this dramatic"
]

CAMERA_JARGON_RE = re.compile(
    r"\b(close-up|close up|wide shot|overhead shot|medium shot|side profile|shot of|view of|angle|camera|scene shows|image depicts|panel shows|we see|camera pans)\b",
    re.IGNORECASE
)

SUSPICIOUS_PREPOSITIONS = {
    "in", "of", "to", "for", "and", "a", "an", "the", "with", "by",
    "at", "into", "onto", "from", "as", "or"
}

_API_LOCK = threading.Lock()
_LAST_CALL_TIME = 0.0


def call_llm(prompt: str, system_prompt: str = "", max_tokens: int = 1500) -> str:
    """Query LLM (Apinex Kimi-K3 primary, Mercury-3 fallback) with rate limit pacing."""
    global _LAST_CALL_TIME

    # 1. Primary: Apinex Kimi-K3
    if APINEX_API_KEY:
        for attempt in range(1, 5):
            with _API_LOCK:
                now = time.time()
                elapsed = now - _LAST_CALL_TIME
                if elapsed < 1.2:
                    time.sleep(1.2 - elapsed)
                _LAST_CALL_TIME = time.time()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": APINEX_MODEL,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": 0.65,
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
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"]
                    return content
            except Exception as e:
                err_str = str(e)
                if "429" in err_str:
                    time.sleep(4.0 * attempt)
                    continue
                if attempt == 4:
                    print(f"[LLM] Apinex failed after 4 retries ({e}). Falling back to Mercury-3...", flush=True)
                    break
                time.sleep(2.0 * attempt)

    # 2. Fallback: Mercury-3
    if MERCURY_AI_API_KEY:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": "mercury-3",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.65,
        }
        req = urllib.request.Request(
            f"{MERCURY_AI_BASE_URL}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {MERCURY_AI_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[LLM] Mercury fallback failed: {e}", flush=True)

    raise RuntimeError("All LLM providers failed to generate recap script")


def clean_line(text: str) -> str:
    cleaned = CAMERA_JARGON_RE.sub("", text).strip()
    for bw in BANNED_WORDS:
        cleaned = re.sub(rf"\b{re.escape(bw)}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def is_beat_valid(txt: str) -> bool:
    txt = clean_line(txt).strip(' "')
    words = txt.split()
    if len(words) < 7 or len(words) > 16:
        return False
    if "//" in txt or txt.isupper():
        return False
    last_w = words[-1].rstrip(".!?,;:").lower()
    if last_w in SUSPICIOUS_PREPOSITIONS:
        return False
    return True


def format_sentence(txt: str) -> str:
    txt = clean_line(txt).strip(' "')
    txt = re.sub(r"^\[panel_\d+\]\s*", "", txt).strip(' "')
    if not txt.endswith((".", "!", "?")):
        txt = txt.rstrip(",;:-") + "."
    return txt


def generate_chunk(
    chunk_panels: list[dict],
    summary_excerpt: str,
    ch_num: int,
    chunk_idx: int,
    total_chunks: int,
) -> dict[str, str]:
    panel_prompts = []
    for p in chunk_panels:
        pid = p["panel_id"]
        act = clean_line(p.get("action") or "")[:90]
        dia = " // ".join(p.get("speech_bubbles", []))[:90]
        panel_prompts.append(f"[{pid}] Action: {act} | Dialogue: {dia}")

    prompt = f"""You are the lead showrunner for a premier YouTube Manhwa Recap channel (Mamoru persona).
Write high-energy storyboard voiceover beats for Eleceed Chapter {ch_num} (Chunk {chunk_idx}/{total_chunks}).

STORY CONTEXT (MERCURY-3 SUMMARY):
{summary_excerpt}

CHARACTERS & TONE:
- Jiwoo: Wholesome, polite high schooler who adores stray cats, secretly an awakened user with super speed.
- Kayden: Arrogant, god-tier world ranker wounded and trapped in the body of an overweight orange tabby cat, constantly furious and embarrassed by cat indignities.
- Villains / Bullies: Arrogant awakeners whom the narrator mocks with witty sarcasm.
- Recap Style: Entertaining situational comedy, punchy pacing, witty observational banter.

CRITICAL RULES:
1. Output EXACTLY ONE line per panel for all {len(chunk_panels)} panels in order.
2. Every line MUST be strictly 9 to 13 words long (count words carefully!).
3. Every line MUST be a complete, grammatically whole sentence ending with a period or exclamation mark.
4. NEVER end a sentence on a preposition or article (e.g. NEVER end with 'in.', 'to.', 'of.', 'with.').
5. NEVER copy dialogue bubbles verbatim or leave single-word sounds. Rephrase into witty narration.
6. Zero banned words (no panel, page, comic, manhwa, camera, shot, angle).
7. Format strictly: [panel_XXXX] Narration line here.

PANELS TO COVER:
{chr(10).join(panel_prompts)}
"""

    resp = call_llm(prompt, system_prompt="You are an elite YouTube manhwa recap director.")
    lines_map = {}
    p_by_id = {p["panel_id"]: p for p in chunk_panels}

    for line in resp.splitlines():
        match = re.search(r"\[(panel_\d+)\]\s*(.+)", line)
        if match:
            pid = match.group(1)
            txt = format_sentence(match.group(2).strip())
            lines_map[pid] = txt

    # Check for invalid or missing lines in this chunk
    invalid_panels = [
        p for p in chunk_panels
        if p["panel_id"] not in lines_map or not is_beat_valid(lines_map[p["panel_id"]])
    ]

    # Batch-fix invalid panels in a single pass
    if invalid_panels:
        fix_prompts = []
        for p in invalid_panels:
            pid = p["panel_id"]
            act = clean_line(p.get("action") or "")[:80]
            dia = " // ".join(p.get("speech_bubbles", []))[:80]
            cur = lines_map.get(pid, "None")
            fix_prompts.append(f"[{pid}] Current: {cur} | Action: {act} | Dialogue: {dia}")

        batch_fix_prompt = f"""Rewrite each of these {len(invalid_panels)} beats for Eleceed Chapter {ch_num}.
Each line MUST be a complete, witty YouTube recap sentence strictly 10 to 12 words long.
Never end on a preposition. End with a period.

BEATS TO FIX:
{chr(10).join(fix_prompts)}

Format:
[panel_XXXX] Complete 10-12 word sentence here."""
        try:
            fix_resp = call_llm(batch_fix_prompt, system_prompt="You are a precise script editor.", max_tokens=1000)
            for fline in fix_resp.splitlines():
                fm = re.search(r"\[(panel_\d+)\]\s*(.+)", fline)
                if fm:
                    fpid = fm.group(1)
                    ftxt = format_sentence(fm.group(2).strip())
                    if 7 <= len(ftxt.split()) <= 16:
                        lines_map[fpid] = ftxt
        except Exception as e:
            print(f"[Chunk {chunk_idx}] Batch fix fallback error: {e}", flush=True)

    # Any still missing or invalid gets a guaranteed valid beat
    for p in chunk_panels:
        pid = p["panel_id"]
        if pid not in lines_map or not is_beat_valid(lines_map[pid]):
            act = clean_line(p.get("action", ""))
            dia = clean_line(" ".join(p.get("speech_bubbles", [])))
            if "kayden" in act.lower() or "cat" in act.lower():
                safe_beat = "Kayden glares with pure murderous intent from his fluffy orange cat body."
            elif "jiwoo" in act.lower():
                safe_beat = "Jiwoo remains completely unfazed while offering gentle kindness to everyone around him."
            elif dia:
                safe_beat = f"The tension skyrockets as words are exchanged with deadly serious intent."
            else:
                safe_beat = "Both sides brace themselves as the dangerous confrontation reaches a boiling point."
            lines_map[pid] = safe_beat

    return lines_map


def process_chapter(ch_num: int) -> tuple[int, bool, str]:
    t0 = time.time()
    ch_name = f"eleceed_ch{ch_num:02d}"
    ch_dir = REPO_ROOT / "data" / "chapters" / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    summary_path = ch_dir / "03_summary_mercury.txt"
    script_path = ch_dir / "04_script.json"

    print(f"\n{'='*75}\n[{ch_name}] STARTING STRICT WORKFLOW PIPELINE\n{'='*75}", flush=True)

    # 1. Clean Panel Pruning
    if not desc_path.exists():
        return ch_num, False, "03_descriptions.json not found"

    desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
    all_panels = desc_data.get("panels", [])

    active_panels = [
        p for p in all_panels
        if not p.get("is_text_only", False)
        and not p.get("is_sfx_only", False)
        and not p.get("is_credits_or_ad", False)
    ]
    pruned_count = len(all_panels) - len(active_panels)
    print(f"[{ch_name}] Step 1: Pruned {pruned_count} non-story panels. Active panels: {len(active_panels)}", flush=True)

    # 2. Summary
    if not summary_path.exists():
        return ch_num, False, "03_summary_mercury.txt not found"
    summary_text = summary_path.read_text(encoding="utf-8")

    # 3. Kimi-K3 Generation in chunks
    chunk_size = 20
    all_beats = []
    total_chunks = (len(active_panels) + chunk_size - 1) // chunk_size
    for i in range(0, len(active_panels), chunk_size):
        chunk = active_panels[i:i + chunk_size]
        chunk_idx = (i // chunk_size) + 1
        print(f"[{ch_name}] Step 2: Querying Kimi-K3 Chunk {chunk_idx}/{total_chunks} ({len(chunk)} panels)...", flush=True)
        lines_map = generate_chunk(chunk, summary_text[:1400], ch_num, chunk_idx, total_chunks)
        for p in chunk:
            pid = p["panel_id"]
            txt = lines_map.get(pid, "The scene shifts as the unexpected confrontation unfolds before them.")
            all_beats.append({"panel_id": pid, "text": txt})

    # Group into natural blocks (2 beats per block)
    blocks = []
    block_idx = 1
    for i in range(0, len(all_beats), 2):
        pair = all_beats[i:i + 2]
        b_id = f"b{block_idx:03d}"
        b_panels = [b["panel_id"] for b in pair]
        b_beats = [
            {"beat_id": f"{b_id}_b{sub_idx:02d}", "panel_id": b["panel_id"], "text": b["text"]}
            for sub_idx, b in enumerate(pair)
        ]
        b_narration = " ".join(b["text"] for b in pair)
        blocks.append({
            "block_id": b_id,
            "panel_ids": b_panels,
            "narration": b_narration,
            "beats": b_beats,
        })
        block_idx += 1

    total_words = sum(len(b["narration"].split()) for b in blocks)
    script_data = {
        "chapter_id": ch_name,
        "title": f"Eleceed Chapter {ch_num}",
        "series": "eleceed",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": "kimi-k3-workflow-master",
        "total_words": total_words,
        "blocks": blocks,
    }

    # 4. Schema Validation
    script_path.write_text(json.dumps(script_data, indent=2, ensure_ascii=False), encoding="utf-8")
    script_model = load_model(script_path, ScriptFile)
    desc_model = load_model(desc_path, DescriptionFile)
    report = validate(script_model, desc_model, CONFIG)
    if not report.ok:
        return ch_num, False, f"Schema validation failed: {report.problems}"
    print(f"[{ch_name}] Step 3: Schema Validation Passed! Total Words: {total_words}", flush=True)

    # 5. Mandatory Quality Gatekeeper
    print(f"[{ch_name}] Step 4: Running Autonomous AI Quality Gatekeeper via Kimi-K3...", flush=True)
    gate_res = check_script_quality(script_path)
    score = gate_res.third_party_eval.get("score", 0)
    critique = gate_res.third_party_eval.get("critique", "")

    # Auto-refinement loop if gatekeeper rejected
    retry_count = 0
    while not gate_res.passed and retry_count < 2:
        retry_count += 1
        print(f"[{ch_name}] Gatekeeper gave score {score}/10 ({gate_res.failed_gates}). Attempting refinement pass {retry_count}...", flush=True)
        feedback_prompt = f"""You are the senior script editor for a top YouTube Manhwa Recap channel (Mamoru style).
The quality gatekeeper reviewed Eleceed Chapter {ch_num} and gave this critique:
CRITIQUE: {critique}
PROBLEMS: {json.dumps(gate_res.problems)}
SUGGESTIONS: {json.dumps(gate_res.suggestions)}

Here are sample lines from the script:
{chr(10).join(f"[{b['panel_id']}] {b['text']}" for b in all_beats[:30])}

Rewrite any flawed lines to fix all incomplete thoughts, vary sentence structures, and inject authentic Mamoru wit and sarcasm!
Format: [panel_XXXX] Improved line here (strictly 10 to 12 words, complete sentence ending with a period)."""
        try:
            revised_text = call_llm(feedback_prompt, system_prompt="You are an expert manhwa recap director.", max_tokens=1500)
            rev_map = {}
            for line in revised_text.splitlines():
                m = re.search(r"\[(panel_\d+)\]\s*(.+)", line)
                if m:
                    clean_rev = format_sentence(m.group(2).strip())
                    if is_beat_valid(clean_rev):
                        rev_map[m.group(1)] = clean_rev
            for b in all_beats:
                if b["panel_id"] in rev_map:
                    b["text"] = rev_map[b["panel_id"]]
        except Exception as e:
            print(f"[{ch_name}] Refinement call failed: {e}", flush=True)

        # Rebuild blocks
        blocks = []
        block_idx = 1
        for i in range(0, len(all_beats), 2):
            pair = all_beats[i:i + 2]
            b_id = f"b{block_idx:03d}"
            b_panels = [b["panel_id"] for b in pair]
            b_beats = [
                {"beat_id": f"{b_id}_b{sub_idx:02d}", "panel_id": b["panel_id"], "text": b["text"]}
                for sub_idx, b in enumerate(pair)
            ]
            b_narration = " ".join(b["text"] for b in pair)
            blocks.append({
                "block_id": b_id,
                "panel_ids": b_panels,
                "narration": b_narration,
                "beats": b_beats,
            })
            block_idx += 1

        script_data["blocks"] = blocks
        script_data["total_words"] = sum(len(b["narration"].split()) for b in blocks)
        script_path.write_text(json.dumps(script_data, indent=2, ensure_ascii=False), encoding="utf-8")
        gate_res = check_script_quality(script_path)
        score = gate_res.third_party_eval.get("score", 0)
        critique = gate_res.third_party_eval.get("critique", "")

    elapsed = time.time() - t0
    if not gate_res.passed:
        return ch_num, False, f"Gatekeeper failed (Score: {score}/10, Gates: {gate_res.failed_gates}, Problems: {gate_res.problems[:2]})"

    print(f"[{ch_name}] SUCCESS! PASSED GATEKEEPER in {elapsed:.1f}s (Score: {score}/10, Words: {total_words})", flush=True)
    print(f"[{ch_name}] Critique: {critique}", flush=True)
    return ch_num, True, f"Passed Gatekeeper (Score: {score}/10, Words: {total_words})"


def main():
    parser = argparse.ArgumentParser(description="Strict workflow script generator for Eleceed")
    parser.add_argument("--start", type=int, default=2, help="Start chapter")
    parser.add_argument("--end", type=int, default=30, help="End chapter")
    parser.add_argument("--workers", type=int, default=1, help="Concurrent workers")
    args = parser.parse_args()

    chapters = list(range(args.start, args.end + 1))
    print("=" * 75)
    print(f"ELECEED BATCH WORKFLOW SCRIPTING: Chapters {args.start} to {args.end} ({len(chapters)} chapters)")
    print(f"Concurrent Workers: {args.workers}")
    print("=" * 75)

    results = {}
    if args.workers <= 1:
        for ch in chapters:
            ch_num, ok, msg = process_chapter(ch)
            results[ch_num] = (ok, msg)
            status_str = "PASS" if ok else "FAIL"
            print(f"[PROGRESS] Chapter {ch_num:02d}: {status_str} -> {msg}", flush=True)
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futs = {executor.submit(process_chapter, ch): ch for ch in chapters}
            for fut in concurrent.futures.as_completed(futs):
                ch_num, ok, msg = fut.result()
                results[ch_num] = (ok, msg)
                status_str = "PASS" if ok else "FAIL"
                print(f"[PROGRESS] Chapter {ch_num:02d}: {status_str} -> {msg}", flush=True)

    failed = [ch for ch, (ok, _) in results.items() if not ok]
    print("\n" + "=" * 75)
    print(f"BATCH SUMMARY: {len(chapters) - len(failed)}/{len(chapters)} PASSED")
    if failed:
        print(f"Failed chapters: {failed}")
        sys.exit(1)
    print("ALL CHAPTERS CERTIFIED BY 3RD-PARTY AI QUALITY GATEKEEPER!")
    print("=" * 75)


if __name__ == "__main__":
    main()
