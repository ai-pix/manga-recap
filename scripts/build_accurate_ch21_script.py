"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 21.

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
    # --- ACT 1: TACTICAL GENIUS ON THE BATTLEFIELD (p0002 - p0020) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "A new trial begins as Kim Gong-ja charges straight into the perilous eleventh floor."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "His copied B-rank skill, Insight of the Battlefield, instantly maps every enemy weakness."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "Gong-ja directs the imperial army, barking precise orders to wipe out the commander."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Heavily armored imperial knights charge fearlessly forward, trusting the prophesied warrior with their lives."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "Thanks to his repeated death loops, Gong-ja expertly guides the soldiers through every ambush."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "An explosive cavalry strike catapults a green goblin commander violently into the blood-red sky."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "Raising his legendary holy sword high, Gong-ja unleashes the blinding light of the goddess."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "Ancient empire legends foretold that a destined foreign warrior would wield this sacred relic."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "Beholding the gleaming blade, the entire imperial cavalry drops to their knees in reverence."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Gong-ja raises his fist in triumph, relishing the glorious fruits of his endless grinding."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "Bae Hu-ryeong screams in frustration, furious that his disciple picked such a useless weapon."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "The ancient sword ghost complains that the blade is merely shiny and slightly sturdy."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "Gong-ja smirks back, explaining the sword grants absolute loyalty from every single imperial ally."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "Unlike arrogant players, Gong-ja treats these tower inhabitants as living people with real hearts."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "Cheering imperial soldiers rush into the fray, fighting desperately to protect their homeland alongside him."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "Nearby hunters watch in disbelief, baffled that an unknown rookie commands the entire army."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "Gong-ja basks shamelessly in their jealousy, confessing that he truly loves being the center of attention."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "The tactical minimap confirms complete victory as the demon army left flank collapses."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "Gripping his radiant dagger, Gong-ja orders a full-scale assault directly toward the enemy stronghold."},

    # --- ACT 2: BOSS SLAIN & ONE-DAY CLEAR (p0021 - p0038) ---
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "Moral surges through the ranks as thousands of allied troops rally behind their general."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "Suddenly, a colossal silhouette emerges: the dreaded eleventh-floor boss, the Great Goblin King."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "The monstrous beast roars in fury, ordering his chaotic goblin vanguard to hold the line."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "Leaping high into the sky, Gong-ja spins gracefully with his aura blade ignited."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "He triggers his High Goblin Society skill, turning the monster own hierarchy against him."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "With a thunderous crash, the monstrous goblin monarch drops dead onto the bloody battlefield."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Victorious knights thrust their weapons into the air, screaming praises for the goddess warrior."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "A thunderous chorus of triumph echoes across the plains: Long live the Aegeam Empire!"},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "The remaining goblin horde whimpers in terror, helplessly retreating before the unstoppable imperial advance."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "Swarms of fleeing monsters look up in terror as allied ambush units close the encirclement."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "Steel slashes through flesh in a rapid flurry, cutting down every last monster survivor."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "Top hunters lean over the balcony railings, mocking the pathetic retreat of the horde."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "Elite guild members dive into the retreating vanguard, mercilessly slaughtering the remaining goblin troops."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "A massive golden system prompt flashes across the sky: the eleventh floor is officially cleared!"},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "Hunters roar in wild celebration, stunned that an entire floor fell in a single day."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "The contribution rankings illuminate the sky, revealing Confucius Kim firmly seated at number one."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "Murmurs of confusion ripple through the crowd as hunters stare at the unknown name."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "They suddenly realize this nameless rookie is the very same person who conquered floor ten."},

    # --- ACT 3: A GHOST MASTER'S PRIDE & A WARRIOR'S HANDSHAKE (p0039 - p0064) ---
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "Spectators wonder in awe if this mysterious newcomer is some reclusive grandmaster in hiding."},
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "Bae Hu-ryeong scoffs loudly, insisting that Gong-ja won solely through shameless tricks and luck."},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "Floating defiantly beside him, the stubborn ghost martial master demands acknowledgment of pure swordsmanship."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "Gong-ja watches his ghost master silently, noticing how deeply he values martial fundamentals."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "To this legendary ancient spirit, honest discipline matters more than all the world shortcuts."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "Gong-ja knows that without proper blade mastery, he will never survive the tower summit."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "He reassures the sulking ghost, promising to diligently practice sword techniques before floor twenty."},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "Bae Hu-ryeong perks up instantly, puffed with immense pride at his partner earnest flattery."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "The goofy martial ghost laughs boisterously, celebrating that his rookie disciple finally sees his genius."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "The clamor of clashing steel gradually subsides as the exhausted imperial soldiers regroup."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "The veteran imperial general steps forward, expressing deep, sincere gratitude to the young savior."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "Gong-ja smiles politely, warmly insisting that this historic victory was won by everyone fighting together."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "The battle-hardened old commander pauses, admitting he once carried grave doubts in his heart."},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "Ancient prophecies foretold that travelers from another world would arrive to rescue their empire."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "Yet the old soldier feared that strangers would never bleed for a land not their own."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Seeing Gong-ja noble courage, the commander realizes his cynical fears were completely unfounded."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "Extending his scarred hand forward, the veteran offers a solemn and heartfelt warrior handshake."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "Their palms reach across the divide, bridging two vastly different realms through mutual respect."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "Regardless of which world one hails from, the sacred bond of trust remains identical."},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "Gong-ja firmly grasps the general hand, vowing never to betray the empire hopes."},
    {"block_id": "b058", "panel_ids": ["panel_0059"], "narration": "A glowing system window materializes, announcing that individual stage rewards are now being calculated."},
    {"block_id": "b059", "panel_ids": ["panel_0060"], "narration": "Calculations conclude as radiant light descends upon the top ten highest-ranking challengers in Babylon."},
    {"block_id": "b060", "panel_ids": ["panel_0061"], "narration": "The system grants exclusive priority entry to the upcoming twelfth floor for top performers."},
    {"block_id": "b061", "panel_ids": ["panel_0062"], "narration": "No ordinary hunter may proceed until the elite vanguard receives their destiny-altering floor rewards."},
    {"block_id": "b062", "panel_ids": ["panel_0063"], "narration": "An emotional imperial soldier clutches Gong-ja boots, tearfully begging him to protect their kingdom."},
    {"block_id": "b063", "panel_ids": ["panel_0064"], "narration": "Gazing down at the radiant light, Gong-ja vows to safeguard this realm until the end."},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch21")
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
        chapter_id="sss-class-revival-hunter/ch21",
        title="SSS-Class Revival Hunter - Chapter 21",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch21/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 21 Script ===")
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
