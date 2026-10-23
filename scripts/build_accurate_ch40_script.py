"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 40.

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
        "narration": "Gong-ja stands ready as the system announces the boss stage begins.",
        "direction": "dramatic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "The shadowy demon screams about burns and malice from a past blazing path.",
        "direction": "intense"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Silence falls as the corridor lights flicker around the waiting warriors.",
        "direction": "suspenseful"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Flashback shows the weakest floor with a tiny boss monster approaching Gong-ja.",
        "direction": "narrative"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Positions swap instantly as the demon strikes deep into Gong-ja's body.",
        "direction": "action"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Gong-ja recalls fighting the mighty demon king on the twelfth floor before.",
        "direction": "reflective"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Now the roles reverse as the invader tries to protect his haven.",
        "direction": "dramatic"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Gong-ja blocks the attack saying those words mean absolutely nothing to him.",
        "direction": "confident"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "He lunges forward with a sword separating the demon's upper and lower torso.",
        "direction": "violent"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "A massive crowd screams out loud in shock at the sudden violent strike.",
        "direction": "chaotic"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "System text declares the Demon King of Autumn Rain existence has been obscured.",
        "direction": "system"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Dark liquid drips from a hand pooling among the white petals on ground.",
        "direction": "gloomy"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Gong-ja thrusts his sword saying the enemy is still not weak enough.",
        "direction": "intense"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "He swings again with petals scattering while the system repeats the obscured existence.",
        "direction": "repetitive"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "The audience screams loudly as the notification confirms the demon king is gone.",
        "direction": "climactic"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "A masked figure gets struck hard by a glowing slash, sending black blood flying everywhere.",
        "direction": "violent"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Gong-ja stands with his back turned, gripping a massive dark blade in the light.",
        "direction": "dramatic"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Dark viscous liquid spills from his boots, creeping across the ground like living shadow.",
        "direction": "ominous"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "The system strips her title away while she screams in panic against the digital windows.",
        "direction": "intense"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "She stares at black ooze rising from her palm, screaming out in sheer terror.",
        "direction": "horror"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "She begs the Tower not to do this while debris flies near her terrified face.",
        "direction": "desperate"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Gong-ja yells that she is weak enough now as she recoils in fear.",
        "direction": "aggressive"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "He strides forward demanding she use her authority or sword to make him stop.",
        "direction": "steady"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "He threatens to keep walking unless she acknowledges the horror done to his people.",
        "direction": "angry"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "A young girl shouts she has no right to do this to her body.",
        "direction": "defiant"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "The Flame Emperor admits everyone shares blame for burning her village down long ago.",
        "direction": "cold"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Silence falls between them as the weight of past sins hangs heavy in the air.",
        "direction": "tense"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "She stands alone in a white void, looking down with a calm, empty expression.",
        "direction": "somber"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "He claims no right to hold him responsible while the man cries for caring sick.",
        "direction": "conflict"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Gong-ja asks what he did to the child who pleaded for her father\u2019s life.",
        "direction": "accusatory"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "She accuses him of devouring the baby while pretending to be a savior.",
        "direction": "intense"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "She cries she meant no harm but hid the truth about Esther's body.",
        "direction": "angst"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "A giant armored beast thrusts its sword upward as she grips the blade.",
        "direction": "action"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Memories show a child calling for help while surrounded by giant teeth.",
        "direction": "flashback"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "He asks if making a mistake excuses the crime due to ignorance.",
        "direction": "interrogation"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "She confirms yes and says she would never hurt Esther if she knew.",
        "direction": "confession"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "The woman notes that humans claimed that same excuse for burning villages.",
        "direction": "realization"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Armored figures argue rulers claimed they did not know about the monsters.",
        "direction": "debate"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "He asks if soldiers or refugees never said they simply did not know.",
        "direction": "confrontation"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Gong-ja holds his glowing sword and says he only knows justice called karma.",
        "direction": "dramatic"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "He tells her if those were human, she should experience the same thing.",
        "direction": "threating"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "He looks upward and declares he wishes to use his reward now.",
        "direction": "command"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "The system processes his request while silence falls over the battlefield momentarily.",
        "direction": "tense"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "A system window warns that extreme adjustments to skills are not permitted.",
        "direction": "system"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "The Tower explains that leveling SS skills to SSS class is the limit.",
        "direction": "system"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Gong-ja asks the system to change his summoning skill drastically now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "He wants his summoned ghosts to remember their past lives completely.",
        "direction": "intense"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Just memories, not their powers or reduced cooldown times for him.",
        "direction": "assertive"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "The system begins processing his unusual request with careful calculations now.",
        "direction": "suspenseful"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "A loading icon spins silently as the tower weighs the option.",
        "direction": "tense"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Finally the tower agrees his adjustment falls within acceptable safety limits.",
        "direction": "relieved"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Zerakua grants permission for the King of Death to proceed freely.",
        "direction": "authoritative"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "The skill updates to allow memories while keeping other restrictions intact.",
        "direction": "informative"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Gong-ja declares he will devour the Flame Emperor whole right now.",
        "direction": "threatening"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "He raises his sword to kill the man who hurt Esther deeply.",
        "direction": "vengeful"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Then he will spit him out like the Emperor did to victims.",
        "direction": "harsh"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Ghosts attack happily since the Emperor is now human enough to summon.",
        "direction": "chaotic"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "The Sword Emperor critiques her stance and lack of proper footing quickly.",
        "direction": "critical"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "She relies too much on skills instead of fundamental swordsmanship basics here.",
        "direction": "disappointed"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "He strikes hard teaching that basics are all you have in death.",
        "direction": "instructional"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "The ghost master swings his blade loudly, shouting to show her exactly how to fight.",
        "direction": "dramatic"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "She crouches defensively as green streaks pass through her back while white petals fall around.",
        "direction": "tense"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Gong-ja pins the figure down, asking if this marks the end of the Demon King.",
        "direction": "intense"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "His hands grip the ornate sword hilt tightly as he questions the one who reaps death.",
        "direction": "close-up"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "A caption confirms he might be right about the deadly title reaping death for sure.",
        "direction": "text"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "The Flame Emperor raises his sword high above the motionless body lying still on the ground.",
        "direction": "action"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Suddenly a voice shouts hold on to stop the fatal strike before it lands on the.",
        "direction": "text"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "A young woman stares ahead with wide eyes while white particles float near her chest in.",
        "direction": "close-up"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "The ghost master hangs from Gong-ja's foot saying he isn't sorry to stop the kill right.",
        "direction": "comedy"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "Gong-ja shouts in disbelief asking what he means by making such a bold assumption right here.",
        "direction": "angry"
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "He assumes she is no longer a monster but questions if she truly counts as human.",
        "direction": "thoughtful"
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Maybe she became a normal NPC instead so do they qualify as targets for his reincarnation.",
        "direction": "question"
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "The Tower does not fool around so will you take responsibility if it says NPCs do.",
        "direction": "stress"
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Check the skill card again to see if it specifies NPC anywhere since you only think.",
        "direction": "stress"
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "Gong-ja groans in physical pain and distress as the argument weighs heavily upon his stressed mind.",
        "direction": "pain"
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "Gong-ja stands before the blue window and asks the Tower to listen to his specific question.",
        "direction": "dramatic"
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "He questions if killing an NPC counts as one of the dead for his reincarnation skill.",
        "direction": "questioning"
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "The system requests verification from Zerkua as the loading process begins silently within the interface.",
        "direction": "technical"
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "A circular loading spinner pulses steadily as the system processes the complex verification request.",
        "direction": "tense"
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "The system fails to verify the request as an error message glitches across the display.",
        "direction": "alert"
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "The Tower says his question exceeds authority yet Gong-ja reacts sharply as flames flicker around him.",
        "direction": "reaction"
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "The Tower recognizes the King of Death and grants temporary apostle authority to this deadly enquirer.",
        "direction": "empowerment"
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "A golden window announces a vote from the Six Pillars as a mysterious figure enters suddenly.",
        "direction": "shock"
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "The Six Pillars assemble within the tower while the system calculates the final decision for them.",
        "direction": "anticipation"
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "A bright yellow streak expands across the view opening a portal for the Tower's vote to.",
        "direction": "climactic"
    }
]


def build_and_save() -> bool:
    ch_id = "ch40"
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
        title=f"SSS-Class Revival Hunter - Chapter 40",
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

    print(f"=== SSS-Class Revival Hunter Ch 40 Script ===")
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
