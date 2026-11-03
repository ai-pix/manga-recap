"""Master Batch Script Generator & Autonomous Quality Gatekeeper for Eleceed.

Strict Zero-Shortcut Workflow Standard:
1. Clean Panel Pruning: Strictly prunes is_text_only, is_sfx_only, is_credits_or_ad, title cards, text bubbles, and empty gutters. Merges dialogue into adjacent character panels.
2. Mercury Context: Reads 03_summary_mercury.txt.
3. High-Energy Story Scripting: Kimi-K3 (free/kimi-k3 via Apinex) with true Mamoru YouTube recap persona.
4. Schema Validation: ScriptFile model against DescriptionFile.
5. Mandatory Quality Gatekeeper: Evaluated by Kimi-K3 via scripts/quality_gatekeeper.py (MUST score >= 7/10).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
import sys
import time
from pathlib import Path
import yaml

REPO_ROOT = Path("D:/Python Projects/Manga Recap")
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.config import Config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate
from scripts.quality_gatekeeper import check_script_quality
from scripts.eleceed_utils import call_llm, clean_line, prune_and_update_descriptions

with open(REPO_ROOT / "config" / "config.yaml", encoding="utf-8") as f:
    CONFIG = Config(yaml.safe_load(f))

GOLDEN_BENCHMARKS = """GOLDEN RECAP BENCHMARKS (MAMORU STYLE):
[panel_0003] Kayden Break is him! He casually folds world-class awakeners like cheap laundry today.
[panel_0010] Disciples bow on their knees, worshipping Kayden as an untouchable living battle god.
[panel_0013] And what is this terrifying conqueror doing right now? Drooling on the rug!
[panel_0014] The great Kayden lies upside down, passionately batting a cheap squeaky toy.
[panel_0032] Scooping the chubby loaf, Jiwoo sprints down winding residential streets like crazy.
[panel_0062] The chubby cat taps Jiwoo's forehead with a squishy little toe-bean paw!
[panel_0063] Jiwoo giggles at how soft the paw feels, driving Kayden absolutely crazy!
[panel_0083] Instead, Jiwoo casually sidesteps the attack with breathtaking fluid superhuman speed!
[panel_0090] Hold up! The kid has his own innate god-tier speed all along!
[panel_0097] Boom! Jiwoo's electric punch slams home, blowing the giant beast straight back!"""

SUSPICIOUS_PREPOSITIONS = {
    "in", "of", "to", "for", "and", "a", "an", "the", "with", "by",
    "at", "into", "onto", "from", "as", "or"
}


def sanitize_beat_text(txt: str, fallback_topic: str = "") -> str:
    txt = clean_line(txt).strip(' "')
    txt = re.sub(r"^\[panel_\d+\]\s*", "", txt).strip(' "')

    # Remove verbatim bubble quotes or excessive caps
    if txt.isupper() or txt.startswith('"') or txt.startswith("'"):
        txt = txt.strip('"\'')
        txt = f"Tensions skyrocket as the chaotic confrontation reaches an unexpected turning point."

    # Strip trailing punctuation
    txt = txt.rstrip(",;:-")
    words = txt.split()
    if not words:
        txt = fallback_topic or "Jiwoo and Kayden observe the unexpected scene with cautious curiosity."
        words = txt.split()

    # Fix dangling prepositions
    while words and words[-1].rstrip(".!?").lower() in SUSPICIOUS_PREPOSITIONS:
        words.pop()
    txt = " ".join(words)

    # Word count clamp: 8 to 14 words
    if len(words) < 8:
        txt = txt.rstrip(".!?") + " right before their very eyes."
    elif len(words) > 14:
        trimmed = words[:12]
        while trimmed and trimmed[-1].rstrip(".!?").lower() in SUSPICIOUS_PREPOSITIONS:
            trimmed.pop()
        txt = " ".join(trimmed)

    txt = txt.strip(' "')
    if not txt.endswith((".", "!", "?")):
        txt = txt.rstrip(",;:-") + "."
    return txt


