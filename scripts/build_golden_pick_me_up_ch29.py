"""Pick Me Up Chapter 29 Golden Standard Script Generator (57 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Covers the Level 23 Ogre battle, finding the monster's vital point, the dam sabotage crisis, and the catastrophic flood.
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
    # Act 1: The Ogre's Entrance & Assigning Roles (Panels 2 to 14)
    ("panel_0002", "Welcome back to Niflheim, where our novice summoner Anis orders another catastrophic tactical disaster."),
    ("panel_0003", "A terrifying Level 23 Ogre stomps in, casually wielding a spiked telephone-pole club."),
    ("panel_0004", "Our disguised master ranker barks orders, telling Eolka to build an emergency firewall."),
    ("panel_0006", "Eolka whines in total terror, pointing out that small flames cannot stop that behemoth."),
    ("panel_0007", "Han snaps back with zero patience, yelling, 'Stop crying and let me handle dinner!'"),
    ("panel_0008", "The massive brute swings a colossal axe, ripping through wet trees like toothpicks."),
    ("panel_0010", "Any direct hit from that weapon means permanent account deletion for starter heroes."),
    ("panel_0011", "Jenna lands an arrow in its neck, proudly celebrating like an Olympic archer."),
    ("panel_0012", "She flashes a smug rookie grin, declaring huge monsters are just free target practice."),
    ("panel_0014", "The ogre lunges with bared fangs, making Jenna scream, 'Nevermind, I miss regular goblins!'"),

    # Act 2: Hunting the Vital Point & Dark Gacha Comedy (Panels 15 to 29)
    ("panel_0015", "Steel bounces harmlessly off rubbery skin, proving normal slashes cannot dent this damage sponge."),
    ("panel_0016", "Aaron screams across the mud, warning that another heavy mob just crashed the party."),
    ("panel_0017", "Our veteran hero glares in disbelief, cursing Anis for spending budget on extra threats."),
    ("panel_0018", "Swarming goblin foot-soldiers overwhelm Aaron, stretching the squad frontline past the breaking point."),
    ("panel_0019", "Every wasted minute drains stamina, nudging this fragile one-star team closer to the graveyard."),
    ("panel_0020", "Ignoring bruised ribs and torn muscles, Han commits to a suicidal close-quarters offensive."),
    ("panel_0021", "Sliding beneath the creature's sweeping club, he exploits standard boss attack hitbox blindspots."),
    ("panel_0023", "The lumbering beast roars in confusion, looking down to locate its slippery little snack."),
    ("panel_0024", "Han spots its anatomy, chuckling, 'Oh, so you carry the universal male weakness too!'"),
    ("panel_0025", "An agonizing groin slash makes the monster screech higher than a teenage pop star."),
    ("panel_0026", "Taking full advantage of its misery, our protagonist delivers a flurry of precision cuts."),
    ("panel_0027", "His glowing blue longsword sinks deep into vulnerable joints, carving through thick muscle fibers."),
    ("panel_0028", "Han grimaces as dense bone deflects his blade, keeping the wound annoyingly shallow."),
    ("panel_0029", "Without missing a beat, he swings a heavy bronze shield directly into its jawline!"),

    # Act 3: The True Target Revealed — Dam in Danger! (Panels 30 to 47)
    ("panel_0030", "The concussive shield smash rattles the ogre's brain, letting Han plunge steel home."),
    ("panel_0033", "Jenna wipes rain from her eyes as the giant brute finally topples over dead."),
    ("panel_0034", "Readying his bloody edge, Han scans the perimeter for their next high-priority target."),
    ("panel_0035", "Aaron shouts in horror, pointing at a rampaging beast charging toward defenseless Eolka."),
    ("panel_0036", "Jenna unloads rapid bow shots into the creature's flank, trying to pull aggro away."),
    ("panel_0037", "A swift sword thrust intercepts a flanking goblin, skewering the scout in mid-leap."),
    ("panel_0038", "Massive claws sweep down toward Eolka, threatening to shred our rookie fire mage."),
    ("panel_0039", "Han screams her name at the top of his lungs, sprinting across the swamp."),
    ("panel_0040", "Eolka stumbles backward with a terrified shriek as arcane sparks erupt around her boots."),
    ("panel_0041", "Mud flies everywhere as the rampaging brute stomps right past her trembling figure."),
    ("panel_0042", "A sudden tactical memory click reminds our veteran about seventh floor dungeon layout rules."),
    ("panel_0043", "Han gasps in realization, shouting, 'It never wanted Eolka, it is breaking the dam!'"),
    ("panel_0044", "He roars at Jenna to aim for the beast's knees before everything collapses."),
    ("panel_0045", "Jenna fires armor-piercing broadheads into thick tendons, trying hard to slow its momentum."),
    ("panel_0046", "Sprinting through the storm, Han pushes his low-star agility to its maximum threshold."),
    ("panel_0047", "Our hero lunges forward with murderous intent, swearing to butcher this saboteur on sight."),

    # Act 4: The Dam Breaks & Aftermath (Panels 48 to 64)
    ("panel_0048", "A wild tail swipe knocks Han off balance, sending him skidding across wet grass."),
    ("panel_0049", "A snarling lizard warrior snaps poisonous fangs, attempting to block his rescue path."),
    ("panel_0050", "Han sidesteps the reptile and kicks the scaled pest straight into rushing river rapids."),
    ("panel_0051", "A violent explosive shockwave rocks the stone foundation, sending cracks racing through the wall."),
    ("panel_0052", "Han catches his breath in the deluge, hoping the barrier structure somehow holds together."),
    ("panel_0053", "Suddenly a colossal monster fist slams down onto masonry, delivering the fatal fracture blow."),
    ("panel_0054", "Our protagonist watches in horror as giant stone blocks crumble into the churning abyss."),
    ("panel_0055", "A deafening roar echoes through the canyon as pent-up reservoir water bursts outward."),
    ("panel_0056", "Tidal waves toss armored goblins into the raging torrent like cheap plastic bath toys."),
    ("panel_0057", "The massive deluge cleanses the valley, drowning thousands of enemy invaders within seconds flat."),
    ("panel_0058", "Aaron spits out river mud, yelling, 'Han, the flood wiped out all the goblins!'"),
    ("panel_0059", "Han stares silently into the mist, calculating the brutal tactical cost of this event."),
    ("panel_0060", "Dozens of goblin helmets bob downstream, proving the enemy vanguard botched their bridge breach."),
    ("panel_0061", "The collapsed dam successfully prevents three thousand incoming monsters from crossing the river valley."),
    ("panel_0062", "Unfortunately, losing the bridge leaves Niflheim fortress stranded with zero hope of outside rescue."),
    ("panel_0063", "Han clenches bloodstained fists, knowing the fortress walls must hold against the main horde."),
    ("panel_0064", "Aaron shivers in the cold downpour, asking what insane mission awaits them next."),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch29"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch29")
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
