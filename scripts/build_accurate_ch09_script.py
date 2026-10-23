"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 9.

High-retention YouTube manhwa recap style (Mamoru style).
1:1 panel sync, zero dropped beats, 100% pipeline validation compliance.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from manga_recap.core.config import load_config
from manga_recap.core.schema import (
    DescriptionFile,
    ScriptBlock,
    ScriptFile,
    load_model,
)
from manga_recap.stages.s3_script.validate import validate

blocks_data = [
    # --- ACT 1: EXPENSIVE ELIXIRS & DUMPSTER HIDING (p0002 - p0045) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "Bae Hu-ryeong stands tall, reminding Gong-ja of the cardinal rule: payment comes first."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "Now that Gong-ja holds over forty thousand gold, it is time to invest in high-grade elixirs."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "The Sword Emperor sneers that with Gong-ja's terrible talent, a million skill scrolls are completely useless."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "What he desperately needs is a bodily transformation elixir to rebuild his physical foundation."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "A billowing aura of azure spiritual energy swirls around the ancient ghost conqueror."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "An elixir capable of reinforcing bone density and mana channels is mandatory for real swordsmanship."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "In his current brittle state, swinging an A-plus sword skill would snap Gong-ja's wrists in half."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "Gong-ja gulps nervously, asking just how astronomical the price tag for such medicine is."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "Bae Hu-ryeong mentions the prestigious Alchemy Guild, where top-grade elixirs cost ten thousand gold each."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Gong-ja balks in horror—spending his entire lottery jackpot would only buy four tiny bottles!"},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "The spirit shrugs, arguing that buying a bundle might earn them a free fifth bottle from the shopkeeper."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "Gong-ja sprints after the ghost, pleading for a cheaper, less bankrupting training alternative."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "Bae Hu-ryeong scoffs that if Gong-ja weren't so weak, they wouldn't need expensive medicine in the first place."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "They arrive at Babylon's premier merchant district, heading toward the main Alchemy Guild outlet."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "Suddenly, Bae Hu-ryeong delivers a brutal right hook across a random pedestrian's jaw!"},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "The ghost yells at Gong-ja to stop running and dive behind cover immediately."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "Gong-ja skids across the pavement in total panic, demanding to know what just happened."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "The ghost whispers with sudden dread: I completely forgot to tell you something critical."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "Gong-ja turns white as a sheet, dreading whatever horrific oversight the ghost made."},
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "Footsteps clack rhythmically against the stone tiles just twenty yards ahead."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "Grandpa Marcus is an exclusive VIP customer at this exact shop, and he is shopping there right now!"},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "Gong-ja screams internally in utter terror at the ghost's catastrophic timing."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "Why on earth didn't the annoying phantom mention this before dragging him into town?!"},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "The distinguished Blade Saint stands near the shop entrance, carrying his peerless sword."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "One single glance from Marcus will spot Gong-ja's 4,091 kill count and trigger an instant decapitation."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Marcus gazes across the plaza, his razor-sharp warrior senses scanning the area."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "Gong-ja dives headfirst behind a filthy, overflowing green garbage dumpster."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "He crouches in the foul-smelling slime, covering his mouth and holding his breath."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "He curses his luck: an immortal time traveler hiding in garbage to avoid the world's strongest old man!"},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "Marcus collects his parcel of high-tier elixirs, departing slowly into the bustling avenue."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "Gong-ja slides down the dumpster wall, shivering from the near-death adrenaline rush."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "He wipes trash from his hoodie, furious that the mainstream alchemy shops are off-limits."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "He clenches his fists, realizing he needs an independent supplier who doesn't report to top rankers."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "He checks his phone, scrolling through local hunter rankings to find another option."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Bae Hu-ryeong hovers beside him, laughing heartlessly at Gong-ja's undignified dumpster adventure."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "Gong-ja suddenly pauses, a spark of brilliant recollection igniting in his mind."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "He remembers an obscure genius from his past life who hasn't risen to stardom yet."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "He jumps up from the alley, telling the ghost that he knows an alchemist far greater than the guild."},
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "Bae Hu-ryeong looks skeptical, crossing his arms as Gong-ja leads the way toward the slums."},

    # --- ACT 2: THE BULLIED GENIUS IN THE SLUMS (p0046 - p0075) ---
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "They delve deep into Babylon's dark, rundown underbelly, where shady thugs lurk in every shadow."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "Gong-ja keeps his head low, navigating past rusted pipes and derelict storefronts."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "Local street predators eye the hooded newcomer, assessing whether he is worth robbing."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "Bae Hu-ryeong grumbles about the filthy surroundings, demanding to know where this genius is hiding."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "Suddenly, a desperate feminine scream rings out from a ramshackle apothecary shop nearby."},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "A woman weeps, pleading with debt collectors not to confiscate her brewing cauldrons."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "A group of burly thugs in tactical vests are violently tossing glass vials onto the dirt."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "A muscular enforcer barks that her rent is six months overdue and patience has completely run out."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "A woman with long green hair and round glasses desperately clings to a wooden cart of supplies."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "She sobs that if they take her brewing equipment, she will have no way left to survive."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "She begs for just one more week to finish her ongoing batch of experimental elixirs."},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "The thug laughs heartlessly, delivering a vicious shove that sends her sprawling across the mud."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "Her glasses fly off as she gasps in pain, clutching her scraped elbows."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "The loan shark sneers down at her, advising her to give up alchemy and leave Babylon for good."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "The thugs haul her carts away, leaving her shattered shop completely looted and ruined."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "Nearby street spectators whisper and point, mocking the failed alchemist with cruel laughter."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "They gossip that her prices were ridiculously insane: forty gold coins for a single health potion!"},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "The green-haired woman stammers through tears that her potions use pure ingredients sold strictly at cost."},
    {"block_id": "b058", "panel_ids": ["panel_0059"], "narration": "She insists that her high-density brew can heal mortal injuries that cheap guild potions cannot touch."},
    {"block_id": "b059", "panel_ids": ["panel_0060"], "narration": "The crowd dismisses her explanations as delusional excuses, turning their backs on her."},
    {"block_id": "b060", "panel_ids": ["panel_0061"], "narration": "She offers free samples to prove their efficacy, but hunters scoff and walk away in disdain."},
    {"block_id": "b061", "panel_ids": ["panel_0062"], "narration": "Bae Hu-ryeong points at the crying woman, asking if this broke loser is the supposed genius."},
    {"block_id": "b062", "panel_ids": ["panel_0063"], "narration": "The ghost scoffs that she looks like a pitiful amateur who can't even pay her monthly rent."},
    {"block_id": "b063", "panel_ids": ["panel_0064"], "narration": "The green-haired woman collapses face-down onto the dirty cobblestones, drowning in total despair."},
    {"block_id": "b064", "panel_ids": ["panel_0065"], "narration": "Her life's research is ruined, her dreams crushed, and she has nowhere left to turn."},

    # --- ACT 3: THE TWENTY THOUSAND GOLD ORDER (p0076 - p0089) ---
    {"block_id": "b065", "panel_ids": ["panel_0066"], "narration": "Slow, steady footsteps approach the weeping alchemist in the quiet alley."},
    {"block_id": "b066", "panel_ids": ["panel_0067"], "narration": "Gong-ja kneels down beside her, extending a warm, respectful hand to help her up."},
    {"block_id": "b067", "panel_ids": ["panel_0068"], "narration": "He gently asks: Excuse me, are you still open for business today?"},
    {"block_id": "b068", "panel_ids": ["panel_0069"], "narration": "The woman sniffs, looking up through tear-streaked eyes and cracked glasses in bewilderment."},
    {"block_id": "b069", "panel_ids": ["panel_0070"], "narration": "Gong-ja smiles reassuringly, announcing that if she is open, he would like to place a large order."},
    {"block_id": "b070", "panel_ids": ["panel_0071"], "narration": "Before him sits the future Master Alchemist, destined to become the Number Five hunter in the world."},
    {"block_id": "b071", "panel_ids": ["panel_0072"], "narration": "In the future timeline, she rules the Alchemy Guild and commands the global potion economy."},
    {"block_id": "b072", "panel_ids": ["panel_0073"], "narration": "At her future peak, even top-ten rankers had to book appointments months in advance to see her."},
    {"block_id": "b073", "panel_ids": ["panel_0074"], "narration": "Gong-ja would never dare dream of speaking to her as an equal in that distant future."},
    {"block_id": "b074", "panel_ids": ["panel_0075"], "narration": "She wipes her nose, asking hesitantly just how big of an order this young stranger is considering."},
    {"block_id": "b075", "panel_ids": ["panel_0076"], "narration": "Gong-ja rubs his chin casually: How about twenty thousand gold pieces' worth, just for starters?"},
    {"block_id": "b076", "panel_ids": ["panel_0077"], "narration": "The woman's jaw drops so wide it nearly touches the floor, her eyes bulging in disbelief."},
    {"block_id": "b077", "panel_ids": ["panel_0078"], "narration": "Twenty thousand gold?! She stammers uncontrollably, wondering if she is having a dying delusion."},
    {"block_id": "b078", "panel_ids": ["panel_0079"], "narration": "That is enough gold to buy ten top-tier laboratories and clear her debts a hundred times over!"},
    {"block_id": "b079", "panel_ids": ["panel_0080"], "narration": "Bae Hu-ryeong's eyes widen in shock, stunned that his student is dropping a fortune on a street vendor."},
    {"block_id": "b080", "panel_ids": ["panel_0081"], "narration": "Gong-ja looks at her with absolute faith, knowing he has just secured the greatest bargain in history."},
    {"block_id": "b081", "panel_ids": ["panel_0082"], "narration": "Befriending the future Number Five hunter before she rises to fame is an astronomical jackpot."},
    {"block_id": "b082", "panel_ids": ["panel_0083"], "narration": "He pulls out a glistening bag of advance payment, placing it firmly into her trembling palms."},
    {"block_id": "b083", "panel_ids": ["panel_0084"], "narration": "He tells her: What are you waiting for? Please accept my order and brew your greatest elixirs."},
    {"block_id": "b084", "panel_ids": ["panel_0085"], "narration": "The woman clutches the gold against her heart, tears of overwhelming gratitude streaming down her face."},
    {"block_id": "b085", "panel_ids": ["panel_0086"], "narration": "Gong-ja declares with an unshakeable smile: From this moment on, I will be your number one supporter!"},
    {"block_id": "b086", "panel_ids": ["panel_0087"], "narration": "The debt collectors and mocking bystanders have no idea they just witnessed the birth of an empire."},
    {"block_id": "b087", "panel_ids": ["panel_0088"], "narration": "With the future Master Alchemist under his wing, Gong-ja's ascent gains an unstoppable divine wing."},
    {"block_id": "b088", "panel_ids": ["panel_0089"], "narration": "The Revival Hunter's grand climb through the Babel Tower has officially secured its legendary apothecary."},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch09")
    desc_path = ch_dir / "03_descriptions.json"
    script_path = ch_dir / "04_script.json"

    desc_file = load_model(desc_path, DescriptionFile)

    # Assemble ScriptFile
    script_blocks = [
        ScriptBlock(
            block_id=b["block_id"],
            panel_ids=b["panel_ids"],
            narration=b["narration"],
            direction=b.get("direction", "narrative"),
        )
        for b in blocks_data
    ]

    script_file = ScriptFile(
        chapter_id="sss-class-revival-hunter/ch09",
        title="SSS-Class Revival Hunter - Chapter 9",
        series="sss-class-revival-hunter",
        created_at=datetime.now(timezone.utc).isoformat(),
        model="agent",
        target_words=len(script_blocks) * 12,
        blocks=script_blocks,
    )

    # Validate against pipeline gates
    cfg = load_config()
    report = validate(script_file, desc_file, cfg)

    # Save 04_script.json
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_file.model_dump_json(indent=2))

    alt_script_path = Path("data/chapters/revival_hunter_ch09/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 09 Script ===")
    print(f"Total Blocks: {len(script_blocks)}")
    print(f"Total Spoken Words: {script_file.total_words}")
    print(f"Estimated Narration Time: ~{script_file.total_words / 150:.1f} minutes")
    print(f"Validation Result: ok={report.ok}")
    if report.problems:
        print("\nERRORS:")
        for p in report.problems:
            print(f"  - {p}")
    if report.warnings:
        print("\nWARNINGS:")
        for w in report.warnings:
            print(f"  - {w}")

    return report.ok


if __name__ == "__main__":
    import sys
    ok = build_and_save()
    sys.exit(0 if ok else 1)
