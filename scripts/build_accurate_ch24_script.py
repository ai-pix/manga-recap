"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 24.

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
    # --- ACT 1: A TRUE WARRIOR'S APOLOGY (p0002 - p0026) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "Gong-ja stands firmly before the humbled elder, quietly awaiting a proper apology."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "The hall falls dead silent as humanity greatest legends witness the shocking confrontation."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "The Paladin reminds Marcus that Gong-ja presented a completely reasonable and justified request."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Marcus trembles with visible inner turmoil, his proud gaze dropping to the floor."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "Gong-ja wonders whether the stubborn swordsman will invent excuses or double down furiously."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "Will Marcus claim the Paladin lied to preserve corrupt political guild interests?"},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "Or will he cowardly reveal his vision skill to justify his murderous mistake?"},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "Excuses might soothe his wounded pride, but they would utterly destroy his dignity."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "Marcus slowly looks up, addressing the young rookie by name: Confucius Kim."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Gong-ja tenses slightly, knowing prideful monsters often kill witnesses to silence truth."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "The cold edge of Marcus rapier glints under the grand chandelier light."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "When confronted with monumental errors, fragile human nature naturally seeks cowardly deception."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "Just like the Flame Emperor did when his villainous cruelty was publicly unmasked."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "Marcus takes a deep, ragged breath, asking to restart this dialogue anew."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "Lowering his unsheathed blade, the venerable warrior releases his suffocating aura."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "In front of everyone, Marcus Calenprius bows his head deeply in profound apology."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "He admits that reckless, blind prejudice nearly caused him to butcher an innocent."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "For decades, Marcus appointed himself supreme executioner, slaying anyone he deemed thoroughly wicked."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "He vows solemnly that he will never allow such dangerous arrogance to govern him."},
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "Marcus acknowledges empty verbal apologies are worthless, offering complete restitution for his transgression."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "Instead of lashing out or making pathetic excuses, he genuinely takes full accountability."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "The legendary elder begs for forgiveness, hoping to reach the tower summit someday."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "His heartfelt words echo through the hall: I was wrong; please forgive me."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "He stands vulnerable, relinquishing all pride before a teenage novice hunter."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "The Paladin softly nods, confirming that Marcus speaks with absolute, undeniable sincerity."},

    # --- ACT 2: UNORTHODOX FORGIVENESS & MATCHMAKING CHAOS (p0027 - p0052) ---
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Moved by the elder humility, Gong-ja breaks the heavy silence with a proposal."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "He asks Marcus Calenprius to personally teach him the art of swordsmanship."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "Specifically, Gong-ja requests that the Blade Saint become his official sparring partner."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "With an ancient master sparring against him, his martial growth would explode exponentially."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "Gong-ja quickly backtracks playfully, pretending to feel awkward about such a heavy demand."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "He jokes that forgiving an attempted assassination completely free of charge feels unsatisfying."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "Handing out free forgiveness would make him look way too saintly and forgiving."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "People might think he lacks backbone if he lets the old master off easily."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "Since steel was unsheathed, demanding private sword lessons feels like the perfect middle ground."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Gong-ja scratches his cheek, cheekily asking again for personal sword training lessons."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "The Paladin covers her mouth in pure amusement at the boy unexpected wit."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "She laughs softly, confirming that every single word Gong-ja spoke was completely true."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "Poisonous Viper gapes in disbelief, amazed Gong-ja chose lessons over limitless wealth."},
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "Countess smiles wryly, amused by the young rookie unorthodox, fearless character."},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "Inquisitor clasps his hands together in religious ecstasy, praising this beautiful display of forgiveness."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "A sinner repents honestly and the victim offers graceful redemption: a sublime moral spectacle!"},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "The Witch sighs in immense relief, glad this explosive catastrophe resolved without bloodshed."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "Marcus eyes tear up with overwhelming gratitude, deeply touched by Gong-ja gentle heart."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "Grabbing Gong-ja arm enthusiastically, Marcus promises to spar with him every single day."},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "The overjoyed elder insists that Gong-ja must address him affectionately as Grandpa Marcus."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "Marcus eagerly inquires about Gong-ja age, wondering if he has a girlfriend yet."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "The aggressive elder immediately tries setting him up with his beautiful, beloved granddaughter."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "Bae Hu-ryeong bursts into hysterics, calling Marcus an insufferable, meddlesome old grandpa."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "Gong-ja recoils in comical panic as Marcus pitches romantic matchmaking aggressively."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "Marcus vows to introduce them immediately, determined to turn Gong-ja into family."},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "Gong-ja sweats nervously, jokingly wondering if he should commit suicide just to reset."},

    # --- ACT 3: THE DEMON KING'S TEMPTATION (p0053 - p0065) ---
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "Suddenly, an urgent golden notification chime announces that eleventh-floor clear rewards are arriving."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Having cleared first place, Gong-ja receives the exclusive privilege of choosing first."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "Little was known about floors twelve through twenty before his miraculous revival ability."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "The system displays two contrasting reward choices: the Goddess Blessing and something darker."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "The Goddess of Protection offers prestigious imperial administrative titles with inherited combat capabilities."},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "Positions include Prime Minister, General-in-Chief, Minister of Finance, and Imperial Knight Commander."},
    {"block_id": "b058", "panel_ids": ["panel_0059"], "narration": "Gong-ja turns his gaze toward the mysterious alternative: the Demon King Reward."},
    {"block_id": "b059", "panel_ids": ["panel_0060"], "narration": "The Demon King of Autumn Rain secretly offers an unimaginably sinister proposition."},
    {"block_id": "b060", "panel_ids": ["panel_0061"], "narration": "Assassinate the other nine top challengers to receive immediate teleportation to floor ninety-nine."},
    {"block_id": "b061", "panel_ids": ["panel_0062"], "narration": "Gong-ja eyes widen in horror as the blood-soaked requirements sink into his mind."},
    {"block_id": "b062", "panel_ids": ["panel_0063"], "narration": "Marcus notices Gong-ja sudden trance, wondering why the boy froze in silence."},
    {"block_id": "b063", "panel_ids": ["panel_0064"], "narration": "The system repeats its cold, mechanical prompt, urging Confucius Kim to choose."},
    {"block_id": "b064", "panel_ids": ["panel_0065"], "narration": "Standing between virtue and demonic temptation, Gong-ja faces a destiny-defining decision."},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch24")
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
        chapter_id="sss-class-revival-hunter/ch24",
        title="SSS-Class Revival Hunter - Chapter 24",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch24/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 24 Script ===")
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
