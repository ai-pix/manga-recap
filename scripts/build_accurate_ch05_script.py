"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 5.

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
    # --- ACT 1: RESEARCHING THE NUMBER ONE HUNTER (p0001 - p0020) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "A crisp newspaper page reports the mysterious disappearance of the world's number one hunter."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "Marcus Callenberry, known globally as the Blade Saint, has been missing for twenty-two days."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Before the Flame Emperor rose to glory, Marcus was considered humanity's peerless vanguard."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "Gong-ja sips his drink, realizing that right now in this era, Marcus is still the strongest."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "A legendary hunter of his stature undoubtedly possesses an extraordinary S-rank active sword skill."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "A brilliant scheme begins to form in Gong-ja's opportunistic, calculating mind."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "His passive skill allows him to copy any ability from whoever ends his life."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "With the Return Clock keeping his soul immortal, dying has become a mere stepping stone."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "He grips his phone tightly, excited by the prospect of acquiring the Blade Saint's power."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "He dives deep into anonymous hunter forums, searching for information on the eccentric master."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "User rumors claim Marcus belongs to an aristocratic Northern European lineage of warriors."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "Other posts mention his vast personal fortune and an unusual habit of talking to himself."},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "An anonymous commenter claims Marcus acts like he is constantly listening to an invisible companion."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "Gong-ja scoffs at the bizarre rumors, wondering if top rankers are all somewhat crazy."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "He grumbles that it would have been nice if Marcus was as flashy as the late Flame Emperor."},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "A sudden shout echoes across the tavern as an old man snaps at a nearby table."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "Marcus yells into empty air, angrily ordering someone invisible to shut up and leave him be."},
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "Gong-ja recoils in shock, watching the elder argue furiously with completely empty space."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "The rumors were true: the greatest swordsman alive genuinely bickers with unseen phantoms."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "He reads another forum warning flagged with a red alert: Taboo subjects regarding the Blade Saint."},

    # --- ACT 2: THE FORBIDDEN TABOO & THE TAIL (p0021 - p0045) ---
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "The post sternly warns hunters never to bring up the topic of Marcus's deceased grandchildren."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "Anyone foolish enough to mention his family risks immediate, decapitating wrath."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "An archived incident describes a group of arrogant rankers picking a fight with the old man."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "They claimed territorial ownership over a hunting ground, rudely mocking Marcus's age."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "When one thug brought up his family, Marcus drew his steel and severed the man's throat in seconds."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "The forum thread dissolves into fierce arguments, with some accusing the poster of spreading slander."},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "Yet the warning remains clear: disrespecting Marcus's fallen bloodline is an instant death sentence."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "Gong-ja closes his phone with a wry grin, feeling like he just unlocked an easy cheat code."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "All he has to do is provoke Marcus with a rude comment, get sliced, and copy his sword mastery."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "It sounds almost ridiculously simple: a quick death, a stolen skill, and an instant time rewind."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "Marcus sets his empty glass down, pulls his blue hat low, and steps out into the night."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "Gong-ja quickly tosses a handful of coins onto the wooden counter and follows him outside."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "He steps into the cool evening air, keeping a steady distance behind the distinguished figure."},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "Marcus strolls through Babylon's winding alleys, his hands tucked casually in his coat pockets."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "Gong-ja trails him carefully, ducking behind stone corners whenever the elder pauses."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "The city streets slowly give way to overgrown outskirts bathed in pale silver moonlight."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "They enter an open, desolate field of tall grass swaying gently in the night breeze."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "The silence grows heavy, punctuated only by the chirping of crickets and rustling weeds."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "Marcus suddenly halts in the middle of the field, his back turned toward Gong-ja."},
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "Gong-ja freezes in place, ducking low to keep his silhouette hidden within the brush."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "The old master speaks with chilling calm: How much longer do you intend to follow me?"},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "Gong-ja's heart skips a beat as he realizes he was spotted from the very beginning."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "Marcus turns slowly, his piercing eyes glowing with lethal, sharp intensity."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "He demands the shadow step out into the clearing and state his true business."},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "Gong-ja stands up sheepishly, raising both hands to play the harmless, clumsy fool."},

    # --- ACT 3: THE FATAL MISUNDERSTANDING (p0046 - p0075) ---
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "Gong-ja stammers an apology, claiming he was just lost and admiring the scenery."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "Marcus doesn't buy a single syllable, observing the youth's posture with eagle-eyed scrutiny."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "He remarks that Gong-ja's footsteps were practically soundless until he entered the grass."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "Only an elite, first-class assassin could track the Blade Saint this far without raising suspicion."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "Gong-ja's jaw drops: An assassin? He is literally just an F-rank bum in cheap sneakers!"},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "He vehemently denies it, insisting that he doesn't have a lethal bone in his body."},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "Marcus sneers in cold contempt, unimpressed by the supposed rookie's acting performance."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "He demands to know which rival guild dispatched an assassin to eliminate him in the dark."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "Gong-ja mentally rejoices: if Marcus attacks on his own, there's no need to mention grandchildren!"},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "Getting killed while playing the victim will net him an S-rank skill without moral guilt."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "He pleads for his life, hoping Marcus will deliver a swift, decisive execution strike."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "Marcus reaches toward his side, fingers lightly brushing against his scabbard."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "A brilliant aura of pale blue mana ignites along the length of his unsheathed blade."},
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "The sheer pressure radiating from the sword causes the surrounding tall grass to part."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "Gong-ja feels the suffocating aura of a true master, marveling at the sheer beauty of the weapon."},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "Marcus warns him that lies are useless, revealing that he possesses an infallible sensory ability."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "Among his arsenal of skills is a divine gaze that reveals a person's exact kill count."},
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "The number of sentient lives taken floats visibly above every hunter's forehead in his sight."},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "Gong-ja pauses, doing quick mental inventory of his own track record."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "He only killed one person: the arrogant Flame Emperor he ambushed on the sixth floor."},
    {"block_id": "b066", "panel_ids": ["panel_0066"], "narration": "Marcus will see the number one, assume it was self-defense, and perhaps hesitate."},
    {"block_id": "b067", "panel_ids": ["panel_0067"], "narration": "Gong-ja prepares to explain that he took down a dangerous villain for the greater good."},
    {"block_id": "b068", "panel_ids": ["panel_0068"], "narration": "He looks up at Marcus, ready to plead his righteous justification."},
    {"block_id": "b069", "panel_ids": ["panel_0069"], "narration": "Marcus's eyes narrow into slits of burning hatred as he gazes above Gong-ja's head."},
    {"block_id": "b070", "panel_ids": ["panel_0070"], "narration": "At first, the glowing red numeral one appears in the air, pulsing faintly."},
    {"block_id": "b071", "panel_ids": ["panel_0071"], "narration": "Then, the digital system font violently shifts, expanding with horrifying speed."},
    {"block_id": "b072", "panel_ids": ["panel_0072"], "narration": "The digits tumble and multiply, glowing with the blood-red luminescence of a cosmic atrocity."},
    {"block_id": "b073", "panel_ids": ["panel_0073"], "narration": "Marcus recoils in absolute disgust, stepping back with a look of pure nausea."},
    {"block_id": "b074", "panel_ids": ["panel_0074"], "narration": "He points his trembling blade at Gong-ja, his voice shaking with righteous fury."},
    {"block_id": "b075", "panel_ids": ["panel_0075"], "narration": "He shouts into the night: How dare you utter a single word, you sickening monster!"},

    # --- ACT 4: THE 4,091 SIN & THE BLADE SAINT'S WRATH (p0076 - p0100) ---
    {"block_id": "b076", "panel_ids": ["panel_0076"], "narration": "Gong-ja freezes, bewildered by the old warrior's visceral revulsion."},
    {"block_id": "b077", "panel_ids": ["panel_0077"], "narration": "Marcus proclaims that he has walked through blood and war, but has never met such evil."},
    {"block_id": "b078", "panel_ids": ["panel_0078"], "narration": "He reads the glowing scarlet number hovering directly over Gong-ja's crown."},
    {"block_id": "b079", "panel_ids": ["panel_0079"], "narration": "Four thousand, ninety-one! Over four thousand innocent lives extinguished by his hands!"},
    {"block_id": "b080", "panel_ids": ["panel_0080"], "narration": "The number floats in blazing crimson numerals: 4,091."},
    {"block_id": "b081", "panel_ids": ["panel_0081"], "narration": "Gong-ja's mind goes completely blank as the mathematical truth hits him like lightning."},
    {"block_id": "b082", "panel_ids": ["panel_0082"], "narration": "One kill was Yoo Soo-ha. The other four thousand and ninety kills were his own suicides!"},
    {"block_id": "b083", "panel_ids": ["panel_0083"], "narration": "The tower's kill tracker registered every single self-inflicted death as a murder!"},
    {"block_id": "b084", "panel_ids": ["panel_0084"], "narration": "In the eyes of the cosmos, Kim Gong-ja is a demonic butcher with four thousand bodies to his name."},
    {"block_id": "b085", "panel_ids": ["panel_0085"], "narration": "To Marcus, this unassuming youth is the most prolific serial killer in human history."},
    {"block_id": "b086", "panel_ids": ["panel_0086"], "narration": "Gong-ja stammers frantically, waving his hands to explain the cosmic misunderstanding."},
    {"block_id": "b087", "panel_ids": ["panel_0087"], "narration": "How does anyone explain that four thousand of those corpses were literally himself?"},
    {"block_id": "b088", "panel_ids": ["panel_0088"], "narration": "Marcus refuses to listen, brandishing his blade with unwavering moral disgust."},
    {"block_id": "b089", "panel_ids": ["panel_0089"], "narration": "He demands to know if the Black Dragon Witch contracted such a demon to conquer Babylon."},
    {"block_id": "b090", "panel_ids": ["panel_0090"], "narration": "Gong-ja realizes with rising panic that this is no longer a game of copying skills."},
    {"block_id": "b091", "panel_ids": ["panel_0091"], "narration": "As long as Marcus possesses this kill-count tracker, he will see four thousand murders every time."},
    {"block_id": "b092", "panel_ids": ["panel_0092"], "narration": "Even if Gong-ja resets the day, Marcus will instantly recognize him as a demonic mass murderer."},
    {"block_id": "b093", "panel_ids": ["panel_0093"], "narration": "There can be no negotiations, no bargains, and no peaceful encounters between them."},
    {"block_id": "b094", "panel_ids": ["panel_0094"], "narration": "Every single time their paths cross, the Blade Saint will hunt him down to the ends of the Earth."},
    {"block_id": "b095", "panel_ids": ["panel_0095"], "narration": "Marcus takes a deep stance, his entire body radiating an overwhelming tempest of sword intent."},
    {"block_id": "b096", "panel_ids": ["panel_0096"], "narration": "He vows to use all of his strength to purge this unforgivable devil from existence."},
    {"block_id": "b097", "panel_ids": ["panel_0097"], "narration": "He leaps into the night air, raising his glowing blade high above his head."},
    {"block_id": "b098", "panel_ids": ["panel_0098"], "narration": "A colossal arc of blinding white sword energy splits the sky in two with thunderous force."},
    {"block_id": "b099", "panel_ids": ["panel_0099"], "narration": "The divine strike descends upon Gong-ja, threatening to sever his soul from reality itself."},
    {"block_id": "b100", "panel_ids": ["panel_0100"], "narration": "Kim Gong-ja grits his teeth, determined to conquer the Blade Saint no matter how many deaths it takes."},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch05")
    desc_path = ch_dir / "03_descriptions.json"
    script_path = ch_dir / "04_script.json"

    desc_file = load_model(desc_path, DescriptionFile)

    # Assemble ScriptFile
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
        chapter_id="sss-class-revival-hunter/ch05",
        title="SSS-Class Revival Hunter - Chapter 5",
        series="sss-class-revival-hunter",
        created_at=datetime.now(timezone.utc).isoformat(),
        model="agent",
        target_words=len(script_blocks) * 12,
        blocks=script_blocks,
    )

    # Validate against pipeline gates
    cfg = load_config()
    report = validate(script_file, desc_file, cfg)

    # Save 04_script.json
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_file.model_dump_json(indent=2))

    alt_script_path = Path("data/chapters/revival_hunter_ch05/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 05 Script ===")
    print(f"Total Blocks: {len(script_blocks)}")
    print(f"Total Spoken Words: {script_file.total_words}")
    print(f"Estimated Narration Time: ~{script_file.total_words / 150:.1f} minutes")
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
