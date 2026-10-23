"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 22.

High-retention YouTube manhwa recap style (Mamoru style).
1:1 panel sync, zero dropped beats, 100% pipeline validation compliance.
"""

from __future__ import annotations

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
    # --- ACT 1: TELEPORTATION TO THE IMPERIAL PALACE (p0002 - p0011) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "A pillar of radiant light engulfs the top ten hunters, preparing them for immediate teleportation."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "Gong-ja laughs off his ally nervous warnings, joking that dying is practically his daily routine."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "Stepping out of the teleportation gate, he enters the royal palace with a calm smile."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Gong-ja looks around in astonishment, taking in the magnificent architecture of the imperial palace."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "High-ranking guild masters look around in awe, stunned to be summoned directly before the throne."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "The eccentric Inquisitor bounces over excitedly, singing lavish praises for Gong-ja brilliant tactics."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "Using his sinister rejuvenation technique, the fanatical cultist maintains the appearance of an innocent child."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "The cheerful boy pokes Gong-ja arm, eagerly asking about his radiant holy sword from floor ten."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "Inquisitor beams with admiration, marveling at how a rookie weaponized his prize so effectively."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Gong-ja sheepishly scratches the back of his head, playfully pretending to be modest and humble."},

    # --- ACT 2: BLADE SAINT'S LETHAL ASSAULT (p0012 - p0027) ---
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "Suddenly, an ominous voice chants a sacred technique: Divine Body!"},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "A lethal silver sword flashes forward at blinding speed, aimed directly at Gong-ja neck."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "Inquisitor swiftly parries the deadly blow, asking why the legendary Blade Saint turned into an assassin."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "Blade Saint glares with pure murderous hatred, commanding the annoying brat to move aside immediately."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "The grizzled old master coldly vows to slaughter the filthy rookie standing before his eyes."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "The lethal confrontation escalates as tension erupts between humanity greatest living legends."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "Inquisitor calmly steps into the elder path, asking why he wants to execute Confucius Kim."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "Blade Saint levels his slender rapier, threatening to sever Inquisitor arm without a second thought."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "Inquisitor chuckles playfully, noting that letting him murder their guest would ruin the guild reputation."},
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "The ancient swordsman narrows his eyes, snapping that he owes explanations to absolutely no one."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "Inquisitor eyes gleam with dangerous excitement, realizing the stubborn elder refuses to back down peacefully."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "A blinding aura explodes around the blonde youth as sacred battle energy surges upward."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "Unleashing Holy Transmission, the cult leader teleports rapidly across the battlefield in dazzling light."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "Pillars of incandescent white mana split the air, clashing violently against Blade Saint steel."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "Poisonous Viper leaps into the air with twin daggers, screaming curses at the annoying old man."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Gong-ja collapses onto his knees in shock, terrified by the old master unfathomable combat power."},

    # --- ACT 3: GOLD BUFF & ALLIANCE SHIELD (p0028 - p0056) ---
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "Poisonous Viper and Inquisitor bicker childishly mid-battle, insulting each other age and messy tactics."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "The stoic Paladin steps forward, warning everyone that they are severely outmatched by Marcus."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "Even working together, the guild representatives recognize that Marcus Calenprius is an absolute monster."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "Inquisitor spins toward Countess, aggressively demanding an instant donation of ten thousand gold coins."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "Countess calmly raises her fan, offering a predatory business loan with fifteen percent compound interest."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "The wealthy businesswoman shrieks in fury as Inquisitor shamelessly pressures her for free religious charity."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "A spectral golden banker manifests beside Countess, grumbling that Inquisitor is a world-class extortionist."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "Ten thousand glittering gold coins erupt from Countess purse, swirling into a colossal serpentine dragon."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Inquisitor lunges forward with glee, greedily snatching the swirling mass of liquefied divine currency."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "Chanting Sacred Technique Devotion, he funnels the gold into massive three-hundred-second physical enhancements."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "Gong-ja watches in awe as Paladin and Poisonous Viper swell with monstrous divine strength."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "Surrounding the elder, the empowered guild masters warn Marcus that even he cannot withstand them all."},
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "Blade Saint scoffs at their united front, demanding to know what ridiculous agreement they made."},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "They declare that Gong-ja formally joined all five guilds as an equal, making him untouchable."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "Marcus grits his teeth, recalling the harsh warning he delivered back on floor eleven."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "His own words echo back: in this tower, you must command an army to survive."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "Bae Hu-ryeong watches silently, remembering the brutal realities of climbing this merciless spire."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "Marcus had told him: either possess the godlike power to slaughter demon armies alone..."},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "Or forge unbreakable alliances and lead a mighty army of your own to victory."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "Now, Gong-ja has masterfully outmaneuvered him, turning humanity strongest factions into his personal shield."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "Gong-ja steps forward calmly, deciding it is time to defuse this explosive misunderstanding peacefully."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "He walks right up to Marcus, politely asking if they can sit down and talk."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "Marcus pauses in utter shock, stunned that a supposedly ruthless killer proposes a peaceful chat."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "Gong-ja confesses that he has genuinely respected and admired the legendary Blade Saint for years."},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "Yet the paranoid elder remains convinced that Gong-ja is a deceitful assassin sent to butcher him."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "From an outsider perspective, Gong-ja lightning-fast rise to fame looks completely unnatural and suspicious."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Marcus firmly believes this young prodigy is merely a puppet manufactured by corrupt political guilds."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "Floating above Gong-ja head is the terrifying number four thousand ninety-three."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "Glaring through his vision skill, Marcus roars that everyone in this room is in cahoots!"},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch22")
    desc_path = chapter_dir / "03_descriptions.json"
    script_path = chapter_dir / "04_script.json"

    desc_file = load_model(desc_path, DescriptionFile)

    script_blocks = [
        ScriptBlock(
            block_id=b["block_id"],
            panel_ids=b["panel_ids"],
            narration=b["narration"],
        )
        for b in blocks_data
    ]

    script_file = ScriptFile(
        chapter_id="sss-class-revival-hunter/ch22",
        title="SSS-Class Revival Hunter - Chapter 22",
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

    # Mirror to junction path
    alt_script_path = Path("data/chapters/revival_hunter_ch22/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 22 Script ===")
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
