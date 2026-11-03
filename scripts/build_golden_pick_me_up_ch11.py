"""Pick Me Up Chapter 11 Golden Standard Script Generator (53 Story Panels).

Mamoru YouTube Recap Persona:
- High-adrenaline, comedic, sarcastic narrator voice.
- Roasts gacha noob tactics, describes the brutal permadeath of Gide and Hansen, and hypes the high-wall defense!
- 1:1 synchronization across all 53 clean story panels.
- Strictly 10 to 14 words per beat.
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
    # --- ACT 1: GIDE'S FALL & CHAOTIC ROTATION (Panels 3-15) ---
    ("panel_0003", "We jump straight back into pure chaos as Jenna stammers in complete disbelief!"),
    ("panel_0004", "Rookie Gide lies motionless face-down on the stones, his life bar flashing crimson."),
    ("panel_0005", "Han curses through gritted teeth, realizing their narrow frontline defense is collapsing fast."),
    ("panel_0006", "Jenna panics over Gide's body, terrified that pulling the blade out kills him."),
    ("panel_0007", "Hansen desperately begs fallen Gide for just thirty seconds of relief rotation time."),
    ("panel_0008", "A snarling green wolf beast leaps from the darkness with razor fangs bared!"),
    ("panel_0009", "Han absorbs a punishing claw slash, his one-star body shuddering from raw impact."),
    ("panel_0010", "He roars through the blinding pain, driving his sword directly into monster flesh!"),
    ("panel_0011", "Han barks urgent orders, shouting, 'Hangen, reinforce the left flank immediately right now!'"),
    ("panel_0012", "A cold system notification confirms Gide's soul has officially returned to the goddess."),
    ("panel_0013", "Hangen acknowledges the order with a panicked scream, stepping into the bloodsoaked gap."),
    ("panel_0014", "Han yells at trembling Jenna, 'Gide is already dead, help us over here!'"),
    ("panel_0015", "Han braces his heavy iron shield, holding off another pack of howling fiends."),

    # --- ACT 2: HANSEN'S PERMADEATH & THE HIGH WALL RETREAT (Panels 17-30) ---
    ("panel_0017", "Han roars that killing one more monster matters infinitely more than mourning corpses."),
    ("panel_0018", "A system announcement flashes that heroic souls are awakening inside the town facilities."),
    ("panel_0019", "Han scoffs dryly, muttering that awakenings mean nothing if everyone dies down here."),
    ("panel_0020", "Hansen screams in agony as a monster's fangs pierce straight through his shoulder!"),
    ("panel_0021", "A status window reveals Hansen is heavily bleeding, his stamina draining to zero."),
    ("panel_0022", "Collapsing onto the flagstones, Hansen sobs desperately, 'Hyung-nim, please save my life!'"),
    ("panel_0023", "The terrified rookie shrieks his master's name as monsters drag him into darkness."),
    ("panel_0025", "Han grits his teeth in grim silence, powerless to stop the cruel slaughter."),
    ("panel_0027", "Hansen's desperate cries echo across the corridor as monsters rip through his armor."),
    ("panel_0028", "Han rallies the survivors, shouting, 'Jenna, Aaron, stick close! We must survive!'"),
    ("panel_0030", "A second death notification flashes: Hansen has permanently returned to the goddess forever."),

    # --- ACT 3: SCALING THE WALL & AARON'S RESCUE (Panels 31-45) ---
    ("panel_0031", "Jenna asks in terror if they are all doomed, but Han snaps back!"),
    ("panel_0032", "Spotting high ground, Han orders Jenna to scramble up the ruined stone wall!"),
    ("panel_0033", "Jenna hesitates in shock, asking if he wants her to run away alone."),
    ("panel_0034", "Two vicious green monsters lunge forward, trying to cut off their escape route."),
    ("panel_0035", "Han bellows at the squad, warning them to avoid getting cornered at all!"),
    ("panel_0036", "Jenna scrambles over the wooden ledge safely, shouting down, 'I am up, hurry!'"),
    ("panel_0037", "Han shoves Aaron forward, commanding the young spearman to grab Jenna's outstretched hand."),
    ("panel_0038", "Aaron lunges toward the ledge, desperately reaching upward with all his remaining strength."),
    ("panel_0039", "A shadowy creature darting from the mist lunges straight for Aaron's trailing boots!"),
    ("panel_0040", "The green lizard beast lands a heavy blow, making Aaron scream in agony!"),
    ("panel_0041", "Han lunges downward through the chaos, shouting, 'Jenna, hold on to him tightly!'"),
    ("panel_0042", "A tight profile shows Han locking eyes on the monster clamping Aaron's ankle."),
    ("panel_0043", "Han slashes his sword violently, severing the monster's claw with one clean stroke!"),
    ("panel_0045", "Jenna heaves Aaron upward while a red alert warns Aaron is near death."),

    # --- ACT 4: THE THIRTY-SECOND STAND & DESPERATE SURVIVAL (Panels 46-60) ---
    ("panel_0046", "A dense swarm of monsters begins climbing over each other like rabid zombies!"),
    ("panel_0047", "Han commands Jenna to grab Aaron's spear and thrust down at climbing heads."),
    ("panel_0048", "Both warriors fight back-to-back atop the narrow ledge, giving zero ground to invaders."),
    ("panel_0049", "Jenna shrieks in absolute terror, 'I lost the spear, what do I do?!'"),
    ("panel_0050", "A giant insectoid claw swings up, threatening to drag them down into darkness."),
    ("panel_0051", "Han shouts across the howling storm, 'Just thirty seconds! Hold on thirty seconds!'"),
    ("panel_0052", "A massive fanged abomination lunges upward, jaws snapping inches from Han's battered chest."),
    ("panel_0053", "The monster's gaping maw dives forward, threatening to devour our hero completely whole."),
    ("panel_0054", "A violent strike lands with crushing velocity, sending shockwaves through Han's weary frame."),
    ("panel_0055", "Han coughs up dark blood, his one-star HP bar hovering dangerously above zero."),
    ("panel_0056", "Taking another punishing blow across the chest, Han refuses to drop his guard."),
    ("panel_0057", "A grotesque goblin-like fiend sneers victoriously, thinking the kill is finally secured today."),
    ("panel_0058", "Han glares through crimson sweat, his stubborn master ranker pride burning fiercely bright."),
    ("panel_0059", "He growls through cracked teeth, 'You ugly bastards are not taking me down!'"),
    ("panel_0060", "Han delivers a bone-shattering counter punch straight into the beast's hideous snarling snout!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch11"
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
                    {"beat_id": f"{block_id}_b00", "panel_id": pid1, "text": t1},
                ]
            })
            b_idx += 1
            i += 1

    total_words = sum(len(b["narration"].split()) for b in blocks)
    now_iso = datetime.now(timezone.utc).isoformat()
    script_data = {
        "chapter_id": "ch11",
        "series": "Pick Me Up, Infinite Gacha",
        "created_at": now_iso,
        "title": "Pick Me Up Chapter 11",
        "character_names": ["Han Islat", "Loki", "Gide", "Jenna", "Hansen", "Aaron", "Anis"],
        "blocks": blocks,
        "metrics": {
            "total_blocks": len(blocks),
            "total_words": total_words,
            "panel_coverage": len(STORY_BEATS),
            "generated_at": now_iso,
        }
    }

    out_file.write_text(json.dumps(script_data, indent=2, ensure_ascii=False), encoding="utf-8")
    load_model(out_file, ScriptFile)
    print(f"Wrote {out_file.name}: {len(blocks)} blocks, {total_words} words, {len(STORY_BEATS)} beats")

    # Evaluate with Kimi-K3 Quality Gatekeeper
    res = check_script_quality(out_file, min_words=450, max_words=1600, run_ai_judge=True, series_name="Pick Me Up")
    eval_res = res.third_party_eval or {}
    score = eval_res.get("score", 0)
    print(f"=== QUALITY GATE RESULT: {'PASSED' if res.passed else 'FAILED'} (Score: {score}/10) ===")
    print(f"Critique: {eval_res.get('critique')}")
    if res.problems:
        print(f"Problems: {res.problems}")


if __name__ == "__main__":
    main()
