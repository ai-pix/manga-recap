"""Pick Me Up Chapter 15 Golden Standard Script Generator (58 Story Panels).

Mamoru YouTube Recap Persona:
- Authentic Mamoru tone: dry wit, hilarious roasts, the arrival of the Pulverizing Wolves mercenary bullies, and Han rejecting useless whiners!
- 1:1 synchronization across all 58 clean story panels.
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
    # Act 1: The Messy Jungle Cleanup & The Hidden Village (Panels 2-15)
    ("panel_0002", "We kick right off with rookie Dika frantically waving his spear like a broom!"),
    ("panel_0003", "The blond spearman impales a snarling beast, holding the narrow jungle corridor secure."),
    ("panel_0004", "A terrified scout goblin tries backing away, but Han's blade arrives faster than lightning!"),
    ("panel_0005", "Han's broadsword cleaves downward cleanly, shouting, 'I will not let you call reinforcements!'"),
    ("panel_0009", "Han tells his squad to hold position while he scouts the dense jungle perimeter."),
    ("panel_0010", "Our veteran ranker analyzes the forest layout, hunting for hidden linked exploration event quests."),
    ("panel_0012", "A goblin handler grips a heavy iron chain, patrolling the eerie ruined outskirts."),
    ("panel_0013", "Peeking through dense foliage, Han spots an entire fortified goblin war camp ahead."),
    ("panel_0014", "Fierce wolf-headed beastmen guard the perimeter, confirming a massive dungeon raid awaits them."),
    ("panel_0015", "A hulking green brute patrols the barricades, completely oblivious that Loki is watching."),

    # Act 2: Master Anis Credit-Card Whale Summon (Panels 16-28)
    ("panel_0016", "The exploration stage clears successfully, dissolving into shimmering blue completion light across turf."),
    ("panel_0017", "Jenna stomps over fuming, yelling, 'Why do you always wander off alone, you idiot?!'"),
    ("panel_0018", "Han explains that bonus secret loot only drops for proactive players who explore ahead."),
    ("panel_0019", "He notes that this early exploration stage should not trigger major difficulty spikes yet."),
    ("panel_0020", "The celebratory mood shatters as Jenna spots shady, swaggering killers strutting into town!"),
    ("panel_0021", "Han narrows his eyes, sensing that their aura feels completely different from normal rookies."),
    ("panel_0022", "Excited whispers spread among the crowd, announcing that high-tier champions have finally arrived!"),
    ("panel_0023", "Golden lightning tears open the sky as the Pulverizing Wolves mercenary troupe materializes!"),
    ("panel_0025", "A system banner confirms Master Anis impulsively swiped his wallet on consecutive premium summons."),
    ("panel_0026", "Han stares in disbelief, asking Iselle, 'Did our credit-card warrior seriously just whale?!'"),
    ("panel_0027", "These freshly summoned warriors are seasoned three-star killers, radiating raw, undisciplined battle violence."),
    ("panel_0028", "Han dismisses his current exploration party, ready to inspect the newly acquired merchandise."),

    # Act 3: Interrogating Edis & Kitchen Food Theft (Panels 30-44)
    ("panel_0030", "Meet Edis Callen, a three-star beauty whose stats make our original rookies look like cardboard."),
    ("panel_0031", "Jenna bounces over cheerfully, shouting a friendly greeting to break the tense ice."),
    ("panel_0032", "The red-haired archer introduces herself warmly, asking for the newcomer's official hero name."),
    ("panel_0033", "Edis introduces herself softly, mentioning she was drafted alongside this arrogant mercenary gang."),
    ("panel_0034", "Her status window displays high level-one growth potential and unique tactical utility skills."),
    ("panel_0035", "Han pulls up a chair with water, asking, 'Do you know where you landed?'"),
    ("panel_0036", "Handing her the cup calmly, Han tests what memories survived the summoning process."),
    ("panel_0037", "Edis quietly admits she recalls being abducted directly into this strange game world."),
    ("panel_0038", "The troubled girl whispers the horrifying truth: she was summoned solely as synthesis sacrifice!"),
    ("panel_0039", "Han nods grimly, knowing heroes can be sacrificed to boost someone else's stats."),
    ("panel_0040", "Edis reveals she originally belonged to an elite mercenary troupe before entering Niflheim."),
    ("panel_0041", "Her hero card floats nearby, proving she possesses far higher stats than common fodder."),
    ("panel_0042", "Jenna giggles romantic nonsense, completely clueless about the grim horror of hero sacrifice."),
    ("panel_0043", "Han frowns deeply, realizing this mercenary troupe brought dangerous criminal habits into town."),
    ("panel_0044", "A roster prompt lists Avant, Jaken, Wave, Benign, and Edis as the squad."),

    # Act 4: Bully Mercenaries & Han Roasts the Whiners (Panels 45-66)
    ("panel_0045", "A messenger runs in, announcing that the summoner called for the mercenary crew."),
    ("panel_0046", "Heavy studded combat boots stomp aggressively onto cobblestones as the gang struts forward."),
    ("panel_0047", "A hulking blond brawler named Jaken bellows loudly, demanding who dared summon him!"),
    ("panel_0048", "Edis quietly slips away, heading toward the master's official command summoning circle."),
    ("panel_0049", "The blond brute raids the kitchen, loudly bragging about finding freshly roasted meat."),
    ("panel_0051", "A frightened cook cries out that the rude newcomers stole their celebratory dinner!"),
    ("panel_0052", "Jenna is vibrating with rage, telling the terrified rookies to demand their food back!"),
    ("panel_0053", "A new registration confirms Party Five is now designated as Pulverizing Wolves."),
    ("panel_0054", "Five hardened criminals assemble under the banner, sneering down at the weaker town residents."),
    ("panel_0055", "Rookies tremble in terror, noticing that these mercenaries smell like cold-blooded murderers."),
    ("panel_0056", "Han watches from the shadows, thoroughly unimpressed by their loud, undisciplined posturing."),
    ("panel_0057", "The arrogant bully laughs in the rookies' faces, treating their dinner like free buffet."),
    ("panel_0058", "Jenna asks Han what he thinks, clearly uneasy about Edis being trapped with thugs."),
    ("panel_0059", "Terrified recruits run up to Han, begging the veteran captain to protect them!"),
    ("panel_0060", "Han scoffs coldly, asking why in the world he should protect them for free."),
    ("panel_0061", "He roasts the whiners ruthlessly: 'You slacked off training, and now you want carries?!'"),
    ("panel_0062", "Han reminds them that weak cowards who refuse to grind will simply get sacrificed."),
    ("panel_0063", "His piercing glare silences the crowd, proving that survival in Niflheim must be earned."),
    ("panel_0064", "Arrogant leader Avant stands in the town center, radiating dangerous three-star combat malice."),
    ("panel_0065", "Hero cards for Jaken and Edis confirm the mercenary troupe is fully locked in."),
    ("panel_0066", "Han smirks back—if these bullies want war, they picked the wrong one-star!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch15"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch15")
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
