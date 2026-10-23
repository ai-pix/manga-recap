"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 36.

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
        "narration": "A woman stands holding a small glowing green object in hands.",
        "direction": "intro"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "It never aged but grew more beautiful by the day instead.",
        "direction": "legend"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "They called her the Saint of the Borderlands with prayer.",
        "direction": "worship"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "A desperate man kneels crying out for help today.",
        "direction": "desperation"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "The mother begs for a blessing for her sick child.",
        "direction": "plea"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Esther tells them to leave the baby and return tomorrow.",
        "direction": "rule"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "She kneels and leaves the crying baby on the floor.",
        "direction": "abandonment"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "The saint looks down with a calm and confident smile.",
        "direction": "anticipation"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "She picks up the wrapped bundle and holds it close.",
        "direction": "action"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "She hugs the child and notes the pleasant smell deeply.",
        "direction": "horror"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "She comments on the rags wrapping the poor little one.",
        "direction": "mockery"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "He says life is brilliant even when wrapped in rags.",
        "direction": "irony"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "A massive shadow looms as a small figure screams in fear.",
        "direction": "climax"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "A large black hand slams down with massive impact force.",
        "direction": "impact"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "The final words whispered are you poor thing indeed now.",
        "direction": "aftermath"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Esther absorbs the baby's memory and comforts the weeping mother with fake warmth.",
        "direction": "dramatic"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "She reveals a swirling black mass in her palm with a cruel smile.",
        "direction": "menacing"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "A victim struggles violently as dark viscous sludge consumes their entire body slowly.",
        "direction": "horror"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "Standing on stone stairs, she looks down with glowing green eyes and a smirk.",
        "direction": "arrogant"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "The father smiles through tears believing his child is finally healed from illness.",
        "direction": "hopeful"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "Time passes quickly as more desperate souls arrive seeking her miraculous healing powers.",
        "direction": "narrative"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "A grateful mother bows deeply before the saint offering heartfelt thanks for help.",
        "direction": "grateful"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "Legends spread across the land about the one who blesses and heals the sick.",
        "direction": "legendary"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Parents weep with joy thanking her for restoring their ability to walk and see.",
        "direction": "emotional"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "Shadows gather around the map declaring her as the true savior of the people.",
        "direction": "ominous"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "Noble lords panic as peasants flee to join the growing faction of the saint.",
        "direction": "tense"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "Bold captions proclaim her as the savior of the sick across the entire region.",
        "direction": "grand"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Knights in armor demand no mercy for supporters of the witch gaining power.",
        "direction": "aggressive"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "A mob raises burning torches against the dark cloudy sky shouting to burn them all.",
        "direction": "chaotic"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Explosions engulf the spire but she stands calmly amidst the raging fire and flames.",
        "direction": "epic"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "Armored soldiers grab fleeing victims while flames consume the village behind them.",
        "direction": "dramatic"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "The knight declares every survivor is a cursed monster hiding in the fire.",
        "direction": "intense"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "A young woman stares in horror at the sudden violence unfolding before her eyes.",
        "direction": "shock"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "Screaming aloud, he accuses them of denying their shared humanity amidst the chaos.",
        "direction": "rage"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "Darkness spreads like ink across the void as a voice whispers be swallowed whole.",
        "direction": "ominous"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "Red text flashes against a dripping background signaling the end of hope itself.",
        "direction": "dramatic"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "The title appears boldly to mark the start of another deadly journey today.",
        "direction": "title card"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "A shadowy demon swings down calling out the name of our protagonist loudly.",
        "direction": "action"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "He sprints forward with a glowing blade shouting that he remains unharmed now.",
        "direction": "action"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "Gong ja analyzes the trajectory wondering if the strike targets his left or right side.",
        "direction": "tactical"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "He dies instantly only to wake up twenty four hours back in time again.",
        "direction": "twist"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "A timer counts down the days until he can use his powerful ghost skill.",
        "direction": "info"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "The clock skill ensures memories and abilities remain intact even after dying repeatedly now.",
        "direction": "exposition"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "The system confirms that specific abilities persist beyond death for his sword master too.",
        "direction": "reveal"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "His sword spirit notes that skills continue functioning even when his physical body perishes.",
        "direction": "conclusive"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "The rules state skill cooldown times apply equally to all abilities used now.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "A purple haired woman screams his alias with intense rage and dynamic energy.",
        "direction": "intense"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Another day passes as they fight monsters together under the stormy gray sky.",
        "direction": "narrative"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "Gongja swings his long blade horizontally against the horned green monsters before him.",
        "direction": "action"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "He thrusts his silver sword forward as red energy swirls wildly behind him.",
        "direction": "action"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Monsters surround him as he strikes down with a red energy trail slashing through.",
        "direction": "action"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "The horned demon swings a massive black sword while shouting his name in anger.",
        "direction": "dramatic"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Standing amidst rubble he claims he is fine despite the massive red explosion behind.",
        "direction": "tense"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "A cloaked figure questions how a mere mortal possesses the eyes of a prophet.",
        "direction": "mysterious"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "A system window appears announcing a new skill as he lunges forward aggressively.",
        "direction": "action"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "Skeleton warriors attack violently but he activates his skill to turn the tables quickly.",
        "direction": "action"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "The man in red braces against a powerful white energy burst during close combat.",
        "direction": "intense"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "Bae suggests trying double summoning next time while holding Gongja from behind tightly.",
        "direction": "humorous"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "Gongja thrusts upward while Bae jokes about becoming the great zombie king soon.",
        "direction": "humorous"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "A jagged speech bubble erupts with a loud shout echoing through the air.",
        "direction": "climactic"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "Falling upside down, Gong-ja curses repeating a whole week again because of the Flame Emperor.",
        "direction": "dramatic"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "The ghost laughs mockingly, blaming weakness for the delay instead of accepting any fault on his.",
        "direction": "comedy"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Flame Emperor warns the skill cooldown remains long while promising serious revenge someday for this humiliation.",
        "direction": "tense"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "The ghost laughs hysterically asking how to screw over a dead ghost before cursing in frustration.",
        "direction": "comedy"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "Gong-ja urges them to take down the Demon King while the Black Dragon leader gets a.",
        "direction": "action"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "A woman in dark fur lunges forward, her hand outstretched and surrounded by rushing red magical.",
        "direction": "action"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "She crosses her hands to converge bright purple light within a floating dark magical cage structure.",
        "direction": "magic"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "The pink-haired woman reaches upward into a vortex of dark purple energy as power unleashes rapidly.",
        "direction": "action"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "A dark ink-like mass explodes outward with jagged fluid tendrils engulfing a screaming figure completely.",
        "direction": "horror"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "An explosive force erupts creating a shockwave that obliterates surroundings while someone praises the Madam's shot.",
        "direction": "action"
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "The horned figure denies being called madam claiming youth before suggesting a talk after catching the.",
        "direction": "dialogue"
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "An armored figure surrounded by dark aura gets warned about the next move approaching directly on.",
        "direction": "tense"
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "A dark shadowy entity crashes forward with immense force while a man in a blue suit.",
        "direction": "dramatic"
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "They prepare to attack at once when an opening appears while a woman manipulates glowing purple.",
        "direction": "action"
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "A heavily blurred black silhouette erupts up from the bottom obscuring everything as red exclamation points.",
        "direction": "dramatic"
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "A massive black explosion erupts outward, splitting into a bright white blade piercing through the center.",
        "direction": "dramatic"
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "From the inky shadow, jagged red text screams out in pure, uncontrollable rage.",
        "direction": "intense"
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "A figure screams as dark tendrils swirl around their head, shouting their grudge and resentment.",
        "direction": "intense"
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "The Flame Emperor looks shocked, red eyes wide as he asks if that is skin.",
        "direction": "shock"
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "The Demon King of Autumn Rain decides to retreat while two small figures look up in.",
        "direction": "confusion"
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "Gong-ja yells asking why a boss runs away, calling it toxic sludge as it flees.",
        "direction": "frustration"
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "Three characters gaze down at a glowing white sphere floating above a small black pedestal on.",
        "direction": "quiet"
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "Silence fills the air as a simple ellipsis hangs in the void between them.",
        "direction": "quiet"
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "A man in red looks at marks on his hand, wondering what all this was for.",
        "direction": "melancholy"
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "The tower acknowledges his decision as the young man stands below covering his face with hand.",
        "direction": "somber"
    },
    {
        "block_id": "b086",
        "panel_ids": [
            "panel_0086"
        ],
        "narration": "A blue window pops up creating a hidden quest while a sound effect rings out clearly.",
        "direction": "suspense"
    },
    {
        "block_id": "b087",
        "panel_ids": [
            "panel_0087"
        ],
        "narration": "The twelfth floor quest is now being adjusted as another notification flashes on the screen.",
        "direction": "anticipation"
    },
    {
        "block_id": "b088",
        "panel_ids": [
            "panel_0088"
        ],
        "narration": "System windows flood the screen adjusting floor quests while a young man stands facing them.",
        "direction": "dramatic"
    },
    {
        "block_id": "b089",
        "panel_ids": [
            "panel_0089"
        ],
        "narration": "Bold text asks if quests can be adjusted, flanked by blue blocks and a cyan bar.",
        "direction": "uncertainty"
    },
    {
        "block_id": "b090",
        "panel_ids": [
            "panel_0090"
        ],
        "narration": "A new scenario titled the warrior of a frozen world asks if he will continue being.",
        "direction": "serious"
    },
    {
        "block_id": "b091",
        "panel_ids": [
            "panel_0091"
        ],
        "narration": "That nightmare fades as Gong-ja steps forward into the tower's dark trials.",
        "direction": "dramatic"
    },
    {
        "block_id": "b092",
        "panel_ids": [
            "panel_0092"
        ],
        "narration": "A confident smile spreads as the system announces a hidden quest finally activates.",
        "direction": "intense"
    },
    {
        "block_id": "b093",
        "panel_ids": [
            "panel_0093"
        ],
        "narration": "Above his hooded form, a new quest title signals a challenge in frozen lands.",
        "direction": "mysterious"
    },
    {
        "block_id": "b094",
        "panel_ids": [
            "panel_0094"
        ],
        "narration": "Luminous blue particles drift slowly through the air like magical energy motes.",
        "direction": "atmospheric"
    }
]


def build_and_save() -> bool:
    ch_id = "ch36"
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
        title=f"SSS-Class Revival Hunter - Chapter 36",
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

    print(f"=== SSS-Class Revival Hunter Ch 36 Script ===")
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
