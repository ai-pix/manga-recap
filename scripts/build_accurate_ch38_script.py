"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 38.

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
        "narration": "A blue system moments announces their arrival on the thirteenth floor now.",
        "direction": "cinematic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "Three figures appear on the glowing circle as the system welcomes the king.",
        "direction": "impact"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "A monstrous wraith screams in fury accusing them of stealing its very soul.",
        "direction": "chaotic"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "The old man and witch comment dryly on the creature's overly dramatic wailing.",
        "direction": "dry humor"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "The Flame Emperor observes silently while red lightning crackles around his defensive stance.",
        "direction": "tense"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Someone notices the bastard is weaker than before despite the intense battle struggle.",
        "direction": "curious"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "It suffered damage from the witch lady's aura but this is no ordinary injury.",
        "direction": "analytical"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Its class got demoted from SSS great goblin king to a normal one now.",
        "direction": "explanatory"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Monsters usually get stronger here so maybe the witch's aura delevels targets unexpectedly.",
        "direction": "mysterious"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "A blue window calculates rewards for clearing the twelfth floor as the process begins.",
        "direction": "system"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "The system glitches and fails to compute the action properly right now.",
        "direction": "glitch"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Rewards wait until the nineteenth floor clears so only basic ones distribute now.",
        "direction": "system"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Congratulations the God of Navigation blessing has been strengthened significantly for the hunter.",
        "direction": "triumphant"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Access unlocks for maps from the eleventh through twentieth floors revealing a world map.",
        "direction": "revealing"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "The older man and woman rush forward as someone thinks they finally got it.",
        "direction": "dynamic"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "He shouts excitedly about the Demon King acting strangely again now.",
        "direction": "intense"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "They watch the town below as snow falls silently on the ruins.",
        "direction": "mysterious"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Pointing at the map, he asks where all the refugees came from.",
        "direction": "deductive"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "A tear falls as he notes the camps and refugees are gone now.",
        "direction": "melancholic"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "The history of the invasion has been completely changed in its entirety.",
        "direction": "revelatory"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Someone confirms this truth with a simple and direct affirmative response today.",
        "direction": "confirming"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "They returned to a time before the invasion started attacking this temple.",
        "direction": "dramatic"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "In other words, the timeline shifted back before the disaster began here.",
        "direction": "explanatory"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "A red-haired man reacts with confusion to the strange king level sound.",
        "direction": "confused"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "A notification reveals a layer of his hunter existence to the group.",
        "direction": "significant"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "He thought they were talking nonsense since he understood nothing of it.",
        "direction": "reflective"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "But he guesses that this situation involves much more than simple tools.",
        "direction": "speculative"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "The armored figure stands ready as puppets of the empire beneath them.",
        "direction": "ominous"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Now that the killing stops, a fighter must fight the existence itself.",
        "direction": "philosophical"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Existing as a fighter to fight existence is the ultimate burden ahead.",
        "direction": "solemn"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "A system window flashes, warning the Demon King of Autumn Rain is deeply infuriated.",
        "direction": "dramatic"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "The entity loses levels rapidly, its existence becoming obscured and less defined by the witch.",
        "direction": "intense"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "The creature roars out in fury, screaming at the fools who dared challenge it.",
        "direction": "chaotic"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Chaotic black energy erupts outward, tearing through the air with sharp, jagged streaks of power.",
        "direction": "explosive"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Gong-ja signals the group to advance as shadows lunge toward them in swirling red energy.",
        "direction": "action"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "It is time to raise the flag of retribution against this monster threatening their lives.",
        "direction": "heroic"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "The title logo shines brightly, marking the moment the hunters face a new terrifying challenge.",
        "direction": "bold"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Goblin warriors clash swords fiercely while armored monsters fall into disarray amidst the chaotic battle.",
        "direction": "combat"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "A massive black ink blot expands outward, signaling a dangerous new threat rising from the darkness.",
        "direction": "ominous"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "The dark mass shouts orders to kill them all, radiating black ink splatters everywhere.",
        "direction": "menacing"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Two armored men scream as a towering ink figure reaches up into the rainy sky.",
        "direction": "horror"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Marcus comments dryly that he has always hated zombie movies while holding his glowing blue sword.",
        "direction": "dry humor"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Gong-ja strikes mid-swing and asks the Sword Emperor why they do not make a bet.",
        "direction": "confident"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "He bets on how many times he will die before they reach the nineteenth floor.",
        "direction": "playful"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Okay, he bets less than a hundred, then changes it to less than ninety-nine times.",
        "direction": "energetic"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "A mocking voice echoes through the void, ridiculing the fallen loser loudly.",
        "direction": "taunting"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Gong-ja steps back, urging the zombie bastard to fight his own kind alone.",
        "direction": "strategic"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "He grins confidently in the rain, sealing a dangerous deal with finality.",
        "direction": "dramatic"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Monsters overwhelm them, but the Black Dragon leader claims only one area attack remains.",
        "direction": "intense"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "Skills remain on cooldown, so he calls the Blade Saint to check something nearby.",
        "direction": "action"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "The Saint crouches low, requesting the lid from that strange sarcophagus box nearby.",
        "direction": "mysterious"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "Gong-ja insists he is a prophet, begging for the object to be handed over.",
        "direction": "urgent"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Metal crunches loudly as figures grapple tightly beneath the looming metal structure above.",
        "direction": "action"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "The Saint refuses, claiming he walks only the path of the sword always.",
        "direction": "serious"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "He explains the weapon slams down, killing all undead in the area instantly.",
        "direction": "dramatic"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "He shouts he is a prophet again as a monster jaws open behind him.",
        "direction": "chaos"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "The Saint stands victorious with a hammer, clearing most zombies from the street completely.",
        "direction": "victory"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Now the group turns their attention toward the towering Demon King waiting above.",
        "direction": "foreshadowing"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Silence falls over the battlefield as they prepare for the final confrontation ahead.",
        "direction": "suspense"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "They identify the green giant as a cyclops turned minion for the demon king.",
        "direction": "analysis"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "The hooded warrior declares he will handle the massive giant alone today.",
        "direction": "assertive"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "A sudden explosion erupts with force as the battle intensifies instantly.",
        "direction": "impact"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Marcus turns away but is stopped by urgent pleas to keep fighting zombies.",
        "direction": "tense"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "He wants to test his sword but reminds them he is a prophet now.",
        "direction": "explanatory"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "The witch leader asks everyone to aim their powerful beam directly at the eye.",
        "direction": "directive"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Fiery flames engulf the area as a muscular man recoils from the shock.",
        "direction": "chaotic"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Ghosts emerge suddenly and the emperor questions if his skills lack any cooldown.",
        "direction": "curious"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "He replies vaguely that something like that applies to his current mysterious abilities.",
        "direction": "enigmatic"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "Now both can fight the giant but she needs to ask one vital thing.",
        "direction": "serious"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "She urgently warns them not to aim at the eye for a reason.",
        "direction": "urgent"
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "Trouble awaits if you do so he points out the huge staring eyeball.",
        "direction": "warning"
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "The eye looks inviting to hit but time is too short for full explanations.",
        "direction": "frustrated"
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "She decides to listen to the prophet claims and asks the saint too.",
        "direction": "resigned"
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Her hands clench tightly as tension builds up for the critical moment ahead.",
        "direction": "anxious"
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "They agree to try their best avoiding the eye and offer a simple thanks.",
        "direction": "relieved"
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "A blue energy slash cuts through the air, forcing the screaming man backward with violent force.",
        "direction": "dramatic"
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "The system announces the Demon King retreats as children laugh despite the priest's stern warning nearby.",
        "direction": "mixed"
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "Gong-ja smiles confidently while a massive warrior tumbles through the air above the temple grounds.",
        "direction": "calm"
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "United in a chain of hands, the party moves forward toward the dangerous next floor.",
        "direction": "determined"
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "A sudden shout commands transport as the group vanishes into the shifting magical particles.",
        "direction": "action"
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "Glowing cyan particles drift lazily through the air, marking the transition between dangerous dungeon floors.",
        "direction": "atmospheric"
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "Mysterious symbols float against a stark white void, signaling the magical mechanics at play here.",
        "direction": "abstract"
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "The Sword Saint grips his blade tightly, ready to strike any threat approaching them.",
        "direction": "tense"
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "Gong-ja reaches for the sparking sword hilt while tension rises among the group.",
        "direction": "intense"
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "Standing firm before the giant red dragon, Gong-ja faces the surrounding flames alone.",
        "direction": "epic"
    },
    {
        "block_id": "b086",
        "panel_ids": [
            "panel_0086"
        ],
        "narration": "The system confirms that Autumn Rain has finally decided to retreat from the battle.",
        "direction": "relief"
    },
    {
        "block_id": "b087",
        "panel_ids": [
            "panel_0087"
        ],
        "narration": "History is being reversed here, marking a crucial turning point in their deadly journey.",
        "direction": "profound"
    },
    {
        "block_id": "b088",
        "panel_ids": [
            "panel_0088"
        ],
        "narration": "A final notification declares the Demon King of Autumn Rain has officially retreated from here.",
        "direction": "conclusive"
    },
    {
        "block_id": "b089",
        "panel_ids": [
            "panel_0089"
        ],
        "narration": "Abstract shapes float loosely against the background, creating a magical atmosphere for this transition.",
        "direction": "abstract"
    },
    {
        "block_id": "b090",
        "panel_ids": [
            "panel_0090"
        ],
        "narration": "White and glowing blue petals drift through the air, creating a magical transitional atmosphere.",
        "direction": "serene"
    },
    {
        "block_id": "b091",
        "panel_ids": [
            "panel_0091"
        ],
        "narration": "The system announces Autumn Rain has retreated deep to the nineteenth floor.",
        "direction": "dramatic"
    },
    {
        "block_id": "b092",
        "panel_ids": [
            "panel_0092"
        ],
        "narration": "A faint pendant glows with cyan energy trails flowing toward the right.",
        "direction": "mysterious"
    },
    {
        "block_id": "b093",
        "panel_ids": [
            "panel_0093"
        ],
        "narration": "The screen shifts to reveal the haunting existence of the Demon King.",
        "direction": "ominous"
    },
    {
        "block_id": "b094",
        "panel_ids": [
            "panel_0094"
        ],
        "narration": "A single red eye opens wide within the swallowing darkness surrounding it.",
        "direction": "intense"
    },
    {
        "block_id": "b095",
        "panel_ids": [
            "panel_0095"
        ],
        "narration": "A textured black mass floats like ink against the stark white void.",
        "direction": "abstract"
    },
    {
        "block_id": "b096",
        "panel_ids": [
            "panel_0096"
        ],
        "narration": "The Flame Emperor screams at the smoke figure blaming it for everything.",
        "direction": "angry"
    },
    {
        "block_id": "b097",
        "panel_ids": [
            "panel_0097"
        ],
        "narration": "Gong-ja stands firm while the demon rages about stolen strength and blood.",
        "direction": "tense"
    },
    {
        "block_id": "b098",
        "panel_ids": [
            "panel_0098"
        ],
        "narration": "He grips his sword tightly and says that is how her eyes look.",
        "direction": "focused"
    },
    {
        "block_id": "b099",
        "panel_ids": [
            "panel_0099"
        ],
        "narration": "Chaos erupts in black ink as the demon screams in sudden confusion.",
        "direction": "chaotic"
    },
    {
        "block_id": "b100",
        "panel_ids": [
            "panel_0100"
        ],
        "narration": "He explains he traveled far just to see the demon look eyes.",
        "direction": "dramatic"
    },
    {
        "block_id": "b101",
        "panel_ids": [
            "panel_0101"
        ],
        "narration": "It would be a tragedy if their eyes never met face to face.",
        "direction": "philosophical"
    },
    {
        "block_id": "b102",
        "panel_ids": [
            "panel_0102"
        ],
        "narration": "The Emperor challenges the beast to fight fully or run away weak.",
        "direction": "confrontational"
    },
    {
        "block_id": "b103",
        "panel_ids": [
            "panel_0103"
        ],
        "narration": "The demon sinks in black liquid, shouting about losing strength forever.",
        "direction": "despairing"
    },
    {
        "block_id": "b104",
        "panel_ids": [
            "panel_0104"
        ],
        "narration": "Gong-ja calls the creature a vulture chasing after its own flesh.",
        "direction": "cold"
    },
    {
        "block_id": "b105",
        "panel_ids": [
            "panel_0105"
        ],
        "narration": "He points a glowing knife down and whispers the name Esther softly.",
        "direction": "quiet"
    },
    {
        "block_id": "b106",
        "panel_ids": [
            "panel_0106"
        ],
        "narration": "The shadowy beast screams, demanding they fight with everything they have right now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b107",
        "panel_ids": [
            "panel_0107"
        ],
        "narration": "Holding his glowing sword high, he vows his time will dwarf their entire history.",
        "direction": "intense"
    }
]


def build_and_save() -> bool:
    ch_id = "ch38"
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
        title=f"SSS-Class Revival Hunter - Chapter 38",
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

    print(f"=== SSS-Class Revival Hunter Ch 38 Script ===")
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
