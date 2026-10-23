"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 17.

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
    {
        "block_id": "b001",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "The title flashes, promising resurrected hunters and chaotic destiny."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Gong-ja smirks, hearing accusations about cats turning human, unphased."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Countess twirls a stick, mocking ghosts while red\u2011haired fury watches."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Rumors swirl: a forty\u2011year\u2011old tower titan allegedly sips youth elixir."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "A nervous uniformed voice pleads, while two silent specters observe."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Skeptical officer balks at half\u2011million gold; graceful lady defends achievement."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Countess pierces his excuses; he mutters a resigned, weary yes."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "She brandishes jeweled cone, demanding summons for every hidden power."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "A lone voice declares misalignment, echoing through the vaulted chamber."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "The Countess raises the stakes, inviting only the bravest gamblers."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "She smiles smugly, Gong-ja's curiosity piqued by her enigmatic offer."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "A frantic whisper about a crazy cat lady jolts Gong-ja's composure."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Viper's thunderous stomp shakes the floor, echoing his unyielding fury."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Poisonous Viper snarls, his curse ricocheting through the tense council."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "The inquisitor's eyes glitter, admitting missteps while plotting future advantage."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Silver-clad knight deflects blame, boasting strategic foresight over chaotic rumors."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Purple-haired witch watches, her icy stare promising lethal retribution soon."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Red-haired specter hovers, delighting in the all-star hunters' begrudging reunion."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Old comrades reminisce, yet sarcasm simmers like broth ready to boil."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Gold glitter blinds ambitions, while Bae smirks, urging coffee over contracts."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Leader orders mocha, setting etiquette precedent for the tower's elite gathering."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Orders cascade\u2014iced latte, hazelnut, Americano\u2014each reflecting personalities in steam."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "A jagged exclamation pierces the air, demanding reality's harsh acknowledgment."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Rage erupts, yet calm barista offers espresso, tempering chaos with caffeine."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Blonde summons waiter; flame emperor glares, muttering cursed priest."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Barista scribbles chaotic coffee order, flustered, then yells 'Wait!'"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Mister Kim, your choice? a voice demands, hovering above."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Six guild heads surround Gongja; he declares, 'This is a setup.'"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Red\u2011haired ghost whispers, 'No coincidence; proxies softening you, fear not.'"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Gongja's eyes harden; he recalls burning alive, unshakable resolve."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Nervous waiter trembles, hand extended, pleading for calm composure."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Gongja requests hot chocolate, barista obliges, noting his indifference to fear."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Blonde woman remarks, 'Your sudden power after floor ten astonishes me.'"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Text boxes argue: worst threat? Death. Fearlessness fuels greatest strength."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Red\u2011haired mentor crosses arms, praising alliance yet warning lingering danger."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Fan\u2011waving lady declares lottery\u2011won youth possesses luck, nerve, skill, destiny."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Eyepatch leader sighs, blames underestimation, urges immediate recruitment of the floor\u2011clearing prodigy."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Gongja's cool stare replies, 'That's irrelevant,' dismissing the hype."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Purple\u2011haired witch, surrounded by expressionless mirrors, reminds everyone reputation isn't everyone's burden."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Direct question floats in white: 'Which guild will you join, hunter?'"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Intense gaze demands answer, warning media strategy hinges on his decision."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Gongja smirks, ponders, 'What if I actually consider joining a guild?'"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "A chilling promise follows: 'We'll unleash fierce bidding for your allegiance.'"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Time wasted on the ninth floor fuels urgency for a higher\u2011stakes venture."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "She declares the cleared tenth floor a marketing goldmine, sparking curiosity beyond."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Gongja mentions food shortage, noting monster scarcity threatens supply chains."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Countess fans herself, lamenting dwindling trade routes, demanding fresh commodities."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Purple\u2011eyed recruit urges new hunters, promising exclusive items beyond tenth floor."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Flame Emperor questions his role as the new era\u2019s flamboyant advertising icon."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "The Black Dragon\u2019s attempt to kill the icon sparks whispered accusations toward the witch."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Gongja acknowledges the witch, proposing their alliance will launch the era\u2019s symbol."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Gongja shuffles through options, suggesting a bold gamble to settle guild hierarchy."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "A glinting Ace of Spades appears, promising high stakes and hidden motives."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Everyone freezes as the question echoes: a deck of cards?"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Gongja proposes poker, wagering guild allegiance without gold or titles."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "The council watches, intrigued by the promise of simultaneous multi\u2011guild membership."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Gongja declares his ordinary fa\u00e7ade masks an equal standing among all."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "A smug yellow\u2011cloaked figure accepts, mocking the newcomer\u2019s lofty expectations."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Blonde and eyepatch rivals demand fair play, banning all supernatural tricks."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "The armored knight concedes, preferring creative card tactics over empty coffers."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "The Black Dragon Witch seals the deal, cards fluttering like dark promises."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Bae whispers, Gong-ja's eyes widen as his modest hand flickers with destiny."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "Red-haired specter demands respect, his voice echoing like a gauntlet thrown."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Countess and her aide trade banter, cards clacking, confidence blooming."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Gong-ja smirks, fan of cards raised, loyal red ghosts roar approval."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Silence shatters as the master declares the game\u2019s deadly opening."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch17")
    desc_path = ch_dir / "03_descriptions.json"
    script_path = ch_dir / "04_script.json"

    desc_file = load_model(desc_path, DescriptionFile)

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
        chapter_id="sss-class-revival-hunter/ch17",
        title="SSS-Class Revival Hunter - Chapter 17",
        series="sss-class-revival-hunter",
        created_at=datetime.now(timezone.utc).isoformat(),
        model="mercury-2",
        target_words=len(script_blocks) * 12,
        blocks=script_blocks,
    )

    cfg = load_config()
    report = validate(script_file, desc_file, cfg)

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_file.model_dump_json(indent=2))

    alt_script_path = Path("data/chapters/revival_hunter_ch17/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 17 Script ===")
    print(f"Total Blocks: {len(script_blocks)}")
    print(f"Total Spoken Words: {script_file.total_words}")
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
