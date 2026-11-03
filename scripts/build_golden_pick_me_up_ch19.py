"""Pick Me Up Chapter 19 Golden Standard Script Generator (78 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Covers the dawn squad split lottery, Floor 7 goblin subjugation linked quest, and Master Anis's gacha package spending spree!
- 1:1 synchronization across all 78 clean story panels.
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
    # Act 1: Morning Aftermath, Usher's Test & The Weeding (Panels 2-16)
    ("panel_0002", "Terrified rookies scramble through the fortress corridors after yesterday's horrifying synthesis execution."),
    ("panel_0003", "A sweating newcomer frantically bashes a practice dummy, desperate to look useful."),
    ("panel_0005", "Han watches coldly, knowing support facilities only hold two workers per building."),
    ("panel_0006", "Over in the corner, a lone recruit quietly practices clean sword swings."),
    ("panel_0007", "Approaching the hard-working rookie, Han asks him for his official name."),
    ("panel_0008", "The newcomer introduces himself as Usher Roderick, eager to survive this nightmare."),
    ("panel_0009", "Usher confesses he was merely an ordinary porter hauling mercenary luggage previously."),
    ("panel_0010", "Han praises his disciplined posture, impressed by his natural weapon balance."),
    ("panel_0011", "A knowing smirk crosses Han's face, sensing genuine hidden potential in him."),
    ("panel_0012", "Han challenges the humble porter to spar, testing his mercenary combat instincts."),
    ("panel_0013", "Night falls as Master Anis logs on for another rookie weeding session."),
    ("panel_0014", "Two unlucky recruits dissolve into light, promoting Usher straight to level three!"),
    ("panel_0015", "Surviving heroes grind daily resource dungeons, harvesting precious iron ore under pressure."),
    ("panel_0016", "Freezing dawn settles across Niflheim as another deadly survival challenge begins."),

    # Act 2: The Two-Party Split & Drawing Lots (Panels 17-46)
    ("panel_0017", "Jenna yawns loudly at dawn, whining about the freezing morning weather."),
    ("panel_0018", "Han demands silence, asking if anyone deduced why they were summoned today."),
    ("panel_0019", "Anxious recruits exchange nervous glances, dreading another unexpected execution in the plaza."),
    ("panel_0020", "Shock ripples through the room as Han reveals they must pick parties."),
    ("panel_0021", "Jenna reminds him that Master Anis chooses rosters, but Han manipulates suggestions."),
    ("panel_0022", "Han pulls out a sealed container, introducing his tactical squad lottery system."),
    ("panel_0023", "Tension spikes across the room as nobody wants to leave Han's side."),
    ("panel_0024", "Drawing lots will decide their fates, splitting the squad into two groups."),
    ("panel_0026", "Their six-man roster will divide into two balanced three-hero squads today."),
    ("panel_0027", "Han reassures the trembling squad that nobody is getting abandoned on purpose."),
    ("panel_0028", "Two captains are appointed: Han leads team one, while Edis leads two."),
    ("panel_0029", "Jenna throws an outraged tantrum after being disqualified from squad leadership duties!"),
    ("panel_0030", "Recruits wonder why they cannot keep all their strongest fighters together."),
    ("panel_0031", "Han warns that clustering everyone into one party risks total team annihilation."),
    ("panel_0032", "Floor five proved that massive stat gaps will get underleveled heroes killed."),
    ("panel_0033", "Future tower challenges will demand dozens of heroes fighting at similar levels."),
    ("panel_0034", "Han hopes Master Anis realizes paid summons require smart multi-party planning."),
    ("panel_0035", "Holding colored markers, Han assigns red for his team and blue for Edis."),
    ("panel_0036", "Slamming the drawing box down, he officially begins the squad selection lottery."),
    ("panel_0037", "Tense silence grips the courtyard as everyone draws their party assignment slip."),
    ("panel_0038", "Jenna cheers wildly upon drawing red, overjoyed to stay on Han's team!"),
    ("panel_0039", "Drawing blue, poor Dika stares at captain Edis with pure disappointment."),
    ("panel_0040", "Dika stammers awkwardly, trying to backtrack before insulting his new squad leader."),
    ("panel_0041", "Edis lowers her gaze humbly, understanding why teammates doubt an unproven recruit."),
    ("panel_0042", "Han admits the combat gap is real, urging everyone to work harder."),
    ("panel_0043", "Harsh survival rules apply: anyone falling behind will be left in dust."),
    ("panel_0044", "Edis smirks with fiery determination, swearing her squad will never lose."),
    ("panel_0045", "System banners flash on screen, submitting Han's roster suggestions to the master."),
    ("panel_0046", "Team one pairs Han with Jenna and Aaron, while Edis leads two."),

    # Act 3: Floor 7 Goblin Subjugation & Linked Quest (Panels 48-68)
    ("panel_0048", "A monstrous armored beast roars aggressively as storm clouds gather in dungeon."),
    ("panel_0049", "Floor seven subjugation begins: eliminate thirteen level eight goblins in heavy rain."),
    ("panel_0050", "Towering green brutes emerge from the mist, brandishing jagged rusted blades."),
    ("panel_0051", "Jenna draws her bow cockily, offering to solo the entire goblin pack."),
    ("panel_0052", "Han cuts her off, ordering his teammates to stay behind his broadsword."),
    ("panel_0053", "A snarling green beast ambushes from shadows, lunging with sharp razor claws!"),
    ("panel_0054", "Sweat pours down Han's face as he locks his combat focus into overdrive."),
    ("panel_0055", "Crimson energy ignites around his blade as the Berserk skill triggers instantly!"),
    ("panel_0056", "Aaron rushes in swinging his greatsword, shielding Han's blind spots during battle."),
    ("panel_0057", "Han's glowing red eyes track every enemy movement through the pouring rain."),
    ("panel_0058", "Devastating crimson shockwaves slice through the goblin frontline with surgical precision!"),
    ("panel_0059", "The lone surviving goblin trembles in terror, waving a useless rusted dagger."),
    ("panel_0060", "Rain washes monster blood off polished steel as Han holds his strike."),
    ("panel_0061", "Jenna aims an arrow, asking if they should finish off the monster."),
    ("panel_0062", "Han stops her, realizing this torrential downpour signals a hidden linked quest."),
    ("panel_0063", "Leaving the trembling goblin alive, Han orders a full area search instead."),
    ("panel_0064", "Torrential downpours serve as the primary environmental puzzle clue for this floor."),
    ("panel_0065", "A rushing blue river torrent confirms unnatural water flow throughout the canyon."),
    ("panel_0066", "A shattered wooden dam upstream confirms Han solved the secret linked quest."),
    ("panel_0067", "Golden letters proclaim stage clear, granting Aaron a level up and MVP!"),
    ("panel_0068", "Stage rewards flood their inventory: ten thousand gold coins, iron, and leather."),

    # Act 4: Master Anis's Gacha Spree & The Roster Expands (Panels 69-82)
    ("panel_0069", "Jenna heads off to shower while Aaron plans another intense workout session."),
    ("panel_0070", "Han's eye widens as a golden spending notification flickers in the sky."),
    ("panel_0071", "Grabbing Aaron's shoulder, Han orders him to freeze as mana gathers above."),
    ("panel_0072", "Master Anis impulsively buys the ninety-thousand won Newbie Package on his smartphone!"),
    ("panel_0073", "This marks the third time today our clueless summoner swiped his card!"),
    ("panel_0074", "Han urgently orders Jenna to sprint to his room for lottery slips."),
    ("panel_0075", "Turning to Aaron, Han commands him to summon captain Edis immediately."),
    ("panel_0076", "A billing confirmation on the smartphone charges the transaction to Anis's bill."),
    ("panel_0077", "Five thousand shiny gems flood into the account as mobile payment clears."),
    ("panel_0078", "Anis triggers consecutive summons, drawing five fresh recruits to expand the town!"),
    ("panel_0079", "The veteran squad anchors the frontline: Han, Jenna, Usher, and loyal Aaron."),
    ("panel_0080", "Team two prepares to integrate incoming rookies under Dika and captain Edis."),
    ("panel_0081", "Town crafters Patrick, Enok, and Chloe ready their workshops for new recruits."),
    ("panel_0082", "New arrivals Amarin and Alter spawn in, expanding Niflheim's desperate survival roster!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch19"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch19")
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
