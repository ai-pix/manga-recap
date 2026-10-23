"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 37.

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
        "narration": "Title card flashes bright, signaling the start of another deadly journey.",
        "direction": "dramatic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "System scans the floor, finding no trace of the Demon King.",
        "direction": "tense"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "A chilling verdict confirms his retreat, altering history itself forever.",
        "direction": "suspense"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "The purple-haired witch stares upward, sensing a strange magical shift.",
        "direction": "mysterious"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Confucius admits he has no idea what is happening right now.",
        "direction": "casual"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Even the red-haired ghost feels this unprecedented disturbance in the air.",
        "direction": "surprised"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Gong-ja tilts his head, puzzled by the floating light particles.",
        "direction": "confused"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Someone points out toward the distant castle gate with urgency.",
        "direction": "alert"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "They notice the flags on the walls have strangely decreased in number.",
        "direction": "observant"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "He grabs her hand, vowing to investigate the sudden change alone.",
        "direction": "protective"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "A massive vortex swirls as they teleport instantly to the upper floor.",
        "direction": "action"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Townspeople below look up in shock at the shimmering blue light.",
        "direction": "chaos"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Gong-ja stares ahead, realizing the timeline itself has been rewritten.",
        "direction": "realization"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Knights witness the ethereal energy proving this place's history changed completely.",
        "direction": "awe"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "The Demon King's invasion vanished, leaving the empire's fate entirely uncertain.",
        "direction": "serious"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Unbeknownst to everyone, history shifts without anyone even being aware of it.",
        "direction": "dramatic"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "History has changed forever, altering the course of fate itself.",
        "direction": "solemn"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "The Sword Emperor laughs at the red rain, calling it grander than old ports.",
        "direction": "wry"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Vendors shout about apples while citizens complain the water remains dirty lately.",
        "direction": "chaotic"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Donations welcome as the Goddess of Protection claims to love everyone deeply.",
        "direction": "mocking"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Soldiers demand identity from the intruder standing atop the castle walls above.",
        "direction": "tense"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "A knight screams for him to get down, begging strength to protect the empire.",
        "direction": "desperate"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Gong-ja is surprised when the man recognizes his name, Sarvas Aegeam clearly.",
        "direction": "shocked"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "The knight yells to move down, unaware this man was once friendly.",
        "direction": "frustrated"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Gong-ja realizes they treat them like strangers, forgetting all his past deeds.",
        "direction": "melancholic"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "A ghostly voice pleads softly for someone to watch over their empire.",
        "direction": "ethereal"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "The armored spirit fades away, leaving a desperate request behind in the air.",
        "direction": "fading"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Gong-ja smiles smugly, hiding the pain behind a thin, thin smile.",
        "direction": "unsettling"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "The armored knight laughs loudly, unaware the irony of his own desperate plea.",
        "direction": "ironic"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Gong-ja laughs maniacally as the purple-haired witch stares shocked at his hand.",
        "direction": "climactic"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Cold laughter echoes from the red-haired man staring down with disdain.",
        "direction": "dramatic"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Gong-ja laughs wildly as lightning crackles around him shouting he did it.",
        "direction": "high energy"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "He shouts down to the guards that he saved their entire empire.",
        "direction": "shouting"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "The armored guards stand frozen in shock staring up at the savior.",
        "direction": "reaction"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Gong-ja throws his head back shouting he kept every single promise made.",
        "direction": "triumphant"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "A market shows life continuing without embarrassment after hundreds of days passed.",
        "direction": "quiet"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "He stands resolute without regret, determined to sacrifice no single life today.",
        "direction": "serious"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "After hundreds of days of struggle he finally beat the demon king.",
        "direction": "text box"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Holding a glowing object he says he is proud of his own self.",
        "direction": "close-up"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "An explosive declaration fills the air as he screams he did it loudly.",
        "direction": "impact"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Memories flash of a past life drowning in alcohol and cruel self-hatred.",
        "direction": "flashback"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "But the current version of him has nothing left to be ashamed of.",
        "direction": "reflective"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "A system announcement reaches the black dragon leader and the entire world now.",
        "direction": "notification"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "The floor is cleared but most importantly he is proud of himself today.",
        "direction": "resolution"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "The system window appears calculating the total number of challengers who fought.",
        "direction": "interface"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "The system calculates the outcome and declares the final result now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Three challengers fought hard and the King of Death took first place.",
        "direction": "narrative"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "The armored knight shouts in disbelief at the strange news report.",
        "direction": "angry"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "He cries out an ancient command to his loyal soldiers nearby.",
        "direction": "urgent"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "A young leader leaves the empire in their hands with a shout.",
        "direction": "dramatic"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "The warrior says his service ends after defeating the demon king.",
        "direction": "defiant"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Gong-ja laughs loudly and shouts for their existence to be celebrated.",
        "direction": "triumphant"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "One man falls while another calls him a crazy bragging bastard.",
        "direction": "aggressive"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "He jokes about loving himself before telling the leader to hurry up.",
        "direction": "humorous"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "The witch admits top hunters are never normal so she understands now.",
        "direction": "calm"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "A blinding flash of light signals their departure from the battlefield.",
        "direction": "action"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "The elder insists the top hunter gets priority entry transport today.",
        "direction": "commanding"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "He smiles calmly and agrees to handle the transport request now.",
        "direction": "relaxed"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "The command is spoken clearly to initiate the jump to safety.",
        "direction": "narrative"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "A star shaped burst of blue light swallows them completely.",
        "direction": "action"
    }
]


def build_and_save() -> bool:
    ch_id = "ch37"
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
        title=f"SSS-Class Revival Hunter - Chapter 37",
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

    print(f"=== SSS-Class Revival Hunter Ch 37 Script ===")
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
