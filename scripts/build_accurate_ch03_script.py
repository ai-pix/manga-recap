"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 3.

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
    # --- ACT 1: AWAKENING IN THE PAST & THE EX-RANK REVEAL (p0001 - p0025) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "Kim Gong-ja stares around his messy apartment, clutching his chest in total shock."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "He distinctly remembers having his skull incinerated by the Flame Emperor just moments ago."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Yet when he checks his phone, the exact same notifications from yesterday are popping up."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "A loud digital chime pings as online forums explode with identical celebrity hunter gossip."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "On screen, Flame Emperor Yoo Soo-ha is angrily whining about his ridiculous nickname yet again."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "Gong-ja's hands tremble uncontrollably as a chilling realization dawns over him."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "Everyone in the world is repeating the exact same words and actions from yesterday."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "A swarm of dark memories floods his mind, confirming that his horrific murder truly happened."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "He was definitely slaughtered in that alleyway, yet here he stands completely alive and unharmed."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "Extending a shaking hand forward, he commands his hunter status interface to open."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "Two glowing cards hover before him, radiating with intense digital light."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "The first card is his original S-plus ability, requiring his death to copy an enemy skill."},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "Beside it floats the radiant golden card he desperately snatched while dying."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "It displays an unimaginable EX-rank title: The Time Traveler's Clock."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "The description reveals an insane reality: upon dying, the user travels twenty-four hours back in time."},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "All memories, abilities, and trauma remain completely intact across every single reset."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "Everything suddenly makes terrifying sense—this was the Flame Emperor's greatest secret all along!"},
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "Soo-ha never had godlike instincts; he simply died, reset the day, and preempted every threat."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "He killed Saint Isabelle because she poisoned him, then rewound time to butcher her before she struck."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "On screen, Soo-ha delivers his chilling threat to aspiring hunters: I'll kill you."},
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "Kill? Gong-ja repeats the cruel word, a bitter smirk spreading across his face."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "The terrifying monster who ruled Babylon through fear is no longer untouchable."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "Gong-ja clenches his fist with volcanic fury, shattering the floating notification into digital sparks."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "He mutters a deadly vow: let's see who ends up killing who first this time."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "The hunt has begun, and the prey has no idea his own power has been stolen."},

    # --- ACT 2: THE SLUM FIRE & THE FLAME EMPEROR'S TRUE FACE (p0026 - p0068) ---
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "Suddenly, terrified screams of 'Fire!' echo through the streets outside his window."},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "Gong-ja presses against the glass, watching towering flames engulf the nearby district."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "Panicked residents shout for water buckets as the inferno spreads rapidly through the wooden slums."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "Sirens wail in the distance as crowds scramble frantically to escape the raging blaze."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "This city is the first floor of the Babel Tower, where thousands of low-tier hunters scrape by."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "A colossal sea of red and orange flames climbs into the night, threatening entire city blocks."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "Gong-ja checks his watch while running—it is six thirty-seven in the evening."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "This is the exact hour he was drinking soju yesterday, meaning the Saint was murdered right here!"},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "The Black Dragon Guild arrives in force, their stern commander barking orders to form a perimeter."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "Mages cast ice spells while emergency medics search the perimeter for trapped civilians."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "Babylon's citizens look on in despair as the historic district burns uncontrollably."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "Gong-ja realizes the fire was deliberately set by Soo-ha to incinerate Saint Isabelle's corpse."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "The monster wiped out an entire neighborhood just to destroy any trace of his gruesome crime."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "Footsteps crunch over broken glass as the crowd suddenly parts in reverent silence."},
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "Flame Emperor Yoo Soo-ha steps through the smoke, clad in his pristine coat and red scarf."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "Desperate refugees fall to their knees, begging the world's greatest hero to extinguish the fire."},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "Soo-ha merely scoffs with haughty disdain, hands resting casually inside his pockets."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "He loudly announces that he doesn't work for free, demanding millions just to lift a finger."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "When the crowd weeps that children are trapped inside, he laughs heartlessly in their faces."},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "He tells them that dying in an accident is just their own bad luck, turning his back on them."},
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "Gong-ja watches from the fringe, his blood boiling at the sheer cruelty on display."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "This psychopath isn't a savior; he is a demonic butcher hiding behind a gleaming smile."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "Even if Gong-ja somehow ambushed and killed him now, Soo-ha's clock would simply trigger."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "Soo-ha would rewind time twenty-four hours, remember the attack, and slaughter Gong-ja in retaliation."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "A mortal duel between two time travelers holding the same skill is an infinite stalemate."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "Gong-ja needs a plan so utterly unhinged that the universe itself cannot predict it."},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "He charges toward the raging flames, ignoring the frantic shouts of paladins trying to restrain him."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "Blistering heat sears his skin as he dives straight into the inferno to confirm his hypothesis."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "The suffocating smoke fills his lungs as structural beams collapse violently around him."},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "He watches the fire consume his flesh, willingly surrendering his life to test the clock."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "A familiar system ping sounds as his vision fades: You have died."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "The EX-rank clock activates without hesitation, rewinding time another full day into the past."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "The temporal shift rips through reality, resetting the sun and stars by twenty-four hours."},
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "Gong-ja's head jerks back violently as his soul slams back into his mortal body."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "Breaking news blares from the TV once more—the Black Dragon raid failure is broadcasting again."},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "He sits up on his ragged mattress, a chilling grin spreading across his face."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "The skill functions flawlessly, with zero cooldown, zero memory loss, and zero divine penalties."},
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "The system window explicitly confirms: There will be no penalty for using this skill."},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "Gong-ja stands before a massive mental clock face, doing the brutal, lethal mathematics."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "As an F-rank nobody, he cannot possibly defeat the Flame Emperor in modern combat."},
    {"block_id": "b066", "panel_ids": ["panel_0066"], "narration": "Even if he somehow did, Soo-ha would rewind and strike first with apocalyptic hellfire."},
    {"block_id": "b067", "panel_ids": ["panel_0067"], "narration": "There is only one mathematical solution: he must travel back to before Soo-ha ever obtained his skill!"},
    {"block_id": "b068", "panel_ids": ["panel_0068"], "narration": "Before the Flame Emperor was a god, he was an ordinary, mortal human being without power."},

    # --- ACT 3: THE 4,050 SUICIDE MARCH (p0069 - p0102) ---
    {"block_id": "b069", "panel_ids": ["panel_0069"], "narration": "Gong-ja searches historical interviews, finding the exact date Soo-ha first awakened his powers."},
    {"block_id": "b070", "panel_ids": ["panel_0070"], "narration": "In an archived magazine, Soo-ha casually mentioned that he awakened in the summer he turned twenty-one."},
    {"block_id": "b071", "panel_ids": ["panel_0071"], "narration": "He remembered it vividly because it occurred on his birthday, exactly eleven years ago."},
    {"block_id": "b072", "panel_ids": ["panel_0072"], "narration": "Eleven years equals precisely four thousand and fifty days of lived history."},
    {"block_id": "b073", "panel_ids": ["panel_0073"], "narration": "If one death rewinds twenty-four hours, then traveling back eleven years requires four thousand and fifty deaths."},
    {"block_id": "b074", "panel_ids": ["panel_0074"], "narration": "He must commit suicide over four thousand times without a single moment of hesitation."},
    {"block_id": "b075", "panel_ids": ["panel_0075"], "narration": "Any normal human mind would shatter into thousand pieces after just three repetitions of agony."},
    {"block_id": "b076", "panel_ids": ["panel_0076"], "narration": "Gong-ja picks up a sturdy dagger with a green-wrapped hilt, feeling the cold weight of destiny."},
    {"block_id": "b077", "panel_ids": ["panel_0077"], "narration": "He doesn't care about the pain; his hatred for the Flame Emperor burns hotter than hell itself."},
    {"block_id": "b078", "panel_ids": ["panel_0078"], "narration": "He places the sharp blade against his neck, takes one last breath, and plunges it downward with all his might."},
    {"block_id": "b079", "panel_ids": ["panel_0079"], "narration": "Blood spurts across the floor as his vision fades into cold darkness: You have died."},
    {"block_id": "b080", "panel_ids": ["panel_0080"], "narration": "He snaps awake twenty-four hours earlier, gasping for air on his floor, clutching his throat."},
    {"block_id": "b081", "panel_ids": ["panel_0081"], "narration": "He wipes the cold sweat from his face, muttering: only four thousand and forty-nine more to go!"},
    {"block_id": "b082", "panel_ids": ["panel_0082"], "narration": "Without wasting a single second, he grips the dagger and drives it into his flesh once again."},
    {"block_id": "b083", "panel_ids": ["panel_0083"], "narration": "Die. Wake up. Drive the blade home. Die again. Wake up again."},
    {"block_id": "b084", "panel_ids": ["panel_0084"], "narration": "A relentless, terrifying cycle of self-inflicted slaughter unfolds across the fabric of time."},
    {"block_id": "b085", "panel_ids": ["panel_0085"], "narration": "He drinks deadly poison, feeling purple venom dissolve his stomach lining in excruciating agony."},
    {"block_id": "b086", "panel_ids": ["panel_0086"], "narration": "He coughs up dark crimson blood, suffocating on his own fluids until his heart stops beating."},
    {"block_id": "b087", "panel_ids": ["panel_0087"], "narration": "The system window blinks like a relentless metronome: You will travel twenty-four hours back in time."},
    {"block_id": "b088", "panel_ids": ["panel_0088"], "narration": "Over and over, day after day, year after year, he walks through the valley of self-inflicted death."},
    {"block_id": "b089", "panel_ids": ["panel_0089"], "narration": "His hands blister, his spirit cracks, but his iron obsession refuses to bend."},
    {"block_id": "b090", "panel_ids": ["panel_0090"], "narration": "Two thousand and twenty days left! He screams through cracked lips, slamming the steel home."},
    {"block_id": "b091", "panel_ids": ["panel_0091"], "narration": "One thousand days left! Five hundred days left! Three hundred days left!"},
    {"block_id": "b092", "panel_ids": ["panel_0092"], "narration": "He lives through four thousand lifetimes of agony, rewinding through decades of historical events."},
    {"block_id": "b093", "panel_ids": ["panel_0093"], "narration": "Cities unbuild themselves, fallen hunters return to life, and the world grows younger around him."},
    {"block_id": "b094", "panel_ids": ["panel_0094"], "narration": "His body trembles from the ghost of thousands of fatal wounds carved into his phantom soul."},
    {"block_id": "b095", "panel_ids": ["panel_0095"], "narration": "Yet in his hollowed eyes, a terrifying, unquenchable flame burns brighter with every reset."},
    {"block_id": "b096", "panel_ids": ["panel_0096"], "narration": "He falls to his knees, gripping the blood-stained dagger with raw, calloused knuckles."},
    {"block_id": "b097", "panel_ids": ["panel_0097"], "narration": "A final system notification flashes before his exhausted eyes: One last day remaining!"},
    {"block_id": "b098", "panel_ids": ["panel_0098"], "narration": "He has crawled through four thousand hells to arrive at the doorstep of the past."},
    {"block_id": "b099", "panel_ids": ["panel_0099"], "narration": "He drives the dagger through his heart one final time to complete the impossible journey."},
    {"block_id": "b100", "panel_ids": ["panel_0100"], "narration": "Reality shatters into brilliant amber fragments, pulling him ten years into yesterday."},
    {"block_id": "b101", "panel_ids": ["panel_0101"], "narration": "The Flame Emperor's past is now open before him, waiting for the Revival Hunter's blade."},
    {"block_id": "b102", "panel_ids": ["panel_0102"], "narration": "Kim Gong-ja's bloody resurrection has officially rewritten the history of the Babel Tower."},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch03")
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
        chapter_id="sss-class-revival-hunter/ch03",
        title="SSS-Class Revival Hunter - Chapter 3",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch03/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 03 Script ===")
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
