"""Pick Me Up Chapter 21 Golden Standard Script Generator (72 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Roasts noob Master Anis queueing Floor 8 by mistake, Eolka's glass-cannon arrogance, and Han carrying the squad.
- 1:1 synchronization across all 72 clean story panels.
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
    # Act 1: The New Summon & The Master's Blunder (Panels 2-25)
    ("panel_0002", "We kick right off in Niflheim, where Han interrogates their newest haughty summon."),
    ("panel_0003", "Meet Eolka, a three-star fire mage who thinks she owns the entire universe."),
    ("panel_0004", "Han bluntly asks if this fancy prodigy knows any useful teleportation or support spells."),
    ("panel_0005", "Our master ranker sighs in pure agony, realizing she is completely useless at support."),
    ("panel_0006", "Eolka snaps back with indignant outrage, asking if this peasant has a complaint."),
    ("panel_0007", "The fiery diva smirks proudly, boasting that her explosive magic will blow everyone away."),
    ("panel_0008", "Han mutters under his breath that defensive utility beats flashy glass cannon fireworks anytime."),
    ("panel_0009", "Her lack of awakened skills proves that raw arrogance cannot replace real game mechanics."),
    ("panel_0010", "Han coldly lays down the law, warning that everyone must fight or die here."),
    ("panel_0011", "Eolka proudly declares to Aaron that common folk revere her as Rivel's Witch."),
    ("panel_0012", "The squad prepares for a relaxing training excursion down on peaceful floor four."),
    ("panel_0013", "Dungeon portals flare to life, whisking our unsuspecting party into the spatial crack."),
    ("panel_0014", "Han leads the way with cold confidence, ready for a simple ability test."),
    ("panel_0016", "Clear progress banners confirm seven dungeon floors conquered under Han's veteran leadership so far."),
    ("panel_0017", "Eolka struts forward like a runway model, expecting an effortless stroll through the park."),
    ("panel_0018", "The plan is brilliantly simple: test the newcomer against harmless low-tier dungeon fodder."),
    ("panel_0019", "Fourth-floor harpies and goblins should provide an easy warmup for their noisy new recruit."),
    ("panel_0020", "The spoiled mage panics immediately when Han announces the veterans will just spectate."),
    ("panel_0021", "Han chuckles sarcastically, asking if the great witch is terrified of starter mobs."),
    ("panel_0022", "Eolka pouts defensively, promising her devastating magic will leave them begging for autographs."),
    ("panel_0023", "She flashes a confident thumbs up, completely oblivious to the horror awaiting them."),
    ("panel_0024", "Jenna pumps her fists with cheerful optimism, shouting, 'Let us go kick butt!'"),
    ("panel_0025", "A red system timer counts down ten brief seconds until the dungeon gate opens."),

    # Act 2: Master Anis's Brain-Dead Blunder & Floor 8 Ambush (Panels 26-44)
    ("panel_0026", "Jenna whispers a nervous prayer, wishing Han good luck on this routine run."),
    ("panel_0027", "The massive gate slides open, welcoming the squad into their supposed practice arena."),
    ("panel_0028", "Han's jaw drops in pure fury as the atmospheric pressure crushes their lungs."),
    ("panel_0029", "An ominous system alert reveals that noob master Anis queued them into floor eight!"),
    ("panel_0030", "Our master ranker curses aloud, realizing Anis sent them to die out of spite."),
    ("panel_0031", "Jenna cries out in terror, wondering why their idiot summoner skipped four whole floors."),
    ("panel_0032", "Han bellows at the top of his lungs, screaming, 'Everyone, dodge right now!'"),
    ("panel_0033", "Eolka stands frozen like a startled deer as murderous shockwaves rip through the air."),
    ("panel_0034", "Her eyes bulge in horror as lethal steel drops straight toward her skull."),
    ("panel_0035", "Han yanks her by the collar violently, snapping, 'Wake up, you clueless idiot!'"),
    ("panel_0036", "A massive war hammer obliterates the stone where the pampered mage stood just now."),
    ("panel_0038", "Han grits his teeth, sweating as he recognizes the absolute worst enemy type possible."),
    ("panel_0039", "The quest objective demands the total subjugation of twenty-seven level-nine goblin raiders immediately."),
    ("panel_0040", "An entire cavalry of bloodthirsty skeletal raiders charges forward with terrifying momentum."),
    ("panel_0041", "Han barks urgent orders, shouting, 'Jenna, unleash your arrows and break their vanguard!'"),
    ("panel_0042", "Jenna lets fly a glowing arrow volley, painting the jagged rocks with monster blood."),
    ("panel_0043", "Aaron braces his broad shield, preparing to absorb the brutal flank on uneven ground."),
    ("panel_0044", "Han glares back at Eolka, furiously demanding she start earning her keep right now."),

    # Act 3: Babysitting the Glass Cannon & Frontline Climax (Panels 45-64)
    ("panel_0045", "Our master ranker calculates lethal trajectories, reading enemy micro-movements like an open strategy guide."),
    ("panel_0046", "Han swats away a brutal strike, staggering an armored goblin with pinpoint counterforce."),
    ("panel_0047", "His trusty iron buckler groans as a snarling beast crashes directly into his guard."),
    ("panel_0048", "Han slips beneath a razor-sharp scimitar, letting the mounted raider lunge harmlessly past him."),
    ("panel_0049", "A vicious rising strike decapitates the mounted goblin before the rider can turn around."),
    ("panel_0050", "Cerulean sword energy erupts from Han's blade, bisecting an approaching predator in mid-air."),
    ("panel_0051", "Han spins like a deadly top, carving through three skeletal foot soldiers in seconds."),
    ("panel_0052", "A monstrous shadow wolf pounces from the blind spot, aiming straight for Aaron's neck."),
    ("panel_0053", "Aaron swings his colossal broadaxe with thunderous fury, crushing the beast into red mist."),
    ("panel_0054", "Another heavily armored brute enters the fray, brandishing a massive spiked iron mace."),
    ("panel_0055", "Aaron locks weapons with the brute while Han roars, 'Eolka, cast your magic!'"),
    ("panel_0056", "The haughty witch whines in outrage, but Han snaps, 'Just kill them all already!'"),
    ("panel_0057", "Eolka shamelessly demands a full minute of casting time amidst this chaotic slaughter."),
    ("panel_0058", "Han curses his rotten luck, sprinting into the horde to buy sixty precious seconds."),
    ("panel_0059", "Blinding white slashes explode through the clearing as Han holds the perimeter all alone."),
    ("panel_0060", "Eolka closes her eyes, finally channeling swirling crimson embers between her manicured fingers."),
    ("panel_0061", "Raging fire runes orbit her hands as she dramatically incants La Gran Sedus."),
    ("panel_0062", "The whole dungeon ignites into blinding golden flames, shocking both heroes and monsters alike."),
    ("panel_0063", "Han screams over the roaring inferno, ordering Aaron to protect Jenna from incoming crossbows."),
    ("panel_0064", "Aaron raises his fortress shield instantly, swatting poisonous bolts out of the smoky air."),

    # Act 4: The Stationary Turret & Status Reality Check (Panels 65-75)
    ("panel_0065", "A colossal fire column erupts skyward, incinerating the goblin vanguard in an apocalyptic blast."),
    ("panel_0066", "The surviving raiders suddenly realize that this defenseless, unmoving girl is their primary target."),
    ("panel_0067", "Han dashes back across burning wreckage, desperately scrambling to intercept the murderous goblin cavalry."),
    ("panel_0068", "He screams at Eolka to redirect her explosive artillery toward the shielded enemy captains."),
    ("panel_0069", "Raging fire chains whip wildly from Eolka's palms, threatening friends and foes alike."),
    ("panel_0070", "The frantic witch shrieks that anyone standing near her blast radius will burn alive."),
    ("panel_0071", "Han stops dead in his tracks as the horrifying gamer reality dawns on him."),
    ("panel_0072", "Ferocious monster claws tear through the smoke, converging rapidly on the helpless spellcaster."),
    ("panel_0073", "Our master ranker screams in disbelief, realizing this three-star prodigy cannot cast while moving!"),
    ("panel_0074", "A shiny character portrait introduces Eolka Rivel Strashur, the ultimate stationary turret disaster."),
    ("panel_0075", "Her status window reveals sky-high intelligence completely ruined by pathetic, bottom-tier mobility and agility."),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch21"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    # Verify 1:1 match
    panel_pids = [p["panel_id"] for p in panels]
    beat_pids = [pid for pid, _ in STORY_BEATS]
    if panel_pids != beat_pids:
        missing = set(panel_pids) - set(beat_pids)
        extra = set(beat_pids) - set(panel_pids)
        raise ValueError(f"Mismatch in panel IDs! Missing: {missing}, Extra: {extra}")

    # Check word counts
    for pid, txt in STORY_BEATS:
        wc = len(txt.split())
        if wc < 10 or wc > 14:
            raise ValueError(f"Beat [{pid}] has {wc} words (must be 10-14): {txt}")

    script_dict = build_script_blocks(panels, lines_map, "ch21")
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

    if not res.passed or score < 7:
        sys.exit(1)


if __name__ == "__main__":
    main()
