"""Pick Me Up Chapter 26 Golden Standard Script Generator (70 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Describes the intact doomed city, the terrifying 2,000+ goblin horde, the Twin Goddesses permadeath stake,
  the mystery of the upstream dam, and Han's audacious decapitation strike!
- 1:1 synchronization across all 70 clean story panels.
- Strictly 10 to 14 words per beat.
- Evaluated and verified by Kimi-K3 Quality Gatekeeper.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path("D:/Python Projects/Manga Recap")
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from manga_recap.core.schema import ScriptFile, load_model  # noqa: E402
from scripts.batch_generate_pick_me_up_workflow_master import (  # noqa: E402
    build_script_blocks,
    clean_and_prune_panels,
    format_sentence,
)
from scripts.quality_gatekeeper import check_script_quality  # noqa: E402

STORY_BEATS = [
    # Act 1: The Pristine City & The Scouting Window (Panels 2-18)
    ("panel_0002", "We jump right back into the action as Han inspects the pristine city streets."),
    ("panel_0003", "Crisp autumn leaves flutter across beautiful cobblestones that our crew once explored as ruins."),
    ("panel_0005", "Jenna tugs Han's sleeve, asking anxiously, 'Why are we back in time?'"),
    ("panel_0006", "Han grins confidently, telling his bewildered party to treat this anomaly like any dungeon."),
    ("panel_0007", "A friendly five-minute countdown timer appears, giving the squad time to scout ahead freely."),
    ("panel_0008", "Han dispatches fast scouts, barking, 'Map every single choke point and report back immediately!'"),
    ("panel_0010", "Climbing the central watchtower, Han gets his first clear view of the battlefield."),
    ("panel_0011", "Local city guards tremble in their boots, clearly lacking any professional combat experience."),
    ("panel_0012", "Over two thousand noisy green goblins pack the northern woods like rowdy football fans."),
    ("panel_0013", "A separate monster company marches beside the eastern riverbank, kicking up trails of dust."),
    ("panel_0014", "Han leans over the parapet, whistling, 'Now that is what I call bad odds.'"),
    ("panel_0015", "Heavily armored knights sit on horseback, looking fancy but functionally useless without leadership."),
    ("panel_0016", "Most starter survival stages simply require holding out until the stage timer reaches zero."),
    ("panel_0017", "If that were true, Han could easily outmaneuver the horde by using decoys."),
    ("panel_0018", "Jenna chuckles mischievously, knowing Eolka's flame artillery could easily kite those clumsy monsters forever."),

    # Act 2: The Red Alert & The Twin Goddesses Catch (Panels 19-35)
    ("panel_0019", "Edis's squad rushes into the courtyard just as dark clouds gather overhead dramatically."),
    ("panel_0020", "Three golden warning banners light up the sky, signaling an elite difficulty rating."),
    ("panel_0021", "The official mission prompt appears: Protect the city and repel the invading forces!"),
    ("panel_0022", "Ten player heroes and three hundred jittery town guards must withstand thousands of attackers."),
    ("panel_0023", "Han gathers everyone around the stone table to outline their grand defensive strategy."),
    ("panel_0024", "Jenna rolls her eyes, observing that panicked villagers act like programmed background extras."),
    ("panel_0025", "Frightened citizens sprint toward the inner quarter while drums thunder beyond the walls."),
    ("panel_0026", "Edis swallows nervously, asking how ten people can possibly defend such massive gates."),
    ("panel_0027", "Han slams the war table, barking, 'If one green gremlin enters, we all die!'"),
    ("panel_0028", "Han makes it crystal clear that killing grunts means nothing if gates fall."),
    ("panel_0029", "A nervous recruit clutches his wooden spear, wondering how anyone survives such odds."),
    ("panel_0030", "A cowardly recruit whispers, 'Can we sneak out and hide inside caves?'"),
    ("panel_0031", "Han sneers back coldly, 'Deserters get deleted by the system on sight!'"),
    ("panel_0032", "Walking to the square, Han points his sword at the soaring stone cathedral."),
    ("panel_0033", "Two winged marble goddess statues radiate an intense, pulsing golden glow across cobblestones."),
    ("panel_0034", "Han drops the real horror: 'Protect that glowing marble monument with your actual lives!'"),
    ("panel_0035", "The moment that twin goddess monument breaks, the entire defense mission collapses instantly."),

    # Act 3: Grandmaster Calculations & The Dam Mystery (Panels 36-55)
    ("panel_0036", "The veteran warrior whines, 'Why do developers force us to babysit useless rocks?!'"),
    ("panel_0037", "Han reminds his team that failing a mission here deletes their character profiles forever."),
    ("panel_0038", "Permadeath means mistakes have permanent consequences, so retreat is never an acceptable option."),
    ("panel_0039", "Running into the hills changes nothing because cowardice only guarantees a game-over screen."),
    ("panel_0040", "Edis tightens her belt, determined to find whatever hidden trick the developers left."),
    ("panel_0041", "She observes that the charging goblin ranks curiously lack heavy wooden siege ladders."),
    ("panel_0042", "Han tasks Edis's squad with holding the northern parapets alongside the human archers."),
    ("panel_0043", "Noticing her skeptical grimace, Han asks playfully, 'Got complaints about my brilliant leadership, Edis?'"),
    ("panel_0044", "Static defense behind stone ramparts simply plays directly into the enemy's numbers advantage."),
    ("panel_0045", "Edis snaps back defensively, 'Holding that north gate will not win this war!'"),
    ("panel_0046", "Han smirks back, 'I know, which is why we are attacking directly!'"),
    ("panel_0047", "Even combining both parties on one wall leaves the eastern flank completely unprotected."),
    ("panel_0048", "A battle of pure attrition favors the horde, leaving human defenders slowly surrounded."),
    ("panel_0049", "Han taps his gaming memory, recalling the strange floodwaters from the lower floors."),
    ("panel_0050", "Heavy rainstorms on the seventh floor originally caused an upstream river dam to burst."),
    ("panel_0051", "That historic flood swept away the eastern ramparts when this city was destroyed."),
    ("panel_0052", "Every environmental breadcrumb points straight toward that critical upstream stone river dam!"),
    ("panel_0053", "Frustration boils over as Han punches the stone wall, demanding where enemy cavalry went."),
    ("panel_0054", "Jenna's freckled face lights up as an important sound memory suddenly clicks into place!"),
    ("panel_0055", "The sharp archer reveals that she heard galloping horse hooves through the rainstorm!"),

    # Act 4: The Decapitation Counter-Strike (Panels 57-74)
    ("panel_0057", "Rain drenches Jenna's hair as she mimics the steady rhythm of galloping warhorses."),
    ("panel_0058", "A stealthy mounted vanguard prowls near the eastern river under cover of storm."),
    ("panel_0059", "Han's eyes flash with realization: the enemy sent elite cavalry to sabotage that dam!"),
    ("panel_0060", "The goblins plan to breach the dam and flood the unguarded eastern gate!"),
    ("panel_0061", "Edis grabs Jenna's collar, shrieking, 'Why did you keep that horse intel secret?!'"),
    ("panel_0062", "Han commands Edis, 'Take the north wall and buy every precious minute!'"),
    ("panel_0063", "Flashing a predatory grin, Han promises, 'We will return before your north wall falters.'"),
    ("panel_0064", "Edis nods with determination, swearing to keep the northern ramparts standing until victory."),
    ("panel_0065", "The dark-haired warrior leads her recruits up the battlements to hold the line."),
    ("panel_0066", "Panicked rookies whisper in horror, 'Is our commander seriously charging into that horde?!'"),
    ("panel_0067", "Aaron gulps hard, asking nervously, 'Han, are we really ditching these safe walls?'"),
    ("panel_0068", "Han laughs out loud, 'Hiding behind walls just makes you a dead corpse!'"),
    ("panel_0069", "Instead of waiting to drown, his team will intercept the goblin cavalry vanguard!"),
    ("panel_0070", "Han leads his squad sprinting straight out through the eastern gate into rain!"),
    ("panel_0071", "Jenna grins with excitement as she realizes their leader plans to hunt the hunters!"),
    ("panel_0072", "Han hoists his heavy steel blade, declaring coldly, 'We take their commander's head!'"),
    ("panel_0073", "Party One charges into the stormy wilderness, hunting down the elite mounted monsters!"),
    ("panel_0074", "Party Two locks shields above the gates, bracing for an epic siege battle!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch26"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    # Verify panel alignment
    panel_pids = [p["panel_id"] for p in panels]
    beat_pids = [pid for pid, _ in STORY_BEATS]
    if panel_pids != beat_pids:
        print(f"Mismatch in panels! Kept panels: {len(panel_pids)}, Beats: {len(beat_pids)}")
        missing = set(panel_pids) - set(beat_pids)
        extra = set(beat_pids) - set(panel_pids)
        if missing:
            print(f"Missing from beats: {missing}")
        if extra:
            print(f"Extra in beats: {extra}")
        sys.exit(1)

    # Verify word counts
    for pid, txt in STORY_BEATS:
        wc = len(txt.split())
        if wc < 10 or wc > 14:
            print(f"ERROR: {pid} has {wc} words: '{txt}'")
            sys.exit(1)

    script_dict = build_script_blocks(panels, lines_map, "ch26")
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
    if res.suggestions:
        print("Suggestions:", res.suggestions)

    if score < 7:
        print("FAILED GATEKEEPER! Score must be >= 7/10.")
        sys.exit(1)


if __name__ == "__main__":
    main()
