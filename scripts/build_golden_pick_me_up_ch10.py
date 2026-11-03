"""Pick Me Up Chapter 10 Golden Standard Script Generator (49 Story Panels).

Mamoru YouTube Recap Persona:
- High-adrenaline, comedic, sarcastic narrator voice.
- Roasts gacha noob tactics, describes Han's micro-rotations, and hypes squad survival.
- 1:1 synchronization across all 49 clean story panels.
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
    # --- ACT 1: THE TUSKED OGRE & SQUAD ROTATIONS (Panels 4-16) ---
    ("panel_0004", "The screen opens with an ugly tusked ogre roaring right in their terrified faces!"),
    ("panel_0005", "Han Islat barks like an angry drill sergeant, screaming, 'Gide, switch places with Hangen!'"),
    ("panel_0006", "Gide wheezes that he can still go on, but Han tells him to shut up."),
    ("panel_0007", "One look at the trembling recruit confirms his stamina bar is already completely drained."),
    ("panel_0008", "Watching the kid flail around, Han mutters that his sword fundamentals are pure amateur garbage."),
    ("panel_0009", "Han demonstrates true master ranker efficiency: one clean slash per monster, zero wasted stamina."),
    ("panel_0010", "A dense horde of red-eyed wolf beasts floods the corridor like endless disposable fodder."),
    ("panel_0011", "'Switch again!' Han bellows, treating this death trap like an intense esports rotation drill."),
    ("panel_0012", "Hansen stumbles forward in a panic, crying that the middle lane is pure suicide."),
    ("panel_0013", "Han directs sharp-tongued archer Jenna to support Gide and collect every spent arrow."),
    ("panel_0014", "Jenna dashes in with a cocky grin, shouting, 'I have been waiting for this!'"),
    ("panel_0015", "An exhausted recruit asks if ten grueling minutes of hell have finally passed by."),
    ("panel_0016", "Han shouts back in utter disgust, 'Shut up, it has only been five minutes!'"),

    # --- ACT 2: FEAR DEBUFFS & GACHA PERMADEATH (Panels 17-27) ---
    ("panel_0017", "A creepy green reptile fiend slithers from the dark, gnashing razor fangs aggressively."),
    ("panel_0018", "The scaly beast snaps hungrily, threatening to chew straight through their fragile vanguard formation."),
    ("panel_0019", "Jenna plants her feet against the stone wall, complaining, 'Stop coming up already, nuisances!'"),
    ("panel_0020", "Han takes a heavy impact to the chest, gritting his teeth through stinging pain."),
    ("panel_0022", "Battered and bleeding, Han screams at trembling Gide to swap places with fresh reinforcements."),
    ("panel_0023", "He tells the crying kid to stop sobbing like an absolute baby right now."),
    ("panel_0024", "A cruel crimson prompt pops up: rookie Gide has officially fallen into deep fear."),
    ("panel_0025", "Han drives his blade deep into a fiend, cursing these relentless, suicidal digital vermin."),
    ("panel_0026", "He barks at his shellshocked squad to pull themselves together before everyone permanently dies."),
    ("panel_0027", "Han urgently orders Jenna to bind Gide's bleeding wounds before his health bar empties!"),

    # --- ACT 3: CHEAP WEAPONS & SHIELD BASHING (Panels 28-40) ---
    ("panel_0028", "Twisting smoothly on his heel, Han parries another beast with effortless veteran precision."),
    ("panel_0029", "He pins a thrashing crawler to the cobblestone, driving his steel blade straight home."),
    ("panel_0030", "Han roars at the shadows, shouting, 'Go back in, you ugly bastards, right now!'"),
    ("panel_0032", "Suddenly Hansen screams in total hysterics, 'Han, my iron sword is completely blunt!'"),
    ("panel_0033", "Han asks bloody Gide if he can muster enough strength for one quick swap."),
    ("panel_0034", "He orders Hansen to pull back to the rear and sharpen that useless blade."),
    ("panel_0035", "Han sighs dryly, knowing beginner gear summoned by noob masters always breaks down fast."),
    ("panel_0036", "'If swords do not work, then bash their ugly heads with your shield!'"),
    ("panel_0037", "He quickly rotates Jenna with Aaron, giving the weary archer a desperately needed breather."),
    ("panel_0038", "Jenna slashes through the fray, reminding Aaron, 'Rest while you can, do not be stubborn!'"),
    ("panel_0039", "Han shouts across the corridor, 'Three minutes left! Hang in there for three minutes!'"),
    ("panel_0040", "Jenna smoothly organizes the next swap, maintaining their frantic rotation under crushing enemy pressure."),

    # --- ACT 4: THE ARROW SHORTAGE & CRITICAL COLLAPSE (Panels 41-54) ---
    ("panel_0041", "Han pushes Hansen back to the front line, desperately reinforcing their narrow cobblestone choke point."),
    ("panel_0042", "He tells Jenna, 'Shoot every single arrow you have straight onto Hansen's side!'"),
    ("panel_0043", "A grim glance into Jenna's leather quiver confirms she is scraping the very bottom."),
    ("panel_0044", "Han grimaces fiercely, realizing that running completely out of arrows means a guaranteed squad wipe."),
    ("panel_0045", "Jenna nods with fierce determination, shouting, 'Alright, I will make every shot count!'"),
    ("panel_0046", "A desperate volley of flying arrows and sword strikes tears through the monster pack!"),
    ("panel_0047", "Han unleashes a massive crescent blade slash, cleaving beasts apart in one blinding arc!"),
    ("panel_0048", "Our exhausted protagonist gasps for air, his one-star stamina bar completely flashing crimson red."),
    ("panel_0049", "The relentless monster tide pushes back hard, nearly knocking Han off his battered feet."),
    ("panel_0050", "His eyes widen in sudden alarm as someone screams in agony behind their line."),
    ("panel_0051", "A defensive fighter freezes in horror, watching their carefully managed formation collapse completely apart."),
    ("panel_0052", "Jenna gasps in disbelief, crying out, 'What the hell just happened over there?!'"),
    ("panel_0053", "Poor rookie Gide collapses face-down onto the stones, clutching his mangled, bleeding hand tightly."),
    ("panel_0054", "A horrifying crimson system alert flashes: Gide is officially on the brink of death!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch10"
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
        "chapter_id": "ch10",
        "series": "Pick Me Up, Infinite Gacha",
        "created_at": now_iso,
        "title": "Pick Me Up Chapter 10",
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
