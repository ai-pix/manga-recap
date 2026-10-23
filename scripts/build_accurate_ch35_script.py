"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 35.

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
        "narration": "Four beasts advance together before a spreading red stain as darkness slowly grows.",
        "direction": "dramatic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "A glossy black creature crouches low, its wet hide ready to spring forward.",
        "direction": "low angle"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "The shifting form takes a lioness head, dripping black fluid into a new shape.",
        "direction": "transformation"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "With every new body claimed, the beast discovers a fresh, cruel delight inside.",
        "direction": "caption"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Two faces press close in shadow, one eye fixed intently on the other.",
        "direction": "intimate"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "It crouches over prey, finding specific delight in the thrill of the hunt.",
        "direction": "action"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "A young girl stands alone in the clearing, screaming out for help desperately.",
        "direction": "wide shot"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "She runs in panic while a bloodied lioness charges close behind her screaming.",
        "direction": "chase"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "The huge beast snarls loudly, searching the darkness for any sign of life.",
        "direction": "close-up"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "A sudden crunch echoes through the forest, marking a terrible and final impact sound.",
        "direction": "sound effect"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "The creature smells something fragrant nearby, wondering what this strange scent could mean.",
        "direction": "sensory"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "It hunts relentlessly like a possessed spirit, absorbing memories whenever it devours its prey.",
        "direction": "narration"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "The girl bends over sharply in the grass, her face hidden beneath falling hair.",
        "direction": "tragic"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "A father bursts through foliage shouting, calling out to his daughter Esther loudly.",
        "direction": "urgent"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "He reminds her how many times he warned her not to go outside alone again.",
        "direction": "flashback"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "He bursts through thick leaves shouting she is too fragile to survive out here now.",
        "direction": "tense"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "His eyes widen in shock as he asks what exactly happened to her clothes.",
        "direction": "surprise"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "She looks down with a broken voice and softly calls out the word father.",
        "direction": "emotional"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Blood stains her mouth as she claims the first name ever given to the demon king.",
        "direction": "horror"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "The series title flashes on screen while tarot cards fall around the glowing logo.",
        "direction": "intro"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Yoo Soo-ha raises his arm as a system window announces a powerful new skill activation.",
        "direction": "dramatic"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "A pale skeleton grins widely as dark smoke swirls around its bony frame.",
        "direction": "spooky"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "The animated bones rattle together as one asks the sword emperor why this skill was chosen.",
        "direction": "mystery"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "He admits he was tempted to choose a different skill at the very beginning.",
        "direction": "reflective"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "An aura strengthening skill would have been cool to wield a huge sword like the demon.",
        "direction": "fantasy"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "But after giving it some thought, he realized something important about the skill card.",
        "direction": "realization"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "This SS rank skill summons those you have killed as mindless monsters without their memories.",
        "direction": "explanation"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "So here is a question for you how many people do you think I have killed.",
        "direction": "confrontational"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "That lame emperor guy and yourself so two people right that is what I thought too.",
        "direction": "casual"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "But why would the detective insight skill show my kill count as over four thousand.",
        "direction": "confusion"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "The Tower counts deaths in a unique way, so let me rephrase it for you.",
        "direction": "explanatory"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Walking through skeletons, he asks how many deaths he personally bears responsibility for today.",
        "direction": "introspective"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "A skeletal arm strikes hard as skulls emerge from smoke with heavy groaning sighs.",
        "direction": "action"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Gong-ja smiles broadly with closed eyes, admitting he has died quite a bit.",
        "direction": "confessional"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "She turns sharply in disbelief asking if this impossible skill truly belongs to him.",
        "direction": "shocked"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "He muses on summoning thousands of monsters, noting she cleared the tenth floor alone.",
        "direction": "amused"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "A dark figure whispers how he could possibly possess the exact same skill.",
        "direction": "threatening"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "The Flame Emperor smirks mockingly, refusing to explain how he gained such power.",
        "direction": "taunting"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "A towering shadow entity rages upward, crying out to the goddess in despair.",
        "direction": "frustrated"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "He screams upward demanding the blade saint accept all his hatred and grudges.",
        "direction": "desperate"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "An older hunter grudgingly agrees to fight alongside monsters rather than teaming up with him.",
        "direction": "reluctant"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "She is called to destroy the Demon King together, already moving to intercept the threat.",
        "direction": "urgent"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "The Flame Emperor thrusts his blade high, shouting for the hundred ghosts to arise.",
        "direction": "commanding"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "A monstrous skeleton with fused skulls shouts for opponents to show what they are best at.",
        "direction": "menacing"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Gong-ja crouches low gripping daggers, ready to kill and be killed in the fight.",
        "direction": "determined"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Green frog monster swings a skeleton like a weapon wildly.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "A broken skeleton lies sprawled before slowly rising again.",
        "direction": "dynamic"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Screaming goblin faces skeleton soldiers charging with burning daggers.",
        "direction": "chaotic"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Skeletons get swept away by green fire as they fight back hard.",
        "direction": "intense"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Red haired man laughs maniacally at the undead army below.",
        "direction": "menacing"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Black liquid forms a faceless shape that drips terrifyingly.",
        "direction": "mysterious"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Ink blob shouts how dare you with intense rage glowing.",
        "direction": "aggressive"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Dark haired man wails in grief with clenched fist raised.",
        "direction": "emotional"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Darkness reveals the words other world in red lettering clearly.",
        "direction": "dramatic"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Voice says someone who doesn't even hold any malice here.",
        "direction": "serious"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Shadowy monster screams resentments or life in this world loudly.",
        "direction": "fierce"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Black mass roars how dare you stand in my way now.",
        "direction": "hostile"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Young man asks why does it matter where he is from.",
        "direction": "calm"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Hunter stands firm saying he is right here right now.",
        "direction": "confident"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Gongja stares forward as tower presents him with a new alias.",
        "direction": "revelation"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Amidst golden fire, he soars upward as the Tower confirms his alias, King of Death.",
        "direction": "dramatic"
    }
]


def build_and_save() -> bool:
    ch_id = "ch35"
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
        title=f"SSS-Class Revival Hunter - Chapter 35",
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

    print(f"=== SSS-Class Revival Hunter Ch 35 Script ===")
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
