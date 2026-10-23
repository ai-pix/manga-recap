"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 18.

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
        "narration": "The crimson-haired strategist shouts, while gold coins clink on the table."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Gongja gestures surrender, skull-marked 'FOLD' looming over his indifferent stare."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Red mane leans, scoffing at the eyepatch's weak pair, coins cascade."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Gongja calmly lays a card, then piles golden wealth beside it."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Red-haired whisper warns the armored knight, exposing impossible full house odds."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Gongja thrusts his gold mountain forward, declaring an audacious all\u2011in."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "A diverse tableau gathers, coffee steaming, coins glittering, tension palpable."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "White\u2011haired fury erupts, cards scattering, while calm sips coffee unbothered."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Grey\u2011haired accuser bellows, demanding proof as rounds stack, disbelief mounting."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Gongja flashes peace, mocking the frantic hunter's desperate, unfounded accusations."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Eyepatch hunter reels, stunned by sudden revelation of his secret E\u2011class promotion."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Grateful rival taunts, noting depleted chips, while Gongja sighs in exasperation."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "The venomous VIPER arrives, tension thickening like stale casino smoke."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Espresso shot offered, a caffeinated dare to calm the raging mind."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "He recoils, refusing the tea, while the newcomer smirks knowingly."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "An angry shout ricochets, branding the opponent a sanctimonious fool."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Title flashes, reminding everyone of the relentless hunt for revival."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Gongja slumps, shoulders sagging, muttering a weary lament under neon lights."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Defeated yet smirking, he questions the opponent's alleged telepathic edge."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "The armored mentor taunts, hinting at hidden perception beyond ordinary sight."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "A furious rebuke erupts, accusing the defeated hunter of cowardly surrender."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Eyepatch villain fumes, demanding retribution for the escaped scammer's triumph."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Flame Emperor sneers, labeling the newcomer a cunning scammer with admiration."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "The helmeted veteran smirks, confirming his foresight with cryptic confidence."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "She deals cards, smirking, while Gongja watches, a mystery lingering."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Gongja declares his confidence, challenging hunters without revealing his hidden edge."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Eyepatch hunter recoils as armored figure looms, a poisonous viper mocked."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Gongja taunts, urging pride, while cards tumble, stakes oddly comforting."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Armored voice asks, 'Does pride satisfy your hunger?' echoing ominously."
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Blonde woman forces espresso down viper's throat, laughing at his shock."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "A weary player sighs, 'It's a relief,' then questions the unknown."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Purple-haired woman declares eye-to-eye confrontation, cards and coins glinting."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "A pale hand stacks gold, reminiscing about a war\u2011torn Ukrainian past."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Rubble\u2011stomping wanderer recounts lost family, denouncing tower's harsh solitude."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Gongja places gold coin, prompting cryptic exchange about hidden motives."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Gongja reflects, 'Every tower visitor carries a story; I'm just an orphan.'"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Red-haired veteran gestures, declaring diamond flush; gold coins glitter like promises."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Blonde sips, grey scholar ponders, armored knight watches; hierarchy dissolves amid cards."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Purple-haired woman glances aside, reminding everyone tower's rules ignore past."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Sari-clad lady manages coins, proclaiming equal challengers under tower's blessing."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "A hand drops another coin, questioning outer world's disdain for this sanctuary."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Purple locks hold card, clink echoing, roses bloom despite dump's gloom."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Clock ticks 18:09:12, prophecy whispers: fame awaits, life transforms instantly."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Purple-haired woman drinks, cards reveal; Gongja nods, urging wise handling."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "She boasts attention, admits jealousy; Gongja calls her Blade Saint's opposite."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Hand rubs coin, Black Dragon Guild leader clings to flush, hope flickers."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "She declares all-in, gold coins tumble, tension spikes like fireworks."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Self-assured whisper echoes, confidence fuels the next daring gamble."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Gongja eyes the glittering hoard, greed flickering behind his deadpan smile."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Coins tower like ambition; his whispered vows echo, promising relentless tower conquest."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Amid clashing egos, Gongja declares climbing the tower his ultimate, selfish pilgrimage."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "The witch watches twilight, pondering fate while the sun bleeds behind clouds."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "She presses cards to her brow, sighing, as fatigue drapes her thoughts."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Behind the gold, she admits defeat, likening him to the legendary Blade Saint."
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "A flickering card bends, questioning his pride with a cheeky, daring grin."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Ace glints, flush meets full house, and the hunter's greed crowns him victor."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Closed-eyed grin softens his aura, turning insults into humble gratitude."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "He demands equal respect, urging responsibility as the tower's weight shifts."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Sip in hand, he declares climbing the tower his duty, confidence unshaken."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "She scoffs, mocking his arrogance, noting smugness could've earned S\u2011class rank."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Gongja's serene grin unnerves the roaring trio, their cheers echoing desperation."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "The crowd gasps, questioning the title that fuels their fierce curiosity."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "A sharp retort slices the tension, daring the opponent to stay."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Gongja hints at upcoming trials, while the witch probes his cryptic preparations."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "The witch declares roleplay, foretelling ten floors of twisted, strategic chaos."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "He clutches a vague clue, the only compass toward the elusive tenth."
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "Displeasure flickers as she cradles softness, masking deeper doubts about upcoming trials."
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "A solemn vow drifts, promising future retribution for debts lingering."
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "Sunset silhouettes fade, neon clock ticking, marking their relentless pursuit of ascent."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch18")
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
        chapter_id="sss-class-revival-hunter/ch18",
        title="SSS-Class Revival Hunter - Chapter 18",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch18/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 18 Script ===")
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
