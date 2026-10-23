"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 13.

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
        "narration": "Crowned goblin ponders existence, mutters 'GRUCK' like a philosophical protest."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "A bold, gradient 'G' hovers, promising grandiose quests ahead."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Gongja confronts the towering king, destiny hanging between throne and ruin."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Red eyes flare, pink currents swirl, system whispers activation of forbidden power."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "A glowing yellow alert teases unknown potential, name withheld for dramatic effect."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "He rockets backward, chaos erupts, skill labeled 'High Goblin Society'\u2014ranked futile."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Gongja's crimson blade shatters king's pride, green blood painting betrayal's canvas."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "He bows, whispers farewell, then scoffs at the absurdity of honor."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Red-haired specter rolls eyes, dismissing Gongja's triumph as petty bragging."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Knife poised, he mocks pixel hero, reminding everyone: six coins cost lives."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Red phantom grips him, demanding truth while Gongja clutches glowing evidence."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "He flaunts new skill, citing goblin etiquette, while ghost smirks at inevitable chaos."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Red-haired ghost scoffs, equating goblin cruelty with human folly."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Gongja's hand erupts blinding light, bewildered by sudden spark."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "He flicks fingers, thin energy blades sprout, claiming idle chatter."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "A blue notification flashes, announcing hidden hunter layer revealed."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Staring sternly, the ghost's presence rattles Gongja's already fragile confidence."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Crimson vortex engulfs him, heralding the ascent of Hunter Confucius Kim."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Blue alerts pop, confirming fresh skill slot and newly earned E\u2011class status."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Rain-soaked Gongja watches floating blue window, whispering luck's fickle promise."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "He ponders ambiguous aura, questioning whether rank-up effect resembles flame or blood."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "A hand\u2011rendered oval declares cryptic hint, teasing future revelations."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Gongja glances right, eyebrows raised, startled by the hinted mystery."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Flame Emperor brandishes trident aura, explaining rank\u2011up effects dictate personal aura forms."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Flame Emperor flaunts his fire, while Gong\u2011ja watches, unamused and wary."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Red\u2011haired specter lectures trauma\u2011shaped hunter forms, hinting at hidden, ordinary triggers."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "He points accusingly; Gong\u2011ja replies with open palm, questioning fire or blood."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "A silver crescent hovers, whispering destiny\u2019s shape: the moon\u2019s quiet silhouette."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "White\u2011haired wanderer stands at water\u2019s edge, petals drifting like fleeting hopes."
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Grey\u2011suited sage recounts Grandpa Marcus\u2019s mountain misadventure, warning about stubborn pride."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Silver\u2011haired dreamer gazes upward, yearning for moonlight\u2019s distant, comforting promise."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "He muses: moons borrow sunlight, just as we borrow fate\u2019s reluctant illumination."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Red\u2011haired mentor reveals twelve\u2011year oath, declaring Blade Saint\u2019s abnormal destiny."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "He jubilantly claps, urging onward ascent after conquering the fifth floor."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Gong\u2011ja proposes shortcut, pleading to bypass trials and face the tenth boss directly."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "A stunned gasp echoes, demanding explanation for the abrupt, baffling query."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Red-haired specter scoffs, Gong-ja points, demanding humility over fleeting triumph."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "He rages, recalling countless hunters wasted years chasing elusive tenth floor."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Gong-ja offers a wager, V\u2011sign confidence, promising to call him master."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Ghost questions two-coin logic, mocking six\u2011coin sacrifice, then whispers a condition."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Brown\u2011haired challenger demands full boss skill list; red phantom smirks, conceding."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Bet proposed: defeat earns 'Sir Confucius' title, opponent scoffs, dismisses."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Specter spits disdain, labeling challenger a dipshit daring to mock sword emperor."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Gong-ja accepts, declares immortality, yet ghost threatens eternal servitude under title."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Grins clash, explosive energy crackles between foreheads, echoing impending showdown."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Gong-ja doubles over, laughing maniacally, while companions watch bewildered."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Narrator mutters, 'That guy's crazy,' as absurdity reaches comic peak."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Series logo glimmers, golden cards swirl, promising next epic hunter saga."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "A stern sentinel blocks the entrance, his spear a stubborn question."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Gongja's eyebrows rise as the crimson-haired mentor sighs politely."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "The armored veteran warns, solo hunts on this floor equate self\u2011destruction."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Gongja cites law, reminding everyone that elite guild failed ten\u2011floor raid."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Record\u2011keeper insists his ledger watches every hunter, his tone bureaucratic."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Red hair erupts angrily, Gongja remains stone\u2011cold, muttering 'ugh, what?'"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "A bright sunburst questions destiny, hovering over Gongja's indecision."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Gongja's gloom lifts briefly as he shakes the officer's weary hand."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "He confesses dark desire, his eyes betraying a weary soul."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "One scoffs, the other stares, both bewildered by the absurdity."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "He mourns lost love, grappling with a grim, ticking diagnosis."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Terminally ill, he vows one final hunt, defying fate's cruel decree."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Silver-armored sentinel gasps, empathy flickering as tragedy's weight hits him."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Green-hooded man offers red pouch, pleading desperation over saved treatment funds."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "Gongja begs, promising disappearance, pleading anonymity from the recording officer."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Armored hunter declares final wish, feigning ignorance of any intruder's arrival."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Red-haired specter scoffs, questioning theatrical spectacle, mocking their melodramatic performance."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Knight plummets, crew watches, muttering absurdity of floor\u2011count priorities."
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "Two figures stare upward, mansion looming, the tenth floor whispering destiny."
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "Pink\u2011haired monk sits, Gongja watches, recalling Flame Emperor's doomed assignment."
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "CHAK echoes as pink-haired fighter confronts hoodie\u2011clad rival, tension crackling."
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "Gongja lifted, arms outstretched, doorway blazes, silhouettes hinting unseen watchers."
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Blonde and black\u2011dressed girls stand, surrounded by red\u2011eyed shadows, giggling ominously."
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "Creepy dolls grin side\u2011by\u2011side, laughter bubbles, echoing unsettling childhood nightmares."
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Flaming specter kids taunt Gong-ja, announcing Boss Stage, twisted hide\u2011and\u2011seek."
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "Blue hologram glows, granting cryptic blessing: May luck be on your side."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch13")
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
        chapter_id="sss-class-revival-hunter/ch13",
        title="SSS-Class Revival Hunter - Chapter 13",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch13/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 13 Script ===")
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
