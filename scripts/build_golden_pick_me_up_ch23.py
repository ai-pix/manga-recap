"""Pick Me Up Chapter 23 Golden Standard Script Generator (55 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Covers the chaotic dungeon battle, Eolka's explosive magic, Aaron and Jenna stepping up, Eolka's hilarious glass cannon crash, and the party meta shift.
- 1:1 synchronization across all 55 clean story panels.
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
    # Act 1: The Chaotic Fire Starter (Panels 3-10)
    ("panel_0003", "We kick right off with Han dodging rabid hyenas as Eolka yells, 'Ignite!'"),
    ("panel_0004", "A massive swirling firestorm erupts, forcing Han to dive across the scorched dirt floor!"),
    ("panel_0005", "Han glances back through the smoke, completely stunned by this rookie's absurd firepower!"),
    ("panel_0006", "Flames shoot into the sky around their three-star noble mage like a raid boss."),
    ("panel_0007", "Jenna and Aaron freeze in terror, squealing, 'Wait, is that what real magic does?!'"),
    ("panel_0008", "Dragging his sword, Han roars at his rookie squad to help clear the stragglers!"),
    ("panel_0010", "Lunging with veteran gamer reflexes, Han skewers a leaping beast straight through its chest!"),

    # Act 2: Squad Banter & Frontline Carry (Panels 11-27)
    ("panel_0011", "Stamina drain kicks in hard as heavy beast claws batter against Han's blade!"),
    ("panel_0012", "Gritting his teeth, Han smirks that master ranker micro-footwork always beats brute force!"),
    ("panel_0013", "Han darts past snapping jaws with lightning speed, leaving glowing blue tracer lines behind."),
    ("panel_0014", "Suddenly a surprise kinetic strike rocks the beast, catching our frontline captain off guard."),
    ("panel_0015", "Jenna winks with smug swagger, asking, 'Admit it Han, that was pretty clutch, right?'"),
    ("panel_0016", "Aaron raises his spear proudly, boasting, 'Rest easy captain, I will handle your defense!'"),
    ("panel_0017", "Han chuckles dryly at his carpenter recruit, teasing, 'Look who finally learned some swagger!'"),
    ("panel_0018", "Another wave of armored wolf beasts charges through the dust with ravenous snarls."),
    ("panel_0019", "Jenna leaps through the air like Legolas, sniping a charging goblin beast rider mid-dash!"),
    ("panel_0020", "Her clean defensive sword slash cleaves the ambush, proving Han's brutal boot camp worked!"),
    ("panel_0021", "Aaron delivers a heavy Spartan kick, booting an armored wolf straight across the arena."),
    ("panel_0022", "Eolka hurls a point-blank fireball into an attacking monster's jaws, roasting it into cinders!"),
    ("panel_0023", "A terrifying reptilian demon glares through the smoke, locking its hungry eye onto Eolka."),
    ("panel_0024", "Han drops in from above, splitting the predator's skull with a crushing downward strike!"),
    ("panel_0026", "Jenna collapses on the dirt laughing nervously, admitting that was uncomfortably close to deletion!"),
    ("panel_0027", "The panicked archer points at the firestorm, screaming at Eolka to start running immediately!"),

    # Act 3: Eolka's Ultimate Nuke & The Cavalry Charge (Panels 28-46)
    ("panel_0028", "Eolka raises her slender hand, conjuring a blinding miniature sun of pure concentrated hellfire."),
    ("panel_0029", "The haughty witch shuts her eyes tight, channeling every single drop of her mana."),
    ("panel_0030", "Jenna shrieks in panic, warning that this ultimate spell takes way too long!"),
    ("panel_0031", "A brilliant golden starburst ignites across Eolka's pupil as the spell finally locks on."),
    ("panel_0032", "Han grabs Aaron by the scruff, yelling for everyone to haul ass right now!"),
    ("panel_0033", "Eolka thrusts both palms forward, detonating an inferno that completely wipes the map clean!"),
    ("panel_0034", "Beams of holy destruction obliterate the entire demon cavalry horde into smoking pixel dust!"),
    ("panel_0035", "Massive shockwaves shatter stone pillars, raining blazing boulders across the collapsing dungeon floor."),
    ("panel_0036", "Crouching behind cover, Han grumbles that Eolka's friendly fire is deadlier than enemy mobs!"),
    ("panel_0037", "Han peeks through the smoke, coughing hard while praying the fireworks show finally ended."),
    ("panel_0038", "Suddenly an armored boss charges through the blaze on a massive war wolf!"),
    ("panel_0039", "Eolka screams her transcendence chant, unleashing another catastrophic tidal wave of roaring flame!"),
    ("panel_0040", "The entire cavern flashes blinding white as thermal energy disintegrates the elite commander!"),
    ("panel_0041", "A massive burning timber crashes down, burying the last howling demon under smoking debris."),
    ("panel_0044", "Infernal firewalls sweep along the cavern stone, turning this entire raid into an oven."),
    ("panel_0045", "Eolka stands tall amid floating embers, looking like an untouchable anime villainess conquering worlds."),
    ("panel_0046", "Han raises his battered buckler, barely deflecting the blistering thermal shockwave ripping forward."),

    # Act 4: The 1-Star Reality Check & Party Evolution (Panels 47-61)
    ("panel_0047", "The victory screen announces Stage Clear, pocketing twenty thousand gold and naming Eolka MVP!"),
    ("panel_0048", "Brilliant level up beams shower the squad, boosting their stats by one single point."),
    ("panel_0049", "Aaron stammers in disbelief, marveling that twenty elite goblin raiders just got erased instantly."),
    ("panel_0050", "Eolka laughs haughtily behind her hand, gloating that her noble magic is utterly supreme!"),
    ("panel_0051", "Posing with supreme arrogance, she brags, 'Behold the magnificent witch of Count Rivel!'"),
    ("panel_0052", "Mid-sentence, her knees buckle as fatal mana exhaustion chokes her out in hilarious fashion!"),
    ("panel_0053", "Jenna screeches in horror, watching their shiny three-star MVP faceplant unconscious into the dirt!"),
    ("panel_0054", "Han facepalms hard, explaining that Eolka becomes totally paralyzed for sixty seconds after casting."),
    ("panel_0055", "Her stat sheet reveals the hilarious truth: her physical stats are literally sub-one-star garbage!"),
    ("panel_0056", "Han recalls his ranker days, noting these extreme glass cannon units are insanely rare."),
    ("panel_0057", "Han roasts her hilariously, comparing her to a tank completely stripped of armor plating."),
    ("panel_0058", "Aaron gently hoists their sleeping artillery princess onto his shoulders like an expensive vase."),
    ("panel_0059", "Han smirks, admitting that despite her hilarious flaws, her crazy firepower is worth babysitting."),
    ("panel_0060", "Looking at the sky, Han realizes his days carrying this squad alone are over."),
    ("panel_0061", "Four hero cards shine brightly together, hyping up the terrifying tenth floor boss raid!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch23"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch23")
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


if __name__ == "__main__":
    main()
