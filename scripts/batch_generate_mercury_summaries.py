"""Batch generate Mercury-3 big-picture narrative summaries for Overgeared chapters.

Covers Chapters 02 to 30:
1. Audits & prunes non-story artifacts in 03_descriptions.json.
2. Extracts clean story panel contexts.
3. Calls Mercury-3 (Inception Labs) to generate 04_summary_mercury.md.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters" / "overgeared"
SERIES_BIBLE_PATH = REPO_ROOT / "data" / "series" / "overgeared" / "series.md"

load_dotenv()
load_dotenv(REPO_ROOT / "config" / ".env")

MERCURY_API_KEY = os.getenv("MERCURY_AI_API_KEY")
MERCURY_BASE_URL = os.getenv("MERCURY_AI_BASE_URL", "https://api.inceptionlabs.ai/v1")


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
        "max_tokens": 1600,
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
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                msg = data["choices"][0]["message"]
                content = msg.get("content")
                if not content:
                    raise RuntimeError(f"Mercury-3 returned empty content: {data}")
                return content
        except Exception as e:
            if attempt == 3:
                raise
            print(f"  [Mercury retry {attempt}/3]: {e}")
            time.sleep(3.0 * attempt)


def process_summary(ch_name: str, force: bool = False) -> bool:
    ch_dir = CHAPTERS_ROOT / ch_name
    desc_path = ch_dir / "03_descriptions.json"
    summary_path = ch_dir / "04_summary_mercury.md"

    if not desc_path.exists():
        print(f"[{ch_name}] Error: {desc_path} missing.")
        return False

    if summary_path.exists() and not force:
        words = len(summary_path.read_text(encoding="utf-8").split())
        if words > 100:
            print(f"[{ch_name}] Already exists -> {summary_path.name} ({words} words). Skipping.")
            return True

    pruned, active = audit_and_prune_panels(desc_path)
    desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
    title = desc_data.get("title", f"Overgeared {ch_name}")
    panels = [p for p in desc_data.get("panels", []) if not p.get("is_credits_or_ad")]

    series_bible = SERIES_BIBLE_PATH.read_text(encoding="utf-8") if SERIES_BIBLE_PATH.exists() else ""

    panel_contexts = []
    for p in panels:
        who = ", ".join(p.get("characters", [])) if p.get("characters") else "nobody"
        line = f"[{p['panel_id']}] {who} | Setting: {p.get('setting') or 'N/A'} | Action: {p.get('action')}"
        if p.get("speech_bubbles"):
            line += f" | Dialogue: {' // '.join(p['speech_bubbles'])}"
        panel_contexts.append(line)

    panels_text = "\n".join(panel_contexts)

    mercury_system = (
        "You are an elite narrative architect and story analyst for top-tier manhwa recap channels (like Mamoru Manhwa). "
        "Analyze the plot progression, comedic moments, character motivations, emotional hype, and future story hooks."
    )
    mercury_prompt = f"""You are analyzing {title} of Overgeared.

### SERIES CONTEXT:
{series_bible}

### STORY PANEL SEQUENCE ({len(panels)} panels):
{panels_text}

### YOUR TASK:
Provide a deep, insightful narrative summary of this chapter for a YouTube recapper:
1. Core Plot & Turning Points: Detailed breakdown from start to climax to resolution.
2. Character Dynamics & Subtext: Grid's mindset, comedic reactions, greed vs determination, and interactions with NPCs/players.
3. Key Climax & Emotional / Hype Beats: The biggest visual and emotional payoffs.
4. Recapper Hooks & Foreshadowing: How the narrator should set up cliffhangers, running jokes, and future callbacks.
"""
    print(f"[{ch_name}] Calling Mercury-3 ({active} story panels, {pruned} pruned)...", end="", flush=True)
    t0 = time.time()
    summary_text = call_mercury(mercury_prompt, mercury_system)
    elapsed = time.time() - t0
    summary_path.write_text(summary_text, encoding="utf-8")
    words = len(summary_text.split())
    print(f" Done in {elapsed:.1f}s ({words} words) -> {summary_path.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch generate Mercury-3 summaries")
    parser.add_argument("--from-ch", type=int, default=2, help="Start chapter (default: 2)")
    parser.add_argument("--to-ch", type=int, default=30, help="End chapter (default: 30)")
    parser.add_argument("--force", action="store_true", help="Force regenerate existing summaries")
    args = parser.parse_args()

    targets = [f"ch{i:02d}" for i in range(args.from_ch, args.to_ch + 1)]
    print("=======================================================")
    print(f"STARTING MERCURY-3 BATCH SUMMARY: {len(targets)} CHAPTERS ({targets[0]} to {targets[-1]})")
    print("=======================================================")

    successes = []
    failures = []
    t_start = time.time()

    for idx, ch in enumerate(targets, 1):
        print(f"[{idx}/{len(targets)}] ", end="")
        try:
            ok = process_summary(ch, force=args.force)
            if ok:
                successes.append(ch)
            else:
                failures.append(ch)
        except Exception as e:
            print(f"[{ch}] ERROR: {e}")
            failures.append(ch)
        # Small breath between API calls
        time.sleep(1.0)

    total_time = time.time() - t_start
    print("\n=======================================================")
    print(f"PHASE 1 FINISHED IN {total_time:.1f}s ({total_time/60:.1f} mins)")
    print(f"Successfully generated: {len(successes)} chapters")
    if failures:
        print(f"Failed chapters: {failures}")
    print("=======================================================")


if __name__ == "__main__":
    main()
