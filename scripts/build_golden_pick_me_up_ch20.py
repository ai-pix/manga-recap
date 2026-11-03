"""Pick Me Up Chapter 20 Golden Standard Script Generator (69 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Covers Master Anis's 1,000-gem high-rank summons, pulling rare fire magician Eolka & veteran Roderick, the rigged lottery draft, and the Crack of Time and Space trial!
- 1:1 synchronization across all 69 clean story panels.
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
    # Act 1: Master Anis's Gacha Gamble & Two New Three-Stars Arrive (Panels 3-19)
    ("panel_0003", "Han orders Aaron to freeze as ominous celestial summoning mana fills the sky."),
    ("panel_0004", "Aaron sprints to summon captain Edis, sensing another chaotic roster shakeup incoming."),
    ("panel_0005", "Up in reality, Master Anis sweats nervously over next month's mobile phone bill."),
    ("panel_0006", "He says screw it and hits purchase, dumping five thousand shiny gems into inventory."),
    ("panel_0007", "Anis burns one thousand gems immediately, confirming a high-rank double summon gacha pull!"),
    ("panel_0008", "Han sighs from below, knowing once a noob tastes dopamine, there is no stopping."),
    ("panel_0009", "Anis watches in sheer amazement as his newly synthesized units clear tough dungeon trials."),
    ("panel_0010", "The intoxicating thrill of commanding living subordinates hooks our clueless beginner player completely."),
    ("panel_0011", "Tower climbing and PvP leaderboards turn casual mobile gamers into reckless credit card swipers."),
    ("panel_0012", "The sky rips open with golden lightning as two high-tier summon cards materialize."),
    ("panel_0014", "Golden fireworks explode across the interface as Anis pulls three-star fire magician Eolka!"),
    ("panel_0015", "A second golden card flashes, delivering veteran city guard Roderick as another three-star!"),
    ("panel_0016", "Silver-haired Roderick glares around fiercely, demanding to know what sorcery summoned him here."),
    ("panel_0017", "Red-haired noble lady Eolka sheds panicked tears, horrified by her bizarre new surroundings."),
    ("panel_0018", "Tumbling gracelessly onto the stone plaza, the proud aristocrat lands in complete humiliation."),
    ("panel_0019", "Eolka flails helplessly on the cobblestones, paralyzed by her scandalously revealing summon outfit!"),

    # Act 2: The Fire Magician Jackpot & Rigged Draft (Panels 20-44)
    ("panel_0020", "Jenna jogs over with the drawing slips, baffled by the girl crying on pavement."),
    ("panel_0021", "Han whispers to Edis, identifying the dramatic drama queen as an entitled noble lady."),
    ("panel_0022", "Having seen spoiled aristocrats before, Han chuckles knowing she is merely dying of embarrassment."),
    ("panel_0024", "Veteran Roderick understands concepts like masters, but knows nothing about levels or skill stats."),
    ("panel_0025", "A dutiful city watchman at heart, Roderick wonders why he must fight unknown monsters."),
    ("panel_0026", "Han approaches calmly, explaining that team placements will be decided through a lottery draw."),
    ("panel_0027", "Weighing both options, he initially prefers the seasoned guard over a bratty noble."),
    ("panel_0028", "Jenna trips forward clumsily, extending the drawing cup toward both waiting squad leaders."),
    ("panel_0029", "Han spots the red-tipped paper on the right, instantly calculating which slip to grab."),
    ("panel_0030", "Edis catches the color mark too, flashing a mischievous grin right beside him!"),
    ("panel_0031", "Both captains reach forward aggressively, determined to snatch their preferred new three-star recruit."),
    ("panel_0032", "Han lunges like an esports pro, attempting to ninja-loot the winning slip first!"),
    ("panel_0033", "Edis dives forward screaming, desperately grabbing for the exact same winning lottery paper!"),
    ("panel_0034", "Eolka watches the childish scuffle in disbelief, resting her hands on her hips."),
    ("panel_0035", "A sudden wave of scorching heat erupts as Han senses raw blazing fire mana!"),
    ("panel_0036", "Hot winds whip through Edis's dark hair as both leaders freeze in realization."),
    ("panel_0037", "Han and Edis grapple aggressively, shamelessly accusing each other of trying to cheat!"),
    ("panel_0038", "Turning sharply toward Eolka, our ranker demands to know if she is a magician."),
    ("panel_0039", "A glowing stat card confirms Eolka is an ultra-rare intermediate fire magic specialist!"),
    ("panel_0040", "Han refuses to be a gentleman, knowing fire magic synergizes god-tier with archer Jenna."),
    ("panel_0041", "Magicians are ultra-rare gacha jackpot pulls, completely impossible to craft through hero synthesis."),
    ("panel_0042", "Eolka crosses her arms furiously, offended at being appraised like auction house livestock."),
    ("panel_0043", "Chibi Eolka throws a comical fit, screaming that both squad captains are shameless cheaters!"),
    ("panel_0044", "Jenna steps in like a referee, insisting they must redraw using pure honest luck."),

    # Act 3: The Fair Redraw & Sacrificial Feast (Panels 45-64)
    ("panel_0045", "Eolka stomps her feet angrily, demanding to know who dared abduct an aristocrat."),
    ("panel_0046", "Roderick advises her to pipe down before making dangerous enemies in this realm."),
    ("panel_0047", "Both new recruits sweat nervously, realizing heroes are treated like disposable inventory items."),
    ("panel_0048", "Jenna shuffles the drawing cup vigorously, demanding absolute fairness with zero sleight of hand."),
    ("panel_0049", "Han and Edis agree to terms, promising no hard feelings whichever way lots fall."),
    ("panel_0050", "A hand reaches into the shuffled cup, selecting a final hidden paper slip."),
    ("panel_0051", "Edis pulls her paper slowly, holding her breath for the big squad reveal."),
    ("panel_0052", "Both captains examine their drawn colors in tense silence across the sunlit courtyard."),
    ("panel_0053", "Han flashes a triumphant grin holding red, successfully scoring fire magician Eolka today!"),
    ("panel_0054", "A party invitation flashes across the system, officially drafting Eolka into Han's squad."),
    ("panel_0055", "Eolka accepts the prompt reluctantly, cementing her spot alongside Han, Jenna, and Aaron."),
    ("panel_0056", "Roderick receives his assignment notice, assigned to anchor the frontline for captain Edis."),
    ("panel_0057", "A screaming slacker is dragged past them, kicking frantically toward the synthesis chamber."),
    ("panel_0058", "The doomed recruit begs Han for mercy, weeping that this cannot be happening."),
    ("panel_0059", "Han glares at Eolka coldly, warning that lagging behind earns that exact fate."),
    ("panel_0060", "Two fodder recruits dissolve into glowing dust, supercharging Eolka with fresh level-up stats!"),
    ("panel_0061", "Han reminds her that survival requires non-stop grinding, or deletion becomes her future."),
    ("panel_0062", "Fairy Iselle cackles overhead with whips, warning nobody escapes synthesis without hard work."),
    ("panel_0063", "Roderick watches in horrified silence as trembling recruits are dragged away like livestock."),
    ("panel_0064", "Golden system notices confirm Roderick levels up as well from sacrificial stat fodder."),

    # Act 4: Entering the Crack of Time and Space (Panels 65-73)
    ("panel_0065", "Fairy Iselle chants ancient commands, ripping open the glowing blue Crack of Time!"),
    ("panel_0066", "Han announces that the newcomers' deadly trial begins right now inside the rift."),
    ("panel_0067", "Edis marches Roderick toward the portal, ready to test their team two cohesion."),
    ("panel_0068", "Approaching the swirling vortex, Han demands to know what combat spells Eolka casts."),
    ("panel_0069", "Eolka scoffs arrogantly, asking why a noble lady should answer to a peasant."),
    ("panel_0070", "Han steps closer ruthlessly, asking if the spoiled aristocrat is simply terrified of fighting."),
    ("panel_0071", "Eolka snaps in tearful frustration, complaining about risking her life against unknown monsters."),
    ("panel_0072", "Han snaps back fiercely, reminding her she just consumed two human lives today."),
    ("panel_0073", "His glowing blue eyes stare into her soul: 'Fight, or get deleted next!'"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch20"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch20")
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
