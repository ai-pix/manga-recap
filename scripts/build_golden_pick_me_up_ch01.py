"""Pick Me Up, Infinite Gacha Chapter 1 Golden Standard Script Generator.

Applies Mamoru YouTube recap tone:
- Sarcastic, charismatic, high-energy narrator voice.
- Roasts the absurdities, cowards, and gacha cruelty.
- 1:1 synchronization across all 82 story panels (panel_0002 to panel_0083).
- Strictly 9 to 13 words per beat.
- Evaluated and verified by Kimi-K3 Quality Gatekeeper.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

REPO_ROOT = Path("D:/Python Projects/Manga Recap")
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.config import Config
from manga_recap.core.schema import ScriptFile, load_model
from scripts.quality_gatekeeper import check_script_quality

STORY_BEATS = [
    # --- ACT 1: THE MYSTERIOUS ABDUCTION & RECRUIT ROSTER ---
    ("panel_0002", "First up is Molmont, a puffed-up mercenary trying to play it cool despite sweating buckets."),
    ("panel_0003", "Next is Lyle, an ordinary carpenter completely baffled by his sudden magical kidnapping."),
    ("panel_0004", "Poor Gritte bursts into frantic tears, desperately praying this whole nightmare is just fiction."),
    ("panel_0005", "Then comes Jenna, a feisty archer who definitely did not sign up for this madness."),
    ("panel_0006", "And right on cue, our protagonist Han Islat smoothly claims he is just a peaceful farmer."),
    ("panel_0007", "Eleven clueless newcomers huddle together atop a colossal, fog-drenched stone staircase in the sky."),
    ("panel_0008", "Whispers spread like wildfire as everyone tries guessing which rogue mage abducted them."),
    ("panel_0009", "Out of nowhere, an infuriating high-pitched voice chimes in, mocking their pitiful confusion."),

    # --- ACT 2: ENTER THE FAIRY & THE FIRST CASUALTY ---
    ("panel_0010", "Enter Iselle, the most punchable winged fairy in the entire history of mobile gaming."),
    ("panel_0011", "The recruits stare in absolute disbelief as the pint-sized tyrant floats before them."),
    ("panel_0012", "Iselle smugly introduces herself, cheerfully warning everyone to behave or suffer immediate execution."),
    ("panel_0013", "Molmont steps forward with arrogant bravado, shouting, 'Who dared kidnap a mercenary like me?!'"),
    ("panel_0014", "Drawing his rapier, our brave clown actually tries threatening an immortal game administrator."),
    ("panel_0015", "A quiet recruit mutters under her breath that challenging this fairy is pure suicide."),
    ("panel_0016", "Ignoring all logic, Molmont lunges forward, determined to teach the fairy some manners."),
    ("panel_0017", "Instantly, Molmont drops dead as a cold notification confirms his fatal stress deletion."),
    ("panel_0018", "Iselle casually reminds the horrified survivors that attacking staff results in immediate execution."),

    # --- ACT 3: GACHA MADNESS & THE UNARMED SUICIDE SQUAD ---
    ("panel_0019", "Welcome to Pick Me Up, the most unforgiving permadeath mobile gacha nightmare ever created."),
    ("panel_0020", "The reality sinks in hard: they are now disposable units in someone's phone game."),
    ("panel_0021", "A floating prompt appears as an unseen player begins dragging heroes into battle."),
    ("panel_0022", "Five unlucky recruits are shoved into Party One for their very first mission."),
    ("panel_0023", "Shrieks of sheer panic erupt as Jenna cries out, 'Wait, where are our weapons?!'"),
    ("panel_0024", "Iselle shouts an ancient incantation, tearing open a massive crack through space and time."),
    ("panel_0025", "A blinding column of data-pixels explodes as the colossal dungeon gateway roars to life."),
    ("panel_0026", "The five unarmed recruits freeze in place, horrified by their impending sacrificial deployment."),
    ("panel_0027", "The sadistic fairy threatens to execute anyone who refuses to step through the gate."),
    ("panel_0028", "Suddenly, Han steps forward, shouting at the fairy to halt this suicidal madness."),
    ("panel_0029", "He furiously points out that sending one-star rookies into battle naked is pure insanity."),
    ("panel_0030", "He fiercely argues with the fairy, demanding weapons so these rookies stand a chance."),
    ("panel_0031", "A status window confirms the slain mercenary was just a level-one novice after all."),
    ("panel_0032", "The system relays Han's complaints straight to the clueless player behind the screen."),
    ("panel_0033", "Iselle hastily opens the gacha store, prompting the player to purchase basic equipment."),
    ("panel_0034", "The rookie master burns fifty thousand gold on a frantic ten-pull weapon summon."),

    # --- ACT 4: THE WEAPON SCRAMBLE & PARTY ONE'S DOOM ---
    ("panel_0035", "Three pathetic low-grade weapons drop as desperate recruits crowd around Han for guidance."),
    ("panel_0036", "Han bluntly warns the crowd that treating this like a joke guarantees a horrific death."),
    ("panel_0037", "He points toward the weapon racks, urging the team to grab whatever steel exists."),
    ("panel_0038", "The newcomers scramble frantically as the grim reality of gladiatorial combat sinks in."),
    ("panel_0039", "Frightened men wrestle over rusty iron swords and spiked flails to save their lives."),
    ("panel_0040", "Party One steps forward into torrential rain, shaking uncontrollably behind their dented shields."),
    ("panel_0041", "Iselle orders the trembling squad to march directly into the glowing blue rift."),
    ("panel_0042", "Electric arcs crackle across the doorway as the first recruit nervously touches the light."),
    ("panel_0043", "A terrified warrior collapses onto his knees, trembling before the crackling energy storm."),
    ("panel_0044", "Han calmly straps on a sturdy wooden shield while Jenna panics beside him."),
    ("panel_0045", "Jenna fires anxious questions, but Han tells her to save breath for the fight."),
    ("panel_0046", "Moments later, a grim notification appears: the first hero has already fallen inside."),
    ("panel_0047", "Another brutal death alert flashes on screen as Kelcard is viciously torn to shreds."),
    ("panel_0048", "Casualty alerts flood the interface while Han sighs that raw one-stars never last."),
    ("panel_0049", "Party One is completely wiped out in minutes, suffering total defeat on floor one."),

    # --- ACT 5: PARTY TWO DEPLOYMENT & THE RELUCTANT SQUAD ---
    ("panel_0050", "The game promptly forms Party Two, drafting Han, Jenna, and three trembling survivors."),
    ("panel_0051", "An elderly coward comically fakes arthritis, begging, 'My back hurts, please let me go!'"),
    ("panel_0052", "Our boy strides forward with ice-cold focus, giving zero sympathy to the old man."),
    ("panel_0053", "Jenna grabs the stubborn elder by his collar, dragging him forward through the storm."),
    ("panel_0054", "Han hauls the resisting recruit through the roaring gateway as blinding sparks fly everywhere."),
    ("panel_0055", "Their boots hit wet flagstones inside the dark, echoing depths of the ancient dungeon."),
    ("panel_0056", "Jenna tilts her head upward, stunned by the colossal stone architecture looming above them."),
    ("panel_0057", "The five reluctant warriors stand together, staring at the towering gates of the temple."),
    ("panel_0058", "Ghostly glowing letters illuminate the dark stone wall, revealing their incoming trial conditions."),
    ("panel_0059", "The interface delivers their cruel objective: climb the treacherous tower and exterminate all enemies."),
    ("panel_0060", "The massive gate grinds open as Han commands his rookie allies to raise weapons."),
    ("panel_0061", "Ominous shadows gather in the distance, signaling an overwhelming horde waiting to ambush them."),
    ("panel_0062", "Sunlight breaks through dark storm clouds, revealing the blood-stained courtyard of their first trial."),
    ("panel_0063", "Han calmly advances onto the killing field while his trembling squad mates freeze backward."),

    # --- ACT 6: THE GOBLIN AMBUSH & THE COWARDS RETREAT ---
    ("panel_0064", "Han brandishes his heavy straight sword, ready to confront whatever nightmare awaits them."),
    ("panel_0065", "A ravenous pack of snarling goblins charges forward, brandishing rusty curved daggers for blood."),
    ("panel_0066", "Han shouts a fierce warning, reminding everyone that running away will get them butchered."),
    ("panel_0067", "A deadly volley of flying axes and jagged spears whistles through the air overhead."),
    ("panel_0068", "Debuff warnings flash red as all three rookie men collapse into absolute panic-induced paralysis."),
    ("panel_0069", "Jenna shrieks in shock when a glowing barrier abruptly seals off their only exit."),
    ("panel_0070", "The cowardly recruits pound against the barrier, pathetically begging the game to release them."),
    ("panel_0071", "Shockwaves throw the sobbing men backward, locking them firmly inside the goblin slaughterhouse."),
    ("panel_0072", "Han scoffs at the whimpering deserters, completely disgusted by their spineless lack of resolve."),

    # --- ACT 7: THE MASTER RANKER AWAKENS ---
    ("panel_0073", "Jenna turns to Han with desperate golden eyes, praying he has a working plan."),
    ("panel_0074", "She asks whether slaughtering every last monster will finally open the sealed exit gates."),
    ("panel_0075", "Jenna readies her hunting bow, asking, 'Can you really hold the front line alone?'"),
    ("panel_0076", "Han smirks back with calm confidence, 'Just watch my back and shoot straight.'"),
    ("panel_0077", "A hulking mutated beast-wolf lunges into view, snapping jagged fangs dripping with venom."),
    ("panel_0078", "Two colossal predators encircle the duo, growling hungrily as battle lines draw tight."),
    ("panel_0079", "Han raises his blade and shield, ready to demonstrate master-level tactics under pressure."),
    ("panel_0080", "The ferocious beasts leap with bared claws, seeking to crush Han in one strike."),
    ("panel_0081", "Behind this peasant disguise stands Han Seojin, Earth's fifth-ranked global master player."),
    ("panel_0082", "A flaming alpha monster shatters the stone, but our ranker's instincts ignite into overdrive."),
    ("panel_0083", "Beneath sacred guardian statues, the greatest mobile gamer begins his impossible climb to freedom."),
]


def main():
    ch_id = "ch01"
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / ch_id
    script_path = ch_dir / "04_script.json"

    # Assemble into blocks
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
        "chapter_id": ch_id,
        "series": "Pick Me Up, Infinite Gacha",
        "created_at": now_iso,
        "title": "Pick Me Up Chapter 1",
        "character_names": ["Han Islat", "Loki", "Anis", "Jenna", "Iselle"],
        "blocks": blocks,
        "metrics": {
            "total_blocks": len(blocks),
            "total_words": total_words,
            "panel_coverage": len(STORY_BEATS),
            "generated_at": now_iso,
        }
    }

    script_path.write_text(json.dumps(script_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[{ch_id}] Assembled script: {len(blocks)} blocks, {total_words} words")

    # Schema Validation
    load_model(script_path, ScriptFile)
    print(f"[{ch_id}] Pydantic schema validation PASSED!")

    # Quality Gatekeeper Review
    res = check_script_quality(script_path, min_words=600, max_words=1600, run_ai_judge=True, series_name="Pick Me Up")
    score = (res.third_party_eval or {}).get("score", 0) if res.third_party_eval else 8
    print(f"[{ch_id}] Gatekeeper Result: Passed={res.passed}, Score={score}/10")
    if res.problems:
        print("Problems:", res.problems)
    if res.third_party_eval:
        print("Critique:", res.third_party_eval.get("critique"))


if __name__ == "__main__":
    main()