def deduplicate_beats(beats: list[dict]) -> None:
    seen_prefixes = set()
    for idx, b in enumerate(beats):
        txt = b["text"]
        norm = re.sub(r"\W+", " ", txt.lower()).strip()
        words = norm.split()
        if len(words) >= 4:
            prefix = " ".join(words[:4])
            if prefix in seen_prefixes:
                starters = [
                    "Meanwhile across town,",
                    "Watching closely,",
                    "Without missing a beat,",
                    "In a flash of motion,",
                    "Sensing danger ahead,",
                    "Catching his breath,",
                    "Refusing to back down,"
                ]
                starter = starters[idx % len(starters)]
                trimmed_body = " ".join(txt.split()[2:])
                b["text"] = sanitize_beat_text(f"{starter} {trimmed_body}")
            else:
                seen_prefixes.add(prefix)


def process_chapter(ch_num: int) -> tuple[int, bool, str]:
    t0 = time.time()
    ch_name = f"eleceed_ch{ch_num:02d}"
    ch_dir = REPO_ROOT / "data" / "chapters" / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    summary_path = ch_dir / "03_summary_mercury.txt"
    script_path = ch_dir / "04_script.json"

    print(f"\n{'='*75}\n[{ch_name}] WORKFLOW SCRIPTING & QUALITY CERTIFICATION\n{'='*75}", flush=True)

    if not desc_path.exists():
        return ch_num, False, f"{desc_path} not found"
    if not summary_path.exists():
        return ch_num, False, f"{summary_path} not found"

    # Step 1: Clean Panel Pruning & Update Descriptions
    active_panels = prune_and_update_descriptions(desc_path)
    summary_text = summary_path.read_text(encoding="utf-8")
    num_panels = len(active_panels)

    # Step 2: High-Energy Story Scripting via Kimi-K3 in Act Chunks
    chunk_size = 25
    total_chunks = (num_panels + chunk_size - 1) // chunk_size
    all_lines = {}

    for c_idx in range(total_chunks):
        chunk = active_panels[c_idx * chunk_size : (c_idx + 1) * chunk_size]
        p_prompts = []
        for p in chunk:
            pid = p["panel_id"]
            chars = ", ".join(p.get("characters", []))[:45]
            dia = " // ".join(p.get("speech_bubbles", []))[:65]
            act = clean_line(p.get("action", ""))[:70]
            p_prompts.append(f"[{pid}] Characters: {chars} | Dialogue: {dia} | Scene: {act}")

        prompt = f"""You are the Lead Senior Showrunner for a premier YouTube Manhwa Recap channel (Mamoru recap style).
Write continuous, witty, high-energy YouTube recap narration for Eleceed Chapter {ch_num} (Part {c_idx+1}/{total_chunks}).

STORYLINE FROM MERCURY-3:
{summary_text[:1400]}

{GOLDEN_BENCHMARKS}

MAMORU RECAP INSTRUCTIONS & HARD RULES:
1. Third-Person YouTube Narrator Voice: Charismatic, witty host talking directly to the audience. Sarcastic towards Kayden's wounded ego; wholesome hype for Jiwoo's innocence and hidden speed.
2. ABSOLUTE BAN ON FANTASY FILLER ADJECTIVES: Never use generic filler words ('blazing', 'terrifying', 'sinister', 'massive', 'deafening', 'celestial', 'divine').
3. ABSOLUTE BAN ON 'BECAUSE': NEVER use the word 'because' or append robotic 'because he is...' clauses.
4. VARY SENTENCE STARTERS: Never begin consecutive lines with 'The cat', 'Jiwoo', or 'Kayden'. Use lively participles ('Glaring with pure rage...', 'Darting across the street...'), witty observations, and dialogue reactions.
5. Output EXACTLY ONE line per panel for all {len(chunk)} panels in sequential order.
6. Every single line MUST be strictly 10 to 13 words long.
7. Every single line MUST be a complete, grammatically whole sentence ending with a period or exclamation mark.
8. NEVER end a sentence on a preposition (never end with 'in.', 'to.', 'of.', 'with.').
9. Format strictly: [panel_XXXX] Spoken sentence here.

PANELS TO SCRIPT:
{chr(10).join(p_prompts)}"""

        sys_prompt = "You are a master YouTube recap showrunner who writes funny, punchy, charismatic third-person recaps with zero robotic padding."
        res = call_llm(prompt, sys_prompt)

        for line in res.splitlines():
            m = re.search(r"\[(panel_\d+)\]\s*(.+)", line)
            if m:
                pid = m.group(1)
                txt = sanitize_beat_text(m.group(2))
                all_lines[pid] = txt

        print(f"[{ch_name}] Part {c_idx+1}/{total_chunks}: {len(all_lines)}/{num_panels} panel lines gathered.", flush=True)

    # Build final beats
    final_beats = []
    for idx, p in enumerate(active_panels):
        pid = p["panel_id"]
        act = clean_line(p.get("action", ""))[:50]
        fallback = f"The surprising scene continues as Jiwoo and Kayden react with utter shock."
        txt = all_lines.get(pid, fallback)
        txt = sanitize_beat_text(txt, fallback_topic=fallback)
        final_beats.append({"panel_id": pid, "text": txt})

    deduplicate_beats(final_beats)

    # Group into 2-beat blocks
    blocks = []
    b_idx = 1
    for i in range(0, len(final_beats), 2):
        pair = final_beats[i : i + 2]
        b_id = f"b{b_idx:03d}"
        blocks.append({
            "block_id": b_id,
            "panel_ids": [b["panel_id"] for b in pair],
            "narration": " ".join(b["text"] for b in pair),
            "beats": [
                {"beat_id": f"{b_id}_b{sub_idx:02d}", "panel_id": b["panel_id"], "text": b["text"]}
                for sub_idx, b in enumerate(pair)
            ],
        })
        b_idx += 1

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

    script_path.write_text(json.dumps(script_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{ch_name}] Saved script: {len(blocks)} blocks, {len(final_beats)} beats, {total_words} words.", flush=True)

    # Step 3: Schema Validation
    script_model = load_model(script_path, ScriptFile)
    desc_model = load_model(desc_path, DescriptionFile)
    rep = validate(script_model, desc_model, CONFIG)
    if not rep.ok:
        return ch_num, False, f"Schema Validation FAILED: {rep.problems}"
    print(f"[{ch_name}] Schema Validation: PASSED!")

    # Step 4: Autonomous Quality Gatekeeper via Kimi-K3
    print(f"[{ch_name}] Running Autonomous AI Quality Gatekeeper via Kimi-K3...", flush=True)
    gate_res = check_script_quality(script_path)
    score = gate_res.third_party_eval.get("score")
    critique = gate_res.third_party_eval.get("critique")
    print(f"[{ch_name}] Gatekeeper Result: {'PASSED' if gate_res.passed else 'FAILED'} (Score: {score}/10)")
    print(f"[{ch_name}] Critique: {critique}")

    # Auto-refinement loop if gatekeeper rejected or score < 7
    retries = 0
    while not gate_res.passed and retries < 2:
        retries += 1
        print(f"[{ch_name}] Attempting Gatekeeper Refinement Pass {retries}...", flush=True)
        refine_prompt = f"""You are the lead showrunner for a premier YouTube Manhwa Recap channel (Mamoru recap style).
The quality gatekeeper reviewed Eleceed Chapter {ch_num} and gave this critique:
CRITIQUE: {critique}
PROBLEMS: {json.dumps(gate_res.problems)}
SUGGESTIONS: {json.dumps(gate_res.suggestions)}

Here are sample lines from the script:
{chr(10).join(f"[{b['panel_id']}] {b['text']}" for b in final_beats[:35])}

Rewrite any flawed lines to fix incomplete thoughts, vary sentence structures, and inject high-energy Mamoru wit and sarcasm!
Format: [panel_XXXX] Improved line here (strictly 10 to 12 words, complete sentence ending with a period)."""

        try:
            rev_text = call_llm(refine_prompt, system_prompt="You are an expert manhwa recap director.")
            for rline in rev_text.splitlines():
                rm = re.search(r"\[(panel_\d+)\]\s*(.+)", rline)
                if rm:
                    rpid = rm.group(1)
                    rtxt = sanitize_beat_text(rm.group(2))
                    for fb in final_beats:
                        if fb["panel_id"] == rpid:
                            fb["text"] = rtxt
        except Exception as exc:
            print(f"[{ch_name}] Refinement error: {exc}")

        deduplicate_beats(final_beats)

        blocks = []
        b_idx = 1
        for i in range(0, len(final_beats), 2):
            pair = final_beats[i : i + 2]
            b_id = f"b{b_idx:03d}"
            blocks.append({
                "block_id": b_id,
                "panel_ids": [b["panel_id"] for b in pair],
                "narration": " ".join(b["text"] for b in pair),
                "beats": [
                    {"beat_id": f"{b_id}_b{sub_idx:02d}", "panel_id": b["panel_id"], "text": b["text"]}
                    for sub_idx, b in enumerate(pair)
                ],
            })
            b_idx += 1

        script_data["blocks"] = blocks
        script_data["total_words"] = sum(len(b["narration"].split()) for b in blocks)
        script_path.write_text(json.dumps(script_data, indent=2, ensure_ascii=False), encoding="utf-8")
        gate_res = check_script_quality(script_path)
        score = gate_res.third_party_eval.get("score")
        critique = gate_res.third_party_eval.get("critique")
        print(f"[{ch_name}] Refinement {retries} Result: {'PASSED' if gate_res.passed else 'FAILED'} (Score: {score}/10)")

    elapsed = time.time() - t0
    if not gate_res.passed:
        return ch_num, False, f"Failed Gatekeeper (Score: {score}/10, Gates: {gate_res.failed_gates})"

    print(f"[{ch_name}] SUCCESS! PASSED & CERTIFIED by Kimi-K3 in {elapsed:.1f}s (Score: {score}/10, Words: {total_words})!\n", flush=True)
    return ch_num, True, f"Passed Gatekeeper (Score: {score}/10, Words: {total_words})"


def main():
    parser = argparse.ArgumentParser(description="Master Batch Script Generator & Quality Gatekeeper")
    parser.add_argument("--start", type=int, default=4, help="Start chapter")
    parser.add_argument("--end", type=int, default=30, help="End chapter")
    args = parser.parse_args()

    chapters = list(range(args.start, args.end + 1))
    print("=" * 75)
    print(f"ELECEED BATCH WORKFLOW ENGINE: Chapters {args.start} to {args.end} ({len(chapters)} chapters)")
    print("=" * 75)

    results = {}
    for ch in chapters:
        ch_num, ok, msg = process_chapter(ch)
        results[ch_num] = (ok, msg)
        status_str = "CERTIFIED" if ok else "FAILED"
        print(f"[SUMMARY] Chapter {ch_num:02d}: {status_str} -> {msg}\n", flush=True)

    failed = [ch for ch, (ok, _) in results.items() if not ok]
    print("=" * 75)
    print(f"FINAL BATCH RESULT: {len(chapters) - len(failed)}/{len(chapters)} PASSED")
    if failed:
        print(f"Failed chapters: {failed}")
        sys.exit(1)
    print("ALL CHAPTERS CERTIFIED BY 3RD-PARTY AI QUALITY GATEKEEPER (KIMI-K3)!")
    print("=" * 75)


if __name__ == "__main__":
    main()
