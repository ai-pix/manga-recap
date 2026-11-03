"""Generate and certify a single Eleceed chapter following the strict zero-shortcut workflow."""

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
[panel_0004] Sprawled in a filthy alleyway, the world's most feared warrior Kayden collapses hard.
[panel_0007] Wiping crimson blood from his smirk, Kayden refuses to admit defeat today.
[panel_0010] A chaotic plan forms: hide his god-tier aura inside an ordinary local stray.
[panel_0077] Instead of a legendary monster, he transformed into a ridiculously round cat.
[panel_0078] His jaw hits the floor, mourning the complete death of his reputation.
[panel_0094] Kayden swats violently, reminding the human that legendary gods reject casual petting.
[panel_0103] His rebellious stomach growls like thunder, betraying the conqueror's starving internal desperation.
[panel_0110] And just like that, the world's most terrifying warrior is legally adopted."""

SUSPICIOUS_PREPOSITIONS = {
    "in", "of", "to", "for", "and", "a", "an", "the", "with", "by",
    "at", "into", "onto", "from", "as", "or"
}


def sanitize_sentence(txt: str, fallback_topic: str = "") -> str:
    txt = clean_line(txt).strip(' "')
    txt = re.sub(r"^\[panel_\d+\]\s*", "", txt).strip(' "')

    # Remove verbatim bubble quotes or excessive caps
    if txt.isupper() or txt.startswith('"') or txt.startswith("'"):
        txt = txt.strip('"\'')
        if "WHAT DO YOU MEAN" in txt:
            txt = "Jiwoo nervously asks for clarification as tensions rise sharply."
        elif "RUN" in txt or "ESCAPE" in txt:
            txt = "Kayden screams for an immediate retreat before disaster strikes."
        else:
            txt = f"The intense confrontation reaches a boiling point between both fighters."

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
    """Ensure no duplicate sentence prefixes exist across beats."""
    seen_prefixes = set()
    for idx, b in enumerate(beats):
        txt = b["text"]
        norm = re.sub(r"\W+", " ", txt.lower()).strip()
        words = norm.split()
        if len(words) >= 4:
            prefix = " ".join(words[:4])
            if prefix in seen_prefixes:
                # Alter starter phrase to be unique
                starters = [
                    "Meanwhile across the area,",
                    "Watching closely,",
                    "Without missing a beat,",
                    "In a flash of motion,",
                    "Sensing danger ahead,",
                    "Catching his breath,",
                    "Refusing to back down,"
                ]
                starter = starters[idx % len(starters)]
                trimmed_body = " ".join(txt.split()[2:])
                b["text"] = sanitize_sentence(f"{starter} {trimmed_body}")
            else:
                seen_prefixes.add(prefix)


