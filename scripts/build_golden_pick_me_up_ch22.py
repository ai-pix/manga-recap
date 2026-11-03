"""Pick Me Up Chapter 22 Golden Standard Script Generator (57 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Describes Han babysitting glass-cannon Eolka, second Berserk activation, solo cavalry kiting, and apocalyptic inferno.
- 1:1 synchronization across all 57 clean story panels.
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
from scripts.batch_generate_pick_me_up_workflow_master import build_script_blocks, format_sentence, clean_and_prune_panels

STORY_BEATS = [
    # Act 1: Babysitting the Glass Cannon (Panels 3-23)
    ("panel_0003", "A chrome-plated mechanical hound lunges forward, welcoming our squad to another brutal dungeon nightmare."),
    ("panel_0004", "Han catches an incoming battle axe on his vambrace, teeth gritted against the impact."),
    ("panel_0005", "Dika scrambles across jagged rocks, baiting goblin archers into shooting their own vanguard."),
    ("panel_0006", "Our master ranker shatters a wolf skull bare-handed, muttering, 'Trash mobs never learn.'"),
    ("panel_0007", "Aaron swings his heavy broadsword in wide arcs, shielding Jenna from flanking infantry."),
    ("panel_0008", "Steel flashes through the dust as Han creates breathing space for his exhausted squad."),
    ("panel_0009", "A charging predator splits down the middle, dissolved by a razor-sharp sword arc."),
    ("panel_0010", "Han wipes sweat from his brow, growling, 'These persistent mutts are wasting my stamina.'"),
    ("panel_0011", "Dika dances around the perimeter, buying precious seconds for their formation to reset."),
    ("panel_0012", "Behind those focused eyes, Loki calculates aggro radius and spell cooldowns with esports precision."),
    ("panel_0014", "Whirling on his heel, Han impales a sneaky stalker creeping into Jenna's blind spot."),
    ("panel_0015", "A sudden shriek makes his stomach drop: someone just broke formation behind him."),
    ("panel_0016", "Look at this madness: Eolka is standing out in the open, chanting without defense!"),
    ("panel_0018", "A golden-armored goblin commander spots the helpless mage, grinning at the free meal."),
    ("panel_0019", "A flame-engulfed cleaver drops toward Eolka's neck while she freezes in sheer panic."),
    ("panel_0020", "Han throws himself over the petrified girl, taking the fiery blade across his back."),
    ("panel_0021", "Pinning her down in the dirt, Han roars, 'Are you trying to commit suicide?!'"),
    ("panel_0022", "Eolka stammers about her wasted mana, but Han points toward the distant tree line."),
    ("panel_0023", "Jenna screams the forest path was locked, but Han refuses to die out here."),

    # Act 2: Dragging the Diva & The Choke Point (Panels 24-31)
    ("panel_0024", "Grabbing Eolka's wrist firmly, Han snaps, 'Start chanting your bombardment the second we enter!'"),
    ("panel_0025", "Skeletal cavalry close the gap while Eolka whines that her delicate hands hurt."),
    ("panel_0026", "Jenna scrambles through the brush, shouting back that the forest route is wide open."),
    ("panel_0027", "The frightened archer waves frantically, screaming for Eolka to get into the trees."),
    ("panel_0028", "Eolka tumbles past the bushes, grumbling that nobody respects a third-circle court mage."),
    ("panel_0029", "Han parries an incoming spear, sneering, 'Dead corpses do not get polite royal service.'"),
    ("panel_0030", "Aaron begs from the tree line, shouting, 'Islat, fall back! You cannot hold alone!'"),
    ("panel_0031", "Han flashes a grim smirk, whispering, 'Go inside, I will handle these fools.'"),

    # Act 3: Solo Berserk Stand & Stamina Crash (Panels 32-47)
    ("panel_0032", "A crimson system banner ignites the sky: Han Islat has entered full Berserk state!"),
    ("panel_0033", "Han grimaces in pain, muttering that popping Berserk twice today will wreck his body."),
    ("panel_0034", "Despite agonizing muscle strain, our ranker holds the choke point so his squad survives."),
    ("panel_0035", "A crazed boar beast thrusts a heavy blunderbuss right into Han's face."),
    ("panel_0036", "Han knocks the barrel aside, letting the thunderous shot blast harmlessly into stone."),
    ("panel_0037", "A skeletal warlord rides in on an armored beast, brandishing a hooked scimitar."),
    ("panel_0038", "Han braces behind his buckler, his teeth clattering against the beast's bone-rattling speed."),
    ("panel_0039", "A horned demon brings down a massive cleave, splitting the rocky ground wide open."),
    ("panel_0040", "Our protagonist pivots on his heel, using veteran footwork to dodge the killing blow."),
    ("panel_0041", "Explosive shockwaves throw Han backward into the dirt, surrounded by raining enemy arrows."),
    ("panel_0042", "Han glares through blood-red eyes, snarling, 'Hit-and-run tactics? You cowards are really annoying me!'"),
    ("panel_0043", "A goblin lancer charges forward on an armored mount, eager to claim Han's head."),
    ("panel_0044", "The beast smashes through crystalline rubble, jaws snapping inches from Han's exposed throat."),
    ("panel_0045", "Han lunges under the jaws, shouting, 'Say goodbye to your precious mobility!'"),
    ("panel_0046", "His blade shears through the beast's legs, sending mount and rider crashing headfirst."),
    ("panel_0047", "A chilling red prompt appears: Berserk has expired, and Han's stamina is completely gone."),

    # Act 4: The Master Ranker Lure & Fiery Retribution (Panels 48-62)
    ("panel_0048", "Fingers trembling around his hilt, Han forces his battered knees to stay upright."),
    ("panel_0049", "Frantic friendly-fire erupts among the monsters, giving our exhausted hero a desperately needed breath."),
    ("panel_0050", "Bludgeons and claws clash together as the bloodthirsty horde fights over the final blow."),
    ("panel_0051", "A multi-headed abomination snaps its jaws, trying to push through the monster pileup."),
    ("panel_0052", "Aaron screams in anguish from the trees, terrified that Han is going to die."),
    ("panel_0053", "Han roars back across the clearing, 'I am grouping them together, shoot your targets!'"),
    ("panel_0054", "Jenna gives the thumbs up through the foliage, yelling, 'Islat, the spell is ready!'"),
    ("panel_0055", "Sliding between two mounted raiders, Han herds twenty bloodthirsty monsters into one tight clump."),
    ("panel_0056", "The greedy monsters trip over one another, walking right into Han's textbook kiting trap."),
    ("panel_0057", "Han throws his body into an ogre captain, locking the cluster in place."),
    ("panel_0058", "Detonating a massive shockwave, Han shouts at the top of his lungs, 'Get lost!'"),
    ("panel_0059", "Eolka hovers above the tree line, conjuring a tempest of raging golden fire."),
    ("panel_0060", "Rune circles illuminate the entire sky as the fire witch unleashes her full fury."),
    ("panel_0062", "Han dives clear of the blast zone as Eolka smirks, whispering one word: 'Ignite.'"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch22"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    # Verify 1:1 match
    panel_pids = [p["panel_id"] for p in panels]
    beat_pids = [pid for pid, _ in STORY_BEATS]
    if panel_pids != beat_pids:
        missing = set(panel_pids) - set(beat_pids)
        extra = set(beat_pids) - set(panel_pids)
        raise ValueError(f"Mismatch in panel IDs! Missing: {missing}, Extra: {extra}")

    # Check word counts
    for pid, txt in STORY_BEATS:
        wc = len(txt.split())
        if wc < 10 or wc > 14:
            raise ValueError(f"Beat [{pid}] has {wc} words (must be 10-14): {txt}")

    script_dict = build_script_blocks(panels, lines_map, "ch22")
    out_file.write_text(json.dumps(script_dict, indent=2, ensure_ascii=False), encoding="utf-8")
    load_model(out_file, ScriptFile)
    print(f"Wrote {out_file.name}: {len(script_dict['blocks'])} blocks, {script_dict['metrics']['total_words']} words, {len(STORY_BEATS)} beats")

    res = check_script_quality(out_file, min_words=450, max_words=1600, run_ai_judge=True, series_name="Pick Me Up")
    eval_res = res.third_party_eval or {}
    score = eval_res.get("score", 0)
    print(f"=== QUALITY GATE RESULT: {'PASSED' if res.passed else 'FAILED'} (Score: {score}/10) ===")
    print("Critique:", eval_res.get("critique"))
    if res.problems:
        print("Problems:", res.problems)
    if res.suggestions:
        print("Suggestions:", res.suggestions)

    if not res.passed or score < 7:
        sys.exit(1)


if __name__ == "__main__":
    main()
