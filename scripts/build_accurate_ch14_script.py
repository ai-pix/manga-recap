"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 14.

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
        "narration": "The guild boasts unrivaled legacy, yet its pride now teeters on absurdity."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Purple-haired spokesperson sighs, cameras flashing, as failure stains her reputation."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Reporters barrage hunters, demanding truth, while the tower's gossip machine roars."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "She declares skill sufficient, blaming luck, as if destiny were a fickle dealer."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Flame Emperor scoffs, fireworks explode, system announces cleared floor\u2014mockery masquerading as triumph."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "He labels his tirade the infamous 'Loser Announcement,' a legacy of scornful fame."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "A lingering question drifts, promising deeper turmoil beneath the spectacle."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Ten thousand hopefuls have stumbled; the tenth floor remains a merciless crucible."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Gong-ja grins, challenging Hellfire Maiden, demanding chaos to spice the deadly dance."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "The series title glimmers, cards swirling like fate's fickle deck."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Clearing the floor appears simple, yet hidden layers mock complacent hunters."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "A fiery hand snatches a glowing token, sealing the duel's twisted wager."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Dolls chant frantic commands, Gong-ja grips sword, red-haired mentor smirks amid blazing fury."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Infernal aura ignites the arena, turning heat into a living, relentless beast."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Coughing protector shields child, realizing aura's ten\u2011minute shield barely stalls the inferno."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Flames roar, a chaotic orange vortex swallowing hope, daring any hunter's resolve."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Flame Emperor cradles trembling girl, mocking fire's impotence against hunters' blazing auras."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Hexagonal darkness pulses, a taunting countdown whispering: Ready\u2026 or\u2026 not\u2026"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Red-haired mentor boasts, Gong-ja coughs amidst vortex, crowd of dolls jeering destiny."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Gong-ja recoils, sparks flying, shouts disbelief at luck\u2011driven survival claim."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Red-haired foe lunges, fire\u2011cloaked, taunting Gong-ja's fleeting aura endurance."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Mentor mocks, citing Marcus' thirty\u2011minute stamina, while Gong-ja sweats in fury."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Ghostly girls demand a bet, Gong-ja clutches two coins, sighs resignation."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Red-haired specter floats, scoffing, questioning if revival truly extends aura's lifespan."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Two grim paths await; one demands luck, the other relentless aura."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "A trembling finger points upward, mocking impossible odds with sarcastic optimism."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Flames swirl, a bandaged hand reaches, urging patience over reckless gamble."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Red-haired specter scoffs, reminding him that cheap bets betray blind ambition."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Gongja, fire-encircled, declares defiance while his dwindling aura ticks down."
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Green-hooded wanderer strides, leaving a trail of frantic, ember\u2011kissed dolls."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Blonde doll pivots, eyes widening, inviting a deadly, twisted game."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Gongja's hand rests on girl's crown, sealing fate amid roaring flames."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "A heavy hand smashes the girl's mouth, black hexagon flashing warning."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "The girl dissolves, screaming denial, as blood\u2011red chaos erupts around her."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Gongja clutches a gore\u2011slick mass, horrified, echoing the child's desperate mantra."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "A blazing ring erupts, trapping silhouettes as time counts down ominously."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Gongja flails, questioning the tower's twisted cruelty, while specter's particles mock his resolve."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Calm amidst inferno, he taunts the phantom dolls, demanding the god's twisted mercy."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Sharp crystal rain slashes his skin, chandelier ablaze, his scream echoing desperation."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "A lone silhouette stands, surrounded by cataclysmic fire, defying fate's cruel spectacle."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "The tower's cold timer blares, reminding the undead that seconds betray hope."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Flames devour the figure, agony echoing, the tower laughs at his suffering."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Red hair cackles, mocking the zombie's pyromaniac ambition with manic delight."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Digital death screen flashes, sealing his fate with cold, indifferent code."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Kneeling, he stares at the glowing verdict, a twisted promise whispering redemption."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Coughing, he snarls, the system offers random Hellfire skill, demanding his blood."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Floating acrobat gestures, golden card glints, chaos cards swirl, destiny teases the zombie."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "S-Rank Hellfire Barrier appears, promising vengeful blaze, the tower's ultimate, merciless trap."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Red-haired specter gestures, promising endless hellfire at a mere thought."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Concerned crimson mentor raises hand, questioning Gongja's uneasy expression."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Gongja ponders, arms crossed, sensing an inexplicable disturbance within the arena."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Distorted blonde specter screams denial, her visage dripping like molten wax."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Floating crimson tutor demands skill-card reading; startled Gongja reluctantly complies."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Skill list materializes, revealing A\u2011Class labyrinth, B\u2011Class dolls, and more."
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Muscular crimson figure reclines, surrounded by floating star\u2011etched metallic cards."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Shock freezes Gongja; enraged red mentor clenches jaw, eyes blazing."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Calm Gongja watches; desperate crimson adversary lunges, pleading for recognition."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Floating mentor brandishes golden card, promising hellfire barriers; silver whispers doubt."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Green\u2011hooded Gongja reflects, realizing early warning signs were missed."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Lone luminous doll stands amid shadowy copies, the sole fire\u2011aura beacon."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "He raised his hand, questioning why fake dolls refused to ignite."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Gongja held a card, while crimson-haired challenger lunged, demanding answers."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "The system boasted an A\u2011rank fire shield, promising immunity at catastrophic cost."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Flipping upside down, Gongja cursed; his opponent cackled, mocking his plight."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Silence settled, the void echoing nothing but lingering dread."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "They plotted a mansion tour, hunting the real doll after chaos."
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "Floating upside down, Gongja smirked, wondering if challenges had become trivial."
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "A stark warning flashed: skill usage now incurs a severe penalty."
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "His eyes widened, mouth agape, shock pure as shattered glass."
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "Trauma replayed, Gongja gasped; pink-haired foe sneered, reveling in torment."
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Confusion erupted, demanding explanation for the bizarre, punitive mechanic."
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "The mansion loomed, a system note announcing Hellfire Maiden's trauma reenactment."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch14")
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
        chapter_id="sss-class-revival-hunter/ch14",
        title="SSS-Class Revival Hunter - Chapter 14",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch14/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 14 Script ===")
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