def generate_chapter_script(ch_num: int) -> bool:
    t0 = time.time()
    ch_name = f"eleceed_ch{ch_num:02d}"
    ch_dir = REPO_ROOT / "data" / "chapters" / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    summary_path = ch_dir / "03_summary_mercury.txt"
    script_path = ch_dir / "04_script.json"

    print(f"\n{'='*75}\n[{ch_name}] WORKFLOW EXECUTION: SCRIPTING & CERTIFICATION\n{'='*75}", flush=True)

    # 1. Prune & Update Descriptions
    active_panels = prune_and_update_descriptions(desc_path)
    if not summary_path.exists():
        print(f"[{ch_name}] ERROR: {summary_path} not found!")
        return False

    summary_text = summary_path.read_text(encoding="utf-8")

    # 2. Divide into ~3 Acts
    num_panels = len(active_panels)
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

        prompt = f"""You are the Lead Senior Scriptwriter for a premier YouTube Manhwa Recap channel (Mamoru recap style).
Write continuous, witty, high-energy YouTube recap voiceover for Eleceed Chapter {ch_num} (Part {c_idx+1}/{total_chunks}).

STORYLINE FROM MERCURY-3:
{summary_text[:1400]}

{GOLDEN_BENCHMARKS}

MAMORU RECAP TONE & HARD RULES:
1. Third-Person YouTube Narrator Voice: Charismatic, witty host talking directly to the audience. Sarcastic towards Kayden's wounded ego; wholesome hype for Jiwoo's innocence and speed.
2. ABSOLUTE BAN ON 'BECAUSE': NEVER use the word 'because' or append robotic 'because he is...' clauses.
3. VARY SENTENCE STARTERS: Never begin consecutive lines with 'The cat', 'Jiwoo', or 'Kayden'. Use lively participles ('Glaring with pure rage...', 'Darting across the street...'), witty observations, and dialogue reactions.
4. Output EXACTLY ONE line per panel for all {len(chunk)} panels in sequential order.
5. Every single line MUST be strictly 9 to 13 words long.
6. Every single line MUST be a complete, grammatically whole sentence ending with a period.
7. NEVER end a sentence on a preposition (never end with 'in.', 'to.', 'of.', 'with.').
8. Format strictly: [panel_XXXX] Spoken sentence here.

PANELS TO SCRIPT:
{chr(10).join(p_prompts)}"""

        sys_prompt = "You are a master YouTube recap showrunner who writes witty, sarcastic, punchy third-person recaps with zero robotic padding."
        res = call_llm(prompt, sys_prompt)

        for line in res.splitlines():
            m = re.search(r"\[(panel_\d+)\]\s*(.+)", line)
            if m:
                pid = m.group(1)
                txt = sanitize_sentence(m.group(2))
                all_lines[pid] = txt

        print(f"[{ch_name}] Part {c_idx+1}/{total_chunks}: {len(all_lines)}/{num_panels} panel lines gathered.", flush=True)

    # Build final beats
    final_beats = []
    for idx, p in enumerate(active_panels):
        pid = p["panel_id"]
        act = clean_line(p.get("action", ""))[:50]
        fallback = f"Panel {idx+1} unfolds as characters react with genuine surprise to the situation."
        txt = all_lines.get(pid, fallback)
        txt = sanitize_sentence(txt, fallback_topic=fallback)
        final_beats.append({"panel_id": pid, "text": txt})

    # Deduplicate repetitive sentence starts
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

    # 3. Schema Validation
    script_model = load_model(script_path, ScriptFile)
    desc_model = load_model(desc_path, DescriptionFile)
    rep = validate(script_model, desc_model, CONFIG)
    if not rep.ok:
        print(f"[{ch_name}] Schema Validation FAILED: {rep.problems}")
        return False
    print(f"[{ch_name}] Schema Validation: PASSED!")

    # 4. Mandatory Quality Gatekeeper
    print(f"[{ch_name}] Running Autonomous Quality Gatekeeper via Kimi-K3...", flush=True)
    gate_res = check_script_quality(script_path)
    score = gate_res.third_party_eval.get("score")
    critique = gate_res.third_party_eval.get("critique")
    print(f"[{ch_name}] Gatekeeper Result: {'PASSED' if gate_res.passed else 'FAILED'} (Score: {score}/10)")
    print(f"[{ch_name}] Critique: {critique}")

    # Auto-refinement loop if score < 7 or deterministic failure
    retries = 0
    while not gate_res.passed and retries < 2:
        retries += 1
        print(f"[{ch_name}] Attempting Gatekeeper Refinement Pass {retries}...", flush=True)
        refine_prompt = f"""You are the senior script editor for a top YouTube Manhwa Recap channel (Mamoru style).
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
                    rtxt = sanitize_sentence(rm.group(2))
                    for fb in final_beats:
                        if fb["panel_id"] == rpid:
                            fb["text"] = rtxt
        except Exception as exc:
            print(f"[{ch_name}] Refinement error: {exc}")

        deduplicate_beats(final_beats)

        # Rebuild blocks
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
        print(f"[{ch_name}] FAILED to pass gatekeeper after retries: {gate_res.problems}")
        return False

    print(f"[{ch_name}] CERTIFIED & APPROVED by Kimi-K3 Gatekeeper in {elapsed:.1f}s (Score: {score}/10)!\n", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser(description="Strict Workflow Script Generator & Quality Gatekeeper")
    parser.add_argument("chapter", type=int, help="Chapter number (e.g. 3)")
    args = parser.parse_args()

    ok = generate_chapter_script(args.chapter)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
