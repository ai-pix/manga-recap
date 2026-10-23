"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 25.

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
    # --- ACT 1: GHOST MASTER'S WARNING & STRATEGIC FORFEIT (p0002 - p0020) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "Staring at the floating notification window, Gong-ja instantly recognizes the demonic offer as a trap."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "Bae Hu-ryeong urgently whispers into his ear, warning his reckless partner not to take the bait."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "Gong-ja deduces that the arrogant Flame Emperor undoubtedly chose this demonic shortcut in his previous life."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "The stakes heighten as Gong-ja uncovers the dark history of the tower trials."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "Yet Yoo Soo-ha was still stuck on floor forty, proving this demonic deal never worked."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "The Flame Emperor must have chosen betrayal, experienced horrible disaster, and used regression to escape."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "Even so, skipping straight to floor ninety-nine is an extraordinarily tempting, once-in-a-lifetime proposition."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "Gong-ja playfully ponders scouting the final boss room before resetting with his death skill."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "Bae Hu-ryeong glares furiously, firmly commanding his disciple not to dare take that leap."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "The ancient sword emperor speaks from agonizing personal failure: he conquered up to ninety-nine himself."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "Having experienced that nightmare firsthand, the ghost warns that floor ninety-nine is pure revolting agony."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "Gong-ja lacks the combat prowess to slaughter nine champions or conquer the upper floors."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "When Gong-ja asks if the boss is invincible, Bae Hu-ryeong drops a chilling bombshell."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "There is no boss waiting at floor ninety-nine; only something infinitely more vicious and cruel."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "Chained by spectral memories, the ancient master shudders, leaving Gong-ja terrified by the ominous truth."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "Bae Hu-ryeong reminds Gong-ja that his steady, patient path will eventually conquer the spire safely."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "Gong-ja gazes downward, contemplating the profound wisdom of his ghost master ancient advice."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "He resolves to take a tactical step back, refusing the reckless gamble entirely."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "Prioritizing long-term survival, Gong-ja decides to forfeit both stage rewards completely this round."},

    # --- ACT 2: MAFIA IN BABYLON & REWARD DRAFT (p0021 - p0046) ---
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "Taking a temporary step back now will ensure humanity ultimate leap forward later."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "Turning toward the assembled guild leaders, Gong-ja announces that the stage rewards have appeared."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "The leaders urge him to claim his well-deserved prize so the selection can pass along."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "To everyone utter astonishment, Gong-ja loudly declares that he will not choose any reward."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "The hall erupts in sheer disbelief as the system registers Gong-ja historic forfeiture."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "A perplexed divine notification appears: the Goddess of Protection deeply questions his unexpected decision."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Meanwhile, a chilling darkness ripples as the Demon King of Autumn Rain chuckles sinisterly."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "The Paladin gasps in bewilderment, asking why Gong-ja would throw away such monumental blessings."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "Marcus steps forward next in line, accepting his turn as the second-place floor challenger."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "Gong-ja stands calmly on the sidelines, observing how the remaining nine contenders will react."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "Marcus inspects the imperial titles, remarking that selecting an administrative post is a complex duty."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "Pledging his allegiance to the empire, Marcus selects the prestigious title of Knight Commander."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "The remaining hunters watch intently as the unique reward distribution mechanics unfold before them."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "Inquisitor claps his hands cheerfully, suddenly realizing how the two opposing options function."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "The eccentric cultist bounces forward excitedly, promising to explain the deadly hidden rule."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Displaying the contrasting Goddess and Demon King rewards, Inquisitor lays out the chilling reality."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "Marcus and the guild masters stare in shock at the Demon King shortcut to ninety-nine."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "Inquisitor excitedly compares this twisted stage setup to a classic game of psychological mafia."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "Those choosing the Goddess are Warriors, while anyone picking the Demon King is a Traitor."},
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "The Paladin notes the Traitor faces terrible odds against nine allied Warriors with lie detection."},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "Inquisitor beams, reiterating that the Warriors hold an overwhelming tactical and moral advantage here."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "Selecting next, Inquisitor claims the role of General-in-Chief, pledging fealty to the imperial flag."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "Poisonous Viper chooses Captain of the Guard, while another master takes Minister of Foreign Affairs."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "The Witch chooses Prime Minister, frantically pleading for everyone to reject the Demon King option."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "Countess smiles smugly, naturally choosing the lucrative position of Imperial Minister of Finance."},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "A massive chime rings through the imperial cathedral: all reward selections have officially concluded."},

    # --- ACT 3: THE TRAITOR REVEALED (p0047 - p0058) ---
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "Bae Hu-ryeong nudges Gong-ja, asking if sitting out with zero buffs feels too punishing."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "The system screen flickers, preparing to tally the votes among humanity top ten champions."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "A blue prompt confirms that exactly one challenger chose to forfeit their floor reward."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "The system reveals the tally for recipients who chose the Goddess of Protection blessing."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "Goddess recipients: eight people. Demon King recipients: exactly one treacherous individual!"},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "The horrifying prompt freezes everyone blood: a traitor walks among the top ten hunters."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "The Witch screams in panic, cursing the foolish traitor who chose the demonic trap."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Countess narrows her eyes in disbelief that someone dared accept such suicidal disadvantages."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "Poisonous Viper shudders with cold chills, feeling a grim déjà vu from the tower early days."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "Countess recalls the bloodbath when the original Ten Great Guilds brutally butchered each other."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "The Witch shouts hysterically, commanding the Paladin to interrogate every single person immediately!"},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "The system flashes an ominous farewell: may luck be on your side in Babylon."},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch25")
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
        chapter_id="sss-class-revival-hunter/ch25",
        title="SSS-Class Revival Hunter - Chapter 25",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch25/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 25 Script ===")
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
