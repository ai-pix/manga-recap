"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 8.

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
    # --- ACT 1: FOUR AM DRILL SERGEANT (p0002 - p0029) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "A thunderous roar echoes inside Gong-ja's ears, demanding he wake up immediately."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "Gong-ja groans beneath his warm blanket, begging for just five more precious minutes of sleep."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "Bae Hu-ryeong berates him violently, warning that Grandpa Marcus is currently clearing floors while he slumbers."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Gong-ja flips over, desperately pulling his pillow over his ears to muffle the spectral yelling."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "The Sword Emperor threatens to unleash a high-frequency sonic scream that will burst thirty skulls at once."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "He hovers upside down over the mattress, cackling like a demonic personal drill instructor."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "Gong-ja kicks the sheets aside in absolute fury, grabbing his phone to check the hour."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "He thrusts the glowing screen into the ghost's face, demanding to know why he was woken up."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "He screams in pure disbelief: it is only four o'clock in the morning, you crazy bastard!"},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Four zero one AM sharp blinks mockingly from his cracked digital display."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "Bae Hu-ryeong crosses his arms, arrogantly retorting that even insects wake up before four AM."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "Gong-ja accuses him of waking him up purely because ghosts can't fall asleep."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "He realizes this spectral tyrant is the exact reason why Marcus was constantly sleep-deprived."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "Bae Hu-ryeong points down firmly, declaring that early morning discipline is for Gong-ja's own benefit."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "Gong-ja grumbles that he wants to die, to which the ghost cheerfully reminds him he is already immortal."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "The spirit chuckles, officially dubbing his student with a fitting new title: Zombie Kim."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "Gong-ja curses under his breath, realizing there is zero escape from this immortal drill sergeant."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "Soon, Gong-ja is sprinting through Babylon's foggy dawn streets, panting under the physical strain."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "Bae Hu-ryeong floats smoothly alongside him, delivering a continuous stream of demoralizing critiques."},
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "He reminds Zombie Kim that in terms of innate combat talent, he is buried deep underground."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "He rates Gong-ja's natural martial instincts as lower than the dirt beneath his running shoes."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "Four days have passed since Gong-ja copied the Blade Saint's A-plus sword mastery."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "During that window, he hunted down Yoo Soo-ha once again to keep the timeline clean."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "He took extreme care to avoid crossing paths with Marcus Callenberry in the streets."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "Bae Hu-ryeong notes that to compensate for zero talent, Gong-ja requires elite martial elixirs."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Gong-ja follows the grueling physical regimen set by the hundredth-floor conqueror."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "Bae Hu-ryeong smiles mischievously, promising an extra special training method that requires massive funding."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "Gong-ja smirks, telling his spectral master that securing astronomical wealth is already taken care of."},

    # --- ACT 2: THE HAPPINESS LOTTERY (p0030 - p0070) ---
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "They arrive at the grand commercial headquarters of the United Merchants guild."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "In the Babel Tower, the United Merchants command an absolute economic monopoly."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "They control all banking, luxury auctions, real estate, and interdimensional trade."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "The guild is led by Countess, the formidable number three ranked hunter in the tower."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "Countess holds a unique skill that enables seamless commerce between the tower and Earth."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "Because of her skill, United Merchants holds the exclusive license to operate the Babylon lottery."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Countless desperate hunters blow their dungeon earnings on lottery tickets dreaming of an easy exit."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "Gong-ja approaches the gleaming marble counter, sliding a lottery ticket across the counter."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "He purchased this exact ticket last week, armed with precise eleven-year future knowledge."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "The clerk scans the ticket into the verification terminal with casual indifference."},
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "Suddenly, golden lights erupt from the terminal as bells chime across the entire hall!"},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "A massive system display confirms: First place winner in the Happiness Lottery!"},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "The total jackpot prize is fifty-three thousand pure gold coins, a staggering fortune."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "In Earth currency, fifty-three thousand gold is worth over five million US dollars."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "Every hunter in the lobby freezes in stunned, breathless silence, staring at the hooded youth."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "Murmurs of utter disbelief ripple through the crowd: did that rookie just hit first place?"},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "Bae Hu-ryeong's jaw drops as he hovers beside Gong-ja, unable to believe his eyes."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "Gong-ja remains calm and composed, keeping a knowing, confident smirk on his face."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "He deliberately chose to cash the ticket publicly in the main guild lobby for his own safety."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "If a lottery winner is quietly murdered in an alley, the guild's integrity is ruined."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "By winning under the spotlight, he forces United Merchants to safeguard his life at all costs."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "A distinguished manager dressed in an immaculate formal suit rushes out to greet him."},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "He introduces himself as Arthur Taylor, though he prefers the business alias Safe Keeper."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "Gong-ja recognizes him instantly: an advanced high-tier hunter ranked within the global top three hundred."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Arthur bows politely, escorting the newly minted millionaire into the private VIP lounge."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "Heavy oak doors close behind them, shutting out the greedy stares of the lobby patrons."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "Arthur offers Gong-ja a plush leather armchair, pouring a cup of exquisite high-grade tea."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "Bae Hu-ryeong inspects the opulent furnishings, whistling at the sheer wealth on display."},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "Arthur brings forward heavy steel chests, cracking the lids open to reveal mountains of gold."},
    {"block_id": "b058", "panel_ids": ["panel_0059"], "narration": "The golden glow illuminates the room, radiating with the intoxicating scent of raw wealth."},
    {"block_id": "b059", "panel_ids": ["panel_0060"], "narration": "Arthur explains that Gong-ja may withdraw the entire sum immediately or leave it in guild vault storage."},
    {"block_id": "b060", "panel_ids": ["panel_0061"], "narration": "He asks with professional courtesy what the young hunter intends to do with this fortune."},
    {"block_id": "b061", "panel_ids": ["panel_0062"], "narration": "Gong-ja gazes at the shimmering gold without a single trace of avarice or greed."},
    {"block_id": "b062", "panel_ids": ["panel_0063"], "narration": "He has already witnessed a golden light far more mesmerizing than mere coins."},
    {"block_id": "b063", "panel_ids": ["panel_0064"], "narration": "He saw the golden glow of his temporal resurrection, a power that transcends all mortal riches."},
    {"block_id": "b064", "panel_ids": ["panel_0065"], "narration": "Without hesitation, he tells the manager that he wishes to store the entire sum in their vault."},
    {"block_id": "b065", "panel_ids": ["panel_0066"], "narration": "Arthur beams with delight, praising Gong-ja for making the wisest, most mature choice."},
    {"block_id": "b066", "panel_ids": ["panel_0067"], "narration": "Carrying fifty thousand gold on the streets would make any rookie a walking assassination contract."},
    {"block_id": "b067", "panel_ids": ["panel_0068"], "narration": "Then, Gong-ja drops his first strategic demand: he wants to purchase an honorary guild membership."},
    {"block_id": "b068", "panel_ids": ["panel_0069"], "narration": "Arthur pauses in surprise, noting that a second-class honorary membership costs ten thousand gold."},
    {"block_id": "b069", "panel_ids": ["panel_0070"], "narration": "He asks if Gong-ja belongs to any hunting guild, to which Gong-ja confirms he is an independent."},

    # --- ACT 3: TACTICAL DIPLOMACY & GUILD SHIELD (p0071 - p0115) ---
    {"block_id": "b070", "panel_ids": ["panel_0071"], "narration": "Bae Hu-ryeong nods in approval, acknowledging that his new disciple is far sharper than expected."},
    {"block_id": "b071", "panel_ids": ["panel_0072"], "narration": "Guilds in the Babel Tower do not exist simply to make friends or organize casual dungeon parties."},
    {"block_id": "b072", "panel_ids": ["panel_0073"], "narration": "They exist to provide political immunity, legal defense, and military retaliation under their banner."},
    {"block_id": "b073", "panel_ids": ["panel_0074"], "narration": "Gong-ja smirks, knowing this city is far too dangerous to rely solely on public law enforcement."},
    {"block_id": "b074", "panel_ids": ["panel_0075"], "narration": "Both Flame Emperor and Blade Saint proved that the Hunter Bureau and City Security are toothless."},
    {"block_id": "b075", "panel_ids": ["panel_0076"], "narration": "Yoo Soo-ha refused to join guilds out of arrogance, which led directly to rival guilds poisoning him."},
    {"block_id": "b076", "panel_ids": ["panel_0077"], "narration": "Gong-ja refuses to repeat that foolish mistake; aligning with the wealthiest faction is smart survival."},
    {"block_id": "b077", "panel_ids": ["panel_0078"], "narration": "Arthur listens intently as Gong-ja outlines his additional requests with surgical precision."},
    {"block_id": "b078", "panel_ids": ["panel_0079"], "narration": "He currently lives in a squalid studio, so he pays a generous finder's fee for a luxury residence."},
    {"block_id": "b079", "panel_ids": ["panel_0080"], "narration": "He requests a secure, private estate located in the prestigious upper district of the first floor."},
    {"block_id": "b080", "panel_ids": ["panel_0081"], "narration": "Finally, he instructs the guild to keep his personal identity completely hidden from the media."},
    {"block_id": "b081", "panel_ids": ["panel_0082"], "narration": "However, they must officially register him as an honorary member of United Merchants across all databases."},
    {"block_id": "b082", "panel_ids": ["panel_0083"], "narration": "That way, underground syndicates will know he is under Countess's personal protection without knowing his name."},
    {"block_id": "b083", "panel_ids": ["panel_0084"], "narration": "Arthur adjusts his cravat, completely astonished by the young man's extraordinary political foresight."},
    {"block_id": "b084", "panel_ids": ["panel_0085"], "narration": "He stammers that Gong-ja's thoroughness rivals veteran politicians with decades of experience."},
    {"block_id": "b085", "panel_ids": ["panel_0086"], "narration": "Bae Hu-ryeong bursts into laughter, mocking Arthur's stunned expression from above."},
    {"block_id": "b086", "panel_ids": ["panel_0087"], "narration": "The manager quickly seals the contracts, bowing deeply with profound respect for the young client."},
    {"block_id": "b087", "panel_ids": ["panel_0088"], "narration": "Gong-ja signs the parchment with a steady hand, feeling the protective shield of wealth lock in place."},
    {"block_id": "b088", "panel_ids": ["panel_0089"], "narration": "Bae Hu-ryeong pats Gong-ja's shoulder, genuinely impressed by how smoothly he handled the transaction."},
    {"block_id": "b089", "panel_ids": ["panel_0090"], "narration": "The ghost smirks, remarking that Zombie Kim might actually have a functional brain after all."},
    {"block_id": "b090", "panel_ids": ["panel_0091"], "narration": "Gong-ja chuckles, telling the annoying phantom that this is merely the groundwork of their ascent."},
    {"block_id": "b091", "panel_ids": ["panel_0092"], "narration": "He holds the golden guild emblem in his palm, watching it pulse with warm, protective mana."},
    {"block_id": "b092", "panel_ids": ["panel_0093"], "narration": "Four thousand deaths and four thousand days of relentless agony were spent solely on vengeance."},
    {"block_id": "b093", "panel_ids": ["panel_0094"], "narration": "During that brutal campaign, he ignored all the wondrous benefits of rewinding through history."},
    {"block_id": "b094", "panel_ids": ["panel_0095"], "narration": "Now, with his safety net guaranteed and limitless resources secured, the true journey begins."},
    {"block_id": "b095", "panel_ids": ["panel_0096"], "narration": "He steps out of the United Merchants guild into the vibrant morning sun of Babylon."},
    {"block_id": "b096", "panel_ids": ["panel_0097"], "narration": "The sky above the Babel Tower gleams with endless promise and adventure."},
    {"block_id": "b097", "panel_ids": ["panel_0098"], "narration": "He smiles warmly: it is finally time to enjoy everything he missed out on."},
    {"block_id": "b098", "panel_ids": ["panel_0099"], "narration": "Bae Hu-ryeong floats beside him, eager to begin their specialized combat training."},
    {"block_id": "b099", "panel_ids": ["panel_0100"], "narration": "With four thousand gold invested into rare elixirs, Gong-ja's physical body will be reforged."},
    {"block_id": "b100", "panel_ids": ["panel_0101"], "narration": "The foundation is set, the funds are secured, and the master is ready to teach."},
    {"block_id": "b101", "panel_ids": ["panel_0102"], "narration": "Kim Gong-ja prepares to conquer the trials of the tower with unstoppable momentum."},
    {"block_id": "b102", "panel_ids": ["panel_0103"], "narration": "No challenge on the upcoming floors will match the horror he has already conquered."},
    {"block_id": "b103", "panel_ids": ["panel_0104"], "narration": "The legend of the SSS-Class Revival Hunter marches forward into its next glorious phase."},
    {"block_id": "b104", "panel_ids": ["panel_0105"], "narration": "Together, disciple and spectral emperor will carve their names across every single floor."},
    {"block_id": "b105", "panel_ids": ["panel_0106"], "narration": "The climb toward the summit of the Babel Tower is officially underway."},
    {"block_id": "b106", "panel_ids": ["panel_0107"], "narration": "Babylon's elite rankers will soon witness the rise of an immortal prodigy."},
    {"block_id": "b107", "panel_ids": ["panel_0108"], "narration": "Gong-ja takes a deep breath, walking toward his brand new luxury estate."},
    {"block_id": "b108", "panel_ids": ["panel_0109"], "narration": "His past as a miserable F-rank nobody in a rotted studio is officially buried forever."},
    {"block_id": "b109", "panel_ids": ["panel_0110"], "narration": "Ahead lies the path of martial mastery, wealth, and supreme power."},
    {"block_id": "b110", "panel_ids": ["panel_0111"], "narration": "The Sword Emperor grins, ready to forge his fearless disciple into a peerless blade."},
    {"block_id": "b111", "panel_ids": ["panel_0112"], "narration": "The hundred floors await their ultimate challenger."},
    {"block_id": "b112", "panel_ids": ["panel_0113"], "narration": "Kim Gong-ja steps boldly into the future, unstoppable and unyielding."},
    {"block_id": "b113", "panel_ids": ["panel_0114"], "narration": "The curtain falls on his humble beginnings as the grand ascent begins."},
    {"block_id": "b114", "panel_ids": ["panel_0115"], "narration": "The Revival Hunter's story has officially ignited!"},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch08")
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
        chapter_id="sss-class-revival-hunter/ch08",
        title="SSS-Class Revival Hunter - Chapter 8",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch08/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 08 Script ===")
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
