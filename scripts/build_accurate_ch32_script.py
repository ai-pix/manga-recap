"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 32.

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
    {
        "block_id": "b001",
        "panel_ids": [
            "panel_0001"
        ],
        "narration": "The golden title shines bright as our story of revival begins today.",
        "direction": "dramatic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "A massive black name appears on screen with jagged edges everywhere.",
        "direction": "dramatic"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "A lone hunter faces a charging horde of armored soldiers ahead.",
        "direction": "dramatic"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Gongja screams about arrows while others stare in shock at lightning.",
        "direction": "dramatic"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "The knight demands strength to protect the empire from chaos now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "The purple haired vampire leader shouts for her dragons to gather.",
        "direction": "dramatic"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "She declares her guild takes charge of this massive battlefield today.",
        "direction": "dramatic"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "He divides the guilds into left and right flanks quickly.",
        "direction": "dramatic"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Dust rises as fighters rush forward to kill more orcs now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Hunters fight slimes in heavy rain while leaders urge teams to stay safe.",
        "direction": "dramatic"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "A strange plant grows on a helmet amidst chaotic energy streaks.",
        "direction": "dramatic"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Empire soldiers rally to support the ruthless warriors fighting monsters.",
        "direction": "dramatic"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Gongja speaks to a warrior while the Flame Emperor hovers nearby.",
        "direction": "dramatic"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "The battle rages on as tension builds between the enemies.",
        "direction": "dramatic"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Two men discuss attention and fame with sharp words exchanged.",
        "direction": "dramatic"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Gong-ja smiles confidently despite the looming dark creature above him.",
        "direction": "dramatic"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "The red-haired man notes his growth with a confident smirk.",
        "direction": "neutral"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Gong-ja laughs, insisting he still plans to claim his rewards.",
        "direction": "humorous"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "A sharp turn of head reveals sudden tension in the air.",
        "direction": "tense"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "The older man warns him that he is keeping an eye.",
        "direction": "serious"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Gong-ja questions if he will be watched for the whole day.",
        "direction": "concerned"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "He swings his sword, demanding Gong-ja contribute to the fight.",
        "direction": "aggressive"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "The man boasts he plans to hunt monsters alongside them.",
        "direction": "confident"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Gong-ja sighs deeply, finding this situation truly troublesome indeed.",
        "direction": "frustrated"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Someone is restrained as others shout about guarding their guild leader.",
        "direction": "chaotic"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "The woman reacts with surprise to the names Hunter Kim and Saint.",
        "direction": "surprised"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "The Black Dragon leader commands guilds and offers a reward for clearing.",
        "direction": "authoritative"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Gong-ja explains the mini-map reward shows all allies and enemies.",
        "direction": "explanatory"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "She asks if he is serious, and he confirms he tells truth.",
        "direction": "tense"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Flame Emperor grabs Gong-ja, demanding the location of the boss monster.",
        "direction": "urgent"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "She grabs his sleeve urgently, asking consent for her skill amidst the monster chaos.",
        "direction": "urgent"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "He consents quickly, knowing she reveals her true nature when things get hectic.",
        "direction": "narrative"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "With a shout, she teleports him upward, away from the snarling creatures below.",
        "direction": "action"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "He spins and points, shouting where the shadowy figure stands in the distance.",
        "direction": "action"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "They dash forward again, teleporting past the short green monster on the floor.",
        "direction": "action"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Supporting the falling man, he asks if he knows how to use his sword.",
        "direction": "dialogue"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "He claims enough skill to take down the bastard, then is told to go.",
        "direction": "action"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "A bright beam strikes through his body, causing chaotic green splatters to erupt outward.",
        "direction": "impact"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Monsters stand confused by black smoke columns while figures sit amidst the wreckage nearby.",
        "direction": "atmosphere"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Blood drips down his face as he taunts them, asking if they want to be cut.",
        "direction": "taunt"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Giant humanoid monsters run away into the distance while Gong-ja observes them from behind.",
        "direction": "observation"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Standing atop a high point, he commands hunters to not let a single one escape.",
        "direction": "command"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "A shouted command echoes out, demanding the goblin bastards stop right there immediately.",
        "direction": "command"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "He shouts yes loudly, clutching his jacket tightly with intense shock and realization.",
        "direction": "reaction"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "She praises Confucius, noting low casualties and that they will clear the stage quickly.",
        "direction": "praise"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "He wonders if her lack of expression meant she cared about hunter deaths.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Maybe she is happy only because fewer hunters died this time around.",
        "direction": "tense"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "He calms her excitement, praising her simple joy over the low casualties.",
        "direction": "light"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Casualties have never been this low since they started climbing the tower.",
        "direction": "informative"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "She beams with pride, her hands framing her face in genuine delight.",
        "direction": "happy"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Although you surely wanted to claim the reward for yourself entirely.",
        "direction": "reflective"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "He feels relief that our new hero turns out to be you.",
        "direction": "emotional"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Prepare yourself because tower media will focus entirely on you from now.",
        "direction": "warning"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Being praised feels great, but there is something more important than fame.",
        "direction": "contemplative"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "These hard-working people did not live to their fullest but they tried.",
        "direction": "somber"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Yet I can say they lived to the best of their abilities.",
        "direction": "proud"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Blade Saint, Witch, and countless hard-working people mean so much to him.",
        "direction": "emotional"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "He wants a life acknowledged by them, and he wants to protect them.",
        "direction": "hopeful"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "They shake hands as he vows to protect these people at all costs.",
        "direction": "sincere"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "He refuses to mock them like Flame Emperor did, wanting only to acknowledge their efforts.",
        "direction": "resolved"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "He demands respect from everyone, living loudly even if it sounds impossible to achieve.",
        "direction": "dramatic"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Watching this bastard change the world feels rewarding, just like his own transformation.",
        "direction": "reflective"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Gong-ja notices the rankings differ from last time, signaling priority entry for top challengers.",
        "direction": "internal"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "She smiles brightly, confident they will reach the twentieth floor without any further delays now.",
        "direction": "close-up"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "The Flame Emperor worries many innocents will die if they continue this dangerous path forward.",
        "direction": "serious"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Losing their connection to the outside world could cost hundreds of thousands of hunter lives.",
        "direction": "tense"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Gong-ja sits perfectly still as light and water streaks fall silently around his body.",
        "direction": "calm"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "That is exactly why he speaks up to address the gathering with sudden conviction.",
        "direction": "focused"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "Three new arrivals freeze in shock, realizing they have been unexpectedly transported to this place.",
        "direction": "shock"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "A blonde woman shouts praise for Hunter Kim, amazed by his recent incredible performance here.",
        "direction": "excited"
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "He asks if she found the boss location, but she tells him to wait right now.",
        "direction": "conversation"
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Gong-ja lowers his head slightly to announce he has a vital message for everyone present.",
        "direction": "announcement"
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "The woman and older man stand silently, their expressions shifting as they await his next words.",
        "direction": "anticipation"
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Relieved the Blade Saint holds back, he grins confidently, asking if they recall his words.",
        "direction": "confident"
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "The blonde man confirms they remember he promised to ask a favor soon in the future.",
        "direction": "cooperative"
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "He asks the purple haired leader what favor he seeks from her right at this moment.",
        "direction": "tense"
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "He gestures for the leaders to stay put for the next five days without moving.",
        "direction": "commanding"
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "He vows to clear up to the twentieth floor within the next five days time.",
        "direction": "dramatic"
    }
]


def build_and_save() -> bool:
    ch_id = "ch32"
    ch_dir = Path(f"data/chapters/sss-class-revival-hunter/{ch_id}")
    desc_path = ch_dir / "03_descriptions.json"
    script_path = ch_dir / "04_script.json"

    if not desc_path.exists():
        raise FileNotFoundError(f"Missing descriptions at {desc_path}")

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
        chapter_id=f"sss-class-revival-hunter/{ch_id}",
        title=f"SSS-Class Revival Hunter - Chapter 32",
        series="sss-class-revival-hunter",
        created_at=datetime.now(timezone.utc).isoformat(),
        model="mercury-2.5",
        target_words=len(script_blocks) * 12,
        blocks=script_blocks,
    )

    cfg = load_config()
    report = validate(script_file, desc_file, cfg)

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_file.model_dump_json(indent=2))

    alt_script_path = Path(f"data/chapters/revival_hunter_{ch_id}/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 32 Script ===")
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
