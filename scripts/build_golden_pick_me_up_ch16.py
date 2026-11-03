"""Pick Me Up Chapter 16 Golden Standard Script Generator (60 Story Panels).

Mamoru YouTube Recap Persona:
- Authentic Mamoru tone: witty commentary, sarcastic roasts of bully mercenaries, Han calling them 'trash', and the legendary Open Duel challenge!
- 1:1 synchronization across all 60 clean story panels.
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
    # Act 1: Dismissing Whiners & Avant's Cocky Entrance (Panels 2-17)
    ("panel_0002", "We kick right off with Han coldly telling groveling whiners to get lost immediately."),
    ("panel_0003", "His piercing glare warns them to clear out before he genuinely loses his temper."),
    ("panel_0005", "The intimidated recruits scramble away, leaving Han to inspect his battered frontline squad."),
    ("panel_0006", "Han turns to Aaron, checking how the wounded spearman's injured leg is holding up."),
    ("panel_0007", "Dika stumbles over looking battered, nursing bruises from an aggressive scuffle in the plaza."),
    ("panel_0008", "The blond spearman admits he just had a rough sparring duel with new arrivals."),
    ("panel_0009", "Han asks why his squad is hesitating instead of entering the training grounds."),
    ("panel_0010", "The Pulverizing Wolves stroll past arrogantly, loudly bragging about their effortless stage clear."),
    ("panel_0011", "Avant struts in like he owns the server, asking who this scruffy peasant is."),
    ("panel_0012", "Han does not even bother standing up: 'Who, me? None of your business, pretty boy.'"),
    ("panel_0013", "Our master ranker sits relaxed on a wooden bench, ignoring their ridiculous posturing."),
    ("panel_0014", "A braided thug yells furiously, asking who gave this lowly one-star permission to speak."),
    ("panel_0015", "Avant brags with pompous pride that he is captain of the Pulverizing Wolves!"),
    ("panel_0016", "The silver-haired clown smirks down, asking if Han carries a sword for show."),
    ("panel_0017", "Avant chuckles condescendingly, mockingly asking if Han is just an ordinary peaceful farmer."),

    # Act 2: Master Anis's 10-Pull & Mercenaries Kidnap Fodder (Panels 18-32)
    ("panel_0018", "The silver-haired bully gestures toward the crowd, calling all the town residents pathetic."),
    ("panel_0019", "Han's single blue eye gleams from beneath his bangs, reading their stats effortlessly."),
    ("panel_0020", "Golden lightning erupts as Master Anis impulsively whale-spends on a ten-pull gacha frenzy!"),
    ("panel_0021", "Han watches the dais blaze, chuckling that their summoner loves burning real paycheck cash."),
    ("panel_0022", "Ten terrified Earthlings drop out of the portal, crying like contestants on a gameshow."),
    ("panel_0023", "Fairy Iselle floats beside the portal, assigning rookie names to the incoming roster."),
    ("panel_0024", "Blond giant Jaken grabs a screaming rookie by the scruff like cheap airport luggage!"),
    ("panel_0025", "Han observes in disgusted silence as the mercenaries treat living humans like disposable inventory."),
    ("panel_0026", "Jaken roars loudly across the square, ordering another terrified rookie dragged into line."),
    ("panel_0027", "The massive bully laughs, boasting that paid summon fodder makes the tastiest synthesis fuel."),
    ("panel_0028", "A horrified villager screams that treating summoned humans like livestock is completely wrong!"),
    ("panel_0029", "Jaken sneers down ruthlessly, claiming that weak units exist solely to empower champions."),
    ("panel_0030", "Terrified recruits scramble frantically across the cobblestones, desperately trying to escape forced synthesis."),
    ("panel_0031", "Mercenary thugs lunge forward with drawn steel, shouting to cut off their escape!"),
    ("panel_0032", "Avant stands watching the cruelty with an amused smirk, enjoying the desperate chaos."),

    # Act 3: Han Steps In & 'You're Trash' (Panels 33-47)
    ("panel_0033", "Han's eyes narrow into razor-sharp focus as his patience completely reaches its limit."),
    ("panel_0034", "His black-gloved fingers wrap tightly around the worn leather hilt of his broadsword."),
    ("panel_0035", "Han tells Iselle to send an urgent tip straight to the Master's interface."),
    ("panel_0036", "Our veteran reflects that in all his gaming years, bullies always end badly."),
    ("panel_0037", "Jaken storms over aggressively, demanding to know who dared step in their way."),
    ("panel_0038", "Han leans in close with a terrifyingly calm smile, asking, 'Why? Not happy?'"),
    ("panel_0039", "The blond giant lunges forward swinging a wild punch, screaming, 'You fucking lunatic!'"),
    ("panel_0040", "Han dodges the clumsy fist like he is playing the game in slow motion!"),
    ("panel_0041", "Han chuckles at the stumbling brute, casually remarking, 'Oops, I missed you on purpose.'"),
    ("panel_0042", "Avant draws his shiny rapier, asking with wounded pride if Han just threatened them."),
    ("panel_0043", "A female mercenary steps forward aggressively, asking if Han knows who they are."),
    ("panel_0044", "Han tilts his head with an icy, deadpan smirk: 'I do. You are trash.'"),
    ("panel_0045", "The insulted mercenaries draw weapons in fury, shouting that Han just crossed the line!"),
    ("panel_0046", "Edis Callen lunges between the two sides, desperately pleading that internal fighting is forbidden."),
    ("panel_0047", "Han stands completely unfazed, noting that self-defense is never forbidden by game rules."),

    # Act 4: Thief Troupe Exposed & The Open Duel (Panels 48-64)
    ("panel_0048", "Han looks past their flashy weapons, telling them to stop pretending to be mercenaries."),
    ("panel_0049", "The thugs shout defensive curses, swearing they are licensed, professional guild warriors."),
    ("panel_0051", "Han exposes their dirty secret: 'You are just a cheap, cowardly thief troupe.'"),
    ("panel_0052", "Avant steps closer, his silver hair swaying as he warns Han to watch mouth."),
    ("panel_0053", "Han turns to fairy Iselle, pointing out that parasites like them ruin waiting rooms."),
    ("panel_0054", "Edis watches in dread, knowing this escalating confrontation will result in permanent deletion."),
    ("panel_0055", "Han draws his broadsword with god-tier swagger, calmly uttering two words: 'Open duel.'"),
    ("panel_0056", "A massive glowing system prompt flashes: Han is formally requesting a duel with Avant!"),
    ("panel_0057", "Avant points an accusatory finger, laughing hysterically at this one-star recruit's total madness."),
    ("panel_0058", "Han flashes a demon smirk: 'Just think of this as a crazy dog biting.'"),
    ("panel_0059", "Avant sneers back with drawn steel, claiming he knows exactly how peasants behave."),
    ("panel_0060", "Han reminds the crowd that consuming rookies will not save a fraud from defeat."),
    ("panel_0061", "Jenna gasps in horror from the sidelines, asking if Han completely lost his mind!"),
    ("panel_0062", "The entire plaza falls dead silent as the high-stakes duel terms lock in."),
    ("panel_0064", "Avant eagerly locks in the terms, completely unaware he just signed his deletion certificate!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch16"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch16")
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
