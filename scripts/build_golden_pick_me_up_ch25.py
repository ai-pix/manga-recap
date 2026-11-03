"""Pick Me Up Chapter 25 Golden Standard Script Generator (72 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Describes the grueling Floor 10 training grind, Edis's grim return, Master Anytng's reckless launch,
  and the chilling realization of the doomed 5th floor pre-destruction city!
- 1:1 synchronization across all 72 clean story panels.
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
    # Act 1: The Floor 10 Boot Camp Hell (Panels 3-22)
    ("panel_0003", "We kick off with fiery mage Eolka throwing a massive tantrum during boot camp."),
    ("panel_0004", "Han glares back with glowing blue eyes, asking chillingly, 'You want to disobey me?'"),
    ("panel_0005", "The trembling mage instantly wilts under his gaze, whimpering in complete submission."),
    ("panel_0006", "Eolka groans in surrender, shouting, 'Fine, I will cast whatever you tell me to!'"),
    ("panel_0007", "She unleashes three blazing fireballs, drilling rapid Class One ignition magic under supervision."),
    ("panel_0008", "Han notes that raw magic without split-second trigger discipline is completely useless."),
    ("panel_0009", "Jenna notches another arrow, shouting that Floor Ten will slaughter them without intense practice."),
    ("panel_0010", "Dodging like a seasoned veteran, Han weaves through incoming arrow fire effortlessly."),
    ("panel_0011", "Catching his breath, Han smirks and warns, 'Save the useless compliments for after survival.'"),
    ("panel_0012", "A golden system notification confirms Han just unlocked the legendary Projectile Defense combat skill."),
    ("panel_0013", "Beginner Sword-Shield Technique immediately spikes to Level Six after endless grueling drills."),
    ("panel_0014", "Han smiles like a greedy gacha gamer who just pulled an ultra-rare skill drop."),
    ("panel_0015", "Jenna spins with lethal speed, ditching her bow to slash with a hunting dagger."),
    ("panel_0016", "Watching her smooth transition, Han marvels at how rapidly this novice archer improves."),
    ("panel_0017", "Jenna winks playfully, teasing, 'Did our ruthless master ranker just pay me a compliment?'"),
    ("panel_0018", "Han grabs her cheeky face, laughing, 'I am someone who beats up smart mouths.'"),
    ("panel_0019", "Meanwhile, poor Aaron locks himself in his barracks, sweating blood to grind pain resistance."),
    ("panel_0020", "Eolka continues detonating targets at the magic hall to expand her explosive burst capacity."),
    ("panel_0021", "Hopeless one-star recruits stumble around the yard, looking like disposable fodder waiting for execution."),
    ("panel_0022", "Han shudders in horror, praying their clueless summoner does not draft these helpless rookies."),

    # Act 2: Edis Returns & The Looming Trap (Panels 23-44)
    ("panel_0023", "The next morning, Edis leads her battered exploration party limping back into town plaza."),
    ("panel_0024", "Seeing their severed limbs, Han demands, 'Give me the full Floor Nine combat report.'"),
    ("panel_0025", "Edis stammers in terror, describing a savage ambush by fifty bloodthirsty, howling cave goblins."),
    ("panel_0026", "Her haunted eyes stare into nowhere, traumatized by the horrific slaughter of her comrades."),
    ("panel_0027", "She whispers that deep mud drenched the battlefield from endless unnatural downpours."),
    ("panel_0028", "Han's veteran gamer senses tingle, asking if any other weird environmental anomalies occurred there."),
    ("panel_0029", "Edis shakes her head helplessly, completely unaware that the dungeon was actively baiting them."),
    ("panel_0030", "Rallying his frontline killers, Han declares, 'Get ready, because our turn has officially arrived.'"),
    ("panel_0033", "A flashy stage-clear screen flashes, rewarding gold while crowning Eolka as party MVP again."),
    ("panel_0034", "Han calculates that their squad has officially hit the available level cap."),
    ("panel_0035", "Blacksmith forged plate armor glints as the vanguard gears up for the impending trial."),
    ("panel_0036", "Unfortunately, useless rookies Shurn and Mekhin get drafted into both parties as emergency filler."),
    ("panel_0037", "Fairy Iselle flutters overhead, giggling, 'Can our almighty master Loki predict this upcoming mission?'"),
    ("panel_0038", "Han chuckles dryly, answering, 'Only an actual omniscient god could predict this broken game.'"),
    ("panel_0039", "In normal mobile games, whales learn by wiping repeatedly until they finally clear stages."),
    ("panel_0040", "But here under clueless Master Anytng, a single wiped party means permanent, irreversible deletion."),
    ("panel_0041", "Glancing toward the heavens, Han realizes one brain-dead misclick will erase his existence."),
    ("panel_0042", "Eight tense adventurers assemble in the central plaza, awaiting their unpredictable summoner's final move."),
    ("panel_0043", "Jenna looks around the crowded square, whispering anxiously, 'Why did everyone assemble right now?'"),
    ("panel_0044", "Han groans, knowing Master Anytng has stared at his screen for thirty minutes."),

    # Act 3: Impulsive Summoner & Spatial Deployment (Panels 45-60)
    ("panel_0045", "A system prompt blares across the sky: 'Challenge the Tenth Floor right now?'"),
    ("panel_0046", "The crystalline angel statue glows ominously, waiting for the clueless player's life-or-death choice."),
    ("panel_0047", "A sane player would spend three weeks grinding hero promotions before touching this boss."),
    ("panel_0048", "Patience and preparation ensure safe farming, but mobile gacha addicts are notoriously impatient gamblers."),
    ("panel_0049", "Sure enough, impulsive summoner Anytng immediately slams the shiny red confirmation button without thinking!"),
    ("panel_0050", "Iselle chants the activation sequence, tearing open a blinding spatial rift across the sky!"),
    ("panel_0051", "Han glares upward with icy focus, knowing this nightmare is merely a game."),
    ("panel_0052", "Han orders the terrified rookies, 'The second combat starts, run and hide like cowards.'"),
    ("panel_0053", "A blood-red warning flashes, announcing that failing this crucial mission brings catastrophic server penalties."),
    ("panel_0054", "Han inspects the tactical console, sighing that their noob player probably never touched it."),
    ("panel_0055", "He barks at Iselle, demanding every single useful combat item hoarded in the warehouse."),
    ("panel_0056", "The supply check yields only six health potions across eight doomed fighters."),
    ("panel_0057", "Han warns Edis that spatial warp turbulence might scatter their squads across town."),
    ("panel_0058", "Edis points toward the skyline, shouting, 'Rally at the center if separated!'"),
    ("panel_0059", "Panic ripples through recruits, but Han snaps, 'Keep heads down and follow me.'"),
    ("panel_0060", "Locking eyes with his trembling teammates, Han vows, 'I will drag everyone back alive.'"),

    # Act 4: The Doomed Metropolis (Panels 62-77)
    ("panel_0062", "Pouring rain drenches the plaza, where a ragged man weeps upon wet cobblestones."),
    ("panel_0063", "The stranger clutches his drenched hair, screaming, 'We are all going to die tonight!'"),
    ("panel_0064", "Bloodcurdling wails echo through the storm as the broken man curses their helpless doom."),
    ("panel_0065", "Hearing footsteps, the frantic stranger scrambles backward, shrieking, 'Who is there right now?!'"),
    ("panel_0066", "Jenna blinks in confusion, whispering, 'Why is this weird peasant completely ignoring our presence?'"),
    ("panel_0067", "Eolka waves in front of his blank eyes, shouting, 'Hey, can you see us?'"),
    ("panel_0068", "Han realizes this weeping guy is an unskippable atmospheric story non-player character."),
    ("panel_0069", "Escort and civilian protection quests are universally hated nightmares in every single mobile game."),
    ("panel_0070", "Han scans the looming timber houses, struck by a bizarre sensation of nostalgia."),
    ("panel_0071", "Aaron rubs his chin, muttering that these cobblestone alleyways look eerily familiar."),
    ("panel_0072", "Suddenly Han freezes in place, a wave of pure icy dread washing over him!"),
    ("panel_0073", "Crowds of huddled civilians sit shivering against tavern walls, waiting for impending, inevitable slaughter."),
    ("panel_0074", "This bustling western metropolis is the exact destroyed ruined city from the fifth floor!"),
    ("panel_0075", "The horrific difference is this living city has not been slaughtered yet!"),
    ("panel_0076", "The mission roster locks into place as their apocalyptic urban defense battle officially begins!"),
    ("panel_0077", "Han draws his blade, preparing to fight through hell to rewrite history!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch25"
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

    script_dict = build_script_blocks(panels, lines_map, "ch25")
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
