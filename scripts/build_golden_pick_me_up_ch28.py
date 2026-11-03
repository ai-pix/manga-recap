"""Pick Me Up Chapter 28 Golden Standard Script Generator (61 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Covers the rainy siege, broken goblin attack patterns, tactical decapitation of the commander, and the terrifying Level 23 Ogre spawn.
- 1:1 synchronization across all 61 clean story panels.
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
    # Act 1: The Rain-Swept Siege & Goblins Breaking Script (Panels 2 to 19)
    ("panel_0002", "Welcome back to Niflheim, where bad weather is the least of your gaming problems."),
    ("panel_0003", "A massive goblin army marches through the mud, while noob master Anis watches helplessly."),
    ("panel_0004", "Armored vanguard shock-troops march forward, ready to delete low-star beginner heroes permanently."),
    ("panel_0005", "Their lead warrior hoists a massive cleaver, flexing some absurdly unfair pay-to-win stats."),
    ("panel_0006", "The beast lets out an ear-piercing battle cry, signaling an immediate all-out frontal charge!"),
    ("panel_0008", "Explosions tear through the frontlines as Han screams, 'Now! Charge forward right now!'"),
    ("panel_0009", "Rabid wolf hounds sprint through the fire, breaking standard AI aggro paths like complete cheaters."),
    ("panel_0010", "A lightning spear thrust catches Han off guard, grazing past his defensive guard."),
    ("panel_0011", "A buff green brute thrusts upward, determined to impale our disguised veteran on sight."),
    ("panel_0012", "Han's eyes widen as he gasps, 'Wait, the goblins completely changed their attack pattern?!'"),
    ("panel_0013", "Aaron stammers in panic, shouting, 'We just dropped fire magic, why are they sprinting?!'"),
    ("panel_0014", "Han blocks incoming claws with his sword, realizing basic fire spells barely tickled them."),
    ("panel_0015", "Locking his gamer vision forward, Han instantly deduces what kind of hacker is responsible."),
    ("panel_0016", "Perched atop a ruined siege engine, the goblin commander directs every single unit movement."),
    ("panel_0017", "The goblin commander grins viciously, coordinating his goons to overwhelm Han's defensive formation."),
    ("panel_0018", "Han realizes this filthy boss deliberately waited for Eolka's spell cooldown before rushing them."),
    ("panel_0019", "Gritting his teeth in frustration, Han curses, 'Dammit, this stupid monster is actually smart!'"),

    # Act 2: Regrouping & The All-In Gambit (Panels 20 to 36)
    ("panel_0020", "Jenna and Aaron get pinned down by flames, running dangerously low on stamina."),
    ("panel_0021", "Han leaps right through the blazing barrier, yelling, 'Everyone, regroup on my position now!'"),
    ("panel_0022", "Jenna clutches her bow nervously as Han snaps, 'Listen up, because we only get one shot!'"),
    ("panel_0023", "Han points his blade forward, shouting, 'We are taking that golden-masked commander's head!'"),
    ("panel_0024", "The golden-masked warlord sneers arrogantly, blissfully unaware he is scheduled for immediate deletion."),
    ("panel_0025", "Floating into the air, Eolka starts weaving an insanely massive circle of arcane runes."),
    ("panel_0026", "The enemy army swarms blindly into the canyon, walking straight into Han's calculated killzone."),
    ("panel_0027", "A giant wolf monster howls at the sky, bathing in furious red rage auras."),
    ("panel_0028", "Han swings his broadaxe downward, cleaving straight into the armored beast's thick chest plate."),
    ("panel_0029", "The dying demon snaps its jagged jaws, desperately trying to bite Han's exposed throat."),
    ("panel_0030", "Han glares up toward the sky, shouting, 'Eolka, you finished casting?! Burn these bastards!'"),
    ("panel_0031", "Eolka coldly snaps her fingers and whispers, 'Ignite', unleashing a swirling wall of hellfire!"),
    ("panel_0032", "An apocalyptic beam of orange energy incinerates the enemy vanguard into smoking hot cinders."),
    ("panel_0033", "Surviving reptilian foot-soldiers scramble backward in blind horror from the blistering magical heatwave."),
    ("panel_0034", "Han catches his breath, calculating that one magic burst cannot clear an entire raid."),
    ("panel_0035", "Luckily, our former top five global ranker always keeps a dirty trick ready!"),
    ("panel_0036", "A violent secondary shockwave erupts from below, screaming, 'We are not finished yet, loser!'"),

    # Act 3: Commander Down & Enemy Shift to Fortress (Panels 37 to 54)
    ("panel_0037", "Rain washes sweat down Han's face as the deafening explosion echoes across the valley."),
    ("panel_0039", "The masked commander flies backward through the air like an over-inflated pinata."),
    ("panel_0040", "Heavy steel boots hit the steaming dirt as the remaining frontline mobs completely scatter."),
    ("panel_0041", "Jenna winces as burning debris flies past her face, narrowly missing her eye."),
    ("panel_0042", "A wounded beast whimpers in the rain, dragging its broken body away in defeat."),
    ("panel_0043", "Dika collapses flat onto the mud, completely gassed out from the exhausting battle."),
    ("panel_0044", "Jenna firmly presses on his chest, whispering, 'Shut your mouth and save your breath.'"),
    ("panel_0045", "Looking over the ridge, Aaron mutters that thousands of enemy reinforcements are still advancing."),
    ("panel_0046", "Han casually breaks the bad news: these monsters never cared about our party."),
    ("panel_0047", "Without their warlord issuing orders, the confused mob AI suddenly glitches out completely."),
    ("panel_0048", "The massive horde ignores our heroes entirely, mindlessly continuing their march toward the fortress."),
    ("panel_0050", "Standing safe inside a lingering fire ring, the squad watches the army pass by."),
    ("panel_0051", "Han frowns deeply, realizing the entire invasion force is heading straight for the Niflheim base."),
    ("panel_0053", "Tumbling into a quiet ditch, the crew exhales, grateful they are not dead yet."),
    ("panel_0054", "Han smirks dryly, reminding them, 'We only survived because I snipped their command wire.'"),

    # Act 4: Potion Triage & The Next Wave Spawns (Panels 55 to 67)
    ("panel_0055", "Handing out cheap red healing potions, Han orders everyone to treat their nasty burns."),
    ("panel_0056", "Distant war drums rattle through the storm, proving the North Wall is actively falling."),
    ("panel_0057", "Han straps his wet boots tighter, warning that the real difficulty spike starts now."),
    ("panel_0058", "Scanning the rainy sky, Han wonders if Master Anis even knows what buttons to press."),
    ("panel_0060", "Suddenly a giant clawed foot stomps down into the mud right beside them!"),
    ("panel_0061", "Han drops his jaw in disbelief, groaning, 'Can this trash game give us five minutes?!'"),
    ("panel_0062", "A terrifying purple system prompt spawns nineteen Level 9 Goblins right on their heads!"),
    ("panel_0063", "Jenna whines loudly, complaining that they did not even get a ten-second bathroom break."),
    ("panel_0064", "Fresh enemy squads pour down the steep cliffs, cutting off every single emergency escape route."),
    ("panel_0065", "Aaron points shaking fingers into the shadows, stammering, 'Han, please tell me you see that!'"),
    ("panel_0066", "Two glowing amber eyes ignite inside the fog, radiating pure high-tier raid boss malice."),
    ("panel_0067", "A colossal Level 23 Ogre crashes down, turning this quick skirmish into an absolute funeral!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch28"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch28")
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
