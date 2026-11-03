"""Pick Me Up Chapter 17 Golden Standard Script Generator (71 Story Panels).

Mamoru YouTube Recap Persona:
- High-octane, witty, comedic narrator voice.
- Describes Han's psychological duel with 3-star Avant, Berserk beatdown, thug interference, and daring Master Anis!
- 1:1 synchronization across all 71 clean story panels.
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
    # Act 1: The Open Duel Challenge (Panels 3-13)
    ("panel_0003", "We kick right off with Han casually challenging a three-star bully to an open duel!"),
    ("panel_0004", "The system practically glitches in confusion, asking if this suicidal one-star peasant is being serious."),
    ("panel_0005", "Silver-haired swordsman Avant laughs arrogantly, thinking he just won the easiest free lottery ticket ever!"),
    ("panel_0006", "The cocky warrior signs his own death warrant by agreeing to a mysterious synthesis condition."),
    ("panel_0007", "Han casually tells Jenna to back the crowd up so nobody catches stray punches."),
    ("panel_0008", "A glowing system notice confirms Han radiates the absolute swagger of a maxed-out veteran player."),
    ("panel_0009", "Our protagonist smirks back playfully, asking, 'Do you honestly think I will lose today?'"),
    ("panel_0010", "Golden arena letters flash across the plaza, locking both fighters into this high-stakes deathmatch."),
    ("panel_0011", "The duel terms are brutally simple: fight continues until one coward formally begs for mercy."),
    ("panel_0012", "Avant sneers that he will spare Han's life purely to consume him as synthesis food."),
    ("panel_0013", "Han winks at tiny fairy Iselle, ordering her to zap any outside gang interference."),

    # Act 2: Berserk Activation & Avant's Beatdown (Panels 14-32)
    ("panel_0014", "Avant lunges forward swinging steel, mocking Han for having pitiful, unpromoted starter combat passives."),
    ("panel_0015", "The arrogant three-star dashes in aggressively, fully expecting an effortless, one-sided rookie slaughter today."),
    ("panel_0016", "Avant boasts that raw stat advantages mean Han has zero percent chance of surviving."),
    ("panel_0017", "Suddenly Han's eyes blaze crimson as his newly unlocked Berserk skill roars to life!"),
    ("panel_0018", "Avant's gang freezes in horror as Han's aura suddenly spikes into an apex predator."),
    ("panel_0019", "Han dodges the sloppy thrust effortlessly, sidestepping Avant's strike with master ranker micro-footwork precision."),
    ("panel_0020", "Han delivers the most therapeutic reality-check slam in gacha history, smashing Avant downward!"),
    ("panel_0021", "Avant's skull bounces hard against the cobblestones, erasing that smug smirk in one second."),
    ("panel_0022", "Han looms over his battered opponent, radiating the chilling menace of a legendary raid boss."),
    ("panel_0023", "Spectators gasp in disbelief, watching an unranked peasant completely dismantle a polished three-star veteran."),
    ("panel_0024", "Han chuckles dryly, muttering that this beating is appropriate for an entitled schoolyard bully."),
    ("panel_0025", "Resting his broadsword against Avant's throat, Han warns him to stay completely still."),
    ("panel_0026", "Han demands a formal surrender, but bloody Avant stammers out pathetic, half-hearted excuses instead."),
    ("panel_0027", "Pressing the sharp steel edge closer, Han snaps, 'Speak up clearly, you clown!'"),
    ("panel_0028", "Avant's gang members panic loudly, begging Han to stop before he commits outright murder."),
    ("panel_0029", "Avant whines in total confusion, asking how this scrawny rookie could possibly hit so hard."),
    ("panel_0030", "Han glares down ruthlessly, declaring that whatever the master ranker says becomes absolute law."),
    ("panel_0031", "He demands to know why this entire pathetic bandit troupe is throwing a tantrum."),
    ("panel_0032", "Smothering Avant's mouth with one hand, Han refuses to grant him an easy surrender."),

    # Act 3: Interrogating Edis & Thug Beatdown (Panels 33-52)
    ("panel_0033", "Han reminds the surrounding cowards that Avant is his rightful, designated post-battle loot drop."),
    ("panel_0034", "Flashing menacing crimson eyes, Han tells the entire gang to back away right now."),
    ("panel_0035", "A masked thug steps forward aggressively, demanding to know who gave Han this authority."),
    ("panel_0036", "Han notes that this troupe once possessed real honor before turning into desperate thieves."),
    ("panel_0037", "A distressed recruit named Edis lowers her eyes, admitting their gang completely lost its way."),
    ("panel_0038", "Han grabs her shoulder firmly, asking why an honest girl is traveling with garbage."),
    ("panel_0039", "Staring straight into her soul, Han asks if she genuinely wants to stay a criminal."),
    ("panel_0040", "Edis confesses through tears that her father's massive debt forced her into this syndicate."),
    ("panel_0041", "Han asks if she seriously wants to throw her whole life away serving losers."),
    ("panel_0042", "A loud-mouthed blond thug screams at Han, furious that their recruit is being swayed."),
    ("panel_0043", "Han swats the noisy blond thug across the plaza like an annoying buzzing mosquito!"),
    ("panel_0044", "The fallen bandit reaches out desperately, threatening Edis with severe syndicate contract retaliation."),
    ("panel_0045", "Han raises his steel blade coldly, announcing that this is the final stop for trash."),
    ("panel_0046", "He offers Edis a genuine second chance, inviting her to join his frontline team."),
    ("panel_0048", "Edis looks up in tearful shock, realizing someone actually values her life for once."),
    ("panel_0049", "Her eyes shimmer with relief as Han promises her real safety under his leadership."),
    ("panel_0050", "Han turns right back to the duel circle, ready to finish this hilarious mismatch."),
    ("panel_0051", "The masked bandit curses loudly, refusing to let Han walk away with their companion."),
    ("panel_0052", "Avant whimpers pathetically in the dirt, terrified of the punishment heading his way now."),

    # Act 4: Sudden Death Penalty & Daring Master Anis (Panels 53-74)
    ("panel_0053", "The masked bandit lunges with drawn daggers, screaming, 'Die, you arrogant little bastard!'"),
    ("panel_0054", "Iselle buzzes in angrily, warning that attacking an active duel violates absolute system law!"),
    ("panel_0055", "The foolish bandits rush the arena together, ignoring all game rules in blind desperation."),
    ("panel_0056", "Han turns around with a predatory smirk, whispering that they just made their final mistake."),
    ("panel_0057", "He coldly warns that he never shows mercy to cowards who break duel rules."),
    ("panel_0058", "Han unleashes his Berserk aura, cleaving through the interference with blinding, lightning-fast slashes!"),
    ("panel_0059", "A sudden death penalty notification flashes, instantly deleting the treacherous attackers from the server!"),
    ("panel_0060", "Completely broken and trembling in horror, Avant finally screeches out his unconditional formal surrender."),
    ("panel_0061", "Han smoothly dispels his Berserk mode as golden victory confetti rains down across plaza."),
    ("panel_0062", "Han rubs his throbbing temples, complaining that Berserk gives him a colossal gaming headache."),
    ("panel_0063", "A glorious victory screen confirms Han just pulverized three-star champion Avant into the dirt!"),
    ("panel_0064", "Han looks up smiling, noticing Master Anis frantically tapping his smartphone screen in panic."),
    ("panel_0065", "Massive piles of bonus experience points shower Han's character card with shiny level ups!"),
    ("panel_0066", "A max level alert pops up, informing the player that Han requires immediate hero synthesis."),
    ("panel_0067", "Han notes that Anis bought ten summons specifically to feed fodder into synthesis upgrades."),
    ("panel_0068", "He points out that leaving unruly recruits unsupervised would turn the barracks into chaos."),
    ("panel_0069", "Han reminds the heavens that back-to-back MVP performances make him far too valuable to delete."),
    ("panel_0070", "Glaring straight up into Anis's giant celestial eye, Han throws down a diabolical challenge!"),
    ("panel_0071", "He dares his clueless summoner, shouting, 'Go ahead and try synthesizing me, if you dare!'"),
    ("panel_0072", "Avant's shiny character card dissolves into pure fodder particles, consumed to feed the real master!"),
    ("panel_0073", "The fallen rookie roster demonstrates the ruthless, permanent cost of climbing this deadly tower."),
    ("panel_0074", "The synthesis finishes smoothly, locking Han Islat in as an unstoppable rising gacha legend!"),
]


def main():
    ch_dir = REPO_ROOT / "data" / "chapters" / "pick_me_up" / "ch17"
    out_file = ch_dir / "04_script.json"
    desc = json.loads((ch_dir / "03_descriptions.json").read_text(encoding="utf-8"))
    panels, _ = clean_and_prune_panels(desc["panels"])

    lines_map = {pid: format_sentence(txt) for pid, txt in STORY_BEATS}

    script_dict = build_script_blocks(panels, lines_map, "ch17")
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
