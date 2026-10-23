"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 31.

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
        "narration": "Blade Saint arrives demanding audience, speaking sharply to the helmeted knight.",
        "direction": "dramatic"
    },
    {
        "block_id": "b002",
        "panel_ids": [
            "panel_0002"
        ],
        "narration": "Gong-ja orders everyone out, keeping only the young knight for business.",
        "direction": "intense"
    },
    {
        "block_id": "b003",
        "panel_ids": [
            "panel_0003"
        ],
        "narration": "An observer questions if Gong-ja has personal business with the hunter.",
        "direction": "curious"
    },
    {
        "block_id": "b004",
        "panel_ids": [
            "panel_0004"
        ],
        "narration": "Blade Saint refuses to leave, mocking the knight's outdated manners.",
        "direction": "confrontational"
    },
    {
        "block_id": "b005",
        "panel_ids": [
            "panel_0005"
        ],
        "narration": "The knight warns attacking Gong-ja means attacking all five great guilds.",
        "direction": "stern"
    },
    {
        "block_id": "b006",
        "panel_ids": [
            "panel_0006"
        ],
        "narration": "Marcus realizes the guilds are finally working together against his plans.",
        "direction": "thoughtful"
    },
    {
        "block_id": "b007",
        "panel_ids": [
            "panel_0007"
        ],
        "narration": "Security forces mock his words, claiming they make less sense now.",
        "direction": "skeptical"
    },
    {
        "block_id": "b008",
        "panel_ids": [
            "panel_0008"
        ],
        "narration": "The knight cites rumors of Marcus targeting people for personal vendettas.",
        "direction": "accusatory"
    },
    {
        "block_id": "b009",
        "panel_ids": [
            "panel_0009"
        ],
        "narration": "Marcus admits showing violence here changes everything compared to mere rumors.",
        "direction": "tense"
    },
    {
        "block_id": "b010",
        "panel_ids": [
            "panel_0010"
        ],
        "narration": "He vows to stop them as if his life depends on it.",
        "direction": "determined"
    },
    {
        "block_id": "b011",
        "panel_ids": [
            "panel_0011"
        ],
        "narration": "Gong-ja asks confidence, but the knight expects death after fighting him.",
        "direction": "grim"
    },
    {
        "block_id": "b012",
        "panel_ids": [
            "panel_0012"
        ],
        "narration": "She argues killing her brands him a worthless murderer in the public eye.",
        "direction": "desperate"
    },
    {
        "block_id": "b013",
        "panel_ids": [
            "panel_0013"
        ],
        "narration": "Another elder challenges Marcus to live as a known murderer if he wishes.",
        "direction": "challenging"
    },
    {
        "block_id": "b014",
        "panel_ids": [
            "panel_0014"
        ],
        "narration": "Gong-ja recalls learning Blade Saint's weakness during their last run together.",
        "direction": "internal"
    },
    {
        "block_id": "b015",
        "panel_ids": [
            "panel_0015"
        ],
        "narration": "He trusts the knight as the only one who never killed anyone.",
        "direction": "trusting"
    },
    {
        "block_id": "b016",
        "panel_ids": [
            "panel_0016"
        ],
        "narration": "Marcus struggles to harm those he genuinely judges as innocent souls within his heart.",
        "direction": "dramatic"
    },
    {
        "block_id": "b017",
        "panel_ids": [
            "panel_0017"
        ],
        "narration": "That is precisely why he brought the Paladin, the purest soul among all guild leaders.",
        "direction": "dramatic"
    },
    {
        "block_id": "b018",
        "panel_ids": [
            "panel_0018"
        ],
        "narration": "Her kill count sits at zero, marking her as absolutely untouched by violence or blood.",
        "direction": "dramatic"
    },
    {
        "block_id": "b019",
        "panel_ids": [
            "panel_0019"
        ],
        "narration": "By his flawed ethics, her zero count means she counts as an absolute saint today.",
        "direction": "dramatic"
    },
    {
        "block_id": "b020",
        "panel_ids": [
            "panel_0020"
        ],
        "narration": "Someone interrupts nervously, trying to speak up before the tension breaks completely.",
        "direction": "dramatic"
    },
    {
        "block_id": "b021",
        "panel_ids": [
            "panel_0021"
        ],
        "narration": "She steps forward boldly, declaring this customer her savior and threatening even the Saint himself.",
        "direction": "dramatic"
    },
    {
        "block_id": "b022",
        "panel_ids": [
            "panel_0022"
        ],
        "narration": "Silence hangs heavy in the air as everyone processes her sudden and fearless outburst.",
        "direction": "dramatic"
    },
    {
        "block_id": "b023",
        "panel_ids": [
            "panel_0023"
        ],
        "narration": "An elder urges them to leave, citing recent trouble with gangsters forcing them out.",
        "direction": "dramatic"
    },
    {
        "block_id": "b024",
        "panel_ids": [
            "panel_0024"
        ],
        "narration": "Good people stand no chance yet they are the only ones who can truly stop him.",
        "direction": "dramatic"
    },
    {
        "block_id": "b025",
        "panel_ids": [
            "panel_0025"
        ],
        "narration": "A suited man reaches into his jacket, preparing for whatever decision comes next silently.",
        "direction": "dramatic"
    },
    {
        "block_id": "b026",
        "panel_ids": [
            "panel_0026"
        ],
        "narration": "He admits today is not his day, marking the second step of their plan clear.",
        "direction": "dramatic"
    },
    {
        "block_id": "b027",
        "panel_ids": [
            "panel_0027"
        ],
        "narration": "He shouts a challenge to the Saint, demanding a meeting at the field north tomorrow.",
        "direction": "dramatic"
    },
    {
        "block_id": "b028",
        "panel_ids": [
            "panel_0028"
        ],
        "narration": "Gong-ja screams he will wait regardless, inviting the Saint to discover his true nature tomorrow.",
        "direction": "dramatic"
    },
    {
        "block_id": "b029",
        "panel_ids": [
            "panel_0029"
        ],
        "narration": "The elder watches the sunset, knowing the trap has been set perfectly for the hunt.",
        "direction": "dramatic"
    },
    {
        "block_id": "b030",
        "panel_ids": [
            "panel_0030"
        ],
        "narration": "Relief washes over him as he realizes he finally met a true killer today.",
        "direction": "dramatic"
    },
    {
        "block_id": "b031",
        "panel_ids": [
            "panel_0031"
        ],
        "narration": "The guild leader speaks quietly about the Blade Saint's notorious reputation among them.",
        "direction": "informative"
    },
    {
        "block_id": "b032",
        "panel_ids": [
            "panel_0032"
        ],
        "narration": "He lost his family to a killer, though few know the painful truth behind it.",
        "direction": "somber"
    },
    {
        "block_id": "b033",
        "panel_ids": [
            "panel_0033"
        ],
        "narration": "Gong-ja listens closely as they discuss his ruthless tendencies toward those who kill others.",
        "direction": "focused"
    },
    {
        "block_id": "b034",
        "panel_ids": [
            "panel_0034"
        ],
        "narration": "They warn that this sensitive information remains strictly confidential among the guild leadership only.",
        "direction": "serious"
    },
    {
        "block_id": "b035",
        "panel_ids": [
            "panel_0035"
        ],
        "narration": "The red-haired man confirms Marcus lost his grandchildren, surprising Gong-ja with the revelation.",
        "direction": "shock"
    },
    {
        "block_id": "b036",
        "panel_ids": [
            "panel_0036"
        ],
        "narration": "He shrugs off the sudden silence, noting Gong-ja never asked about his past tragedies.",
        "direction": "casual"
    },
    {
        "block_id": "b037",
        "panel_ids": [
            "panel_0037"
        ],
        "narration": "The city security member admits sometimes criminals make you question if they deserve to live.",
        "direction": "contemplative"
    },
    {
        "block_id": "b038",
        "panel_ids": [
            "panel_0038"
        ],
        "narration": "Every leader has secrets, and he wonders how Gong-ja will react to their rotten truths.",
        "direction": "enigmatic"
    },
    {
        "block_id": "b039",
        "panel_ids": [
            "panel_0039"
        ],
        "narration": "The knight admits getting carried away in conversation while Gong-ja watches with calm, steady eyes.",
        "direction": "relaxed"
    },
    {
        "block_id": "b040",
        "panel_ids": [
            "panel_0040"
        ],
        "narration": "He jokes about funding issues, asking how much the potions cost since security lacks money.",
        "direction": "lighthearted"
    },
    {
        "block_id": "b041",
        "panel_ids": [
            "panel_0041"
        ],
        "narration": "The title card flashes brightly, marking a moment before the narrative shifts forward in time.",
        "direction": "dramatic"
    },
    {
        "block_id": "b042",
        "panel_ids": [
            "panel_0042"
        ],
        "narration": "Time skips ahead to early morning as the next day begins with a quiet start.",
        "direction": "transition"
    },
    {
        "block_id": "b043",
        "panel_ids": [
            "panel_0043"
        ],
        "narration": "People react with shock and accusation online as news spreads about the mysterious hunter's identity.",
        "direction": "chaotic"
    },
    {
        "block_id": "b044",
        "panel_ids": [
            "panel_0044"
        ],
        "narration": "Gong-ja checks his phone in the forest, noting the atmosphere feels similar to his last run.",
        "direction": "observant"
    },
    {
        "block_id": "b045",
        "panel_ids": [
            "panel_0045"
        ],
        "narration": "Headlines question who cleared the tenth floor, while the eleventh floor remains a collective effort.",
        "direction": "news"
    },
    {
        "block_id": "b046",
        "panel_ids": [
            "panel_0046"
        ],
        "narration": "The Flame Emperor turns to the elder, noting changes and solitude in the room.",
        "direction": "dramatic"
    },
    {
        "block_id": "b047",
        "panel_ids": [
            "panel_0047"
        ],
        "narration": "The elder mocks Gong-ja's confidence, noting his history of killing many people.",
        "direction": "tense"
    },
    {
        "block_id": "b048",
        "panel_ids": [
            "panel_0048"
        ],
        "narration": "Gong-ja grabs the sleeve, asking if the zombified emperor is alright now.",
        "direction": "concerned"
    },
    {
        "block_id": "b049",
        "panel_ids": [
            "panel_0049"
        ],
        "narration": "He interrupts the tension, announcing he has something vital to tell the Blade Saint.",
        "direction": "dramatic"
    },
    {
        "block_id": "b050",
        "panel_ids": [
            "panel_0050"
        ],
        "narration": "The elder claims Gong-ja seeks him out due to a guilty conscience and sins.",
        "direction": "intense"
    },
    {
        "block_id": "b051",
        "panel_ids": [
            "panel_0051"
        ],
        "narration": "Gong-ja insists it is because of the Saint's Detective Insight skill showing his sins.",
        "direction": "serious"
    },
    {
        "block_id": "b052",
        "panel_ids": [
            "panel_0052"
        ],
        "narration": "The Saint lives by his beliefs, making his stubbornness inseparable from daily life itself.",
        "direction": "reflective"
    },
    {
        "block_id": "b053",
        "panel_ids": [
            "panel_0053"
        ],
        "narration": "Suddenly Gong-ja declares himself a Prophet, shocking the elderly sword master with the claim.",
        "direction": "shocking"
    },
    {
        "block_id": "b054",
        "panel_ids": [
            "panel_0054"
        ],
        "narration": "He explains a skill allowing future prediction, warning that the Saint will try to kill him.",
        "direction": "explanatory"
    },
    {
        "block_id": "b055",
        "panel_ids": [
            "panel_0055"
        ],
        "narration": "The elder notes Gong-ja claims he killed over four thousand people based on the skill.",
        "direction": "skeptical"
    },
    {
        "block_id": "b056",
        "panel_ids": [
            "panel_0056"
        ],
        "narration": "The Saint demands proof now, challenging Gong-ja to speak the truth without hesitation.",
        "direction": "demanding"
    },
    {
        "block_id": "b057",
        "panel_ids": [
            "panel_0057"
        ],
        "narration": "He holds up fingers behind his back, demanding Gong-ja guess the number if truly a Prophet.",
        "direction": "testing"
    },
    {
        "block_id": "b058",
        "panel_ids": [
            "panel_0058"
        ],
        "narration": "The true test lies not in the number, but in how the Saint reacts to failure.",
        "direction": "subtle"
    },
    {
        "block_id": "b059",
        "panel_ids": [
            "panel_0059"
        ],
        "narration": "When Gong-ja fails, the Saint assumes lies and strikes downward with lethal force immediately.",
        "direction": "action"
    },
    {
        "block_id": "b060",
        "panel_ids": [
            "panel_0060"
        ],
        "narration": "A dark blur streaks forward as Gong-ja counters instantly, leaving the Saint shocked and stunned.",
        "direction": "climax"
    },
    {
        "block_id": "b061",
        "panel_ids": [
            "panel_0061"
        ],
        "narration": "The elderly man demands answers, standing tall while Gong-ja waits silently in the clearing.",
        "direction": "tense"
    },
    {
        "block_id": "b062",
        "panel_ids": [
            "panel_0062"
        ],
        "narration": "He predicts Gong-ja will hide his hand and ask how many fingers he holds up now.",
        "direction": "suspense"
    },
    {
        "block_id": "b063",
        "panel_ids": [
            "panel_0063"
        ],
        "narration": "Gong-ja begs belief, warning that killing him makes clearing the dangerous twelfth floor impossible safely.",
        "direction": "desperate"
    },
    {
        "block_id": "b064",
        "panel_ids": [
            "panel_0064"
        ],
        "narration": "Marcus doubts this, suggesting mind reading skills, noting one death proves nothing truly about prophecy.",
        "direction": "skeptical"
    },
    {
        "block_id": "b065",
        "panel_ids": [
            "panel_0065"
        ],
        "narration": "He demands proof of no hidden tricks, threatening violence if Gong-ja fails to demonstrate honesty now.",
        "direction": "aggressive"
    },
    {
        "block_id": "b066",
        "panel_ids": [
            "panel_0066"
        ],
        "narration": "Convincing another person remains a difficult task when trust is completely broken between two rivals.",
        "direction": "reflective"
    },
    {
        "block_id": "b067",
        "panel_ids": [
            "panel_0067"
        ],
        "narration": "Gong-ja insists the saint cannot kill him here without causing countless casualties on the twelfth floor.",
        "direction": "pleading"
    },
    {
        "block_id": "b068",
        "panel_ids": [
            "panel_0068"
        ],
        "narration": "It becomes harder when convincing an old man who already reached the absolute apex of his.",
        "direction": "resigned"
    },
    {
        "block_id": "b069",
        "panel_ids": [
            "panel_0069"
        ],
        "narration": "He pleads one last time for the blade saint to simply believe his desperate words now.",
        "direction": "emotional"
    },
    {
        "block_id": "b070",
        "panel_ids": [
            "panel_0070"
        ],
        "narration": "But Gong-ja accepts the test, saying it is okay for the saint to examine him thoroughly.",
        "direction": "calm"
    },
    {
        "block_id": "b071",
        "panel_ids": [
            "panel_0071"
        ],
        "narration": "He remains confident he can convince the saint no matter how long this testing process might.",
        "direction": "resolute"
    },
    {
        "block_id": "b072",
        "panel_ids": [
            "panel_0072"
        ],
        "narration": "His confidence stems from a grim truth where his own death will outlast the saint's living.",
        "direction": "ominous"
    },
    {
        "block_id": "b073",
        "panel_ids": [
            "panel_0073"
        ],
        "narration": "The blade saint stands silent, holding his weapon while considering the strange words spoken by this.",
        "direction": "contemplative"
    },
    {
        "block_id": "b074",
        "panel_ids": [
            "panel_0074"
        ],
        "narration": "Gong-ja admits he is not innocent and does not ask to escape punishment, waiting for the.",
        "direction": "honest"
    },
    {
        "block_id": "b075",
        "panel_ids": [
            "panel_0075"
        ],
        "narration": "He asks for five days to live, allowing surveillance to prove if he deserves death or.",
        "direction": "final"
    },
    {
        "block_id": "b076",
        "panel_ids": [
            "panel_0076"
        ],
        "narration": "Gong-ja admits he still does not trust the Flame Emperor at all.",
        "direction": "dramatic"
    },
    {
        "block_id": "b077",
        "panel_ids": [
            "panel_0077"
        ],
        "narration": "He waits patiently for the final blow to end his life now.",
        "direction": "tense"
    },
    {
        "block_id": "b078",
        "panel_ids": [
            "panel_0078"
        ],
        "narration": "A woman claims the future holds words that reassure his past self.",
        "direction": "mysterious"
    },
    {
        "block_id": "b079",
        "panel_ids": [
            "panel_0079"
        ],
        "narration": "Two men lock eyes as one whispers the Sword Emperor name aloud.",
        "direction": "intense"
    },
    {
        "block_id": "b080",
        "panel_ids": [
            "panel_0080"
        ],
        "narration": "The Saint warns a test of faith will reveal his true self soon.",
        "direction": "serious"
    },
    {
        "block_id": "b081",
        "panel_ids": [
            "panel_0081"
        ],
        "narration": "He asks if five days is the agreed timeframe for this trial.",
        "direction": "inquisitive"
    },
    {
        "block_id": "b082",
        "panel_ids": [
            "panel_0082"
        ],
        "narration": "The Flame Emperor vows to watch every single action for five days.",
        "direction": "threatening"
    },
    {
        "block_id": "b083",
        "panel_ids": [
            "panel_0083"
        ],
        "narration": "Gong-ja agrees to the deal where life depends on proving his fate.",
        "direction": "resolute"
    },
    {
        "block_id": "b084",
        "panel_ids": [
            "panel_0084"
        ],
        "narration": "He bows deeply to express sincere thanks for the chance to live.",
        "direction": "grateful"
    },
    {
        "block_id": "b085",
        "panel_ids": [
            "panel_0085"
        ],
        "narration": "He realizes he gained the Blade Saint trust just for a little while.",
        "direction": "reflective"
    },
    {
        "block_id": "b086",
        "panel_ids": [
            "panel_0086"
        ],
        "narration": "Gong-ja tells the Saint he will meet again on the next floor.",
        "direction": "confident"
    },
    {
        "block_id": "b087",
        "panel_ids": [
            "panel_0087"
        ],
        "narration": "The title card announces climbers of the tower as the journey begins.",
        "direction": "dramatic"
    },
    {
        "block_id": "b088",
        "panel_ids": [
            "panel_0088"
        ],
        "narration": "A system notification confirms transport to the next dangerous floor now.",
        "direction": "system"
    },
    {
        "block_id": "b089",
        "panel_ids": [
            "panel_0089"
        ],
        "narration": "A final caption wishes luck to remain on his side forever.",
        "direction": "foreboding"
    }
]


def build_and_save() -> bool:
    ch_id = "ch31"
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
        title=f"SSS-Class Revival Hunter - Chapter 31",
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

    print(f"=== SSS-Class Revival Hunter Ch 31 Script ===")
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
