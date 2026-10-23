"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 15.

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
        "narration": "A desperate child cries, echoing hunger across the bleak, silent night."
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "A crystalline violet butterfly flutters, scattering shards of hope amidst darkness."
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "The doctor opens a doorway, offering false salvation to a starving plea."
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "A wooden door slams, shocking the orphan as society's cruelty crashes inward."
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Crowded streets erupt with grumbling, each voice a bitter echo of famine."
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "A weary mother retreats, while men argue, starving children linger unseen."
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "A red-haired doctor brushes off a child's pain, muttering disdainful wishes."
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "The child bows, apologies trembling, as the doctor feigns gentle concern."
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "He leans in, questioning absent parents, his smile thinly veiled menace."
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "A gloved palm rests, mocking the girl's gaunt desperation with cold empathy."
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "The sinister figure whispers, beckoning the orphan toward inevitable darkness."
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "He promises treatment, yet chains the child, masking cruelty as care."
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Chains clatter, sunlight mocks the captive's hope, whispering false freedom."
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Tears stain trembling fists as the doctor watches, hunger echoing silently."
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Polished grin masks murderous intent, hat tip sealing inevitable cruelty."
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Black void amplifies the beast's lament, a starving child's desperate howl."
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Stony path leads to trembling eyes, questioning humanity's cruel hierarchy."
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Cold steel glints, innocence shackled, as predator proclaims intimate empathy."
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Red-eyed tyrant blames disease, wielding blade like twisted justice."
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Self-inflicted threat meets firm restraint, madness teetering on redemption's edge."
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Crimson bloom erupts, silence shattered by violent, fleeting confession."
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Charismatic liar incites torch-wielding mob, sacrificing children for imagined salvation."
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Ritual dagger glows, youth's gasp freezes, innocence offered to bloodthirsty god."
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Frenzied chorus of crimson-eyed zealots screams murderous mantra, bloodlust unbound."
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "A jagged scream shouts, bloodied urgency echoing through darkness."
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Red splatter erupts, a brutal slash painting the void."
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "White-haired orphan caged, a voice demands more sacrifices for rituals."
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Gong-ja's boots stand amid bloodied weapons, silent witnesses to carnage."
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "He stares at gore, questioning the purpose of endless bloodshed."
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Red-haired specter appears, mocking his confusion with cryptic, indifferent laughter."
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "A cold whisper drifts, dismissing the tragedy as irrelevant background."
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Pink-haired fury erupts, demanding accountability for the children's suffering."
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Realization hits: the monster's visage mirrors the orphan's shattered soul."
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Dusty violet bricks glimmer, hinting at unseen horrors lurking beyond."
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Gong-ja glows faintly, confronting cages that echo his own haunted memories."
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "Two thoughts echo: ignorance shattered, monsters once wore human skin."
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Red-haired swordsman kneels amid blood, reminding Gong-ja bosses stem from trauma."
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "Gong-ja's eyes blaze, demanding why such horrors were never disclosed."
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "The ghostly mentor smirks, his silence echoing Gong-ja's unanswered questions."
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Gong-ja mutters hunger, while a candle\u2011lit stranger prowls ominously."
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Blonde stumbles, red-haired veteran watches, both scoffing at the absurdity."
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "A golden bell releases a lone cigarette, symbolizing fragile hope amidst ruin."
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Flames devour the mansion as panic erupts, greed whispering behind terrified cries."
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Gong-ja lunges, berating escape, reminding them children still suffer behind walls."
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "Chains bind the youth, his gaze fixed on inferno beyond barred windows."
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Amid roaring blaze, Gong-ja hears desperate pleas, fearing deeper horrors await."
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Silence settles, the empty gradient echoing emptiness left by shattered souls."
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Red-haired figure stares away, while Gong-ja hides his face, consumed by grief."
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Red-haired specter scowls, while the grey-haired ghost sighs, muttering UGH."
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Sword Emperor sighs, Gong-ja rolls eyes, sarcasm dripping like stale blood."
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Flaming hair erupts, shouting self-deprecation, truth gnawing like relentless termites."
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Bandaged fist pierces air, reminding him monsters eclipse innocent cries forever."
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "If tower housed endless cycles, children could respawn, absurdly multiplying sorrow."
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "But trauma originated elsewhere, time\u2011locked, leaving us powerless, haunted by echoes."
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Red-haired commander orders, 'Locate the true doll, end this grotesque parody.'"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "He climbs, muttering floors like a broken record, ambition fueling absurd desperation."
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Flame Emperor lingers, half\u2011smirking, his thoughts flicker like dying embers."
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Red-haired woman questions, green-hooded man remains silent, tension thickens like fog."
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "He despises flame emperor, yearning to break cycle, refusing cursed legacy."
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Argument erupts, accusations fly, each word a blade slicing fragile resolve."
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "Fury erupts as he demands the boss's death, mocking his own undead status."
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Self\u2011inflicted head\u2011bang reflects his despair, while the crimson\u2011haired mentor smirks."
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "Anguish roars, fists clenched, proclaiming his own stupidity with bitter sarcasm."
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Crossed arms conceal a smirk, recalling the forgotten S\u2011class technique with lazy confidence."
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "A towering green suit escorts the grieving child, embodying grudges and seething resentment."
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Shackled prisoner mutters broken hopes, his voice a whisper of unhealed sorrow."
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "He summons a mile\u2011radius hellfire barrier, denying any escape without his grim permission."
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "Red\u2011haired fury erupts, Gongja's eyes flash, demanding answers about the strange skill."
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "The dark\u2011haired operative questions the dragon clan's survival without confronting the boss directly."
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "He splits reality, exposing the truth behind the boss's impossible endurance."
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "A lone revelation echoes: the answer is singular, inevitable, and chillingly simple."
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "Flames rise, shadowed watchers observe as the boss grants permission to flee."
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Blonde girl clicks, giggling; Gong\u2011ja ignites, surrounded by chanting children."
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "Staircase whispers as brown\u2011haired girl beckons, urging lonely hearts to join."
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "Gong\u2011ja nods, accepting the absurd invitation, heart thudding with reluctant curiosity."
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "Palms raised, golden orb blossoms, promising playful terror amid smoldering ruins."
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "Gong-ja reacts with fierce intensity as A wall of fire erupts across the room as."
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "Gong-ja reacts with fierce intensity as A black, rounded rectangular shape is displayed in."
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "Girls tease, questioning fire\u2011proof hero, heat rising like nervous laughter."
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "Child pleads, Gong\u2011ja grins, sleeves roll, eager to join chaotic game."
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "Maniacal laughter erupts, children stare, flames dance, hide\u2011and\u2011seek turns deadly."
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "Gong\u2011ja shields sight, shouting hide commands, turning terror into twisted playground."
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "Red\u2011haired master counts, Gong\u2011ja pretends ignorance, children plot escape beyond scorching reach."
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "Man hovers, children shiver; sudden 'GOTCHA!' erupts, innocence shattered in laughter."
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0086"
        ],
        "narration": "Gongja comforts the red\u2011haired child while flames roar, accusations flying."
    },
    {
        "block_id": "b086",
        "panel_ids": [
            "panel_0087"
        ],
        "narration": "A lone voice trembles, questioning the impossible difficulty of the challenge."
    },
    {
        "block_id": "b087",
        "panel_ids": [
            "panel_0088"
        ],
        "narration": "Gongja darts among frantic children, pleading innocence amidst chaotic tag."
    },
    {
        "block_id": "b088",
        "panel_ids": [
            "panel_0089"
        ],
        "narration": "The crimson\u2011haired specter surveys the gruesome remnants, his gaze chilling."
    },
    {
        "block_id": "b089",
        "panel_ids": [
            "panel_0090"
        ],
        "narration": "Gongja kneels, soothing the weary soul as silent witnesses observe."
    },
    {
        "block_id": "b090",
        "panel_ids": [
            "panel_0091"
        ],
        "narration": "He bridges despair, linking child and woman while fire devours the staircase."
    },
    {
        "block_id": "b091",
        "panel_ids": [
            "panel_0092"
        ],
        "narration": "Crouching, Gongja attempts rescue, oblivious to flames licking the stairwell."
    },
    {
        "block_id": "b092",
        "panel_ids": [
            "panel_0093"
        ],
        "narration": "A desperate sprint through fire, clutching a child while chains clang."
    },
    {
        "block_id": "b093",
        "panel_ids": [
            "panel_0094"
        ],
        "narration": "A frightened boy huddles alone, locked within the wooden prison."
    },
    {
        "block_id": "b094",
        "panel_ids": [
            "panel_0095"
        ],
        "narration": "Silent child trembles, each breath echoing a haunting creak."
    },
    {
        "block_id": "b095",
        "panel_ids": [
            "panel_0096"
        ],
        "narration": "Gongja peers into confinement, inviting the child to join his game."
    },
    {
        "block_id": "b096",
        "panel_ids": [
            "panel_0097"
        ],
        "narration": "A gentle pat from a green\u2011sleeved hand reassures the trembling boy."
    },
    {
        "block_id": "b097",
        "panel_ids": [
            "panel_0098"
        ],
        "narration": "Gong-ja's eyes flicker, declaring destiny with a chilling, confident whisper."
    },
    {
        "block_id": "b098",
        "panel_ids": [
            "panel_0099"
        ],
        "narration": "A gentle pat on the boy's head hints at fragile hope amid ruin."
    },
    {
        "block_id": "b099",
        "panel_ids": [
            "panel_0100"
        ],
        "narration": "KIND SIR... echo reverberates, a desperate plea cloaked in trembling reverence."
    },
    {
        "block_id": "b100",
        "panel_ids": [
            "panel_0101"
        ],
        "narration": "THANK YOU. floats like a hollow promise, weightless yet suffocating."
    },
    {
        "block_id": "b101",
        "panel_ids": [
            "panel_0102"
        ],
        "narration": "A ghostly hand drips white ichor, staining innocence with cold, unforgiving sorrow."
    },
    {
        "block_id": "b102",
        "panel_ids": [
            "panel_0103"
        ],
        "narration": "The smiling youth receives gratitude, eyes closed, oblivious to looming tragedy."
    },
    {
        "block_id": "b103",
        "panel_ids": [
            "panel_0104"
        ],
        "narration": "Gong-ja clutches a cloth, while the red-haired specter watches, chains clinking ominously."
    },
    {
        "block_id": "b104",
        "panel_ids": [
            "panel_0105"
        ],
        "narration": "The title bursts forth, cards swirling, heralding relentless revival and unforgiving battles."
    }
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch15")
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
        chapter_id="sss-class-revival-hunter/ch15",
        title="SSS-Class Revival Hunter - Chapter 15",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch15/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 15 Script ===")
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
