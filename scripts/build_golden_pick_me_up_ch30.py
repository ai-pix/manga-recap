"""Pick Me Up Chapter 30 Golden Standard Script Generator (47 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Covers the desperate siege, Eolka's secret telekinesis, Han's hilarious face-pinching scolding, the epic arrival of the Iron Lion Cavalry, and buying the 500-gem horse skill.
- 1:1 synchronization across all 47 clean story panels.
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
    # Act 1: Siege Despair & The Elusive "Plan B" (Panels 2 to 10)
    ("panel_0002", "Aaron screams into the pouring rain, asking what their next suicidal order is."),
    ("panel_0003", "Explosions tear through wooden barricades as three hundred goblins swarm their crumbling defenses."),
    ("panel_0004", "Jenna clutches her bow in despair, fighting back bitter tears of sheer exhaustion."),
    ("panel_0005", "Rain streaks down Han's face while his battered squad waits for a miracle."),
    ("panel_0006", "Welcome back to Pick Me Up, where bad RNG turns into permadeath nightmares."),
    ("panel_0007", "Han turns around in the mud, facing the trembling survivors of his squad."),
    ("panel_0008", "His gloved hand grips his sword hilt, preparing for a bloody last stand."),
    ("panel_0009", "Aaron begs to retreat and find a plan B, but respawns do not exist."),
    ("panel_0010", "Eolka raises her pale hand, quietly interrupting their panic with a calm whisper."),

    # Act 2: Eolka's Secret Magic & Han's Face-Pinch Comedy (Panels 11 to 20)
    ("panel_0011", "Swirling purple arcane energy suddenly dances across her slender fingers and jeweled bracelet."),
    ("panel_0012", "Eolka chants an ancient spell, channeling massive magical runes into the wet air."),
    ("panel_0014", "Han's eyes widen in shock as he bellows at everyone to move back!"),
    ("panel_0015", "Eolka screams with fury, unleashing a telekinetic shockwave that obliterates the goblin vanguard!"),
    ("panel_0016", "Crushed monster bodies slump over shattered barricades amidst the steaming, rain-soaked debris."),
    ("panel_0017", "Han confronts Eolka in disbelief, asking why she hid basic telekinesis until now."),
    ("panel_0018", "Eolka snaps back defensively, whining that she just saved the entire mission single-handedly."),
    ("panel_0019", "Han aggressively pinches her soft cheeks like silly putty, demanding absolute transparency hereafter!"),
    ("panel_0020", "Rubbing his sore face, Han sighs, admitting they survived purely thanks to her."),

    # Act 3: Goblin Surge & Iron Lion Cavalry Arrival (Panels 21 to 38)
    ("panel_0021", "Jenna shrieks in terror as a colossal winged shadow looms over the ridge."),
    ("panel_0022", "Over three hundred fresh goblins charge down the muddy hill in ravenous hunger."),
    ("panel_0023", "Han carves through frontline minions, calculating when friendly reinforcements might finally arrive."),
    ("panel_0024", "Shoving a mana potion into Eolka's mouth, Han orders her to keep casting."),
    ("panel_0025", "A ferocious winged demon lunges aggressively, screeching with razor fangs bared wide open."),
    ("panel_0026", "Han roars Eolka's name, parrying incoming talons with a lightning-fast sword block."),
    ("panel_0027", "Aaron braces against a roaring fiend, struggling to keep his wooden shield intact."),
    ("panel_0028", "Jenna leaps through the air, driving sharp steel daggers into thick beast hide."),
    ("panel_0029", "A silver-plated mechanical horse hoof crashes down into the muddy earth with force."),
    ("panel_0030", "Snarling goblins freeze in place as heavy ground tremors rattle the entire canyon."),
    ("panel_0031", "Han catches his ragged breath, feeling the unmistakable rhythmic thunder of incoming cavalry."),
    ("panel_0032", "An imposing knight clad in jet-black plate armor draws a massive shining broadsword."),
    ("panel_0033", "A booming war cry roars across the valley: 'Iron Lion Cavalry, attack now!'"),
    ("panel_0034", "Hundreds of armored elite riders storm down the hill, cutting through monster ranks."),
    ("panel_0035", "A golden system prompt announces the Iron Lion Cavalry has officially joined battle!"),
    ("panel_0036", "Han orders Jenna and Aaron to fall back toward Eolka's defensive line."),
    ("panel_0037", "Five hundred heavy mounted knights charge forward, impaling panicked monsters on glowing lances."),
    ("panel_0038", "Jenna watches in absolute awe as high-level NPC soldiers completely steamroll the battlefield."),

    # Act 4: The 500-Gem Horse Riding Skill & The Counter-Charge (Panels 39 to 49)
    ("panel_0039", "Aaron sighs with relief, wondering if they can just lie down and nap."),
    ("panel_0040", "The cavalry officers pause, asking if any of these ragged adventurers ride horses."),
    ("panel_0041", "Han pulls up the floating blue game menu, navigating to the cash shop."),
    ("panel_0042", "A steep price tag of five hundred gems unlocks the Basic Horse Riding skill."),
    ("panel_0043", "Clueless summoner Anis gets forced to swipe the gems for an instant download!"),
    ("panel_0044", "A golden chime flashes overhead, confirming Han successfully learned the equestrian skill book."),
    ("panel_0045", "Han grabs the wet leather reins, stepping up into the armored horse stirrups."),
    ("panel_0046", "Aaron gasps in disbelief, asking how this broke farmer became a cavalry master."),
    ("panel_0047", "Our protagonist smirks with icy resolve, knowing the tactical balance has finally flipped."),
    ("panel_0048", "The united cavalry charges across the storm, ready to trample the remaining monsters."),
    ("panel_0049", "Golden system text flashes across reality, declaring it is finally time for retribution!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch30"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch30")
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
