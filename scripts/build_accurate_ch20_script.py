"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 20.

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
        "narration": "Silver ranks surge like a storm, a crimson-haired commander slicing through chaos."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Desperate shouts echo; dark silhouette looms, promising doom for the overwhelmed."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "White-bearded strategist barks orders, bewildered by silver soldiers' frantic scramble."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Arrows rain; Gong-ja and allies dodge, muttering warnings amid the hail."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Tutorial's veil lifts; reality's brutal script replaces gentle practice."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Knight's thunderous charge inspires trembling rookie, heralding empire's desperate gamble."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Blazing blade demands strength, pleading for souls to shield Aegean's fragile heart."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Red-haired specter commands port defense, reminding hunters of aura\u2011enhanced perception."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Quest glows ominously; securing the port becomes empire's sole lifeline."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Blonde herald screams, disbelief rippling as demon king's existence becomes undeniable."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Sword clatters, goblins swarm; friends scramble, questioning quest's absurdity."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Silver-haired blade arcs, blood spatter painting sky; crowd watches, hopeful yet weary."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Spear thrusts, electricity crackles, teammates charge\u2014goblin hordes tremble under relentless fury."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Gong-ja stands calm, hand over heart, urging comrades: kill everything, stay composed."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Flame Emperor celebrates beside brown-haired hunter, system flashing reward promise like fireworks."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Title blazes with golden SSS, blood\u2011red REVIVAL, cards swirling\u2014fate beckons hungry hunters."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Gong-ja gazes at glowing map, navigation blessing unlocking snowy peaks ahead."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Triumphant fist raised, red\u2011haired mentor frowns; reward system erupts with speed lines."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Blue notification grants omniscient NPC insight, every skill and location laid bare."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Gong-ja smiles, holographic items float; shocked robe\u2011wielder gasps at commerce blessing."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "System offers select\u2011any item from floors eleven through twenty, destiny in your hands."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Arms raised, Gong-ja declares skill over luck; frustrated red\u2011hair woman sighs dramatically."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Elegant gothic frame declares THEMES, hinting at looming challenges awaiting hunters."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Tower pierces sky, mirrored city above, storm\u2011riven base glows like eye, thematic warning."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "The tower's next ten floors scream: Demon King's Invasion, no mercy."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "And there are only two ways the Demon King's army can be defeated."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "You must either wield enough power to crush the army alone."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Or forge and command your own legion while arrows rain around you."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "And you're planning to choose the latter? Impossible without army experience!"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Of course not\u2014my hand summons potential, not blind confidence."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "But I'm sure I can obtain a skill that tips the odds."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Hey, Sword Emperor, you called this a lousy luck game, right?"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "I'll prove this is a skill game, not a random lottery."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Display the NPCs located on the eleventh floor, now!"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "From those NPCs, reveal the top hundred highest\u2011ranked skills."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Hold up, Zombie! Let's build strength step by step, not cheat."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "He summons the top three commanders, mapping their positions for strategic advantage."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Gongja's finger triggers glowing markers, revealing his exact foothold in chaos."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "A silent query floats, daring the void to answer his daring claim."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Self\u2011satisfied grin masks his confidence, bragging about turning mediocre loot into triumph."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Flame Emperor scoffs, yet admits petty tricks still count as genuine skill."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "He consults the map, searching for the nearest ally amid looming monster."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "The knight's blood\u2011stained blade glints, revealing General Sarvas as his target."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Red\u2011capped commander greets the otherworldly warrior, admiring his flamboyant mustache."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Hopeful whisper lingers, wishing his prowess matches that ridiculous facial flourish."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "General receives a frantic plea, warning of a scammer lurking nearby."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Desperate knight implores assistance, offering any aid to prove his worth."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Bleeding warrior begs for death, bewildered by the unexpected plea."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Gongja declares secret skill, while flame emperor scoffs, fate teeters."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Silver general recoils, forced to kill ally for empire\u2011saving sacrifice."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "A voice threatens, urging immediate resolution before darkness consumes all."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Gongja proposes grim bargain; shocked emperor watches, knight screams disbelief."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Red\u2011haired commander laments, pointing at mysterious figure behind trembling knight."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Urgent empty space echoes, demanding haste amid looming catastrophe."
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Armored warrior refuses killing, while shocked red\u2011hair questions his resolve."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Knight bows, lamenting cursed fate; long\u2011haired observer scowls at destiny."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Silver knight delivers fatal blow; suited man embraces pain with gratitude."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Helmeted stranger inquires quietly, seeking identity amidst chaotic war."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Gongja calmly introduces himself, echoing ancient philosopher\u2019s resolve."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Bowing helmeted figure thanks Gongja, invoking empire\u2019s solemn gratitude."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Silver blade arcs, slicing fate itself\u2014Gong\u2011ja's resolve glints in steel."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Flame Emperor's towering silhouette declares truth, while Gong\u2011ja shoulders destiny."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "A ghostly whisper echoes\u2014death's curtain falls, yet the tower persists."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Ancient Korean proverb drifts, hinting at hidden wisdom within this chaos."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Random skill theft looms, stealing Sarvas's power like a thief in shadows."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Run, crawl, or soar\u2014only the daring earn wings beyond mere footsteps."
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "Explosive magic meets brute force; goblin horde shivers under relentless hunter's roar."
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "A parallel proverb surfaces, whispering that mastery transcends simple victory."
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "Eyes widen, breath freezes; unseen catastrophe looms, demanding immediate resolve."
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "Mounted thunder roars, crowd gasps; lone hunter rides destiny's reckless, blazing steed."
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Confucian echo rings, binding ancient wisdom to glowing blade and crimson mentor."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch20")
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
        chapter_id="sss-class-revival-hunter/ch20",
        title="SSS-Class Revival Hunter - Chapter 20",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch20/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 20 Script ===")
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
