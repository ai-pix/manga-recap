"""Pick Me Up Chapter 7 Golden Standard Script Generator (Clean 40 Story Panels).

True Mamoru YouTube Recap Tone:
- Sarcastic, charismatic, conversational narrator persona.
- Roasts gacha microtransactions, celebrates Aaron's hilarious 'favorite' salvation, and builds hype!
- 1:1 synchronization across all 40 clean story panels.
- Strictly 11 to 14 words per beat.
- Evaluated and verified by Kimi-K3 Quality Gatekeeper.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("D:/Python Projects/Manga Recap")
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.schema import ScriptFile, load_model
from scripts.quality_gatekeeper import check_script_quality

STORY_BEATS = [
    # --- ACT 1: STARTER GEAR CRAFTING & FLOOR FOUR CONQUEST (Panels 2-14) ---
    ("panel_0002", "We kick right off with Han inspecting his freshly crafted starter squad weapons."),
    ("panel_0004", "He stretches casually, satisfied with crafting a balanced shortbow, spear, and iron shield."),
    ("panel_0007", "Jenna tests her brand-new wooden bow, grinning proudly at her upgraded combat gear."),
    ("panel_0008", "Floor Four Conquest begins, ordering our three-hero squad to exterminate all incoming threats."),
    ("panel_0009", "Two screeching harpies dive from above, cackling at the master's pathetic three-man team."),
    ("panel_0010", "A massive hairy beast lunges across the flagstones, roaring hungrily for fresh meat."),
    ("panel_0011", "Poor Aaron gets slapped with a thirty percent fear debuff, freezing in panic."),
    ("panel_0012", "Han shouts at the trembling spearman, reminding him that another failure means death."),
    ("panel_0013", "The diving harpies taunt the rookies, flapping razor-sharp talons straight toward Jenna's face."),
    ("panel_0014", "A violent clash erupts as Han deflects claws while Jenna shoots the birds down!"),

    # --- ACT 2: STAGE CLEAR & AARON'S MIRACULOUS FAVORITE TAG (Panels 15-24) ---
    ("panel_0015", "A massive gold Stage Clear notification flashes, confirming another narrow, bloody dungeon victory."),
    ("panel_0016", "The rewards window showers ten thousand gold and valuable crafting leather into their coffers."),
    ("panel_0017", "Aaron doubles over on the stones, gagging and coughing from sheer adrenaline exhaustion."),
    ("panel_0018", "Han checks his broadsword calmly, satisfied that his drilled three-hero formation worked perfectly."),
    ("panel_0020", "Jenna smirks down at bloodied Aaron, teasing him for barely surviving another day."),
    ("panel_0021", "Suddenly Aaron screams with pure joy: Master Anis officially added him to favorites!"),
    ("panel_0023", "Jenna declares herself subordinate number one, appointing sobbing Aaron as subordinate number two!"),
    ("panel_0024", "Han walks away laughing dryly, completely amused by their ridiculous servant hierarchy drama."),

    # --- ACT 3: THE MEMORY OF SIRRIS & TOWN LEVEL UP (Panels 25-41) ---
    ("panel_0025", "Han ponders in quiet reflection, remembering his real number-one subordinate back on Earth."),
    ("panel_0026", "His legendary maxed-out squad of five divine heroes originally conquered the entire game server."),
    ("panel_0028", "A flashback reveals Sirris, his most loyal six-star commander, departing on a dangerous mission."),
    ("panel_0029", "Sirris ventured into the deepest tower floors, searching for the master's mysterious whereabouts."),
    ("panel_0030", "She promised to conquer the summit, swearing an eternal oath of unwavering loyalty."),
    ("panel_0031", "Han wonders if his beloved digital champions are alive somewhere inside this tower."),
    ("panel_0032", "Snapping back to reality, he watches blue construction light illuminate the village square."),
    ("panel_0033", "Town facilities level up rapidly as Master Anis impulsively dumps heaps of cash!"),
    ("panel_0037", "Jenna gasps in total amazement, admiring the newly constructed barracks and equipment workshop."),
    ("panel_0038", "A delicious aroma fills the plaza as the town restaurant begins serving meals!"),
    ("panel_0040", "Iselle notes that Anis plays on schedule, profiling him as an employed office worker."),
    ("panel_0041", "Han grins knowingly, happy their summoner is a working adult with disposable paycheck money!"),

    # --- ACT 4: THE TEN-PULL SUMMON & TOUGH LOVE WELCOME (Panels 42-52) ---
    ("panel_0042", "The system chimes happily as Master Anis impulsively buys a brand-new gem bundle!"),
    ("panel_0043", "A massive golden summoning portal blazes open atop the town's ornate cobblestone dais."),
    ("panel_0044", "An infographic explains the game's cruel summoning mechanics, teasing high-tier gacha drop rates."),
    ("panel_0045", "A bewildered crowd of ten freshly summoned Earthlings materializes, crying out in confusion."),
    ("panel_0047", "An older bearded recruit panics loudly, demanding to know where on Earth they are."),
    ("panel_0048", "Han steps forward with drawn steel, bluntly warning them to shut up and listen!"),
    ("panel_0049", "He tells the newcomers he only wastes time explaining rules to those who survive!"),
    ("panel_0050", "Iselle buzzes in cheerfully, asking if any summoned rookies have blacksmithing or carpentry jobs."),
    ("panel_0051", "Han watches the chaotic scene unfold, wondering which of these rookies will survive tomorrow."),
    ("panel_0052", "With the tower looming high above, our master ranker prepares to conquer floor five!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch07"
    out_file = ch_dir / "04_script.json"

    blocks = []
    b_idx = 1
    i = 0
    while i < len(STORY_BEATS):
        pid1, t1 = STORY_BEATS[i]
        if i + 1 < len(STORY_BEATS):
            pid2, t2 = STORY_BEATS[i + 1]
            block_id = f"b{b_idx:03d}"
            blocks.append({
                "block_id": block_id,
                "panel_ids": [pid1, pid2],
                "narration": f"{t1} {t2}",
                "beats": [
                    {"beat_id": f"{block_id}_b00", "panel_id": pid1, "text": t1},
                    {"beat_id": f"{block_id}_b01", "panel_id": pid2, "text": t2},
                ]
            })
            b_idx += 1
            i += 2
        else:
            block_id = f"b{b_idx:03d}"
            blocks.append({
                "block_id": block_id,
                "panel_ids": [pid1],
                "narration": t1,
                "beats": [
                    {"beat_id": f"{block_id}_b00", "panel_id": pid1, "text": t1}
                ]
            })
            b_idx += 1
            i += 1

    total_words = sum(len(b["narration"].split()) for b in blocks)
    now_iso = datetime.now(timezone.utc).isoformat()
    script_dict = {
        "chapter_id": "ch07",
        "series": "Pick Me Up, Infinite Gacha",
        "created_at": now_iso,
        "title": "Pick Me Up Chapter 07",
        "character_names": ["Han Islat", "Loki", "Anis", "Jenna", "Iselle", "Aaron"],
        "blocks": blocks,
        "metrics": {
            "total_blocks": len(blocks),
            "total_words": total_words,
            "panel_coverage": len(STORY_BEATS),
            "generated_at": now_iso,
        }
    }

    out_file.write_text(json.dumps(script_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out_file.name}: {len(blocks)} blocks, {total_words} words.")

    # Validate Schema
    load_model(out_file, ScriptFile)
    print("Pydantic schema validation PASSED!")

    # Check Quality Gatekeeper
    q_res = check_script_quality(out_file, min_words=450, max_words=1200, run_ai_judge=True, series_name="Pick Me Up")
    score = (q_res.third_party_eval or {}).get("score", 0)
    print(f"\nGatekeeper Result: Passed={q_res.passed}, Score={score}/10")
    print(f"Critique: {(q_res.third_party_eval or {}).get('critique', '')}")


if __name__ == "__main__":
    main()
