"""Build, validate, and save the accurate, emotional, humorous recap script for barbarian_ch01.

Faithfully covers every single plot detail, character reaction, dialogue line,
and lore element from the manga panels while infusing expressive emotion,
tactical humor, and seamless storytelling across all 94 authentic art panels.
"""

from __future__ import annotations

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
    # --- ACT 1: THE HOSPITALIZED GAMER & THE 0-STAR INDIE OBSESSION ---
    {
        "block_id": "b001",
        "panel_ids": ["panel_0001"],
        "narration": "Confined to a sterile hospital bed for years, gaming wasn't just a hobby for Hansoo—it was his entire life.",
    },
    {
        "block_id": "b002",
        "panel_ids": ["panel_0002"],
        "narration": "Day after day, he stared intently at his console, desperately seeking any shred of genuine excitement.",
    },
    {
        "block_id": "b003",
        "panel_ids": ["panel_0003", "panel_0005"],
        "narration": "Another Game Over flashed because his idiot AI healer healed the enemy, and he slammed the console across the table in pure rage!",
        "beats": [
            {"beat_id": "b003_0", "panel_id": "panel_0003", "text": "Another Game Over flashed because his idiot AI healer healed the enemy,"},
            {"beat_id": "b003_1", "panel_id": "panel_0005", "text": "and he slammed the console across the table in pure rage!"},
        ],
    },
    {
        "block_id": "b004",
        "panel_ids": ["panel_0006", "panel_0008"],
        "narration": "Modern games had devolved into generic copycats, with forums flooded with gamers complaining about the total lack of depth.",
        "beats": [
            {"beat_id": "b004_0", "panel_id": "panel_0006", "text": "Modern games had devolved into generic copycats,"},
            {"beat_id": "b004_1", "panel_id": "panel_0008", "text": "with forums flooded with gamers complaining about the total lack of depth."},
        ],
    },
    {
        "block_id": "b005",
        "panel_ids": ["panel_0010"],
        "narration": "Slumped over his hospital tray, he sighed deeply, wondering if a truly original game even existed anymore.",
    },
    {
        "block_id": "b006",
        "panel_ids": ["panel_0012", "panel_0014"],
        "narration": "That's when he spotted a zero-star review warning: Not Recommended! Dungeon and Stone—forces players to do one hundred percent of the work.",
        "beats": [
            {"beat_id": "b006_0", "panel_id": "panel_0012", "text": "That's when he spotted a zero-star review warning: Not Recommended!"},
            {"beat_id": "b006_1", "panel_id": "panel_0014", "text": "Dungeon and Stone—an indie roguelike that forces players to do all the work."},
        ],
    },
    {
        "block_id": "b007",
        "panel_ids": ["panel_0016", "panel_0017"],
        "narration": "Booting it up on his laptop, he groaned seeing it was English only, but since it was free, he decided to give it a shot.",
        "beats": [
            {"beat_id": "b007_0", "panel_id": "panel_0016", "text": "Booting it up on his laptop, he groaned seeing it was English only,"},
            {"beat_id": "b007_1", "panel_id": "panel_0017", "text": "but since it was free, he decided to give it a quick shot."},
        ],
    },
    {
        "block_id": "b008",
        "panel_ids": ["panel_0018", "panel_0019"],
        "narration": "Looking over the character select, he shrugged and picked Barbarian, thinking he'd only play for ten minutes anyway.",
        "beats": [
            {"beat_id": "b008_0", "panel_id": "panel_0018", "text": "Looking over the character select,"},
            {"beat_id": "b008_1", "panel_id": "panel_0019", "text": "he shrugged and picked Barbarian, thinking he'd only mess around for ten minutes."},
        ],
    },
    {
        "block_id": "b009",
        "panel_ids": ["panel_0020"],
        "narration": "He plunged into the 2D grid, learning the hard way that every room was packed with lethal traps and sadistic monsters.",
    },
    {
        "block_id": "b010",
        "panel_ids": ["panel_0021", "panel_0022"],
        "narration": "Engrossed in the combat, he suddenly glanced at the hospital clock and gasped—an entire night had completely vanished!",
        "beats": [
            {"beat_id": "b010_0", "panel_id": "panel_0021", "text": "Completely absorbed in the tactical combat,"},
            {"beat_id": "b010_1", "panel_id": "panel_0022", "text": "he glanced at the clock and gasped—an entire night had completely vanished!"},
        ],
    },
    {
        "block_id": "b011",
        "panel_ids": ["panel_0023", "panel_0025"],
        "narration": "His pupils dilated with sheer excitement, even as his party was brutally wiped out yet again.",
        "beats": [
            {"beat_id": "b011_0", "panel_id": "panel_0023", "text": "His pupils dilated with unhinged excitement,"},
            {"beat_id": "b011_1", "panel_id": "panel_0025", "text": "even as his pixel barbarian lay butchered on the dungeon floor."},
        ],
    },
    {
        "block_id": "b012",
        "panel_ids": ["panel_0027", "panel_0028"],
        "narration": "He screamed in fury after dying to stupid priest AI, only for the angry head nurse to barge in and yell at him to shut up!",
        "beats": [
            {"beat_id": "b012_0", "panel_id": "panel_0027", "text": "He screamed in fury after another wipe, only for the head nurse to barge in and yell at him!"},
            {"beat_id": "b012_1", "panel_id": "panel_0028", "text": "He sheepishly yanked off his headphones, apologizing with red cheeks."},
        ],
    },
    {
        "block_id": "b013",
        "panel_ids": ["panel_0029"],
        "narration": "Because zero tutorials existed in Korean or English, pure unadulterated gamer spite took over his soul.",
    },
    {
        "block_id": "b014",
        "panel_ids": ["panel_0032", "panel_0034"],
        "narration": "Through hospital stays, public service duty, college graduation, and soul-crushing job commutes, he kept grinding for nine straight years!",
        "beats": [
            {"beat_id": "b014_0", "panel_id": "panel_0032", "text": "Through hospital stays, public service, college graduation, and job commutes,"},
            {"beat_id": "b014_1", "panel_id": "panel_0034", "text": "he kept grinding Dungeon and Stone for nine relentless years!"},
        ],
    },
    {
        "block_id": "b015",
        "panel_ids": ["panel_0035", "panel_0037"],
        "narration": "Dying thousands of times, he memorized every single pixel, trap coordinate, and monster pattern across all nine floors.",
        "beats": [
            {"beat_id": "b015_0", "panel_id": "panel_0035", "text": "Dying thousands of agonizing deaths,"},
            {"beat_id": "b015_1", "panel_id": "panel_0037", "text": "he memorized every single pixel, trap coordinate, and boss pattern across all nine floors."},
        ],
    },

    # --- ACT 2: THE 10TH FLOOR BOSS ROOM & THE DEVELOPER'S CRUEL TROLL ---
    {
        "block_id": "b016",
        "panel_ids": ["panel_0038", "panel_0039"],
        "narration": "Late in the dark, a manic grin spread across his face as he stared at his monitor with an energy drink in hand.",
        "beats": [
            {"beat_id": "b016_0", "panel_id": "panel_0038", "text": "Late in the dark, a manic grin spread across his face"},
            {"beat_id": "b016_1", "panel_id": "panel_0039", "text": "as he stared at his glowing monitor with an energy drink in hand."},
        ],
    },
    {
        "block_id": "b017",
        "panel_ids": ["panel_0040", "panel_0041"],
        "narration": "His pixel warrior stood before the mythical Gate of the Abyss—the final boss room that no player on Earth had ever reached!",
        "beats": [
            {"beat_id": "b017_0", "panel_id": "panel_0040", "text": "His pixel warrior stood before the mythical Gate of the Abyss,"},
            {"beat_id": "b017_1", "panel_id": "panel_0041", "text": "the final boss room that no player on Earth had ever reached!"},
        ],
    },
    {
        "block_id": "b018",
        "panel_ids": ["panel_0042", "panel_0043"],
        "narration": "Hansoo threw his arms up cheering with tears streaming down his face: Did you see that, you bastards?! I sacrificed my entire twenties for this!",
        "beats": [
            {"beat_id": "b018_0", "panel_id": "panel_0042", "text": "Hansoo threw his arms up cheering wildly: Did you see that, you bastards?!"},
            {"beat_id": "b018_1", "panel_id": "panel_0043", "text": "Tears streamed down his face as he cried: Nine years! I sacrificed my twenties for this!"},
        ],
    },
    {
        "block_id": "b019",
        "panel_ids": ["panel_0044", "panel_0045"],
        "narration": "He clicked yes to enter, but an eerie warning popped up asking: You might never come back. Will you really enter?",
        "beats": [
            {"beat_id": "b019_0", "panel_id": "panel_0044", "text": "He enthusiastically clicked yes to enter the boss room,"},
            {"beat_id": "b019_1", "panel_id": "panel_0045", "text": "but an eerie prompt warned: You might never come back. Will you really enter?"},
        ],
    },
    {
        "block_id": "b020",
        "panel_ids": ["panel_0046", "panel_0049"],
        "narration": "Laughing it off as typical edgy indie flavor text, he clicked yes and kicked back in his chair to analyze boss patterns.",
        "beats": [
            {"beat_id": "b020_0", "panel_id": "panel_0046", "text": "Laughing it off as typical edgy indie developer humor, he clicked yes,"},
            {"beat_id": "b020_1", "panel_id": "panel_0049", "text": "kicking back in his chair to prepare for the boss attack patterns."},
        ],
    },
    {
        "block_id": "b021",
        "panel_ids": ["panel_0050", "panel_0054"],
        "narration": "His smug smile instantly shattered when the screen flashed with the message: Tutorial Complete!",
        "beats": [
            {"beat_id": "b021_0", "panel_id": "panel_0050", "text": "His smug smile instantly shattered into bewildered shock"},
            {"beat_id": "b021_1", "panel_id": "panel_0054", "text": "when the screen flashed with the horrifying words: Tutorial Complete!"},
        ],
    },
    {
        "block_id": "b022",
        "panel_ids": ["panel_0055", "panel_0056"],
        "narration": "He leaped out of his chair screaming in utter betrayal: Wait, this is in Korean?! I suffered through English patch notes for nine whole years?!",
        "beats": [
            {"beat_id": "b022_0", "panel_id": "panel_0055", "text": "He leaped out of his chair screaming in utter betrayal: Wait, this is in Korean?!"},
            {"beat_id": "b022_1", "panel_id": "panel_0056", "text": "I had to suffer through a dictionary for nine years, and the game was Korean all along?!"},
        ],
    },
    {
        "block_id": "b023",
        "panel_ids": ["panel_0057"],
        "narration": "Before he could sue the developer, a blinding blue vortex erupted from the screen, pulling him headfirst into the void!",
    },

    # --- ACT 3: AWAKENING AS A MASSIVE BARBARIAN RECRUIT ---
    {
        "block_id": "b024",
        "panel_ids": ["panel_0059", "panel_0060"],
        "narration": "He opened his eyes in a massive subterranean stone hall, surrounded by dozens of towering, half-naked barbarians holding giant weapons!",
        "beats": [
            {"beat_id": "b024_0", "panel_id": "panel_0059", "text": "He opened his eyes in a massive subterranean stone hall,"},
            {"beat_id": "b024_1", "panel_id": "panel_0060", "text": "surrounded by dozens of towering, half-naked barbarians holding giant weapons!"},
        ],
    },
    {
        "block_id": "b025",
        "panel_ids": ["panel_0062", "panel_0063"],
        "narration": "Torches blazed as an imposing bearded Chieftain bellowed across the hall in a guttural language Hansoo somehow understood fluently.",
        "beats": [
            {"beat_id": "b025_0", "panel_id": "panel_0062", "text": "Torches blazed against ancient carved pillars"},
            {"beat_id": "b025_1", "panel_id": "panel_0063", "text": "as an imposing bearded Chieftain bellowed in a tongue Hansoo somehow understood fluently."},
        ],
    },
    {
        "block_id": "b026",
        "panel_ids": ["panel_0065", "panel_0067"],
        "narration": "Cold sweat poured down his face as he looked down, realizing his frail gamer body was completely gone.",
        "beats": [
            {"beat_id": "b026_0", "panel_id": "panel_0065", "text": "Cold sweat poured down his face as he nervously touched his cheek,"},
            {"beat_id": "b026_1", "panel_id": "panel_0067", "text": "staring down at massive, leather-strapped warrior pecs and bulging biceps."},
        ],
    },
    {
        "block_id": "b027",
        "panel_ids": ["panel_0068", "panel_0069"],
        "narration": "He clenched a scarred, calloused fist in awe—he had transmigrated into a two-meter slab of barbarian muscle wearing a fur loincloth!",
        "beats": [
            {"beat_id": "b027_0", "panel_id": "panel_0068", "text": "He clenched a scarred, calloused fist in utter disbelief—"},
            {"beat_id": "b027_1", "panel_id": "panel_0069", "text": "he had turned into a two-meter slab of barbarian muscle wearing a fur loincloth!"},
        ],
    },
    {
        "block_id": "b028",
        "panel_ids": ["panel_0071"],
        "narration": "His jaw dropped as the terrifying truth settled in: he had literally become the Barbarian character from his game!",
    },

    # --- ACT 4: THE TRIBAL CEREMONY & THE CITY OF RAFDONIA ---
    {
        "block_id": "b029",
        "panel_ids": ["panel_0072", "panel_0073"],
        "narration": "He stood rigidly in line as young recruits were called forward one by one to face the terrifying tribal leadership.",
        "beats": [
            {"beat_id": "b029_0", "panel_id": "panel_0072", "text": "He stood rigidly in line as a smug recruit pushed past him,"},
            {"beat_id": "b029_1", "panel_id": "panel_0073", "text": "stepping forward before the terrifying barbarian elders."},
        ],
    },
    {
        "block_id": "b030",
        "panel_ids": ["panel_0074", "panel_0075"],
        "narration": "The blond youth picked up a double-headed battleaxe, and the Chieftain beamed with savage pride: Great choice, young warrior!",
        "beats": [
            {"beat_id": "b030_0", "panel_id": "panel_0074", "text": "The blond youth hoisted a heavy double-headed battleaxe,"},
            {"beat_id": "b030_1", "panel_id": "panel_0075", "text": "and the Chieftain beamed with savage pride: Great choice, young warrior!"},
        ],
    },
    {
        "block_id": "b031",
        "panel_ids": ["panel_0076", "panel_0077"],
        "narration": "The Chieftain roared the next recruit's name, triggering a flood of foreign memories into Hansoo's pounding skull.",
        "beats": [
            {"beat_id": "b031_0", "panel_id": "panel_0076", "text": "The Chieftain roared the next recruit's name,"},
            {"beat_id": "b031_1", "panel_id": "panel_0077", "text": "triggering a flood of foreign barbarian memories into Hansoo's pounding skull."},
        ],
    },
    {
        "block_id": "b032",
        "panel_ids": ["panel_0078", "panel_0079"],
        "narration": "He remembered the tribal custom: every coming-of-age barbarian must choose a weapon and survive the lethal labyrinth.",
        "beats": [
            {"beat_id": "b032_0", "panel_id": "panel_0078", "text": "He recognized the custom: recruits chose swords or spears,"},
            {"beat_id": "b032_1", "panel_id": "panel_0079", "text": "preparing to be cast into the unforgiving labyrinth for their initiation rite."},
        ],
    },
    {
        "block_id": "b033",
        "panel_ids": ["panel_0081", "panel_0082"],
        "narration": "Those who survived would earn true glory and citizenship in the grand city of Rafdonia, while failures were devoured by beasts.",
        "beats": [
            {"beat_id": "b033_0", "panel_id": "panel_0081", "text": "Those who survived earned citizenship in the grand city of Rafdonia,"},
            {"beat_id": "b033_1", "panel_id": "panel_0082", "text": "while failures were simply devoured by dungeon beasts in the dark."},
        ],
    },
    {
        "block_id": "b034",
        "panel_ids": ["panel_0083", "panel_0084"],
        "narration": "The architecture, the portals, the weapon tiers—everything matched Dungeon and Stone down to the exact mechanic!",
        "beats": [
            {"beat_id": "b034_0", "panel_id": "panel_0083", "text": "The architecture, the lore, the weapon stats—"},
            {"beat_id": "b034_1", "panel_id": "panel_0084", "text": "everything matched Dungeon and Stone down to the exact mechanic!"},
        ],
    },
    {
        "block_id": "b035",
        "panel_ids": ["panel_0087"],
        "narration": "His nine years of encyclopedic game knowledge were no longer useless nerd trivia—they were his literal lifeline.",
    },

    # --- ACT 5: THE CLUELESS RECRUIT & THE BRUTAL EXECUTION ---
    {
        "block_id": "b036",
        "panel_ids": ["panel_0089", "panel_0090"],
        "narration": "Suddenly, a red-haired recruit beside him began hyperventilating in sheer panic, shaking like an autumn leaf.",
        "beats": [
            {"beat_id": "b036_0", "panel_id": "panel_0089", "text": "Suddenly, a red-haired recruit beside him began hyperventilating,"},
            {"beat_id": "b036_1", "panel_id": "panel_0090", "text": "clutching his chest in sheer panic and shaking like an autumn leaf."},
        ],
    },
    {
        "block_id": "b037",
        "panel_ids": ["panel_0091", "panel_0092"],
        "narration": "Hansoo watched in horror as the idiot recruit blurted out in fluent Korean: Wait... Dungeon and Stone?! Why am I here?!",
        "beats": [
            {"beat_id": "b037_0", "panel_id": "panel_0091", "text": "Hansoo's eyes widened with dread as the idiot recruit"},
            {"beat_id": "b037_1", "panel_id": "panel_0092", "text": "blurted out in fluent Korean: Wait... Dungeon and Stone?! Why am I here?!"},
        ],
    },
    {
        "block_id": "b038",
        "panel_ids": ["panel_0094", "panel_0095"],
        "narration": "The entire hall went dead silent as the Chieftain slowly turned, his eyes glowing with murderous, demonic bloodlust!",
        "beats": [
            {"beat_id": "b038_0", "panel_id": "panel_0094", "text": "The entire hall went dead silent as the Chieftain loomed over them,"},
            {"beat_id": "b038_1", "panel_id": "panel_0095", "text": "his eyes burning with murderous, demonic bloodlust: Who opened their mouth?!"},
        ],
    },
    {
        "block_id": "b039",
        "panel_ids": ["panel_0096", "panel_0097"],
        "narration": "Hansoo sweated bullets screaming internally: Do not look at me! It was this brainless fool beside me!",
        "beats": [
            {"beat_id": "b039_0", "panel_id": "panel_0096", "text": "Hansoo sweated bullets screaming internally: Do not look at me!"},
            {"beat_id": "b039_1", "panel_id": "panel_0097", "text": "He glared down at the shivering boy, praying the warlord wouldn't cleave them both."},
        ],
    },
    {
        "block_id": "b040",
        "panel_ids": ["panel_0099", "panel_0100"],
        "narration": "The clueless recruit looked up and actually asked the towering warlord: You mean... this is Dungeon and Stone?",
        "beats": [
            {"beat_id": "b040_0", "panel_id": "panel_0099", "text": "The clueless recruit looked up trembling,"},
            {"beat_id": "b040_1", "panel_id": "panel_0100", "text": "and actually asked the towering warlord: You mean... this is Dungeon and Stone?"},
        ],
    },
    {
        "block_id": "b041",
        "panel_ids": ["panel_0101", "panel_0102"],
        "narration": "The Chieftain coldly growled: What about it—and cleaved the boy's head clean off in a horrific spray of crimson!",
        "beats": [
            {"beat_id": "b041_0", "panel_id": "panel_0101", "text": "The Chieftain coldly growled: What about it—"},
            {"beat_id": "b041_1", "panel_id": "panel_0102", "text": "and swung his massive axe, decapitating the boy in a horrific explosion of blood!"},
        ],
    },
    {
        "block_id": "b042",
        "panel_ids": ["panel_0103", "panel_0105"],
        "narration": "Hansoo froze in paralyzed terror as the decapitated body collapsed with a thud right against his feet!",
        "beats": [
            {"beat_id": "b042_0", "panel_id": "panel_0103", "text": "Hansoo froze in paralyzed terror with eyes wide,"},
            {"beat_id": "b042_1", "panel_id": "panel_0105", "text": "watching the headless body collapse with a wet thud against his feet."},
        ],
    },
    {
        "block_id": "b043",
        "panel_ids": ["panel_0106", "panel_0107"],
        "narration": "Warm blood dripped down his face, while the Chieftain roared: Orm was possessed by an Evil Spirit! Erase his words from your minds!",
        "beats": [
            {"beat_id": "b043_0", "panel_id": "panel_0106", "text": "Warm blood dripped down his face, while the Chieftain roared:"},
            {"beat_id": "b043_1", "panel_id": "panel_0107", "text": "Orm was possessed by an Evil Spirit! Erase everything he said from your memories!"},
        ],
    },
    {
        "block_id": "b044",
        "panel_ids": ["panel_0108"],
        "narration": "Blood trickled down Hansoo's back as the horrific reality sank in: one wrong syllable, and his head rolls next.",
    },

    # --- ACT 6: THE THREE LAWS OF SURVIVAL & THE ULTIMATE NAME GAMBLE ---
    {
        "block_id": "b045",
        "panel_ids": ["panel_0109"],
        "narration": "Rule Number One: Transmigrated players who enter the game are branded as Evil Spirits and purged without mercy.",
    },
    {
        "block_id": "b046",
        "panel_ids": ["panel_0110"],
        "narration": "Rule Number Two: Revealing modern knowledge, speaking Korean, or breaking character means instant decapitation.",
    },
    {
        "block_id": "b047",
        "panel_ids": ["panel_0111"],
        "narration": "Rule Number Three: To survive, he had to bury his gamer identity and become a bloodthirsty barbarian down to his marrow.",
    },
    {
        "block_id": "b048",
        "panel_ids": ["panel_0112", "panel_0113"],
        "narration": "The elders shouted for the ceremony to proceed, but Hansoo realized a fatal problem: the game never told him his name!",
        "beats": [
            {"beat_id": "b048_0", "panel_id": "panel_0112", "text": "The Chieftain barked for the ceremony to continue with a corpse on the floor,"},
            {"beat_id": "b048_1", "panel_id": "panel_0113", "text": "but Hansoo realized a fatal dilemma: the game never gave him his barbarian name!"},
        ],
    },
    {
        "block_id": "b049",
        "panel_ids": ["panel_0114", "panel_0116"],
        "narration": "Recruits stepped forward as names were called. If his name was called and he stayed still, he died; if he stepped for the wrong name, he died!",
        "beats": [
            {"beat_id": "b049_0", "panel_id": "panel_0114", "text": "Recruits stepped forward as names were bellowed down the line."},
            {"beat_id": "b049_1", "panel_id": "panel_0116", "text": "If his name was called and he didn't move, he died; if he answered wrong, he died!"},
        ],
    },
    {
        "block_id": "b050",
        "panel_ids": ["panel_0119", "panel_0120"],
        "narration": "Sweating profusely, he hatched a desperate gamble: wait exactly two seconds after each call. If nobody moves, it must be him!",
        "beats": [
            {"beat_id": "b050_0", "panel_id": "panel_0119", "text": "Sweating profusely, he hatched a desperate gamble:"},
            {"beat_id": "b050_1", "panel_id": "panel_0120", "text": "wait exactly two seconds after each name. If nobody else steps forward, it has to be him!"},
        ],
    },
    {
        "block_id": "b051",
        "panel_ids": ["panel_0121", "panel_0122"],
        "narration": "The Chieftain bellowed: Jandel's son, Bjorn! Hansoo swallowed hard, counting the agonizing seconds in his head: One... Two...",
        "beats": [
            {"beat_id": "b051_0", "panel_id": "panel_0121", "text": "The Chieftain bellowed: Jandel's son, Bjorn!"},
            {"beat_id": "b051_1", "panel_id": "panel_0122", "text": "Hansoo swallowed hard, counting the agonizing seconds in his head: One... Two..."},
        ],
    },
    {
        "block_id": "b052",
        "panel_ids": ["panel_0123", "panel_0124"],
        "narration": "The entire line stood motionless under the flickering bonfires, with every eye waiting for someone to claim the name.",
        "beats": [
            {"beat_id": "b052_0", "panel_id": "panel_0123", "text": "The recruits stood completely motionless,"},
            {"beat_id": "b052_1", "panel_id": "panel_0124", "text": "under the flickering bonfires of the initiation grounds."},
        ],
    },
    {
        "block_id": "b053",
        "panel_ids": ["panel_0126", "panel_0127"],
        "narration": "Stamping his leather sandal into the dust, he glared forward with ferocious resolve: Then that's my name! Bjorn, son of Yandel... probably!",
        "beats": [
            {"beat_id": "b053_0", "panel_id": "panel_0126", "text": "Stamping his leather sandal into the dust,"},
            {"beat_id": "b053_1", "panel_id": "panel_0127", "text": "he glared forward with ferocious resolve: Then that's my name! Bjorn, son of Yandel... probably!"},
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
    print(f"Successfully saved {len(script.blocks)} blocks ({script.total_words} words) to {script_path}")
    return True


if __name__ == "__main__":
    main()
