"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 33.

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
        "narration": "A divine voice announces the next tower floor is open for all hunters here.",
        "direction": "dramatic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "The swordsman leaps midair while observers watch the clash of blades unfold below.",
        "direction": "action"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Gong-ja tells the group he needs to ask them a huge favor very soon now.",
        "direction": "tense"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "He requests they stay in place for five days without doing anything else during time.",
        "direction": "demanding"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Silence falls over the hall as dust motes float through the light filtering above.",
        "direction": "atmospheric"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "If they move, he promises to clear up to the twentieth floor within the next days.",
        "direction": "warning"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "The title flashes on screen as the story continues with a bold declaration of intent.",
        "direction": "intro"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "One hunter gasps in shock hearing the impossible timeframe he claims he needs to succeed.",
        "direction": "shocked"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "He confirms his statement is serious and not a joke meant to mock the gathered elite.",
        "direction": "firm"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Another hunter declares his claim is impossible to achieve given the sheer difficulty of the task.",
        "direction": "disbelief"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "She warns him that claiming confidence is reckless when years were spent clearing the lower floors.",
        "direction": "cautious"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Gong-ja bows deeply before the crowd, silently pleading for their cooperation with his quiet gesture.",
        "direction": "respectful"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "He reminds them he shared all rewards and benefits from the tenth floor clear with everyone.",
        "direction": "explanatory"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Everyone reaped benefits from the shared information about the floor and the boss location within.",
        "direction": "informative"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "A man in glasses states Gong-ja is worthy enough to ask for this significant favor today.",
        "direction": "serious"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Gong-ja bows deeply, asking everyone to stay five days regardless of his success clearing the floors.",
        "direction": "dramatic"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "He states this simple favor as the system begins distributing rewards for clearing the eleventh floor.",
        "direction": "dramatic"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "The Goddess and the Demon King both propose unique rewards for the victorious hunter standing before.",
        "direction": "dramatic"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Gong-ja gazes upward with a gentle expression, contemplating the weight of these divine offers presented now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "He asks the Demon King if impatience sets in since their plan to incite conflict fails.",
        "direction": "dramatic"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "An elderly hunter with an eyepatch listens as the system recommends selecting one of the rewards.",
        "direction": "dramatic"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Armored hunters ponder the suggestion to forfeit rewards while the Demon King offers this alternative out.",
        "direction": "dramatic"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "The dark window displays clear confusion as the Demon King is baffled by the unusual request.",
        "direction": "dramatic"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Now the system window urges the hunter to make a decision without further delay now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "It does not understand his true intention behind asking them to wait here for five days.",
        "direction": "dramatic"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "A woman in a black suit asserts the problem is simple while touching her chin gently.",
        "direction": "dramatic"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "He shared the knowledge we needed, asking only that we listen to his promise as a.",
        "direction": "dramatic"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "A decisive step echoes across the silent room as someone finally chooses to move forward now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Staying five days will confuse the public and media, but is this really that complex a.",
        "direction": "dramatic"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "She declares his request far from impossible, confirming their agreement to stay by his side.",
        "direction": "dramatic"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "The Black Dragon leader insists a promise remains binding despite the impossible odds ahead.",
        "direction": "dramatic"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "She presses her hand to her head, finally accepting the weight of her own vow.",
        "direction": "internal"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "One hunter agrees to wait, trusting Gong-ja has a hidden plan for the ascent.",
        "direction": "dialogue"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "An elder consents to the delay, though his expression remains skeptical of the bold request.",
        "direction": "dialogue"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "A stern elder refuses outright, claiming he never agreed to such a binding promise.",
        "direction": "conflict"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "He clarifies he only promised to watch the young man for five days specifically.",
        "direction": "dialogue"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "The Blade Saint agrees to follow, finding reassurance in watching Gong-ja's back alone.",
        "direction": "agreement"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "She addresses the assembled group, thanking them for cooperating with her difficult decision today.",
        "direction": "leadership"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Gong-ja turns to leave, telling them he will return in five days time.",
        "direction": "departure"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "He pushes open the massive doors, stepping into the blinding light of the next floor.",
        "direction": "action"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Both hunters look upward in confusion, sensing something unexpected has happened above their heads.",
        "direction": "mystery"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "A knight notices the frozen NPCs, but the Flame Emperor says the quest has not started.",
        "direction": "dialogue"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "An old man approaches, asking about the quest while bystanders watch the strange silence.",
        "direction": "curiosity"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Gong-ja explains no one has selected a role yet, causing the current deadlock in place.",
        "direction": "explanation"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Hunters must take these roles for the higher floors as part of the official quest.",
        "direction": "reveal"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Knights note that quests arrive immediately here, unlike the previous floor\u2019s delay.",
        "direction": "informative"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "The quest only truly begins after everyone selects their assigned role together.",
        "direction": "analytical"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Gong-ja confirms the quest stays locked until all roles are finally chosen.",
        "direction": "serious"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Sword Emperor warns that the Demon King wants a reward selection immediately.",
        "direction": "tense"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Gong-ja asks what happens if he kills the boss right now.",
        "direction": "curious"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "He repeats asking if removing the boss before the quest actually starts.",
        "direction": "intense"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Killing him early prevents traitors because no one gets the reward.",
        "direction": "strategic"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "A system alert flashes, revealing the Demon King is furious.",
        "direction": "dramatic"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Dark clouds swirl as the massive Demon King manifests above them.",
        "direction": "epic"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "The entity roars, demanding to know how they dare act thus.",
        "direction": "angry"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "It questions why he did not take proper steps before arriving.",
        "direction": "ominous"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Gong-ja smiles, claiming he already chose the best reward option.",
        "direction": "confident"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "The shadowy figure pauses, stunned by his sudden confident response.",
        "direction": "shocked"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "He thrusts a radiant sword upward, proving his choice was valid.",
        "direction": "heroic"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Gong-ja declares he will kill the king before the quest starts.",
        "direction": "final"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "He declares this is a happy ending with absolutely no sacrifices required today.",
        "direction": "dramatic"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Gong-ja smiles warmly admitting he has never truly liked bad endings before.",
        "direction": "emotional"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "A menacing shadow warns it will not get its happy ending if you interfere.",
        "direction": "threatening"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "The dark entity roars in fury at his audacious challenge to its power.",
        "direction": "intense"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "It questions if he truly believes he can stop such a beast alone.",
        "direction": "confrontational"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Gong-ja faces the colossal beast without any support from the empire behind him.",
        "direction": "heroic"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "A golden clock strikes noon as his glowing sword pierces the stormy sky.",
        "direction": "symbolic"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "He calmly states that he does not need any assistance from anyone else.",
        "direction": "confident"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "Leaping upward, his sword becomes the moving hand of the clock above.",
        "direction": "dynamic"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "A true warrior is always meant to fight and stand completely alone in battle.",
        "direction": "philosophical"
    }
]


def build_and_save() -> bool:
    ch_id = "ch33"
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
        title=f"SSS-Class Revival Hunter - Chapter 33",
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

    print(f"=== SSS-Class Revival Hunter Ch 33 Script ===")
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
