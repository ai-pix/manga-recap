"""Pick Me Up Chapter 14 Golden Standard Script Generator (55 Story Panels).

Mamoru YouTube Recap Persona:
- Authentic Mamoru tone: dry wit, sarcastic banter, gamer grinding, dark comedy about hoping the Master never logs in, and tense stealth ambush!
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
    # Act 1: The Golden Horned Deer & Butchering Banter (Panels 2-14)
    ("panel_0002", "We kick right off with a rabid wolf-beast drooling fangs in Han's face."),
    ("panel_0003", "Our master ranker leans forward with a casual smirk, whispering, 'Bring it on.'"),
    ("panel_0006", "A startled recruit reels backward in panic, shrieking that a giant monster appeared."),
    ("panel_0007", "A colossal golden-horned deer collapses onto the grass, completely dismantled by veteran speedrunning."),
    ("panel_0008", "The rookie swordsman stammers in disbelief, completely stunned by Han's lightning-fast hunting efficiency."),
    ("panel_0009", "Han wipes his blade calmly, asking the trembling recruit if he is blind."),
    ("panel_0010", "The massive horned deer lies sprawled across the turf, leaking valuable purple essence."),
    ("panel_0011", "Jenna gawks at the carcass, screaming, 'How on Earth is a deer that large?!'"),
    ("panel_0012", "Han walks over, demanding to know how much game the feisty archer harvested."),
    ("panel_0013", "Jenna questions why he kept the severed head, complaining it will taste horrible."),
    ("panel_0014", "Han deadpans that female horned beasts possess unique alchemy horns, you ignorant rookie."),

    # Act 2: Lounge Feast & The Plateau Vacation (Panels 16-28)
    ("panel_0016", "A joyful system pop-up announces Jenna officially awakened her Hunter of the Forest skill."),
    ("panel_0017", "Jenna blinks at her glowing hands, amazed that simple butchering unlocked combat passives."),
    ("panel_0018", "Han inspects a rare wind stone, calculating that her upcoming hero promotion looks easy."),
    ("panel_0020", "Back at the lounge, starving recruits cheer wildly over a lavish roasted meat feast!"),
    ("panel_0021", "Jenna smiles at the celebration, noting the squad has not eaten well in days."),
    ("panel_0023", "Han studies the rotating event board, selecting the low-rank Sinmiel Plateau for grinding."),
    ("panel_0024", "A two-person party notification confirms Han and Jenna entered the breezy gathering zone."),
    ("panel_0025", "Jenna asks skeptically if gathering low-tier herbs can genuinely make their squad stronger."),
    ("panel_0026", "Han's boot crunches into the plateau dirt, soaking in the crisp mountain wind."),
    ("panel_0027", "The breathtaking view stretches across floating sky islands, offering a rare peaceful moment."),
    ("panel_0028", "Han exhales a quiet breath, enjoying a temporary break from brutal dungeon survival."),

    # Act 3: Plants of Life & Hoping the Master Never Logs In (Panels 29-46)
    ("panel_0029", "Bright red star-petaled flowers catch his eye, recognized instantly as valuable Plants of Life."),
    ("panel_0030", "These rare healing blooms serve as primary crafting ingredients for high-grade HP recovery potions."),
    ("panel_0032", "A stray grey wolf leaps from the tall grass, trying to disrupt their foraging."),
    ("panel_0033", "The predatory canine lunges aggressively, snapping jaws straight toward Jenna's slender shoulder."),
    ("panel_0034", "Jenna drops the predator with one casual arrow, declaring one wolf is nothing."),
    ("panel_0035", "She quickly harvests the hide, warning that blood scent might attract hungry packs."),
    ("panel_0037", "Han pockets the sharp beast teeth, collecting every valuable material for town crafting."),
    ("panel_0038", "Jenna sits back against the warm grass, remarking how surprisingly peaceful foraging feels."),
    ("panel_0039", "The relaxed archer stretches comfortably, wishing their daily life could always stay like this."),
    ("panel_0040", "Han tilts his head thoughtfully, admitting this place would be paradise without a Master."),
    ("panel_0042", "He wonders if past Niflheim heroes also secretly prayed their summoner never logged back."),
    ("panel_0043", "Han reflects that gathering materials beats worrying about getting fed into hero synthesis."),
    ("panel_0044", "Jenna looks over curiously, wondering what mysterious craft project her captain is planning."),
    ("panel_0045", "She teases him about slacking off, asking why he is not grinding combat."),
    ("panel_0046", "Han smirks quietly, keeping his master ranker upgrade strategy hidden for right now."),

    # Act 4: Floor 6 Jungle & The Goblin Ambush (Panels 47-66)
    ("panel_0047", "A few days later, a fresh exploration mission officially begins on Floor Six."),
    ("panel_0048", "Four armed party members assemble inside an eerie, densely overgrown primeval jungle canopy."),
    ("panel_0049", "A notification confirms rookie spearman Dika officially joined Party One for this trial."),
    ("panel_0050", "Han warns the newcomers that exploration floors carry zero safety nets or tutorials."),
    ("panel_0051", "The nervous blond recruit whispers that he cannot spot a single enemy anywhere."),
    ("panel_0052", "Han snaps at him to crouch low and keep his loud mouth shut."),
    ("panel_0053", "Observing the unnatural forest silence, Han suspects an organized enemy ambush lurks ahead."),
    ("panel_0055", "Three level-eight scout goblins huddle in the thick brush, carrying a curved warning horn!"),
    ("panel_0056", "Han signals Jenna to scale a giant tree and scout the surrounding jungle."),
    ("panel_0057", "Jenna whispers down in horror, spotting an entire goblin war camp containing hundreds!"),
    ("panel_0058", "Han whispers tactical orders, instructing Jenna to silently eliminate the right-side scout goblin."),
    ("panel_0059", "Aaron grips his spear tightly, preparing to strike the instant Han gives word."),
    ("panel_0060", "Han reminds the frontline vanguard to stay ready if chaos breaks loose immediately."),
    ("panel_0062", "The goblin scouts suddenly sense danger, raising their warning horn toward scaly lips!"),
    ("panel_0063", "Dika lunges from the bushes, driving his heavy spear straight through one scout!"),
    ("panel_0064", "The rookie spearman strikes with deadly precision, impaling the creature into damp moss."),
    ("panel_0065", "The lead goblin lifts the blowing horn, desperately trying to sound the alarm!"),
    ("panel_0066", "Han's broadsword cleaves through the air, shouting, 'I will not let you call reinforcements!'"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch14"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch14")
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
