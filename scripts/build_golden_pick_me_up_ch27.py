"""Pick Me Up Chapter 27 Golden Standard Script Generator (62 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Sally-out past the East Gate, panicked garrison conscripts, Eolka's 20-second cooldown defense, charging through walls of fire!
- 1:1 synchronization across all 62 clean story panels.
- Strictly 10 to 14 words per beat.
- Evaluated and verified by Kimi-K3 Quality Gatekeeper.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path("D:/Python Projects/Manga Recap")
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.schema import ScriptFile, load_model  # noqa: E402
from scripts.batch_generate_pick_me_up_workflow_master import (  # noqa: E402
    build_script_blocks,
    clean_and_prune_panels,
    format_sentence,
)
from scripts.quality_gatekeeper import check_script_quality  # noqa: E402

STORY_BEATS = [
    # Act 1: The Sally-Out & Portcullis Madness (Panels 2-17)
    ("panel_0002", "We jump right into pure chaos as our squad prepares a suicidal sally-out."),
    ("panel_0003", "Instead of hiding behind safety walls, our master ranker plans to assassinate goblin commanders."),
    ("panel_0004", "Hoisting his broadsword high, Han announces they are hunting the enemy cavalry commander directly."),
    ("panel_0005", "Welcome to the craziest tactical raid maneuver in mobile gacha gaming history, everyone."),
    ("panel_0006", "Terrified refugees scramble toward the inner fortress, screaming about demonic curses and certain doom."),
    ("panel_0007", "Floating down gracefully, Eolka sighs that evacuating useless civilians took way too long."),
    ("panel_0008", "Jenna receives orders to scale the outer ramparts and scout incoming monster hordes."),
    ("panel_0009", "Han shouts upward, telling their resident noble mage to prepare massive fire artillery."),
    ("panel_0010", "Rookie spearman Shurn hurries forward, sweating nervously beside veteran frontline fighters."),
    ("panel_0011", "Aaron grips the giant iron chains, groaning loudly as he cranks the portcullis."),
    ("panel_0012", "The massive iron fortress gate grinds open, sending garrison conscripts into utter panic."),
    ("panel_0013", "Jenna gasps from the battlements, warning that an endless green ocean awaits outside."),
    ("panel_0014", "Our fearless captain smirks back playfully, ordering her to jump down immediately."),
    ("panel_0015", "Terrified fortress guards scream in horror, convinced an evil poltergeist unlocked the doors."),
    ("panel_0016", "Jenna looses a whistling arrow mid-air, pinning a leaping goblin to the stone."),
    ("panel_0017", "Eolka clasps her delicate hands together, chanting an explosive ancient high-tier spell incantation."),

    # Act 2: Firestorm Breach & Gates Slamming Shut (Panels 19-42)
    ("panel_0019", "A charging green beast eats a black-gloved fist right to its ugly snout."),
    ("panel_0020", "Weeping fortress guards watch in total disbelief as our tiny four-man squad attacks."),
    ("panel_0021", "Heavy black boots splash into muddy cobblestones as Han steps outside the walls."),
    ("panel_0022", "Tilting his face toward the dark sky, our gamer notices heavy downpour falling."),
    ("panel_0023", "Cold raindrops stream down his cheek while tactical combat formulas calculate in seconds."),
    ("panel_0024", "Jenna glances over anxiously, wondering if stormy rain will extinguish their fiery magic."),
    ("panel_0025", "Panicked fortress sentries scream bloody murder, expecting the squad to get slaughtered instantly."),
    ("panel_0026", "A massive winged hound lunges forward, snapping its jaws viciously at their caster."),
    ("panel_0028", "Dodging the snapping beast smoothly, Eolka unleashes her fully charged mystical flame burst."),
    ("panel_0029", "Han shouts a quick warning, reminding her not to blow up the gateway."),
    ("panel_0030", "A colossal nuclear fireball vaporizes the charging vanguard, scorching the rain-soaked earth black."),
    ("panel_0032", "Sprint formations activate instantly as Han orders Jenna and Aaron to secure perimeters."),
    ("panel_0033", "Handing over a blue potion bottle, Han instructs their panting mage to drink."),
    ("panel_0034", "Our captain asks if she can keep casting during this relentless dungeon raid."),
    ("panel_0035", "Puffing her chest proudly, Eolka snaps that she could cast another hundred times."),
    ("panel_0036", "Rookie Shurn stammers nervously, asking if he should follow them into certain death."),
    ("panel_0037", "Glancing back with a cold smirk, Han tells the rookie to turn around."),
    ("panel_0038", "He directs the trembling rookie toward Edis, who needs extra hands for support."),
    ("panel_0039", "Behind their backs, the heavy iron gate rattles downward, locking shut with finality."),
    ("panel_0040", "Han casually shouts at the terrified guards to close the doors even faster."),
    ("panel_0041", "Surrounded by blazing fire and heavy rain, our squad notices their retreat vanished."),
    ("panel_0042", "With the escape route permanently sealed, moving forward remains their single surviving option."),

    # Act 3: The 20-Second Spell Cooldown Countdown (Panels 43-57)
    ("panel_0043", "Battle positions lock in immediately as our veteran party forms a defensive perimeter."),
    ("panel_0044", "Han tells their mage to use stage one flames to manage mana efficiently."),
    ("panel_0045", "Torrential rain pours down heavily, but monster blood keeps temperatures boiling across cobblestones."),
    ("panel_0046", "A monstrous horned beast roars furiously as the twenty-second spell timer begins ticking."),
    ("panel_0047", "Nineteen seconds remain as massive stone clubs smash down against muddy fortress paving."),
    ("panel_0048", "Charging goblins swarm the flanks at seventeen seconds, testing their tight triangular defense."),
    ("panel_0049", "Leaping through the stormy air, Han severs goblin necks with clean steel cuts."),
    ("panel_0050", "Explosive mini-flames detonate across the frontline, keeping aggressive beastmen from closing distance."),
    ("panel_0051", "Twelve seconds display on the mental clock as Han parries another savage club."),
    ("panel_0053", "A ferocious wolf-headed brute charges in at seven seconds, hunting their concentrating caster."),
    ("panel_0055", "Aaron slams his heavy iron shield forward, absorbing the bone-crushing impact like bedrock."),
    ("panel_0056", "White knuckles tighten around weapon hilts as the timer ticks down toward zero."),
    ("panel_0057", "Han commands a quick position shift as monsters desperately lock onto their mage."),

    # Act 4: Nuclear Ignition & The Chasm Charge (Panels 58-71)
    ("panel_0058", "The internal skill cooldown timer flashes a glorious number one across the interface."),
    ("panel_0059", "Eolka releases her pent-up magic, sending a colossal geyser of roaring golden flames."),
    ("panel_0061", "Shouting the battle command, Han orders everyone to charge straight through burning wreckage."),
    ("panel_0062", "Heat waves ripple through the storm as our fearless heroes sprint behind firestorms."),
    ("panel_0064", "Catching her breath quickly, Eolka receives orders to queue another spell cycle immediately."),
    ("panel_0065", "Aaron shifts right to shield their flank while Jenna snipes distant goblin archers."),
    ("panel_0066", "Another twenty-second countdown starts ticking as fresh enemy waves flood the narrow valley."),
    ("panel_0067", "Slashing through beastmen relentlessly, Han counts down the final two seconds of combat."),
    ("panel_0068", "The timer hits one again, triggering another synchronized squad rotation across the turf."),
    ("panel_0070", "Using rolling flame walls as portable cover, our four heroes advance like bulldozers."),
    ("panel_0071", "The story freezes on Han standing victorious in the chasm, hunting their commander."),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch27"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch27")
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
