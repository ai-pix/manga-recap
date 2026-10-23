"""Build and validate fast-paced, high-retention recap script for barbarian_ch01.

Filters out all 36 black/text-only panels so zero black screens appear in the video.
Maps cleanly across all 94 story art panels in reading order.
Target: ~800 words (~5.0 minutes).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from manga_recap.core.config import load_config
from manga_recap.core.schema import (
    DescriptionFile,
    ScriptBeat,
    ScriptBlock,
    ScriptFile,
    load_model,
    save_model,
)
from manga_recap.stages.s3_script.validate import validate

blocks_data = [
    # Act 1: The Hospitalized Gamer & The Obscure Roguelike (p0001 - p0037)
    {
        "block_id": "b001",
        "panel_ids": ["panel_0001"],
        "narration": "Confined to a sterile hospital bed for years, gaming was Hansoo's only true escape.",
    },
    {
        "block_id": "b002",
        "panel_ids": ["panel_0002"],
        "narration": "Day in and day out, he lost himself in pixelated worlds on his handheld console.",
    },
    {
        "block_id": "b003",
        "panel_ids": ["panel_0003", "panel_0005"],
        "narration": "Another infuriating game over screen flashed, and he shoved the console away in total disgust.",
        "beats": [
            {"beat_id": "b003_0", "panel_id": "panel_0003", "text": "Another infuriating game over screen flashed,"},
            {"beat_id": "b003_1", "panel_id": "panel_0005", "text": "and he shoved the console away in total disgust."},
        ],
    },
    {
        "block_id": "b004",
        "panel_ids": ["panel_0006", "panel_0008"],
        "narration": "Modern releases had become soulless copycat cash grabs, and gaming forums echoed his exact frustrations.",
        "beats": [
            {"beat_id": "b004_0", "panel_id": "panel_0006", "text": "Modern releases had become soulless copycat cash grabs,"},
            {"beat_id": "b004_1", "panel_id": "panel_0008", "text": "and gaming forums echoed his exact frustrations."},
        ],
    },
    {
        "block_id": "b005",
        "panel_ids": ["panel_0010"],
        "narration": "Bored out of his mind, he desperately searched the web for a genuine gaming challenge.",
    },
    {
        "block_id": "b006",
        "panel_ids": ["panel_0012", "panel_0014"],
        "narration": "Buried in an obscure review, he found Dungeon and Stone—an unforgiving 2D indie roguelike.",
        "beats": [
            {"beat_id": "b006_0", "panel_id": "panel_0012", "text": "Buried in an obscure review, he found Dungeon and Stone,"},
            {"beat_id": "b006_1", "panel_id": "panel_0014", "text": "an unforgiving 2D indie roguelike."},
        ],
    },
    {
        "block_id": "b007",
        "panel_ids": ["panel_0016", "panel_0017"],
        "narration": "Drawn to its brutal retro aesthetic, he booted up the punishing title on his laptop.",
        "beats": [
            {"beat_id": "b007_0", "panel_id": "panel_0016", "text": "Drawn to its brutal retro aesthetic,"},
            {"beat_id": "b007_1", "panel_id": "panel_0017", "text": "he booted up the punishing title on his laptop."},
        ],
    },
    {
        "block_id": "b008",
        "panel_ids": ["panel_0018", "panel_0019"],
        "narration": "Reviewing the character roster, he locked in the notoriously difficult Barbarian class.",
        "beats": [
            {"beat_id": "b008_0", "panel_id": "panel_0018", "text": "Reviewing the character roster,"},
            {"beat_id": "b008_1", "panel_id": "panel_0019", "text": "he locked in the notoriously difficult Barbarian class."},
        ],
    },
    {
        "block_id": "b009",
        "panel_ids": ["panel_0020"],
        "narration": "He plunged straight into the labyrinth, exploring lethal dungeon floors packed with sadistic traps.",
    },
    {
        "block_id": "b010",
        "panel_ids": ["panel_0021", "panel_0022"],
        "narration": "Totally lost in the grind, he glanced at the clock and realized an entire night had vanished.",
        "beats": [
            {"beat_id": "b010_0", "panel_id": "panel_0021", "text": "Totally lost in the grind,"},
            {"beat_id": "b010_1", "panel_id": "panel_0022", "text": "he glanced at the clock and realized an entire night had vanished."},
        ],
    },
    {
        "block_id": "b011",
        "panel_ids": ["panel_0023", "panel_0025"],
        "narration": "His eyes dilated with manic excitement, even as his party was repeatedly wiped out.",
        "beats": [
            {"beat_id": "b011_0", "panel_id": "panel_0023", "text": "His eyes dilated with manic excitement,"},
            {"beat_id": "b011_1", "panel_id": "panel_0025", "text": "even as his party was repeatedly wiped out."},
        ],
    },
    {
        "block_id": "b012",
        "panel_ids": ["panel_0027", "panel_0028"],
        "narration": "He raged in frustration at another party wipe, quickly ripping off his headphones in embarrassment.",
        "beats": [
            {"beat_id": "b012_0", "panel_id": "panel_0027", "text": "He raged in frustration at another party wipe,"},
            {"beat_id": "b012_1", "panel_id": "panel_0028", "text": "quickly ripping off his headphones in embarrassment."},
        ],
    },
    {
        "block_id": "b013",
        "panel_ids": ["panel_0029"],
        "narration": "Because the game was completely forgotten, no guides existed—igniting his pure gamer stubbornness.",
    },
    {
        "block_id": "b014",
        "panel_ids": ["panel_0032", "panel_0034"],
        "narration": "Through high school, hospital treatments, and military service, he kept playing for nine straight years.",
        "beats": [
            {"beat_id": "b014_0", "panel_id": "panel_0032", "text": "Through high school, hospital treatments, and military service,"},
            {"beat_id": "b014_1", "panel_id": "panel_0034", "text": "he kept playing for nine straight years."},
        ],
    },
    {
        "block_id": "b015",
        "panel_ids": ["panel_0035", "panel_0037"],
        "narration": "Suffering thousands of devastating deaths, he meticulously mapped out every single tile and boss mechanic.",
        "beats": [
            {"beat_id": "b015_0", "panel_id": "panel_0035", "text": "Suffering thousands of devastating deaths,"},
            {"beat_id": "b015_1", "panel_id": "panel_0037", "text": "he meticulously mapped out every single tile and boss mechanic."},
        ],
    },

    # Act 2: Reaching the Final Boss & The Transmigration (p0038 - p0071)
    {
        "block_id": "b016",
        "panel_ids": ["panel_0038", "panel_0039"],
        "narration": "Late into the dark night, a satisfied smirk curled across Hansoo's tired face.",
        "beats": [
            {"beat_id": "b016_0", "panel_id": "panel_0038", "text": "Late into the dark night,"},
            {"beat_id": "b016_1", "panel_id": "panel_0039", "text": "a satisfied smirk curled across Hansoo's tired face."},
        ],
    },
    {
        "block_id": "b017",
        "panel_ids": ["panel_0040", "panel_0041"],
        "narration": "His pixel warrior stood before the legendary tenth floor portal—the final boss room.",
        "beats": [
            {"beat_id": "b017_0", "panel_id": "panel_0040", "text": "His pixel warrior stood before the tenth floor portal,"},
            {"beat_id": "b017_1", "panel_id": "panel_0041", "text": "reaching the mythical final boss room."},
        ],
    },
    {
        "block_id": "b018",
        "panel_ids": ["panel_0042", "panel_0043"],
        "narration": "He threw his arms up cheering wildly, having finally conquered nine years of impossible torment.",
        "beats": [
            {"beat_id": "b018_0", "panel_id": "panel_0042", "text": "He threw his arms up cheering wildly,"},
            {"beat_id": "b018_1", "panel_id": "panel_0043", "text": "having conquered nine years of impossible torment."},
        ],
    },
    {
        "block_id": "b019",
        "panel_ids": ["panel_0044", "panel_0045"],
        "narration": "An eerie prompt popped up on screen, warning that entering meant he could never return to reality.",
        "beats": [
            {"beat_id": "b019_0", "panel_id": "panel_0044", "text": "An eerie prompt popped up on screen,"},
            {"beat_id": "b019_1", "panel_id": "panel_0045", "text": "warning that entering meant he could never return to reality."},
        ],
    },
    {
        "block_id": "b020",
        "panel_ids": ["panel_0046", "panel_0049"],
        "narration": "Laughing it off as dramatic flavor text, he casually clicked yes without a second thought.",
        "beats": [
            {"beat_id": "b020_0", "panel_id": "panel_0046", "text": "Laughing it off as dramatic flavor text,"},
            {"beat_id": "b020_1", "panel_id": "panel_0049", "text": "he casually clicked yes without a second thought."},
        ],
    },
    {
        "block_id": "b021",
        "panel_ids": ["panel_0050", "panel_0054"],
        "narration": "His smile instantly froze in place as the screen glitch announced an unexpected tutorial initiation.",
        "beats": [
            {"beat_id": "b021_0", "panel_id": "panel_0050", "text": "His smile instantly froze in place"},
            {"beat_id": "b021_1", "panel_id": "panel_0054", "text": "as the screen glitch announced an unexpected tutorial initiation."},
        ],
    },
    {
        "block_id": "b022",
        "panel_ids": ["panel_0055", "panel_0056"],
        "narration": "He bolted out of his chair in pure rage, furious at the prospect of restarting from scratch.",
        "beats": [
            {"beat_id": "b022_0", "panel_id": "panel_0055", "text": "He bolted out of his chair in pure rage,"},
            {"beat_id": "b022_1", "panel_id": "panel_0056", "text": "furious at the prospect of restarting from scratch."},
        ],
    },
    {
        "block_id": "b023",
        "panel_ids": ["panel_0057"],
        "narration": "Suddenly, a blinding supernatural vortex ripped open and pulled his soul straight through the monitor.",
    },
    {
        "block_id": "b024",
        "panel_ids": ["panel_0059", "panel_0060"],
        "narration": "He awoke inside a colossal subterranean hall, surrounded by dozens of imposing barbarian giants.",
        "beats": [
            {"beat_id": "b024_0", "panel_id": "panel_0059", "text": "He awoke inside a colossal subterranean hall,"},
            {"beat_id": "b024_1", "panel_id": "panel_0060", "text": "surrounded by dozens of imposing barbarian giants."},
        ],
    },
    {
        "block_id": "b025",
        "panel_ids": ["panel_0062", "panel_0063"],
        "narration": "Flames flickered off stone pillars as a booming tribal voice echoed across the chamber.",
        "beats": [
            {"beat_id": "b025_0", "panel_id": "panel_0062", "text": "Flames flickered off stone pillars"},
            {"beat_id": "b025_1", "panel_id": "panel_0063", "text": "as a booming tribal voice echoed across the chamber."},
        ],
    },
    {
        "block_id": "b026",
        "panel_ids": ["panel_0065", "panel_0067"],
        "narration": "Panic set in as he looked down at his own massive, leather-strapped warrior chest.",
        "beats": [
            {"beat_id": "b026_0", "panel_id": "panel_0065", "text": "Panic set in as he looked down"},
            {"beat_id": "b026_1", "panel_id": "panel_0067", "text": "at his own massive, leather-strapped warrior chest."},
        ],
    },
    {
        "block_id": "b027",
        "panel_ids": ["panel_0068", "panel_0069"],
        "narration": "Clenching his thick, scarred fists, he was stunned to see he had turned into a towering barbarian.",
        "beats": [
            {"beat_id": "b027_0", "panel_id": "panel_0068", "text": "Clenching his thick, scarred fists,"},
            {"beat_id": "b027_1", "panel_id": "panel_0069", "text": "he was stunned to see he had turned into a towering barbarian."},
        ],
    },
    {
        "block_id": "b028",
        "panel_ids": ["panel_0071"],
        "narration": "His fragile human body was gone, replaced by over two meters of pure muscle and bone.",
    },

    # Act 3: Barbarian Customs & The City of Rafdonia (p0072 - p0087)
    {
        "block_id": "b029",
        "panel_ids": ["panel_0072", "panel_0073"],
        "narration": "He stood in rank with the recruits, summoned forward by the fierce barbarian elders.",
        "beats": [
            {"beat_id": "b029_0", "panel_id": "panel_0072", "text": "He stood in rank with the recruits,"},
            {"beat_id": "b029_1", "panel_id": "panel_0073", "text": "summoned forward by the fierce barbarian elders."},
        ],
    },
    {
        "block_id": "b030",
        "panel_ids": ["panel_0074", "panel_0075"],
        "narration": "A warrior gripped a heavy battleaxe while the Chieftain smiled with terrifying bloodlust.",
        "beats": [
            {"beat_id": "b030_0", "panel_id": "panel_0074", "text": "A warrior gripped a heavy battleaxe"},
            {"beat_id": "b030_1", "panel_id": "panel_0075", "text": "while the Chieftain smiled with terrifying bloodlust."},
        ],
    },
    {
        "block_id": "b031",
        "panel_ids": ["panel_0076", "panel_0077"],
        "narration": "The Chieftain bellowed tribal decrees, triggering a rush of foreign memories in Hansoo's head.",
        "beats": [
            {"beat_id": "b031_0", "panel_id": "panel_0076", "text": "The Chieftain bellowed tribal decrees,"},
            {"beat_id": "b031_1", "panel_id": "panel_0077", "text": "triggering a rush of foreign memories in Hansoo's head."},
        ],
    },
    {
        "block_id": "b032",
        "panel_ids": ["panel_0078", "panel_0079"],
        "narration": "He recalled the brutal barbarian initiation, where every coming-of-age youth is cast into the dungeon.",
        "beats": [
            {"beat_id": "b032_0", "panel_id": "panel_0078", "text": "He recalled the brutal barbarian initiation,"},
            {"beat_id": "b032_1", "panel_id": "panel_0079", "text": "where every coming-of-age youth is cast into the dungeon."},
        ],
    },
    {
        "block_id": "b033",
        "panel_ids": ["panel_0081", "panel_0082"],
        "narration": "Survivors earned honor in the city of Rafdonia, while the weak were slaughtered in the dark.",
        "beats": [
            {"beat_id": "b033_0", "panel_id": "panel_0081", "text": "Survivors earned honor in the city of Rafdonia,"},
            {"beat_id": "b033_1", "panel_id": "panel_0082", "text": "while the weak were slaughtered in the dark."},
        ],
    },
    {
        "block_id": "b034",
        "panel_ids": ["panel_0083", "panel_0084"],
        "narration": "The environment matched Dungeon and Stone perfectly, right down to the ominous dungeon portal.",
        "beats": [
            {"beat_id": "b034_0", "panel_id": "panel_0083", "text": "The environment matched Dungeon and Stone perfectly,"},
            {"beat_id": "b034_1", "panel_id": "panel_0084", "text": "right down to the ominous dungeon portal."},
        ],
    },
    {
        "block_id": "b035",
        "panel_ids": ["panel_0087"],
        "narration": "His encyclopedic mastery of game mechanics was now his only hope of making it out alive.",
    },

    # Act 4: The Panicked Recruit & The Brutal Execution (p0089 - p0108)
    {
        "block_id": "b036",
        "panel_ids": ["panel_0089", "panel_0090"],
        "narration": "Right beside him, a red-haired recruit began trembling violently in complete mental collapse.",
        "beats": [
            {"beat_id": "b036_0", "panel_id": "panel_0089", "text": "Right beside him, a red-haired recruit"},
            {"beat_id": "b036_1", "panel_id": "panel_0090", "text": "began trembling violently in complete mental collapse."},
        ],
    },
    {
        "block_id": "b037",
        "panel_ids": ["panel_0091", "panel_0092"],
        "narration": "Hansoo watched with dread as the terrified youth started speaking frantically in Korean.",
        "beats": [
            {"beat_id": "b037_0", "panel_id": "panel_0091", "text": "Hansoo watched with dread"},
            {"beat_id": "b037_1", "panel_id": "panel_0092", "text": "as the terrified youth started speaking frantically in Korean."},
        ],
    },
    {
        "block_id": "b038",
        "panel_ids": ["panel_0094", "panel_0095"],
        "narration": "The Chieftain stepped forward, his eyes burning with lethal fury at the recruit.",
        "beats": [
            {"beat_id": "b038_0", "panel_id": "panel_0094", "text": "The Chieftain stepped forward,"},
            {"beat_id": "b038_1", "panel_id": "panel_0095", "text": "his eyes burning with lethal fury at the recruit."},
        ],
    },
    {
        "block_id": "b039",
        "panel_ids": ["panel_0096", "panel_0097"],
        "narration": "The boy screamed for his mother, unaware that speaking modern words was an unforgivable death sentence.",
        "beats": [
            {"beat_id": "b039_0", "panel_id": "panel_0096", "text": "The boy screamed for his mother,"},
            {"beat_id": "b039_1", "panel_id": "panel_0097", "text": "unaware that speaking modern words was an unforgivable death sentence."},
        ],
    },
    {
        "block_id": "b040",
        "panel_ids": ["panel_0099", "panel_0100"],
        "narration": "As the recruit begged on his knees, the Chieftain raised his colossal execution axe.",
        "beats": [
            {"beat_id": "b040_0", "panel_id": "panel_0099", "text": "As the recruit begged on his knees,"},
            {"beat_id": "b040_1", "panel_id": "panel_0100", "text": "the Chieftain raised his colossal execution axe."},
        ],
    },
    {
        "block_id": "b041",
        "panel_ids": ["panel_0101", "panel_0102"],
        "narration": "In a gruesome blur of steel, the leader severed the boy's head in a spray of scarlet blood.",
        "beats": [
            {"beat_id": "b041_0", "panel_id": "panel_0101", "text": "In a gruesome blur of steel,"},
            {"beat_id": "b041_1", "panel_id": "panel_0102", "text": "the leader severed the boy's head in a spray of scarlet blood."},
        ],
    },
    {
        "block_id": "b042",
        "panel_ids": ["panel_0103", "panel_0105"],
        "narration": "Hansoo froze in cold shock as the headless body collapsed heavily beside his feet.",
        "beats": [
            {"beat_id": "b042_0", "panel_id": "panel_0103", "text": "Hansoo froze in cold shock"},
            {"beat_id": "b042_1", "panel_id": "panel_0105", "text": "as the headless body collapsed heavily beside his feet."},
        ],
    },
    {
        "block_id": "b043",
        "panel_ids": ["panel_0106", "panel_0107"],
        "narration": "Warm blood splattered his face, while the Chieftain calmly bellowed a warning to the crowd.",
        "beats": [
            {"beat_id": "b043_0", "panel_id": "panel_0106", "text": "Warm blood splattered his face,"},
            {"beat_id": "b043_1", "panel_id": "panel_0107", "text": "while the Chieftain calmly bellowed a warning to the crowd."},
        ],
    },
    {
        "block_id": "b044",
        "panel_ids": ["panel_0108"],
        "narration": "With crimson blood dripping down his back, Hansoo grasped the terrifying rules of survival.",
    },

    # Act 5: The Three Laws of Survival & Entering the Dungeon (p0109 - p0127)
    {
        "block_id": "b045",
        "panel_ids": ["panel_0109"],
        "narration": "First law: Transmigrators are feared as evil spirits and hunted down without mercy.",
    },
    {
        "block_id": "b046",
        "panel_ids": ["panel_0110"],
        "narration": "Second law: Revealing modern speech or breaking barbarian customs brings instantaneous execution.",
    },
    {
        "block_id": "b047",
        "panel_ids": ["panel_0111"],
        "narration": "Third law: To survive this brutal nightmare, he must fully become Bjorn, son of Yandel.",
    },
    {
        "block_id": "b048",
        "panel_ids": ["panel_0112", "panel_0113"],
        "narration": "The tribal elders rallied the line forward, demanding savage bravery from every recruit.",
        "beats": [
            {"beat_id": "b048_0", "panel_id": "panel_0112", "text": "The tribal elders rallied the line forward,"},
            {"beat_id": "b048_1", "panel_id": "panel_0113", "text": "demanding savage bravery from every recruit."},
        ],
    },
    {
        "block_id": "b049",
        "panel_ids": ["panel_0114", "panel_0116"],
        "narration": "Warriors stepped into the circle, and Hansoo locked away his terror to stand among them.",
        "beats": [
            {"beat_id": "b049_0", "panel_id": "panel_0114", "text": "Warriors stepped into the circle,"},
            {"beat_id": "b049_1", "panel_id": "panel_0116", "text": "and Hansoo locked away his terror to stand among them."},
        ],
    },
    {
        "block_id": "b050",
        "panel_ids": ["panel_0119", "panel_0120"],
        "narration": "His eyes hardened with savage resolve as he gripped his heavy iron shield with white knuckles.",
        "beats": [
            {"beat_id": "b050_0", "panel_id": "panel_0119", "text": "His eyes hardened with savage resolve"},
            {"beat_id": "b050_1", "panel_id": "panel_0120", "text": "as he gripped his heavy iron shield with white knuckles."},
        ],
    },
    {
        "block_id": "b051",
        "panel_ids": ["panel_0121", "panel_0122"],
        "narration": "The Chieftain roared the final war cry, and Hansoo swallowed hard, letting warrior instincts take over.",
        "beats": [
            {"beat_id": "b051_0", "panel_id": "panel_0121", "text": "The Chieftain roared the final war cry,"},
            {"beat_id": "b051_1", "panel_id": "panel_0122", "text": "and Hansoo swallowed hard, letting warrior instincts take over."},
        ],
    },
    {
        "block_id": "b052",
        "panel_ids": ["panel_0123", "panel_0124"],
        "narration": "The barbarian recruits marched in unison, approaching the towering bonfires of the initiation gate.",
        "beats": [
            {"beat_id": "b052_0", "panel_id": "panel_0123", "text": "The barbarian recruits marched in unison,"},
            {"beat_id": "b052_1", "panel_id": "panel_0124", "text": "approaching the towering bonfires of the initiation gate."},
        ],
    },
    {
        "block_id": "b053",
        "panel_ids": ["panel_0126", "panel_0127"],
        "narration": "Stamping his sandal onto the cold stone, Bjorn glared into the dark labyrinth, ready to conquer.",
        "beats": [
            {"beat_id": "b053_0", "panel_id": "panel_0126", "text": "Stamping his sandal onto the cold stone,"},
            {"beat_id": "b053_1", "panel_id": "panel_0127", "text": "Bjorn glared into the dark labyrinth, ready to conquer."},
        ],
    },
]


def main():
    config = load_config("config/config.yaml")
    desc = load_model(Path("data/chapters/barbarian_ch01/03_descriptions.json"), DescriptionFile)

    blocks = []
    for b in blocks_data:
        beats = [ScriptBeat(**bt) for bt in b.get("beats", [])]
        narration = " ".join(bt.text for bt in beats) if beats else b["narration"]
        blocks.append(
            ScriptBlock(
                block_id=b["block_id"],
                panel_ids=b["panel_ids"],
                narration=narration,
                beats=beats,
            )
        )

    script = ScriptFile(
        chapter_id="barbarian_ch01",
        series="barbarian",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        total_words=sum(b.word_count for b in blocks),
        blocks=blocks,
    )

    report = validate(script, desc, config)
    print("Validation OK:", report.ok)
    print("Problems:", report.problems)
    print("Warnings:", report.warnings)
    print("Total words:", script.total_words)
    print("Total blocks:", len(script.blocks))

    if not report.ok:
        print("Validation failed!")
        return False

    script_path = Path("data/chapters/barbarian_ch01/04_script.json")
    save_model(script, script_path)
    print(f"Saved {len(script.blocks)} blocks ({script.total_words} words) to {script_path}")
    return True


if __name__ == "__main__":
    main()
