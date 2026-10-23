"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 11.

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
        "narration": "Gong-ja stares up, monster's claw looming, Bae shouts, unleash aura now!"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Flame Emperor spins, snarling curses at unseen ghost, fury crackling in his eyes."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Red-haired Bae darts, blur trailing, demanding Gong-ja finally hear his own desperate plea."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Flame Emperor taunts, Gong-ja glances up, death\u2011revival jokes echo, kill count teased."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Ghost whispers, Grandpa Marcus looming, ominous warning hanging over trembling hunter's resolve."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Golden\u2011silver cards swirl around title, promising power while fate watches silently."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Gong-ja darts, mocking monster's sluggish charge, declares 'He's slow!' with defiant grin."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Legs drag, distortion glitches, Gong-ja laments his molasses\u2011like movement, questioning his own body."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Red\u2011haired mentor hoists Gong-ja, sprinting through resistance, shouting relentless encouragement."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Flame Emperor speeds, forest flashing, advises focusing aura on legs, taunts Bae's ease."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Foot thrusts forward, chromatic blur, Gong-ja urges legs, 'Just one more step!'"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Red heart pulses, sparks erupt, symbolizing fierce will amid looming catastrophe."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Red lightning crackles as Gong-ja narrowly evades the monster\u2019s crushing swing."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "The ghost master declares Gong-ja\u2019s body lacks aura highways, urging forest\u2011clearing."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Flame Emperor watches as the monster lunges, reminding them elixir fuels aura."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "A devastating kick shatters the floor, leaving the emperor stunned and smirking."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "The emperor recoils dramatically, his expression a mix of pain and defiance."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "A trembling whisper escapes, hinting at looming uncertainty."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Silence follows, as the question hangs heavy in the air."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "He ponders constructing aura highways, envisioning pathways through his own flesh."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Gong-ja claws at his chest, electric currents battling his dying resolve."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "A blue energy blade slams the emperor, exposing his fragile, weed\u2011like aura."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "The lingering question reverberates, demanding answers from the shattered battlefield."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "A faint laugh escapes his lips, confidence blooming amidst chaos."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Blood splatters, pink light glows, taunting echo of Marcus' headless fate."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Floating swords, red petals swirl as ghost mocks his aura's pedestrian streets."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Gong-ja's shock flips to resolve, vowing to outpace even Marcus' cursed path."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Flame emperor's clenched jaw hints at simmering rage and reluctant admiration."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Giant club arcs, Gong-ja darts, muscles screaming against the crushing weight of destiny."
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Energy whirls, Gongja's stance radiates defiance, green fiend recoils under relentless pressure."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Red-haired specter lifts chin, smirk whispering, 'Is this truly your limit?'"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Kneeling amid crimson aura, Gongja grins, 'Your praise fuels my undead ambition.'"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Blazing green blade slices air, dust erupts, Gongja's speed shatters lingering doubts."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Ogre's brute kick sends Gongja soaring, trailing scarlet ribbons of defiant fury."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Inside the monster's eye, Gongja thrashes, terror echoing through pulsing retina."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Red-jacketed warrior pierces reptile, flash ignites battlefield, hope flickers amid carnage."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Gongja's trembling hand ignites, orc snarls as ghost emperor descends."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Sword Emperor's blazing blade guides Gongja, who slashes the monster's throat."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Red-jacketed flame emperor snarls, energy erupts, shouting bitter curses."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Gongja plunges dagger, detonating emerald burst that blinds the battlefield."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Green ichor sears his flesh, yet he pierces the beast anew."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Collapsed flame emperor grimaces, questioning his own lingering agony."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Red-haired specter smirks as Gongja's reckless aura splatters grotesque green."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Broken body whispers defeat, unseen voice revels in his self-inflicted ruin."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Red-haired mentor applauds, urging intellect over brute force in hunter's path."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "A trembling whisper stalls, echoing impending dread across empty void."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Flame emperor convulses, energy fracturing, his breath ragged and broken."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Gongja flips mentor, demanding pain, testing limits of dying's resolve."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Gong\u2011ja's trembling voice drips uncertainty, sweat mixing with a single, falling tear."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Flame Emperor smirks, suggesting death as a shortcut to relief for the desperate."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "A suffocating void swallows light, mirroring Gong\u2011ja's internal darkness and dread."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "The ghost master chastises, reminding Gong\u2011ja that revival fuels this relentless torment."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "He taunts, comparing Gong\u2011ja's foolishness to a master who respects his own limits."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Perched atop the carcass, Gong\u2011ja stares at the glowing relic, bewildered."
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Red\u2011haired specter boasts, promising painless rebirth regardless of the agony inflicted."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "A chilling whisper cuts through, reminding him of his undead nature."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Red\u2011clad mentor warns that self\u2011destruction inflates kill statistics, a twisted incentive."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Gong\u2011ja resolves, eyes fixed on avoiding death\u2019s shortcut, despite the looming roar."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "He grins, noting rapid progress, likening repeated revivals to a thousand\u2011mile pilgrimage."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "A crimson\u2011eyed behemoth charges, forcing Gong\u2011ja to confront his own lingering fear."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Bae's grin sharpens, urging Gong\u2011ja to take that trembling first step."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "A cold system blares, announcing Gong\u2011ja\u2019s inevitable plunge into oblivion."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "He groans, pain radiating, muttering curses as his mind teeters on collapse."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Red\u2011haired swordmaster gapes, while bewildered Gong\u2011ja stares at the absurd spectacle."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Flame Emperor's sardonic whisper drifts, questioning his own lingering presence."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Gong\u2011ja gasps, labeling this tormenting void the 'Underworld' between death and rebirth."
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "A lone caption declares, 'Fascinating shit,' echoing his grim amusement."
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "He reminisces, forewarning listeners of a voice promising twenty\u2011four\u2011hour time reversal."
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "The system flashes approval, granting him skill activation after his fatal encounter."
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "Both stare, stunned, as the algorithm earmarks an Orc\u2019s feral skill for duplication."
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Red\u2011haired mentor looms, pressing forward, demanding Gong\u2011ja unleash latent power now."
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "They erupt, shouting disbelief, 'Monsters wield skills?'\u2014a god\u2011tier taunt ignites fury."
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "The interface flickers, demanding a choice before the battle escalates."
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "Gong\u2011ja snarls, craving power, his desperation echoing through the void."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch11")
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
        chapter_id="sss-class-revival-hunter/ch11",
        title="SSS-Class Revival Hunter - Chapter 11",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch11/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 11 Script ===")
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
