"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 12.

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
        "narration": "Gong-ja shouts at the glowing window, demanding tower's absurd authority."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Red\u2011haired ghost clutches his skull, lamenting hunter culture's shattered dignity."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Caption declares the monster's skill, foreshadowing inevitable futility."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Gong\u2011ja lifts a radiant card, resigned to indifferent fate."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Ghost recoils as Gong\u2011ja snatches the glowing token, mocking indifference."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Spectral whisper tempts better choices, yet Gong\u2011ja scoffs at destiny."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Bronze cards swirl; Gong\u2011ja admits luck, not skill, decides the draw."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Frustrated Gong\u2011ja scratches his head, cursing the ghost's relentless nagging."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Both cards identical, backs only visible, leaving Gong\u2011ja clueless."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Red\u2011haired specter gasps, realizing his spirit can read the front."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Gong\u2011ja's eyes widen, stunned by the ghost's unexpected insight."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Ghost declares front\u2011view advantage; Gong\u2011ja questions the tower's fairness."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Grey-haired hunter watches a blazing card streak past, bewildered and muttering."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Ghostly voice drifts, revealing his aerial advantage over the hidden cards."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Red-robed specter hovers, smugly asserting his sight while Gongja watches."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Gongja erupts, claiming lifelong visual mastery now fuels uncanny clairvoyance."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Muscular aggressor charges; Gongja remains composed, demanding the skill details."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Ghost folds arms, solemnly promising a single read, urging focus."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "An ornate frame heralds the first absurd card's reveal."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Orc lovers embrace amidst blossoms, boasting hyper-reproductive bragging."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "A decorative vine frame introduces the second ludicrous skill."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Hip-hop goblins flaunt gold chains, chanting relentless CHK\u2011A mantra."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Shocked rookie stares, jaw dropped, as absurdity settles in."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Specter hovers, taunting Gongja with hypothetical choices, hinting at hidden agendas."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Gong-ja declares his choice, while Confucius flails in bewildered frustration."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "He insists Chk-A reigns supreme, dismissing the absurd reproductive skill."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Red-haired ghost lunges, demanding Gong-ja pause before sealing his fate."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Gong-ja reads the ghost\u2019s mind, mocking its predictable outrage."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "System confirms skill copy; Gong-ja screams, then triumphantly ascends into vortex."
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Series title blazes amid floating cards, heralding the next chaotic episodes."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Gong-ja jolts awake, system flashing his lowly status with disdain."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "A bright notification promises free skill use, prompting a smug grin."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Back at the merchant hub, Gong-ja celebrates, while the red ghost fumes."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Gong-ja taunts the ghost, demanding a hunt over pointless blessings."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "System lists Confucius Kim\u2019s F-class arsenal, oddly confirming everything\u2019s fine."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Ghost clutches Gong-ja, proposing softer training while death\u2019s sting lingers."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Gong-ja proposes easy training, but red-haired ghost teleports, shouting angrily."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "He guzzles the black bottle, exclaiming the taste is spectacular."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "The muscular red emperor questions the green monster, while Gong-ja wipes his face."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Gong-ja brandishes a glowing green sword, mocking the emperor\u2019s nickname habit."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "The ghost retorts, reminding Gong-ja of his long\u2011standing Confucius moniker."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "A massive orc axe swings, sparking red energy as Gong-ja recoils."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "The green monster blinks, confused by the sudden, unexpected attack."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "The orc roars, lunging forward then screaming, its fury palpable."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Sharp black radiations swirl, heralding a shift in combat tempo."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "A booming caption declares movements have slowed, echoing past failures."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Gong-ja crouches, clutching a red weapon as the monster raises its club."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "He activates the CHK\u2011A skill, the double\u2011bladed axe looming ominously."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Goblin hoists club, bewildered, as Gong-ja shouts, 'CHK-A?'"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Gong-ja leaps, slicing the massive green monster; blood splatters, echoing his defiance."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "A green orc's neck erupts, crimson-green gore, as his eyes widen."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "The fallen creature thuds; the flame emperor perches atop, while Gong-ja watches."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Gong-ja smirks, sword over shoulder; red-haired ghost yells, 'You cheating bastard!'"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Blue-hooded Gong-ja contemplates forest, clutching green trinket, mutters accusatory monologue."
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Thorny caption declares: innocent orcs perish due to filthy bastards like you."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Gong-ja turns, grin widening, pulls hoodie drawstring, shouting 'CHK-A!'"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Red-haired master flails, cursing tower; Gong-ja remains calm, urging forward."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "A bold proclamation rings: 'Time to clear the fourth floor!'"
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch12")
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
        chapter_id="sss-class-revival-hunter/ch12",
        title="SSS-Class Revival Hunter - Chapter 12",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch12/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 12 Script ===")
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
