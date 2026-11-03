"""Pick Me Up Chapter 18 Golden Standard Script Generator (56 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Describes the six-man synthesis execution, Edis Callen leveling up, town survival training, and Jenna vs Edis dagger sparring!
- 1:1 synchronization across all 56 clean story panels.
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
    # Act 1: Setting the Morning Stakes & The 6-Man Call (Panels 3-16)
    ("panel_0003", "Morning breaks over Niflheim, but yesterday's miracle brings zero peace in this cruel game."),
    ("panel_0004", "Han leans against the railing, watching nervous townspeople scramble into a frantic formation."),
    ("panel_0005", "Everyone stares in shock, unable to comprehend how a one-star dismantled a veteran."),
    ("panel_0006", "An excited recruit cheers, calling Han the absolute greatest fighter in town."),
    ("panel_0007", "Han grabs Jenna's cheeks, demanding why she leaked their top-secret master strategy."),
    ("panel_0008", "The terrified villagers bow deeply, thanking Han for saving them from bandit newcomers."),
    ("panel_0009", "Han exhales cold breath, bluntly telling the crowd they completely misunderstand his motives."),
    ("panel_0010", "The humble townspeople keep bowing anyway, genuinely grateful to survive another brutal day."),
    ("panel_0011", "Han cuts them off coldly, declaring he only protects recruits showing real potential."),
    ("panel_0012", "Turning back toward the courtyard, Han reminds them that survival offers zero handouts."),
    ("panel_0013", "Suddenly his eyes flash blue as he barks out six veteran names."),
    ("panel_0014", "Bandit Louis chuckles nervously, trying to convince his friends this is routine hunting."),
    ("panel_0015", "Jenna catches the discrepancy: why call six heroes when parties only hold five?"),
    ("panel_0016", "Han drops the horror bomb: six lazy slackers were selected as synthesis food!"),

    # Act 2: The Brutal Synthesis & Reality Check (Panels 17-32)
    ("panel_0017", "Pure horror sweeps across the plaza as the reality of permanent deletion hits."),
    ("panel_0018", "Louis screams in denial, shouting that his boys tried their best to survive."),
    ("panel_0019", "Han calls forward Aaron and Dika, demanding an honest review of these bullies."),
    ("panel_0020", "Aaron steps up firmly, exposing how these useless thugs slept during training."),
    ("panel_0021", "Jenna adds that these bandits only carried lightweight meat she had already butchered."),
    ("panel_0023", "Han slashes Louis across the jaw, snarling that even livestock carries cargo!"),
    ("panel_0024", "Tiny fairy Iselle screeches from above, threatening instant execution for dragging feet."),
    ("panel_0025", "The condemned thugs collapse, desperately weeping and begging Master Anis for any mercy."),
    ("panel_0026", "Jenna nervously asks Han which lucky hero will receive all this sacrificial exp."),
    ("panel_0027", "Desperately clawing at the stone floor, the terrified bandit sobs for another chance."),
    ("panel_0028", "Six character cards shatter into dust, elevating Edis Callen to three-star powerhouse!"),
    ("panel_0029", "Edis descends surrounded by golden light, permanently unlocking boosted stats and trap-disarming skills."),
    ("panel_0030", "Han delivers his coldest ultimatum: prove your worth immediately or become someone's food."),
    ("panel_0031", "The surviving recruits tremble, realizing Master Anis deletes useless fodder without second thought."),
    ("panel_0032", "A weeping newcomer clutches his shaking hands, crying that he lacks combat talent."),

    # Act 3: Town Logistics & Strategy (Panels 33-44)
    ("panel_0033", "Han instantly takes charge, ordering veteran craftsmen to train every single newcomer."),
    ("panel_0034", "Blacksmith Enok grumbles that forging takes years, but Han insists everyone learn skills."),
    ("panel_0035", "Han smirks ruthlessly, promising a brutal beatdown to anyone slacking during mandatory practice."),
    ("panel_0036", "Jenna and Enok assign daily chores, opening up hunting and woodworking for survivors."),
    ("panel_0037", "Up in reality, clueless Master Anis taps logout after venting daily gacha frustration."),
    ("panel_0038", "Jenna teases Han smiling, suspecting our cold master ranker secretly cares about people."),
    ("panel_0039", "Han brushes her off, explaining that careless rookie deaths slow down tower clearance."),
    ("panel_0040", "The monolithic tenth floor looms above, warning they need a powerhouse secondary party."),
    ("panel_0041", "The next morning brings the aroma of freshly baked bread across stone fortress."),
    ("panel_0042", "A friendly townswoman surprises Han, presenting a metal tray loaded with golden rolls."),
    ("panel_0043", "Han inspects the pastry in surprise, wondering where on earth she found wheat."),
    ("panel_0044", "She reveals she ground wild potatoes, and Han notes good food slashes stress."),

    # Act 4: Sparring Climax & Hard Truths (Panels 46-61)
    ("panel_0046", "Finishing his potato breakfast, Han marches newly crowned three-star Edis to arena."),
    ("panel_0047", "Jenna is peacefully tuning her hunting bow when Han suddenly interrupts her morning."),
    ("panel_0048", "Our ruthless leader points forward, commanding Jenna to duel Edis using daggers."),
    ("panel_0049", "Jenna panics loudly, arguing she is strictly a ranged sniper, not dagger brawler!"),
    ("panel_0050", "Edis spins twin steel blades at blinding speed, creating a whistling wind vortex."),
    ("panel_0051", "Sparks explode across the ring as Jenna charges, trading lightning-fast slashes with Edis."),
    ("panel_0052", "Onlookers watch with jaws dropped as our hunter completely overwhelms three-star Edis!"),
    ("panel_0053", "Jenna unleashes a roaring blue slash, shouting that she is definitely old enough!"),
    ("panel_0054", "A devastating kick connects cleanly, sending three-star Edis crashing backward across stone floor."),
    ("panel_0056", "Both combatants drop down exhausted on stone, panting heavily as white vapor rises."),
    ("panel_0057", "Jenna catches her breath smiling, clarifying she is simply a humble hunter's daughter."),
    ("panel_0058", "She reminds Edis that their current strength came entirely through relentless daily training."),
    ("panel_0059", "Han steps forward encouragingly, assuring Edis that her three-star stat scaling closes gaps."),
    ("panel_0060", "Aaron drags a heavy wooden dummy nearby, comically shouting that Han is lying!"),
    ("panel_0061", "Clasping her bruised knuckles, Edis bows respectfully, swearing to grind until tower conquest."),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch18"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch18")
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
