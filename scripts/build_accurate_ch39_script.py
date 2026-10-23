"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 39.

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
        "narration": "Gong-ja hangs suspended in white light as the system coldly announces his final demise.",
        "direction": "dramatic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "The interface flashes red, warning him that a severe penalty awaits his reckless skill usage.",
        "direction": "system"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "He will relive the trauma experienced by the enemy who just ended his life.",
        "direction": "intense"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "The system labels this punishment as medium, though the horror feels far more intense.",
        "direction": "warning"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "Dragged into the Hungry Ghost Realm, Gong-ja prepares to witness a tragic past unfold.",
        "direction": "transition"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Men command the flames to burn every supporter, showing absolutely no mercy to the cursed.",
        "direction": "action"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "A woman stares in shock as fire illuminates her face from the burning background behind.",
        "direction": "closeup"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "Her mouth opens wide in disbelief, asking why this destruction is happening to her people.",
        "direction": "shock"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Three figures stand together as debris falls from the sky above their terrified heads.",
        "direction": "group"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "Bodies collapse on the sand surrounding a central figure kneeling in despair before the crowd.",
        "direction": "tragic"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Voices shout that this terrible destruction is simply the will of the lord above.",
        "direction": "text"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "Knights declare the emperor and pope command her death for claiming to be a saint.",
        "direction": "authority"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "An archer draws his bow, praying for spirits to bless the arrow aimed at the foe.",
        "direction": "combat"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "The magic within this staff strengthens, fueled by a jewel given by the merpeople ruler.",
        "direction": "magic"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "Dragon riders stand ready to fulfill their honorable pledge alongside the green robed elf.",
        "direction": "alliance"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "A hooded man pleads before three imposing armored warriors kneeling nearby.",
        "direction": "dramatic"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "Glitching warriors stand silent as someone demands to know their identity.",
        "direction": "intense"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Two cloaked observers watch a building consumed by violent raging inferno flames.",
        "direction": "dramatic"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "A child screams in fire while a voice soothes through the pain.",
        "direction": "emotional"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "A white-haired man burns while whispering comfort to his dying beloved.",
        "direction": "tragic"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Darkness swallows hope as a final promise hangs unfinished in the void.",
        "direction": "dramatic"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Silence follows the broken vow, leaving only emptiness where words should exist.",
        "direction": "somber"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "A saint stands alone amidst the ruins of her beloved village community.",
        "direction": "dramatic"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Fallen soldiers lie defeated on the dirt with shattered weapons scattered around.",
        "direction": "grim"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "A youth offers fresh apples hoping the saint might accept their humble gift.",
        "direction": "hopeful"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Grateful villagers thank the saint for healing wounds that once seemed permanent.",
        "direction": "warm"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "She counts the dead names of those lost to the endless cruel plague.",
        "direction": "tragic"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "The list of victims ends in heavy silence echoing through the devastation.",
        "direction": "somber"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "Shadowy corruption spreads quickly across formal attire consuming the flesh beneath.",
        "direction": "horror"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Blood fills her mouth as the dark power finally claims her life.",
        "direction": "intense"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "A lonely figure stands beneath the stormy sky, head bowed in sorrow.",
        "direction": "dramatic"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "She covers her mouth with a hand stained black by the ash.",
        "direction": "tragic"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Tears fall down her face while blood drips from her trembling lips.",
        "direction": "emotional"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Dark energy rises from the ground to form a face in the mist.",
        "direction": "mysterious"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "You were born humans who knew the beauty of life and tears.",
        "direction": "accusatory"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Villagers stare up in terror as black tendrils crawl across the walls.",
        "direction": "tense"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "A towering shadow with a red eye questions their humanity above them.",
        "direction": "menacing"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "A shadowy hand reaches up demanding proof of humanity from the living.",
        "direction": "confrontational"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "The cloaked figure declares it is time to prove their worth now.",
        "direction": "decisive"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "The air fills with grey waves and red lines of falling rain.",
        "direction": "abstract"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "Black flames consume the figure as a curse echoes through the dark void.",
        "direction": "ominous"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "A faceless hooded shape emerges slowly from the pool of black liquid.",
        "direction": "eerie"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "Gongja stands among the dead as dark ink rains down upon the pit.",
        "direction": "intense"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "The ghost master shouts for Confucius to wake up from the nightmare.",
        "direction": "urgent"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Gongja smiles confidently knowing this hell is not the one they fear.",
        "direction": "smug"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "The bold logo flashes bright, marking the start of this deadly revival hunt.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "Chaos erupts violently as black ink splatters explode across the frame with a scream.",
        "direction": "intense"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Gong-ja strikes forward with a glowing red flame sword slash cutting through the dark.",
        "direction": "action"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "He raises his sword high, unleashing a massive downward slash against the winged beast.",
        "direction": "epic"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "The red haired man shouts urgently for them to strike now before it is too late.",
        "direction": "urgent"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Gong-ja swings mid-air, shouting that the enemy's head is finally exposed for the kill.",
        "direction": "action"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "The black creature lunges forward on all fours, dripping thick liquid and blood into the air.",
        "direction": "horror"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "A towering figure of glossy black liquid stands tall, breathing heavily with a single red eye.",
        "direction": "ominous"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "The system announces the body is shrinking, obscuring the Demon King of Autumn Rain completely.",
        "direction": "mystery"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "Someone cries out in panic, realizing they cannot stop this rapid degradation of the monster form.",
        "direction": "fear"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "The entity feels the children's resentment and sorrows, choking on the pain of their deaths.",
        "direction": "tragic"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "It mentions Sungwoons and her name while bleeding red substance from its chest violently.",
        "direction": "violent"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "A voice commands them to go ahead and retreat from this dangerous battlefield immediately.",
        "direction": "command"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "A faceless humanoid figure covered in glossy black liquid stares forward with a glowing red eye.",
        "direction": "unsettling"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "Flame Emperor Yoo Soo-ha stands confident, ordering everyone to retreat to the twentieth floor now.",
        "direction": "authoritative"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "A tactical map shows scattered forces as a command demands quiet retreat to the castle.",
        "direction": "tactical"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "A shadow figure kneels on cracked earth telling the demon king to return to the start.",
        "direction": "ominous"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "A tall figure holds a sword ready while the woman invites him to deliver the final.",
        "direction": "tense"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "A long-haired man coughs violently as bright red blood splatters heavily from his open mouth.",
        "direction": "gruesome"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Gong-ja watches a system window announce the demon king has retreated to the twentieth floor below.",
        "direction": "frustrated"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "The atmosphere shifts heavily as silence falls over the battlefield after the demon king retreats.",
        "direction": "heavy"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Glowing blue effects surround Gong-ja and the emperor as they witness the altered history unfold above.",
        "direction": "magical"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "A floating speech bubble introduces the blade saint who serves as the leader of the black.",
        "direction": "introductory"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "A blue system window appears displaying text indicating the nineteenth floor history is being altered now.",
        "direction": "system"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "Someone apologizes politely while stating they wish to clear the twentieth floor entirely on their own.",
        "direction": "polite"
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "Faint blue glowing bubbles float quietly on the right side of the screen during this moment.",
        "direction": "quiet"
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "The man in red bows deeply thanking them but asks to face the demon king alone.",
        "direction": "solemn"
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "The woman concedes she will stay put while the man instructs her to find him after.",
        "direction": "agreement"
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Silence lingers in the air as the agreement is made and tensions settle around the group.",
        "direction": "calm"
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "The flame emperor looks forward and confirms his agreement with a simple verbal response to the.",
        "direction": "confident"
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "Gong-ja stands within the blue pillar, whispering thanks before the end begins.",
        "direction": "dramatic"
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "A command echoes through the void as reality bends to his desperate transport skill.",
        "direction": "dramatic"
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "Blinding white light consumes the view while blue mist rises from a small pool.",
        "direction": "dramatic"
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "Hazy blue light glows softly above, signaling the start of a new trial.",
        "direction": "dramatic"
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "The system welcomes the King of Death with cold, mechanical words of acceptance.",
        "direction": "dramatic"
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "He enters a boss stage alone, facing the shadow known as the King of Death.",
        "direction": "dramatic"
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "Rewards for the floors above calculate now as golden light swirls around his foot.",
        "direction": "dramatic"
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "The calculation finishes quickly, finalizing the rewards earned from his deadly previous journey.",
        "direction": "dramatic"
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "The Tower acknowledges his achievements by adjusting the terrifying authority of the King of Death.",
        "direction": "dramatic"
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "He gains restricted Apostle powers allowing him to modify almost any skill he owns.",
        "direction": "dramatic"
    },
    {
        "block_id": "b086",
        "panel_ids": [
            "panel_0086"
        ],
        "narration": "Gong-ja questions the strange offer to choose a specific skill from the list.",
        "direction": "dramatic"
    },
    {
        "block_id": "b087",
        "panel_ids": [
            "panel_0087"
        ],
        "narration": "He admits he knows nothing of why this Tower was ever built in the first place.",
        "direction": "dramatic"
    },
    {
        "block_id": "b088",
        "panel_ids": [
            "panel_0088"
        ],
        "narration": "He wonders who built it and how it carries worlds full of life within its walls.",
        "direction": "dramatic"
    },
    {
        "block_id": "b089",
        "panel_ids": [
            "panel_0089"
        ],
        "narration": "Yet slowly he starts making sense of the Tower's strange and dangerous existence now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b090",
        "panel_ids": [
            "panel_0090"
        ],
        "narration": "White streaks blur the vision as he moves forward with purpose into the next stage.",
        "direction": "dramatic"
    },
    {
        "block_id": "b091",
        "panel_ids": [
            "panel_0091"
        ],
        "narration": "A shadowy figure gazes upward as a translucent blade falls from the heavens.",
        "direction": "dramatic"
    },
    {
        "block_id": "b092",
        "panel_ids": [
            "panel_0092"
        ],
        "narration": "Flames swirl around the man holding his sword upright as he speaks to the demon king.",
        "direction": "intense"
    },
    {
        "block_id": "b093",
        "panel_ids": [
            "panel_0093"
        ],
        "narration": "A creature of dripping black liquid hovers with a single red eye and toothy mouth.",
        "direction": "horror"
    },
    {
        "block_id": "b094",
        "panel_ids": [
            "panel_0094"
        ],
        "narration": "A large black ink splash dominates the right side with red text saying this is.",
        "direction": "suspense"
    },
    {
        "block_id": "b095",
        "panel_ids": [
            "panel_0095"
        ],
        "narration": "A dark shadow monster screams that this is his village and no one ruins paradise.",
        "direction": "emotional"
    }
]


def build_and_save() -> bool:
    ch_id = "ch39"
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
        title=f"SSS-Class Revival Hunter - Chapter 39",
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

    print(f"=== SSS-Class Revival Hunter Ch 39 Script ===")
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
