"""Pick Me Up Chapter 24 Golden Standard Script Generator (70 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Covers Master Anis's town upgrades, the potato diet running drill, potion rhythm game, brutal fire & pain resistance training, and tenth floor raid preparations.
- 1:1 synchronization across all 70 clean story panels.
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
    # Act 1: Master Anis's Town Upgrades & The Humiliating Stamina Drill (Panels 3 - 18)
    ("panel_0003", "Our clueless summoner Anis logs in bright and early, tapping frantically to construct facilities!"),
    ("panel_0004", "The Magic Lab finishes instantly, finally giving this broke town actual research upgrades."),
    ("panel_0005", "Blue pixel magic builds the Alchemy Lab, turning cheap monster trash into usable items!"),
    ("panel_0006", "Next up is the Library, because even braindead gacha units must read tutorial manuals!"),
    ("panel_0007", "A big goofy 'GOOD!' banner pops up, celebrating Anis's rare competent city planning!"),
    ("panel_0008", "All three annexes fuse into the Magic Hall, looking majestic for a starter town!"),
    ("panel_0009", "Meanwhile on the running track, noble mage Eolka is already dying after ten seconds!"),
    ("panel_0010", "Our boy Han casually jogs backwards, roasting her for complaining about basic cardio!"),
    ("panel_0011", "Mages who stand still get deleted, so evasion drills are an absolute life-or-death requirement!"),
    ("panel_0012", "Picking up the pace, the master ranker orders his panting princess to run faster!"),
    ("panel_0013", "Real battlefields do not care about fancy noble bloodlines when sharp spears are flying!"),
    ("panel_0014", "Eolka whines that her enchanted dress was ruined, furious at being treated like peasants!"),
    ("panel_0015", "That fancy family dress actually amplifies fire, making her an even deadlier walking nuke!"),
    ("panel_0016", "Three slow laps with zero weights is practically a vacation in Han's book!"),
    ("panel_0017", "The merciless captain sprints ahead laughing, threatening to feed her pure raw potatoes tonight!"),
    ("panel_0018", "Looking up at Anis's giant celestial eye, Han chuckles that their summoner loves comedy!"),

    # Act 2: Anis Logs Off & The Potion Mini-Game Speedrun (Panels 19 - 31)
    ("panel_0019", "With an elite caster secured, the Magic Hall perfectly prepares them for floor ten."),
    ("panel_0020", "Yesterday's dungeon haul stocked their warehouse full of essential high-tier crafting ingredients."),
    ("panel_0021", "Piles of crates sit ready as Han plans to cook up clutch healing potions."),
    ("panel_0022", "A blessed logout notice pops up, finally freeing the squad from Anis's creepy surveillance!"),
    ("panel_0023", "Jenna gets assigned drill sergeant duty, making sure their spoiled mage finishes every lap!"),
    ("panel_0024", "While normal players need maxed alchemy stats, pro gamers can exploit the crafting mini-game!"),
    ("panel_0025", "Level one Magic Hall welcomes our protagonist with glowing purple mana lights and sparkles."),
    ("panel_0026", "Flipping through ancient scrolls, Han laughs that the game's fantasy runes make zero sense!"),
    ("panel_0028", "Tossing flower petals into the cauldron, our veteran boots up the potion mini-game!"),
    ("panel_0029", "His godly gamer fingers shred rhythm notes, hitting pure 'PERFECT' combos like a machine!"),
    ("panel_0030", "Great Success alerts flash repeatedly, brewing pristine health potions with zero failed attempts!"),
    ("panel_0031", "Tiny Iselle cheers in disbelief as Han pockets eight life-saving flasks for floor ten!"),

    # Act 3: Hand in the Fire & The Spartan Drill (Panels 33 - 54)
    ("panel_0033", "A glowing brazier sits in the center as Han calls an emergency squad meeting."),
    ("panel_0034", "Pointing at crackling red embers, the captain asks his team why it is here."),
    ("panel_0035", "Without warning, Han plunges his bare hand directly into the roaring flames to demonstrate!"),
    ("panel_0036", "Jenna and Aaron shriek in pure horror, begging their unhinged captain to pull back!"),
    ("panel_0037", "Gritting his teeth through scorching heat, Han yells they must learn surviving fire!"),
    ("panel_0038", "Veins bulge on his neck as the count begins through agony: one, two, three!"),
    ("panel_0039", "The count hits four, echoing across the training grounds like a chilling permadeath ultimatum!"),
    ("panel_0040", "Aaron and Jenna sweat bullets as Han relentlessly powers through count five and six!"),
    ("panel_0041", "Blistering skin sizzles, yet our hero grimaces through count seven, eight, and nine!"),
    ("panel_0042", "Roaring through the climax of pain, Han hits count ten and conquers the heat!"),
    ("panel_0043", "Yanking his charred arm free, a heavy breath escapes his blackened, smoking fingers."),
    ("panel_0044", "Lobby healing magic kicks in immediately, restoring his crispy skin back to mint condition!"),
    ("panel_0045", "The captain explains that without fire resistance, Eolka's friendly fire will roast them alive!"),
    ("panel_0046", "Jenna freaks out in denial, crying, 'Wait, you expect us to do that now?!'"),
    ("panel_0047", "Aaron swallows hard, asking his hardcore captain when this brutal training actually concludes."),
    ("panel_0048", "A chilling smirk answers: you burn until the system awards Fire Resistance passive!"),
    ("panel_0049", "Memories of the tragic fifth floor flash before Aaron, reminding him what carelessness costs."),
    ("panel_0050", "Steeling his warrior resolve, the former carpenter reaches his trembling hand toward the coals."),
    ("panel_0052", "Guiding Aaron's arm forward, Han provides calm veteran support to push through the fear."),
    ("panel_0053", "Holding Aaron's wrist steady, the captain whispers that true rankers build discipline in silence."),
    ("panel_0054", "Jenna cowers behind her fists, whimpering that backline archers should be exempt from fire!"),

    # Act 4: Tactical Triangle & The Tenth Floor Boss Raid Stakes (Panels 55 - 76)
    ("panel_0055", "Han snatches Jenna's hand playfully, teasing that holding hands makes the burn hurt less!"),
    ("panel_0056", "Our squishy mage lacks shields, meaning party peel is their absolute top priority!"),
    ("panel_0057", "Jenna whines in defeated acceptance while Han turns to give Aaron another sadistic trial."),
    ("panel_0058", "A shattered glass metaphor explains how real gamers overcome crippling psychological trauma on battlefields."),
    ("panel_0059", "Gripping his wrist, the captain announces Aaron must unlock the Pain Resistance skill!"),
    ("panel_0060", "Aaron presses cold steel against his chest, realizing mental toughness separates survivors from corpses."),
    ("panel_0061", "Potions heal wounds, but pain stun will still leave you vulnerable to deletion!"),
    ("panel_0062", "The terrified archer asks if she must stab herself too, earning an emphatic 'NO.'"),
    ("panel_0063", "A mischievous smirk follows immediately, as Han clarifies she will definitely do it later!"),
    ("panel_0064", "Instead, Jenna will master 'Switching', an advanced weapon swapping technique for versatile combat range."),
    ("panel_0065", "This mechanic lets archers swap between longbow snipes and lightning-fast dual dagger parries mid-battle!"),
    ("panel_0066", "Old linear marching ranks are abolished in favor of a triangular perimeter protecting Eolka!"),
    ("panel_0067", "Jenna grumbles about babysitting the spoiled aristocrat, but squad synergy requires protecting their artillery."),
    ("panel_0068", "A chibi tank diagram proves that 'Protect the Princess' is their winning meta strategy!"),
    ("panel_0069", "Strategic planning sends Party Two to floor nine while their main strike team grinds."),
    ("panel_0070", "Analyzing water supplies and dungeon clues, Han prepares for diverse chain quest trial objectives."),
    ("panel_0071", "A grim system notice warns that floor ten requires two separate parties cooperating together!"),
    ("panel_0072", "Flicking a burning match into darkness, Han braces for an unprecedented level of danger."),
    ("panel_0073", "Biting down on a leather scroll, the lone ranker endures another private burn drill."),
    ("panel_0074", "Thick smoke billows through the forge as unyielding master willpower overpowers the agonizing heat!"),
    ("panel_0076", "A golden notification rings out, confirming Han unlocked the coveted Fire Resistance passive!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch24"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch24")
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
