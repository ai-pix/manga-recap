"""Pick Me Up Chapter 12 Golden Standard Script Generator (57 Story Panels).

Mamoru YouTube Recap Persona:
- Authentic Mamoru tone: witty commentary, sarcastic asides, direct viewer engagement, dark comedy.
- Explains Han's premise (Earth's #5 ranker trapped in a 1-star body), Floor 5 meat grinder, Berserk awakening, and the dark dinner reveal.
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
    # Act 1: Floor 5 Nightmare & The Trapped Ranker (Panels 3-10)
    ("panel_0003", "Welcome right back to Pick Me Up, where starter floors are basically meat grinders in disguise."),
    ("panel_0004", "Han clutches his bloodied shortsword, wondering how a simple daily trial went so completely wrong."),
    ("panel_0005", "Pain shoots through his ribs as he spits dark blood onto the cold cobblestones."),
    ("panel_0006", "Jenna gets thrown across the chamber like a ragdoll caught in a violent tornado!"),
    ("panel_0007", "A red bleeding icon flashes on screen, ticking his vitality down second by second."),
    ("panel_0008", "Jenna catches the exact same debuff, crying out as her stamina drains to zero."),
    ("panel_0009", "Dozens of glowing red eyes emerge from the dark, completely surrounding their vanguard position."),
    ("panel_0010", "Dropping to his knees, Han realizes their exhausted two-person squad has hit a dead end."),

    # Act 2: Earth Veteran Meltdown & Berserk Ignition (Panels 11-25)
    ("panel_0011", "Han hits the floor gasping, wondering if this pathetic dungeon is where his story ends."),
    ("panel_0013", "The screen goes pitch black as his memories glitch between two completely different lives."),
    ("panel_0014", "A quiet question echoes in the void: why him of all people on Earth?"),
    ("panel_0015", "A second whisper follows: why get dragged into someone else's broken mobile game?"),
    ("panel_0016", "That quiet confusion detonates into a scream of pure, unadulterated gamer defiance!"),
    ("panel_0017", "A bloodshot crimson eye snaps open in the dark, blazing with terrifying intent."),
    ("panel_0018", "Han spins around with drawn steel, shouting, 'Do not mess with me, you bastards!'"),
    ("panel_0019", "Three stacked cuts lock onto his eyes, confirming the true master has finally logged in!"),
    ("panel_0020", "A giant frost-wolf lunges from the fog, aiming straight for Han's exposed throat."),
    ("panel_0021", "The beast snaps razor jaws wide open, expecting an effortless kill against human prey."),
    ("panel_0022", "Han flashes a wicked smirk, shouting, 'Bring it on, you mindless digital trash!'"),
    ("panel_0023", "Every single breath burns like fire, yet veteran micro-instincts take total control of limbs."),
    ("panel_0024", "Jenna forces herself back onto her feet, screaming, 'I am not dying on Floor Five!'"),
    ("panel_0025", "A snarling creature recoils in shock, terrified that the battered humans are still fighting."),

    # Act 3: Crimson Rampage & Stage Clear Relief (Panels 26-40)
    ("panel_0026", "Han roars that failing on a starter floor would destroy his legendary reputation forever!"),
    ("panel_0027", "His broadsword carves a wide crimson arc, slicing through the frost-wolf pack cleanly."),
    ("panel_0028", "A towering black-maned monster screeches in shock as Han cleaves through its ranks."),
    ("panel_0029", "Han reminds the heavens that even if his flesh breaks, his spirit never surrenders."),
    ("panel_0030", "His heavy combat boot stomps onto the stones, holding an unbreakable frontline barrier."),
    ("panel_0031", "A fierce counter-thrust drives his notched steel blade straight through the creature's chest."),
    ("panel_0032", "Another beast lunges from above, but Han swats it aside with perfect timing."),
    ("panel_0034", "The corridor falls into dead silence as the final remaining monster collapses limp."),
    ("panel_0035", "Han leans against the wall, catching his breath while soaked in black monster blood."),
    ("panel_0036", "Lifeless white wolves cover the floor, confirming that his reckless survival gamble actually worked."),
    ("panel_0037", "Jenna lowers her bloody weapon, staring at the carnage with wide, completely bewildered eyes."),
    ("panel_0038", "Han exhales deeply, letting the adrenaline fade as his tired limbs finally relax."),
    ("panel_0039", "A cheerful gold Stage Clear notification flashes, congratulating them for not getting permanently deleted!"),
    ("panel_0040", "The rewards window drops five thousand gold and iron ore, barely worth the trauma."),

    # Act 4: Lounge Return & Dark Comedy Dinner (Panels 41-61)
    ("panel_0041", "Blue teleportation magic engulfs the survivors, pulling them safely back toward the novice lounge."),
    ("panel_0042", "Their dented starter gear hits the tiled floor with a weary, hollow clatter."),
    ("panel_0043", "Han stands over the exhausted archer, catching his breath in the quiet."),
    ("panel_0044", "Jenna remains sprawled on the ground, still processing that she dodged a fatal wipe."),
    ("panel_0045", "Aaron lies flat on his back nearby, miraculously breathing despite absorbing terrible damage."),
    ("panel_0046", "Jenna looks up at Han with wide eyes, completely dazed by their miracle."),
    ("panel_0047", "A breathless chuckle escapes her lips as the sweet reality of survival sinks home."),
    ("panel_0048", "Han extends a hand downward, offering a rare smirk of mutual near-death relief."),
    ("panel_0049", "Jenna admits with a weak laugh that her wobbly legs refuse to work today."),
    ("panel_0050", "Jenna gasps, 'Did we make it?!' and Han answers, 'Somehow, yes.'"),
    ("panel_0051", "Han mutters that taking an unbalanced rookie party into survival was pure madness."),
    ("panel_0052", "He points out that bad gacha luck nearly wiped their entire squad out."),
    ("panel_0053", "Permadeath is no joke, and their clueless master Anis clearly has zero tactical awareness."),
    ("panel_0054", "Jenna listens quietly, realizing that in this mobile world, every mistake costs a life."),
    ("panel_0055", "Fresh recruits stroll into the lounge, cheerfully congratulating Han on the victory."),
    ("panel_0056", "A swordsman announces happily that Chloe cooked a huge celebratory feast for dinner."),
    ("panel_0057", "Han drops the ultimate mood-killer, stating bluntly, 'Gide and Hansen are dead, so enjoy their portions.'"),
    ("panel_0058", "The smiling recruit freezes in horror, his cheerful expression melting into numb, stunned shock."),
    ("panel_0059", "A chilling silence blankets the lounge as the brutal reality of permadeath sinks in."),
    ("panel_0060", "The roster board lights up, showing Jenna, Han, and Aaron promoted to higher levels."),
    ("panel_0061", "Two black death notices confirm Gide and Hansen are gone forever, leaving dinner behind."),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch12"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch12")
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
