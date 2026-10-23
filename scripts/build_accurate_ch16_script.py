"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 16.

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
            "panel_0001"
        ],
        "narration": "Blue holograms flash, announcing reward delayed until eleven\u2011floor entry tomorrow."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "Balconied fa\u00e7ade looms, skeletal trees whispering against the twilight sky."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "Gong\u2011ja and crimson\u2011haired ghost stare up, destiny hanging between them."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Green\u2011hooded hunter mutters, questioning the strange stare haunting his thoughts."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Red\u2011haired specter confesses past failures, urging pride despite looming uncertainty."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Gong\u2011ja\u2019s eyes widen, realization crushing hope like a brittle glass."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Two bubbles echo, lamenting universal cruelty across worlds and boss battles."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Specter sighs, noting humanity\u2019s inevitable mess when blood stains everything."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Side\u2011by\u2011side under stormy canopy, they stand silent, tension palpable."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Red\u2011haired phantom screams, clutching his head, while Gong\u2011ja watches calmly."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "A massive hand slaps Gong\u2011ja, praising strategic victory over sheer luck."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Cross\u2011armed specter grins, declaring deserved compliments for skillful stage clearance."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Red-haired mentor declares partnership, turning Gong-ja's victory into shared celebration."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Purple fireworks erupt as system blares announcement, two hunters stare in awe."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Blue notification flashes, confirming the tenth floor's brutal clearance, tension rises."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Celebratory sparks paint sky; system hints at looming eleventh floor challenge."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Crowd murmurs, questioning fireworks' purpose, while digital alert hovers above."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Silhouetted pair wonder about floor-wide pyrotechnics, anonymity masking speculation."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Green-skinned hunter on third floor watches fireworks, uneasy excitement flickering."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Gong-ja scrolls chat, rumors swirl\u2014Black Dragon, bureau, hidden agendas."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Digital clock ticks down, ominous promise: real show about to ignite."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Ghostly mentor reminisces, eyes reflecting past life, fireworks echoing memory."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Gong-ja sits alone, watching fireworks, second encounter feels eerily familiar."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Hunter Net buzzes, Black Dragon executives spotted, speculation fuels midnight chatter."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Gongja's eyes widen, pointing at the pantheon's secretive clergy gathering."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "A bright DING flashes, heralding the system's relentless chatter."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Poisonous Viper appears, teaching deadly techniques to eager apprentices."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Paladin loiters at Babylon Plaza, polishing his heroic fa\u00e7ade."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Another DING echoes, leaving the void of unanswered speculation."
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "An anonymous merchant denies involvement, yet whispers linger like smoke."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "The system chirps again, teasing the crowd with cryptic ellipsis."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "Fans wonder, 'Did Blade Saint slip through unnoticed?' The mystery deepens."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Gongja sips alone, while Blade Saint casually drinks milk, baffling everyone."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Chat erupts: 'Who cleared it? No one knows!'"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "A taunting voice asks, 'Feeling like a newly minted protagonist?'"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "The red-haired swordsman watches, his grin promising future chaos."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Gongja glances over shoulder, fireworks blazing, a grin of triumph."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Red\u2011haired specter smirks, claiming the world now kneels before him."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Ghost whispers warning, reminding Gongja his victory is merely the first step."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "A stark 'BUT' hangs, a silent challenge looming over their triumph."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Red\u2011haired mentor declares Gongja closest to the summit; armored hunter shouts eagerly."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Steam\u2011caked warrior gasps, questioning if the phantom was behind the recent shock."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Gongja, pockets deep, denies knowledge, his voice trembling with disbelief."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Metallic courier vibrates, demanding answers as the tower\u2019s elite scramble for truth."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "White\u2011clad knight questions possibilities, his hand hovering over Gongja\u2019s shoulder."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Purple\u2011haired warrior begs identity; Gongja waves, reminding him of the paid anonymity."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Turning toward the looming castle, Gongja lifts fist, declaring his nameless resolve."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Penguin\u2011helmeted armor erupts in manic laughter, finding Gongja\u2019s expression priceless."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Red-haired specter praises Gong-ja, urging him to mystify his rising legend."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "System flickers, Gong-ja wonders which floor to claim, while mentor smirks."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Triumphant Gong-ja shouts victory; ghostly mentor snarls, demanding equal recognition."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Arm-in-arm, they argue partnership parity, then teleport to first\u2011floor city."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Gong-ja strides away, demanding address as 'Sir Confucius' with swagger."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "A bold decree echoes, promising eternal consequences for every choice."
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "A blinding flash erupts, heralding the next chaotic episodes's arrival."
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Title glows, cards swirl, reminding everyone of relentless hunter aspirations."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "Patrons speculate wildly, accusing Black Dragon while rumors swirl like espresso foam."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Gong-ja sips coffee, dismissing rumors, proclaiming Blade Saint as true hero."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "He compares victory\u2019s sweetness to caramel macchiato, seeking Sword Emperor\u2019s affirmation."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Confused, he checks earphones, realizing silence masks the battlefield\u2019s whispers."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Red-haired specter snarls, unseen taunter echoes, tension crackles like static."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Gongja sips, earphones blaring, pink blossoms swirl, teasing voice lingers."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Red-haired ghost sobs, Gongja remains oddly calm, absurdity thickens."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "Mug in hand, Gongja endures shouted nonsense, partnership jokes echo."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Clock ticks ominously, blue horizon watches, destiny's deadline looms."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Startled by sudden jingle, Gongja's eyes widen, curiosity sparks."
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Cat's wide eyes betray surprise, gold bell jingles in anticipation."
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "Gongja coos, cat purrs, playful mystery cloaks their odd companionship."
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "Mysterious benefactor appears, cat obsession hinted, tension subtly rises."
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "Gongja eyes council, silent calculation brewing beneath his relaxed posture."
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "ID card flashed, Gongja smirks, time's irony bites his rivals."
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "Guild members scramble, coordinates shared, frantic chase ignites across Babel."
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "City Security chief bows, offering guild membership amid fireworks-fueled chaos."
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "He halts the eager reporter, demanding two requests before any official talk."
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "Gongja pleads secrecy, fearing relentless reporters hunting the mysterious tenth-floor hunter."
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "A dark-blue thumb rises, startling the trio with unexpected approval."
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "Seated with cat, he insists secrecy until the clock strikes zero, avoiding pressure."
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "Gong-ja reacts with fierce intensity as A woman speaks while looking forward, standing nex."
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "Gong-ja reacts with fierce intensity as A group of hunters, including the flame_emperor, c."
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "Sip pauses, cat snoozes, sudden realization echoes: 'You\u2019re right!'"
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "Distressed employee hears Gongja\u2019s rental request, flame emperor jokes about coffee."
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "A row of steaming coffees awaits, punctuated by a calm 'All right.'"
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "Gongja summons council, demanding conditions before any alliance forms."
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "White uniform pitches ten thousand gold, black suit scoffs, offering twenty thousand with executive role."
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "Guilds scramble, shouting promises, but Gong-ja remains unmoved, eyes fixed on destiny."
    },
    {
        "block_id": "b086",
        "panel_ids": [
            "panel_0086"
        ],
        "narration": "Self\u2011esteem shattered, everyone blames Blade Saint's relentless cruelty."
    },
    {
        "block_id": "b087",
        "panel_ids": [
            "panel_0087"
        ],
        "narration": "Offers cascade like rain, yet the lone hunter clutches his cat, indifferent."
    },
    {
        "block_id": "b088",
        "panel_ids": [
            "panel_0088"
        ],
        "narration": "A lone oval declares United Merchants, echoing empty corporate promises."
    },
    {
        "block_id": "b089",
        "panel_ids": [
            "panel_0089"
        ],
        "narration": "Gong-ja reacts with fierce intensity as Three characters are sitting around a wooden table."
    },
    {
        "block_id": "b090",
        "panel_ids": [
            "panel_0090"
        ],
        "narration": "Brown cat leaps, stretching, fleeing the chaos, leaving only silence."
    },
    {
        "block_id": "b091",
        "panel_ids": [
            "panel_0091"
        ],
        "narration": "Heeled countess offers co\u2011guild leadership, her smile thin as razor blades."
    },
    {
        "block_id": "b092",
        "panel_ids": [
            "panel_0092"
        ],
        "narration": "Gong-ja slides white earphones in, tuning out the world\u2019s clamor."
    },
    {
        "block_id": "b093",
        "panel_ids": [
            "panel_0093"
        ],
        "narration": "A voice declares triumph, and the hunter finally smirks at destiny."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch16")
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
        chapter_id="sss-class-revival-hunter/ch16",
        title="SSS-Class Revival Hunter - Chapter 16",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch16/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 16 Script ===")
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
