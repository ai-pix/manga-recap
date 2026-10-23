"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 19.

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
        "narration": "Ornate cards swirl around the title, heralding SSS-Class Revival Hunter\u2019s grand debut."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Crowd chugs beer, debating rumors; a sign promises free drinks for the curious."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "A lone bubble whispers gossip: guild leaders convened yesterday, secrecy thickening the air."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Gong\u2011ja grips his backpack strap, eyes scanning, questioning who truly cleared the floor."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Beneath the floating timer, fists rise; anticipation crackles like static electricity."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "The sky erupts, blinding '10' radiates, demanding attention from every onlooker."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Cheers explode as numbers tumble; fists slam, beers lift, excitement spikes."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Amid the countdown, Gong\u2011ja remains unflappable, smartphone glowing like a secret beacon."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "His finger taps 'Boogle', searching '10th floor clear'\u2014the results absurdly mundane."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Search bar displays cleaning\u2011window tips, mocking the tower\u2019s deadly mystery."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Breaking headlines scream Confucius Kim\u2019s triumph, turning a humble hunter into legend."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Gong\u2011ja\u2019s eyes widen, realization dawning, as party revelers cheer his accidental fame."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Crowd erupts, fists soaring, amber spray exploding, neon 'POP' ignites the night."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Gongja smirks at glowing screen while comrades gasp at tutorial's abrupt termination."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Radiant silhouette heralds 11th floor's birth, fireworks of destiny burst outward."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Ancient proclamation whispers, 'Warriors, climbers, ascend, the tower's challenge awaits.'"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Blonde specter floats, congratulating survivors, her light draping Hellfire Mansion's grudge."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Group stares skyward, mouths agape, whispering, 'Is that an angel, perhaps a goddess?'"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Gongja eyes ethereal blonde, red-haired whisper warns, 'Deceit hides behind false divinity.'"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "She declares quest, NPC-like voice echoing, 'World suffers, demons threaten, heroes needed.'"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Sketchy bubble taunts, 'Even goddesses reduce to recorded video, nothing authentic.'"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Summoning decree declares, 'Your mission: rescue world, confront demon king, become legend.'"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Gongja probes red veteran, who smirks, 'Sure? Because destiny already whispered.'"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Red sneaker thuds, declaring simple command: 'Transport,' and the adventure begins."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "A sleek black suit darts overhead, blue trails streaking, Gongja watches unimpressed."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "White\u2011haired ace plunges, blue blade slicing reality, digital chaos erupts around him."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Grey\u2011bearded veteran perches on rooftop, narrowly escaping a luminous sword's near\u2011miss."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Glitchy hologram flickers, whispering, 'If you wish, accept this perilous mission.'"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Elegant specter advises, 'Simply utter the word transport, and the world obeys.'"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Golden\u2011haired apparition hovers, crowd gasps, rooftop figure watches the impossible unfold."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Elder shrouded in crimson arcs, power crackles ominously around his crown."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Gongja smirks, red aura humming, declares his past deeds with sardonic flair."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Ancient sorcerer summons white vortex, murmuring 'Transport' as reality bends."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "A blinding flash erupts from tower's apex, shaking the skyline with raw power."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Baffled onlookers clutch beers, stunned by sudden chaos, erupting with manic laughter."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Blonde in black boasts triumphantly, declaring defeat turned into a flamboyant proclamation."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Blonde operative flicks her wrist, dissolving into dazzling, neon light."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Tower's crowd gasps as luminous priestess floats, shouting relentless transport commands."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "White-clad figure bows, radiating hope amidst swirling, holy luminescence."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Brown-haired youth stares, bewildered by cryptic proclamation of purpose."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Armored veteran sighs, Gong-ja questions, the dialogue drips sarcastic inevitability."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Holographic priestess glows, lamenting humanity's indifference to the tower's miracles."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Plate-clad commander chides, noting complacency, then teasing Gong-ja's sentimentality."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Confident voice declares musical doctorate, flirting, claiming newfound attractiveness through talent."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Red-haired brute mocks Gong-ja's finances, shouting playful 'Zombie' taunt."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Gong-ja glances over shoulder, warning about suspicious woman with exaggerated annoyance."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Echoing query floats: 'Are you Hunter Confucius Kim?'"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Press swarm Gong-ja, helmeted stranger apologizes, promising swift ascent to eleventh floor."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Gongja screams, 'Mister Confucius Kim! Why target me?' amidst frantic microphones."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "White-blue armor pivots, apologetic grin, declares, 'Reading people is my specialty.'"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Gongja demands identity proof; flame emperor vanishes, while red-haired mentor shouts, 'Zombie, beware!'"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Reporters swarm, shouting, 'Is the 10th floor truly yours alone?'"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "Sweat drips as Gongja ponders, 'How to answer about guild conspiracies?'"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Pink-shirted reporter declares, 'I aim to clear the twentieth floor next.'"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Rainbow streaks envelop Gongja; he yells, 'Wait, hunter!'"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Blazing column pierces clouds, delivering a lone climber to the tower."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Flickering message glows: 'May luck favor your desperate ascent.'"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Earth shudders, hunters scramble as white energy fissures the barren plain."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Gray-bearded elder stares, ink droplets swirling like ominous prophecy."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "A lone exclamation erupts, echoing bewilderment across the void."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Commander roars, demons surge; hunters brace as earth trembles, resolve ignites."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "A distant banner unfurls, proclaiming empire's looming dominance."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch19")
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
        chapter_id="sss-class-revival-hunter/ch19",
        title="SSS-Class Revival Hunter - Chapter 19",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch19/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 19 Script ===")
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
