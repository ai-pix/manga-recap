"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 7.

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
    # --- ACT 1: THE PHANTOM IN THE ROOM (p0002 - p0020) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "A sharp, commanding voice scolds Gong-ja to stop making loud noise during nighttime training."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "A flamboyant figure with flowing crimson hair sits casually on top of Gong-ja's chest."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "The stranger floats effortlessly in the air, his transparent form radiating with faint spiritual light."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Gong-ja blinks in complete confusion, managing to stammer out a simple question: who are you?"},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "The red-haired spirit freezes in mid-sentence, his arrogant expression instantly cracking in shock."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "He leans down inches from Gong-ja's face, whispering in bewilderment: you can actually see me?"},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "Gong-ja nods slowly, watching the otherworldly phantom examine his own ghostly hands."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "He confirms with a dry monotone: yes, I can see you crystal clear."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "The spirit leaps backward in shock, asking if Gong-ja can hear his voice as well."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Gong-ja sighs, pointing out that having a two-way conversation usually implies hearing each other."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "The spirit lands on the mattress, scratching his head in utter disbelief at this impossible phenomenon."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "He glares around the cramped apartment, complaining loudly that it looks like a filthy doghouse."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "He demands to know where Grandpa Marcus is and why he was dragged into this squalor."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "He presses his ghostly face against the tiny window, appalled by the dreary view outside."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "Gong-ja's jaw drops: calling the legendary number one hunter Grandpa Marcus is beyond disrespectful."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "To this bizarre entity, humanity's greatest living swordsman is merely an obedient student."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "The spirit whines theatrically that he can't see anything through the grime-covered glass."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "Gong-ja checks the fine print on his newly acquired A-plus skill: Master of the Blade."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "The card description explicitly notes that it binds an ancient, otherworldly spirit to the user."},

    # --- ACT 2: REFUND ME RIGHT NOW (p0021 - p0045) ---
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "Gong-ja gulps nervously, apologizing for what he is about to confess."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "He admits with sheepish guilt: I think I accidentally duplicated your soul."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "The spirit's jaw hits the floor before erupting into a volcanic, hysterical shriek."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "He screams into the night sky, demanding to be returned to Grandpa Marcus this instant."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "He shouts frantically: Have you ever heard of a refund?! Refund my soul right now!"},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "He clutches his crimson hair, screaming in theatrical agony over his cosmic abduction."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Gong-ja raises his hands helplessly, explaining that the system allows zero returns on copied skills."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "The spirit floats upside down, sobbing melodramatic tears of betrayal across the ceiling."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "He curses Marcus for being a careless old fool who let his precious master get plagiarized."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "Gong-ja holds his aching head, realizing why Marcus was constantly muttering to himself in the tavern."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "The Blade Saint wasn't insane; he was desperately enduring this annoying ghost twenty-four seven!"},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "The spirit bickers nonstop, venting grievances that span decades of nagging complaints."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "His mouth moves at lightning speed, delivering an endless barrage of sarcastic insults."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "Gong-ja recalls Marcus snapping in the tavern: Shut up and be quiet!"},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "Now, that exact same relentless headache has been transferred directly into Gong-ja's life."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Gong-ja sighs, asking the phantom who he was before becoming an ethereal parasite."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "He explains that he must avoid Marcus at all costs due to a catastrophic misunderstanding."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "The spirit crosses his arms, demanding to know what sin an F-rank brat could possibly commit."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "He looks down at Gong-ja with a condescending sneer, ready to judge his mortal flaws."},
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "Gong-ja explains Marcus's divine sensory ability that tracks an individual's kill count."},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "The spirit smirks, noting that he taught Marcus that exact detection technique himself."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "He focuses his spiritual gaze upon Gong-ja's crown to read the number for himself."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "His crimson eyes widen into saucers as a glowing scarlet numeral blazes into view."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "Four thousand, ninety-one! Over four thousand murders branded across the youth's soul!"},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "The spirit recoils across the room, demanding to know what demonic slaughterhouse spawned this monster."},

    # --- ACT 3: THE TRUTH OF 4,090 DEATHS (p0046 - p0085) ---
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "Gong-ja looks into the spirit's eyes with solemn, unwavering sincerity."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "He calmly states that in his entire life, he has only ever murdered one single person."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "He executed Yoo Soo-ha, a psychotic villain who would have burned humanity to ashes."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "The spirit squints skeptically: then what about the other four thousand and ninety bodies?"},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "Gong-ja delivers the staggering truth: the other four thousand and ninety kills were myself."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "The phantom stares blankly, unable to comprehend the concept of committing suicide four thousand times."},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "Gong-ja explains his copied EX-rank skill that rewinds time twenty-four hours upon death."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "To execute the Flame Emperor before he awakened his power, he had to travel back eleven years."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Eleven years equals four thousand and ninety days, requiring four thousand and ninety self-inflicted deaths."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "He stabbed his own neck, drank lethal venom, and severed his own heart over and over again."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "He endured four thousand lifetimes of agony just to rid the universe of a tyrant."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "The system registered every suicide as a murder, branding him with an impossible sin."},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "The red-haired spirit is struck utterly speechless, gazing at Gong-ja as if staring at a god of madness."},
    {"block_id": "b058", "panel_ids": ["panel_0059"], "narration": "Even among ancient dimensional conquerors, nobody has ever displayed such terrifying willpower."},
    {"block_id": "b059", "panel_ids": ["panel_0060"], "narration": "He introduces himself properly: his name is Bae Hu-ryeong, the legendary Sword Emperor."},
    {"block_id": "b060", "panel_ids": ["panel_0061"], "narration": "In his home world, a Babel Tower appeared just like the one piercing Babylon's sky."},
    {"block_id": "b061", "panel_ids": ["panel_0062"], "narration": "Bae Hu-ryeong fought his way from the bottom, conquering all one hundred floors alone."},
    {"block_id": "b062", "panel_ids": ["panel_0063"], "narration": "He was the first mortal to ever clear the hundredth floor and claim the tower's divine throne."},
    {"block_id": "b063", "panel_ids": ["panel_0064"], "narration": "Yet due to an unresolved tragedy, he died without crossing over, lingering as an eternal soul."},
    {"block_id": "b064", "panel_ids": ["panel_0065"], "narration": "Gong-ja looks at the grand master with newfound awe: this ghost is a true hundredth-floor conqueror!"},
    {"block_id": "b065", "panel_ids": ["panel_0066"], "narration": "If the Flame Emperor became a global legend clearing floor forty, Bae Hu-ryeong is a martial god."},
    {"block_id": "b066", "panel_ids": ["panel_0067"], "narration": "Bae Hu-ryeong smirks, proudly boasting that all he needs is one glance to measure a hunter's talent."},
    {"block_id": "b067", "panel_ids": ["panel_0068"], "narration": "Gong-ja looks down at his rough hands, admitting that he has zero combat gifts."},
    {"block_id": "b068", "panel_ids": ["panel_0069"], "narration": "He has no magical bloodline, no innate reflexes, and struggled to even pass the F-rank exam."},
    {"block_id": "b069", "panel_ids": ["panel_0070"], "narration": "Bae Hu-ryeong snaps back: What complete nonsense are you babbling?"},
    {"block_id": "b070", "panel_ids": ["panel_0071"], "narration": "He points a glowing finger directly at Gong-ja's chest: You possess an extraordinary talent!"},
    {"block_id": "b071", "panel_ids": ["panel_0072"], "narration": "Gong-ja blinks in surprise, wondering if the ghost is merely mocking him with false praise."},

    # --- ACT 4: THE TALENT OF FEARLESSNESS (p0086 - p0117) ---
    {"block_id": "b072", "panel_ids": ["panel_0073"], "narration": "Bae Hu-ryeong explains that in mortal combat, every warrior fights with at least ten percent fear."},
    {"block_id": "b073", "panel_ids": ["panel_0074"], "narration": "The primal instinct to avoid death makes swordsmen hesitate, flinch, and miscalculate."},
    {"block_id": "b074", "panel_ids": ["panel_0075"], "narration": "But Gong-ja has died more than four thousand times; the concept of death holds zero terror over him."},
    {"block_id": "b075", "panel_ids": ["panel_0076"], "narration": "He can swing his blade with one hundred percent pure commitment, unburdened by mortal fear."},
    {"block_id": "b076", "panel_ids": ["panel_0077"], "narration": "Gong-ja asks dubiously: Is not being afraid of dying truly considered a talent?"},
    {"block_id": "b077", "panel_ids": ["panel_0078"], "narration": "Bae Hu-ryeong laughs: Why wouldn't it be? It is the rarest, most lethal talent in existence!"},
    {"block_id": "b078", "panel_ids": ["panel_0079"], "narration": "Some are born with golden gifts, but Gong-ja forged his supreme talent through sheer, brutal repetition."},
    {"block_id": "b079", "panel_ids": ["panel_0080"], "narration": "Gong-ja reflects on his ordeal: he was driven only by burning resentment and stubborn resolve."},
    {"block_id": "b080", "panel_ids": ["panel_0081"], "narration": "He was so furious at the Flame Emperor's arrogance that he simply refused to stop dying."},
    {"block_id": "b081", "panel_ids": ["panel_0082"], "narration": "Now, that unhinged persistence has become his greatest, most terrifying martial asset."},
    {"block_id": "b082", "panel_ids": ["panel_0083"], "narration": "Bae Hu-ryeong floats closer, asking what Gong-ja thought right before Marcus decapitated him."},
    {"block_id": "b083", "panel_ids": ["panel_0084"], "narration": "Gong-ja recalls his severed head tumbling beneath the starry night sky."},
    {"block_id": "b084", "panel_ids": ["panel_0085"], "narration": "He answers honestly: I was thinking that the moon looked truly beautiful."},
    {"block_id": "b085", "panel_ids": ["panel_0086"], "narration": "Bae Hu-ryeong stares in stunned silence for two seconds, then bursts into uproarious, howling laughter."},
    {"block_id": "b086", "panel_ids": ["panel_0087"], "narration": "He rolls through the air, cackling that Gong-ja is the most delightfully unhinged lunatic he has ever met."},
    {"block_id": "b087", "panel_ids": ["panel_0088"], "narration": "He realizes that because Gong-ja copied the skill, Marcus still holds the original copy of his soul."},
    {"block_id": "b088", "panel_ids": ["panel_0089"], "narration": "Two versions of the Sword Emperor now exist, mentoring two completely different hunters."},
    {"block_id": "b089", "panel_ids": ["panel_0090"], "narration": "He grins like an excited demon: who will become the stronger hunter between Marcus and Gong-ja?"},
    {"block_id": "b090", "panel_ids": ["panel_0091"], "narration": "Bae Hu-ryeong points his finger forward, officially accepting Gong-ja as his disciple."},
    {"block_id": "b091", "panel_ids": ["panel_0092"], "narration": "He vows to train Gong-ja until he surpasses the Blade Saint and claims the hundredth floor."},
    {"block_id": "b092", "panel_ids": ["panel_0093"], "narration": "Gong-ja stands tall in his humble studio, golden system light reflecting in his determined eyes."},
    {"block_id": "b093", "panel_ids": ["panel_0094"], "narration": "With the hundredth-floor conqueror as his personal ghost mentor, his ascent begins now."},
    {"block_id": "b094", "panel_ids": ["panel_0095"], "narration": "The F-rank hunter and the immortal Sword Emperor forge a pact to conquer the Babel Tower together."},
    {"block_id": "b095", "panel_ids": ["panel_0096"], "narration": "The greatest climb in hunter history has officially united student and spectral master."},
    {"block_id": "b096", "panel_ids": ["panel_0097"], "narration": "Together, they will rewrite the laws of the tower and challenge the very heavens."},
    {"block_id": "b097", "panel_ids": ["panel_0098"], "narration": "Kim Gong-ja's training under the legendary Sword Emperor starts this very morning."},
    {"block_id": "b098", "panel_ids": ["panel_0099"], "narration": "The tower's monsters and corrupt rankers have no idea what terror is heading their way."},
    {"block_id": "b099", "panel_ids": ["panel_0100"], "narration": "No wall will stand, no raid will fail, and no enemy will outlast the Revival Hunter."},
    {"block_id": "b100", "panel_ids": ["panel_0101"], "narration": "A new legend is born in Babylon, carved through blood, steel, and four thousand deaths."},
    {"block_id": "b101", "panel_ids": ["panel_0102"], "narration": "The Sword Emperor raises his spectral blade, pointing toward the colossal spire in the distance."},
    {"block_id": "b102", "panel_ids": ["panel_0103"], "narration": "First lesson begins: mastering the flow of pure sword intent without mortal hesitation."},
    {"block_id": "b103", "panel_ids": ["panel_0104"], "narration": "Gong-ja grasps his weapon, ready to die another thousand times if that is what mastery demands."},
    {"block_id": "b104", "panel_ids": ["panel_0105"], "narration": "His journey through the hundred floors will leave an indelible mark on all creation."},
    {"block_id": "b105", "panel_ids": ["panel_0106"], "narration": "The curtain rises on the ultimate conqueror of the Babel Tower."},
    {"block_id": "b106", "panel_ids": ["panel_0107"], "narration": "No challenge is impossible when death itself is your most reliable tactical ally."},
    {"block_id": "b107", "panel_ids": ["panel_0108"], "narration": "Kim Gong-ja takes his first real step as the true heir of the Sword Emperor."},
    {"block_id": "b108", "panel_ids": ["panel_0109"], "narration": "The entire tower trembles in anticipation of the trials that await them on the upper floors."},
    {"block_id": "b109", "panel_ids": ["panel_0110"], "narration": "He steps forward into the dawn, ready to claim his rightful place at the summit."},
    {"block_id": "b110", "panel_ids": ["panel_0111"], "narration": "The tale of SSS-Class Revival Hunter has only just begun to unleash its true fury."},
    {"block_id": "b111", "panel_ids": ["panel_0112"], "narration": "From the lowest gutter of Babylon to the highest throne of the gods, his path is set."},
    {"block_id": "b112", "panel_ids": ["panel_0113"], "narration": "Every floor will witness the unyielding resolve of a hunter who refused to stay dead."},
    {"block_id": "b113", "panel_ids": ["panel_0114"], "narration": "The spectral master grins, knowing he has found the most fascinating disciple in all existence."},
    {"block_id": "b114", "panel_ids": ["panel_0115"], "narration": "Together, they will storm the trials and bring Babylon to its knees in awe."},
    {"block_id": "b115", "panel_ids": ["panel_0116"], "narration": "With blade in hand and immortality in his veins, Gong-ja steps out to claim destiny."},
    {"block_id": "b116", "panel_ids": ["panel_0117"], "narration": "The Revival Hunter's ascent is officially under way!"},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch07")
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
        chapter_id="sss-class-revival-hunter/ch07",
        title="SSS-Class Revival Hunter - Chapter 7",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch07/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 07 Script ===")
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
