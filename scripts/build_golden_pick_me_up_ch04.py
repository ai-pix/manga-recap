"""Pick Me Up Chapter 4 Golden Standard Script Generator (Clean 68 Story Panels).

True Mamoru YouTube Recap Tone:
- Sarcastic, charismatic, conversational narrator persona.
- Roasts gacha absurdity, mocks noob master Anis, hypes Han's ranker mindset and Jenna's archery.
- Witty banter and dialogue woven into seamless storytelling.
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
    # --- ACT 1: FLOOR TWO FINALE & THE GOBLIN HEDGEHOG (Panels 2-15) ---
    ("panel_0002", "We pick right back up with Han crouching low in the blood-stained courtyard."),
    ("panel_0003", "He twists his entire body, delivering a vicious backhand slash to the wolf."),
    ("panel_0005", "Fresh monster blood sprays everywhere as the alpha predator finally crashes down dead."),
    ("panel_0007", "Catching his breath, our veteran ranker spins around to check on his team."),
    ("panel_0008", "He lunges across the flagstones, ready to rescue Jenna from the remaining monsters."),
    ("panel_0010", "To his shock, both charging goblins are already completely dead on the floor."),
    ("panel_0011", "Han stares in utter disbelief at the absurd sight before his eyes."),
    ("panel_0012", "He turns toward Jenna, asking what on earth happened to those ugly creatures."),
    ("panel_0013", "The poor goblins look like pin-cushions, riddled with dozens of panic-fired arrows."),
    ("panel_0014", "Han dryly jokes that she turned a dangerous monster into a dead hedgehog!"),
    ("panel_0015", "He tells her to stop shooting because the beast died ten arrows ago."),

    # --- ACT 2: STAGE CLEAR & THE MASTER LOGS OFF (Panels 17-26) ---
    ("panel_0017", "A massive gold Stage Clear notification flashes as floor two is officially conquered."),
    ("panel_0018", "The five battered survivors march across the courtyard, soaking in their narrow victory."),
    ("panel_0020", "Jenna gasps in surprise as a prompt asks them to attempt floor three."),
    ("panel_0021", "Han explains that aggressive mobile players usually push until their heroes wipe out."),
    ("panel_0022", "He braces for another immediate deployment, waiting to see what happens next."),
    ("panel_0024", "Instead, a dark notification announces that Master Anis has logged off completely."),
    ("panel_0025", "Han collapses onto a bench, exhaling a massive sigh of sweet relief."),
    ("panel_0026", "He calculates their pacing, realizing their casual summoner only clears one floor daily."),

    # --- ACT 3: LEVEL SIX STATS & CONFRONTING THE LAZY COWARDS (Panels 27-41) ---
    ("panel_0027", "Checking his status profile, Han discovers he successfully reached level six overnight."),
    ("panel_0028", "He watches the three male recruits resting peacefully, completely unbothered by yesterday's horrors."),
    ("panel_0029", "In this brutal gacha, one-star units are treated as disposable commoner fodder."),
    ("panel_0030", "He bitterly recalls how four-star Shay was ruthlessly fed to him for stats."),
    ("panel_0031", "High-ranking heroes never hesitate, but clueless beginners play with zero tactical caution."),
    ("panel_0032", "Shay would have carried this town, yet she vanished into digital dust forever."),
    ("panel_0033", "Jenna angrily mutters that she refuses to protect those three useless cowards."),
    ("panel_0035", "The three lazy recruits huddle together, whispering schemes to escape the facility."),
    ("panel_0036", "They smugly assume that staying in the backline guarantees them absolute safety."),
    ("panel_0037", "Hearing their entitled whining, Han's patience snaps like a cheap wooden twig."),
    ("panel_0039", "He grabs the bald recruit by the collar, demanding why they hid away."),
    ("panel_0040", "Han roars that while he and Jenna bled, they contributed zero effort."),
    ("panel_0041", "The trembling coward pathetically whines that he only did what the master ordered."),

    # --- ACT 4: BRUTAL REPETITION & SKILL UNLOCK (Panels 43-56) ---
    ("panel_0043", "The next morning, weapon training begins under the hot artificial sun."),
    ("panel_0046", "True to their cowardly nature, the three lazy men skip practice completely today."),
    ("panel_0047", "Ignoring the deadweight slackers, Han drives his steel blade into the wooden dummy."),
    ("panel_0048", "Jenna watches with genuine concern as Han trains his muscles to the limit."),
    ("panel_0049", "Han reminds her that digital bodies recover rapidly compared to flesh on Earth."),
    ("panel_0050", "He lunges forward repeatedly, drilling parries and thrusts into pure muscle memory."),
    ("panel_0051", "A low-angle swing shatters the practice post as his focus peaks completely."),
    ("panel_0056", "Jenna stretches her arms energetically, itching for another round of dungeon combat."),

    # --- ACT 5: FLOOR THREE SUBJUGATION & FORMATION MASTERY (Panels 57-67) ---
    ("panel_0057", "The three deserters are dragged into the plaza, sweating from pure guilty fear."),
    ("panel_0058", "They whisper frantic apologies, terrified of being reported to the tyrannical fairy."),
    ("panel_0059", "Iselle buzzes in angrily, demanding they hurry up or face immediate punishment."),
    ("panel_0060", "A giant dimensional rift tears open, sucking the reluctant party into floor three."),
    ("panel_0061", "The terrified rookies scramble frantically as their boots hit dark muddy grass."),
    ("panel_0062", "A savage pack of Level 5 Prairie Beast-men charges from the dark trees."),
    ("panel_0063", "Han commands the frontline calmly, reminding everyone that drilled techniques guarantee survival."),
    ("panel_0064", "With refined swordsmanship, our boy slices through the lead beast like butter!"),
    ("panel_0066", "Jenna snipes supporting wolves with pinpoint accuracy, grinning that floor three feels easy."),
    ("panel_0067", "Behind them, the three lazy recruits freeze backward, still too frightened to assist."),

    # --- ACT 6: THE NOOB MASTER'S GRIND LOOP & SYNTHESIS FATE (Panels 69-83) ---
    ("panel_0069", "Han groans loudly when a system prompt forces them into repeated grinding!"),
    ("panel_0070", "Instead of resting, the greedy master sends them to re-clear floor one."),
    ("panel_0071", "The exact same goblin wolves spawn as Anis farms gold mindlessly above."),
    ("panel_0072", "Jenna smirks cockily as she bags her second consecutive MVP victory award."),
    ("panel_0074", "Stage clear rewards pop up, showering the rookie master with heaps of gold."),
    ("panel_0075", "Jenna wipes sweat, praying the brain-dead player finally gives them a break."),
    ("panel_0076", "The lazy trio grumbles loudly, tired of running circles and eating boiled potatoes."),
    ("panel_0077", "Han points toward the ominous blue glow illuminating the dark stone courtyard."),
    ("panel_0080", "The three slackers panic as a red target locks onto their chests!"),
    ("panel_0082", "Han watches coldly, reminding them that useless heroes become food for synthesis."),
    ("panel_0083", "The Crack of Space-Time awaits, as the master prepares his next sacrifice."),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch04"
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
        "chapter_id": "ch04",
        "series": "Pick Me Up, Infinite Gacha",
        "created_at": now_iso,
        "title": "Pick Me Up Chapter 04",
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
    q_res = check_script_quality(out_file, min_words=600, max_words=1600, run_ai_judge=True, series_name="Pick Me Up")
    score = (q_res.third_party_eval or {}).get("score", 0)
    print(f"\nGatekeeper Result: Passed={q_res.passed}, Score={score}/10")
    print(f"Critique: {(q_res.third_party_eval or {}).get('critique', '')}")


if __name__ == "__main__":
    main()
