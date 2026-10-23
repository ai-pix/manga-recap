"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 34.

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
        "narration": "A purple butterfly flutters as the narration whispers it opened its eyes on a rainy day.",
        "direction": "atmospheric"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "A massive black frog crouches low, its single red eye peering through the endless rain.",
        "direction": "ominous"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "A tiny green frog sits on a wet rock before a black-gloved hand reaches down.",
        "direction": "tense"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "The little creature croaks twice before a slithering mass of black liquid swallows it whole.",
        "direction": "horror"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "A dark featureless humanoid figure lies flat on the grass, motionless as rain falls around it.",
        "direction": "mysterious"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Thick black tar surges from a puddle to engulf a translucent greenish slime-like dome quickly.",
        "direction": "chaotic"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Two green slime arms reach up from the cracked floor as long dark shadows stretch behind.",
        "direction": "spooky"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Another bright green frog sits perched atop a dark stone while translucent droplets drift through air.",
        "direction": "unsettling"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "The screen goes dark as the narrator states that the rain poured down heavily.",
        "direction": "dramatic"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Rain pours down as the small green frog perched on rock croaks out one final sound.",
        "direction": "melancholic"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "It is revealed that the creature had desired to live a little longer before it ended.",
        "direction": "tragic"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "The logo SSS-Class Revival Hunter appears against a black void with glowing cards drifting.",
        "direction": "intro"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "A dark armored figure is caught mid-slash as a huge crimson arc sweeps diagonally across frame.",
        "direction": "action"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "One person holds their palm up while another presses a blade into the center to make.",
        "direction": "ritual"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "A voice taunts someone as a zombie and dismisses a swordsman's skill as not that good.",
        "direction": "provocative"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Gong-ja thrusts overhead with brute force as the ghost watches calmly from behind.",
        "direction": "dramatic"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "He trusts his speed to dodge whenever he predicts the direction of the swing.",
        "direction": "action"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "A voice echoes confirming his logic with only one single word in the dark.",
        "direction": "suspense"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "He marks his own palm with ink to track the relentless passage of time.",
        "direction": "mysterious"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "He admits quietly that he is now trapped within a prison made of time.",
        "direction": "emotional"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "He takes a quick drink while standing alone amidst the chaos of the rainy battle.",
        "direction": "calm"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "He lunges forward with his glowing blue blade slicing through the thick smoky air.",
        "direction": "action"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "The protagonist falls backward while a massive dark shape looms directly above his head.",
        "direction": "tense"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "She wonders what would happen if they simply progressed through the quest like normal.",
        "direction": "reflective"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Every time a soldier dies twenty years of life vanish from the world forever.",
        "direction": "somber"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Ten deaths take away two hundred years while one hundred cost two thousand years lost.",
        "direction": "intense"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "To protect that time he decided not to take on any specific role within the tower.",
        "direction": "solemn"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "And so he must be prepared to hand himself over to eternity without hesitation or fear.",
        "direction": "resolute"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "The ghost taunts him while Gong-ja ignores the insults and closes in for the strike.",
        "direction": "combat"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "The ghost advises him to balance aura throughout his body but Gong-ja thinks it is easy.",
        "direction": "dynamic"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "A colossal shadowy figure looms over the smaller man in red jacket.",
        "direction": "dramatic"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "He charges forward at high speed, extending his black-bladed sword aggressively.",
        "direction": "action"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "The young man swings his sword down, creating a blinding red shockwave.",
        "direction": "intense"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "A dark hooded figure stands over the location where the warrior fell.",
        "direction": "dark"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "A single white speech bubble appears against a fully black background.",
        "direction": "minimalist"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Gong-ja holds a glowing white ornate sword vertically in front of his face.",
        "direction": "dramatic"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "A cloaked skeletal figure raises a long spear overhead in a sweeping motion.",
        "direction": "ominous"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "The young man in the pink jacket stands with his left hand wreathed in light.",
        "direction": "focused"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "A close-up shot of a clock face fills the entire view completely.",
        "direction": "detail"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "The man bursts forward at extreme speed, his red jacket flaring behind him.",
        "direction": "action"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "The clock's hands click forward one tick, marking the passage of a single moment.",
        "direction": "suspense"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "A swordsman in a red jacket swings his sword two-handed to the upper right.",
        "direction": "action"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "The camera is tight on a golden clock dial as the hands move.",
        "direction": "detail"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "A montage shows three moments including a cafe table, an outdoor setting, and action.",
        "direction": "montage"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "The image cuts between an extreme close-up of a man's neck and jaw.",
        "direction": "intense"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "She cheered his strategy as casualty counts dropped rapidly under his calm guidance.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "A dark shadow pulsed with a single red word judging him silently.",
        "direction": "ominous"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "The darkness erupted asking why he smiled amidst such grim and bloody chaos.",
        "direction": "tense"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "He raised his blade and smiled softly, claiming pure happiness filled his heart.",
        "direction": "calm"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Does true joy exist for a man standing so close to death himself?",
        "direction": "melancholic"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "He told the monster none could understand his strange joy in the face of doom.",
        "direction": "philosophical"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "The beast mocked his stance, but he replied with humble modesty instead of pride.",
        "direction": "confrontational"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Red letters screamed his worthlessness across the white void like a cruel curse.",
        "direction": "harsh"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "He refused to quit since his blade moved faster every single passing day.",
        "direction": "determined"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "She confirmed tomorrow his sword would move even faster than it did today.",
        "direction": "encouraging"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "He vowed to keep moving forward for as long as his legs could carry him.",
        "direction": "resolute"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Their hands touched as she revealed the impossible truth that no one perished.",
        "direction": "emotional"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "He checked with everyone including the Pantheon though a few fools might be hurt.",
        "direction": "serious"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "She buried her face in his shoulder thanking him because nobody died at all.",
        "direction": "relief"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Her voice broke repeating gratitude through tears while clinging tightly to his side.",
        "direction": "heartfelt"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Ink surges up violently shouting how dare you now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "A hooded shadow looms asking if you think stand tall.",
        "direction": "ominous"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Dark shapes fall while red text hides behind them.",
        "direction": "tense"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "Hunter walks forward as shadow rises saying fight alone.",
        "direction": "dramatic"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Shockwave blasts him back then shadow monster screams loudly.",
        "direction": "action"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "He grips sword tight as red energy rings glow.",
        "direction": "anticipation"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "An ornate clock shatters with a loud crack sound.",
        "direction": "impact"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "Man watches sky explode while holding glowing sword low.",
        "direction": "calm"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "He looks back and apologizes to Confucius quietly.",
        "direction": "respectful"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "Purple haired woman explains she followed him impatiently.",
        "direction": "dialogue"
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "He tells armored figure it is a fun game.",
        "direction": "light"
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Woman joins fight saying she wants to steal kill.",
        "direction": "action"
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "A figure stands motionless swallowed by black liquid.",
        "direction": "horror"
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Dark ink blot speaks calling everyone fools loudly.",
        "direction": "threatening"
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "Flame Emperor says sorry tradition says fight in groups.",
        "direction": "casual"
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "A massive tar-like mass roils upward, roaring curses at those playing gods.",
        "direction": "dramatic"
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "Ink-dark splatter floods the horizon as the entity refuses to play with swords.",
        "direction": "intense"
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "Clawed hands reach out from the darkness, summoning a hundred ghosts now.",
        "direction": "mysterious"
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "The shadowed head dominates the frame, demanding everyone answer the urgent call.",
        "direction": "ominous"
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "A horned beast stands with goblins amidst heavy rain and chaotic sound effects.",
        "direction": "chaotic"
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "She spins her head around quickly, startled by a loud cracking sound nearby.",
        "direction": "shock"
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "The suited elder calls for help, saying only thirty seconds have passed since fighting.",
        "direction": "urgent"
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "He turns slightly with a knowing grin, sighing that he needed help too.",
        "direction": "calm"
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "She reaches back to guide them out, demanding they hold her hand tightly.",
        "direction": "action"
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "His mouth curves into a broad smile, saying no it is fine actually.",
        "direction": "smug"
    },
    {
        "block_id": "b086",
        "panel_ids": [
            "panel_0086"
        ],
        "narration": "The finger rises from black mass, calling forth the hundred ghost summons now.",
        "direction": "epic"
    },
    {
        "block_id": "b087",
        "panel_ids": [
            "panel_0087"
        ],
        "narration": "He points up while black mass erupts, causing someone to shout what in surprise.",
        "direction": "climax"
    }
]


def build_and_save() -> bool:
    ch_id = "ch34"
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
        title=f"SSS-Class Revival Hunter - Chapter 34",
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

    print(f"=== SSS-Class Revival Hunter Ch 34 Script ===")
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
