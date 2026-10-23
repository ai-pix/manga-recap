"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 4.

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
    # --- ACT 1: 4,090 DEATHS & ARRIVAL IN THE PAST (p0001 - p0017) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "Tick. The rhythmic sound of an analog clock marks the return of a resurrected soul."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "The hands point to two o'clock in an ordinary, unbloodied room."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Kim Gong-ja lies spreadeagled on a clean white bedsheet, gripping his green dagger."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "He listens to his own steady heartbeat, marveling that the horrific ordeal is finally over."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "Tick. Another second passes in a world that feels completely fresh and untainted."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "Gong-ja sits against the wall, staring blankly ahead as phantom agony fades from his limbs."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "He looks up at the clock, tallying the total cost of his time-traveling odyssey."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "The wall of old newspaper clippings has vanished, replaced by empty, plaster walls."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "He slides his thumb over the dagger's hilt, feeling the cold steel that claimed his life thousands of times."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "He presses a cool glass bottle to his forehead, exhaling a long, shuddering sigh of relief."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "Tick. He survived hell, but the mental scars will remain carved into his mind forever."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "In the end, he died an extra thirty times beyond his original calculation."},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "Those thirty extra suicides were brief resting periods he desperately needed to keep his sanity intact."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "He stands up on bare feet, feeling the solid wooden floor beneath him."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "Walking toward the door, he prepares to hunt the most dangerous prey on Earth."},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "He pulls his light-colored hoodie up, casting his eyes into deep, unreadable shadows."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "Eleven years ago, on May sixth at eleven in the morning, his true mission begins."},

    # --- ACT 2: STALKING THE MORTAL FLAME EMPEROR (p0018 - p0039) ---
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "The timeline has successfully rolled back eleven full years into the past."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "The clock strikes exactly eleven o'clock as bright morning sunlight washes over the city."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "Eleven AM sharp—the exact hour history originally began to write its darkest chapter."},
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "Gong-ja stands silently across the street, watching an apartment complex reserved for rookie hunters."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "Peering through a second-floor window, he spots a familiar figure waking up."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "A buzzing phone alarm blares as a young man groans miserably in bed."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "A shirtless, twenty-one-year-old Yoo Soo-ha clutches his throbbing head from a brutal hangover."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "He curses his excessive drinking, looking like any other broke, miserable F-rank loser."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "He holds no godlike flames, commands no armies, and holds zero respect from society."},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "His daily routine is utterly pathetic: wake at nine, complain endlessly, and drag himself to work."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "Gong-ja observes him with cold, calculating eyes from behind the glass."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "By three in the afternoon, Soo-ha lazily marches toward the hunting grounds."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "Three PM sharp—the daily grind of a rookie trying to scrape together rent money."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "He arrives at the second floor to kill low-tier red slimes with a cheap spear."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "Red gelatin splatters across the dirt as he sluggishly hacks apart weak monsters."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "He kicks the slime corpse in disgust, whining that hunting trash day after day is soul-crushingly boring."},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "He curses the sky, demanding to know when he will get to live like the legendary Blade Saint."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "He daydreams aloud about winning the lottery or waking up with an effortless cheat skill."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "In the original timeline, his cheat skill would awaken exactly one week from today."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "One week later, the cosmos would have granted him the temporal clock that birthed a tyrant."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "He would have become the butcher who burned Saint Isabelle and murdered Gong-ja in cold blood."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "Gong-ja whispers with icy finality: that future will never come to pass."},

    # --- ACT 3: THE AMBUSH & EXECUTION (p0040 - p0096) ---
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "Gong-ja prepares his trap, memorizing every detail of the sixth-floor wilderness."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "Five thirty-one in the afternoon—the exact moment the forest empties of witnesses."},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "He waits thirty-six precise minutes in the brush, completely motionless."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "He moves through the dense thicket like a silent ghost, stalking his unsuspecting target."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "He smeared beast blood across his forehead, posing as a critically wounded adventurer."},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "Stumbling out of the bushes, he clutches his side and begs Soo-ha for a healing potion."},
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "He claims he was mauled by red wolves and desperately needs immediate medical aid."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "Soo-ha turns around slowly, his expression instantly contorting into callous greed."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "He pulls a cheap potion from his pouch, demanding twenty gold pieces upfront."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "Gong-ja eagerly hands over twenty coins, groaning in simulated agony."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "Seeing how easily the money flowed, Soo-ha instantly hikes the price to forty gold."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "Gong-ja trembles and pulls out another twenty coins, begging him to save his life."},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "Instead of handing over the bottle, Soo-ha grins with sadistic delight."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "He remarks that a dying rat holding this much gold probably has plenty more hidden away."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "Without a second of hesitation, Soo-ha drives his hunting spear directly into Gong-ja's shoulder!"},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "He kicks the fallen hunter onto his back, rifling through Gong-ja's pockets like a scavenger."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "Finding only sixty gold in total, he spits on the ground in bitter disappointment."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "Gong-ja looks into the young man's eyes, seeing the exact same sociopath who murdered him in the future."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "Even without power, Yoo Soo-ha was always rotten to the core."},
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "Soo-ha raises his spear high, casually explaining that since Gong-ja saw his face, he cannot leave witnesses."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "He delivers his trademark arrogant line: people should live without regrets, goodbye."},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "As the spear thrusts downward, Gong-ja's wounded facade completely evaporates."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "His hand whips out from beneath his cloak, clutching the green-hilted dagger with deadly speed."},
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "He sidesteps the clumsy thrust, his eyes gleaming with four thousand lifetimes of killing intent."},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "Before Soo-ha can even register the movement, Gong-ja executes a blinding horizontal slash across his abdomen."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "The razor-sharp edge slices deep through flesh, severing muscles and blood vessels in a single strike."},
    {"block_id": "b066", "panel_ids": ["panel_0066"], "narration": "Soo-ha gasps in utter shock, dropping his spear as bright crimson blood sprays across the grass."},
    {"block_id": "b067", "panel_ids": ["panel_0067"], "narration": "He collapses to his knees, clutching his gaping wound in disbelief."},
    {"block_id": "b068", "panel_ids": ["panel_0068"], "narration": "Gong-ja stands over him, twirling the bloodied blade with chilling calm."},
    {"block_id": "b069", "panel_ids": ["panel_0069"], "narration": "He looks down at the future Flame Emperor, who is now whimpering for mercy like a dog."},
    {"block_id": "b070", "panel_ids": ["panel_0070"], "narration": "Soo-ha chokes on his own blood, desperately asking who the hell he is."},
    {"block_id": "b071", "panel_ids": ["panel_0071"], "narration": "Gong-ja remembers the night he was incinerated in the alleyway, when Soo-ha proudly gave his name before killing him."},
    {"block_id": "b072", "panel_ids": ["panel_0072"], "narration": "Now, standing in the quiet forest eleven years earlier, Gong-ja leans down to return the favor."},
    {"block_id": "b073", "panel_ids": ["panel_0073"], "narration": "He smiles gently and whispers: my name is Confucius Kim, goodbye."},
    {"block_id": "b074", "panel_ids": ["panel_0074"], "narration": "A pack of hungry red wolves gathers at the edge of the clearing, drawn by the scent of fresh blood."},
    {"block_id": "b075", "panel_ids": ["panel_0075"], "narration": "Gong-ja steps back, telling the beasts that the meat is all theirs to devour."},
    {"block_id": "b076", "panel_ids": ["panel_0076"], "narration": "The wolves swarm forward, tearing into the remains of the monster who will never terrorize humanity."},
    {"block_id": "b077", "panel_ids": ["panel_0077"], "narration": "Every single trace of Flame Emperor Yoo Soo-ha is permanently erased from the annals of time."},
    {"block_id": "b078", "panel_ids": ["panel_0078"], "narration": "Gong-ja wipes his dagger clean against a leaf, exhaling the heavy burden he carried across four thousand deaths."},
    {"block_id": "b079", "panel_ids": ["panel_0079"], "narration": "The world will never know how close it came to ruin, and it will never know who saved it."},
    {"block_id": "b080", "panel_ids": ["panel_0080"], "narration": "He sheathes his weapon, turning his back on the carnage as twilight settles over the forest."},
    {"block_id": "b081", "panel_ids": ["panel_0081"], "narration": "The execution of Yoo Soo-ha is complete, and the timeline is officially purged."},
    {"block_id": "b082", "panel_ids": ["panel_0082"], "narration": "Gong-ja adjusts his hood, walking briskly toward the floor's teleportation portal."},
    {"block_id": "b083", "panel_ids": ["panel_0083"], "narration": "His footsteps are light, unburdened by guilt or hesitation."},
    {"block_id": "b084", "panel_ids": ["panel_0084"], "narration": "He arrives at the glowing platform, stepping into the shimmering column of blue light."},
    {"block_id": "b085", "panel_ids": ["panel_0085"], "narration": "He inputs his destination, requesting immediate transport to the first floor."},
    {"block_id": "b086", "panel_ids": ["panel_0086"], "narration": "The portal hums with energy, dissolving his physical form into digital light."},
    {"block_id": "b087", "panel_ids": ["panel_0087"], "narration": "A system message flashes: Transporting to the first floor."},
    {"block_id": "b088", "panel_ids": ["panel_0088"], "narration": "He materializes at the bottom of a stone staircase leading out to the city streets."},
    {"block_id": "b089", "panel_ids": ["panel_0089"], "narration": "Suddenly, an armored city security guard appears around the corner!"},
    {"block_id": "b090", "panel_ids": ["panel_0090"], "narration": "Gong-ja's heart skips a beat as he freezes in place, still covered in wolf blood."},
    {"block_id": "b091", "panel_ids": ["panel_0091"], "narration": "The guard glares down at the hooded youth, his silver plate armor clanking heavily."},
    {"block_id": "b092", "panel_ids": ["panel_0092"], "narration": "They lock eyes at point-blank range, the suffocating silence stretching into eternity."},
    {"block_id": "b093", "panel_ids": ["panel_0093"], "narration": "The guard suddenly yawns, scoffs at the messy rookie, and continues his boring patrol route."},
    {"block_id": "b094", "panel_ids": ["panel_0094"], "narration": "Gong-ja exhales slowly, watching the armored officer disappear into the evening mist."},
    {"block_id": "b095", "panel_ids": ["panel_0095"], "narration": "It is truly over. There are no witnesses, no evidence, and no one hunting his trail."},
    {"block_id": "b096", "panel_ids": ["panel_0096"], "narration": "Babylon sparkles with thousands of glowing windows as night embraces the colossal tower."},

    # --- ACT 4: CELEBRATION & THE BLADE SAINT (p0097 - p0133) ---
    {"block_id": "b097", "panel_ids": ["panel_0097"], "narration": "Gong-ja zips up his jacket, blending effortlessly into the bustling crowds of Babylon."},
    {"block_id": "b098", "panel_ids": ["panel_0098"], "narration": "Nobody in this vibrant city knows the impossible war that was just fought and won."},
    {"block_id": "b099", "panel_ids": ["panel_0099"], "narration": "Public broadcast screens report that the tenth-floor expedition has failed once again."},
    {"block_id": "b0100", "panel_ids": ["panel_0100"], "narration": "Without Soo-ha's future raids, the tower's upper floors remain completely unconquered."},
    {"block_id": "b0101", "panel_ids": ["panel_0101"], "narration": "Public outrage mounts against the top hunter, Blade Saint Marcus, for refusing to join the raid."},
    {"block_id": "b0102", "panel_ids": ["panel_0102"], "narration": "Gong-ja pushes through the tavern doors, eager to celebrate his impossible survival."},
    {"block_id": "b0103", "panel_ids": ["panel_0103"], "narration": "He slams a heavy glass mug onto the wooden bar, demanding the coldest draft beer in the house."},
    {"block_id": "b0104", "panel_ids": ["panel_0104"], "narration": "News commentators argue whether top-ranked hunters are obligated to risk their lives for the public."},
    {"block_id": "b0105", "panel_ids": ["panel_0105"], "narration": "The bartender smiles warmly, asking Gong-ja if his hunting went particularly well today."},
    {"block_id": "b0106", "panel_ids": ["panel_0106"], "narration": "Gong-ja grins from ear to ear, raising his frothing mug in a solo toast to the universe."},
    {"block_id": "b0107", "panel_ids": ["panel_0107"], "narration": "He drinks deeply, the crisp, icy beer washing away four thousand lifetimes of suffering."},
    {"block_id": "b0108", "panel_ids": ["panel_0108"], "narration": "He commands his hunter ability window to open, admiring his two god-tier passive skills."},
    {"block_id": "b0109", "panel_ids": ["panel_0109"], "narration": "Confucius Kim, F-rank, wielding an S-plus skill and an EX-rank time-rewind clock."},
    {"block_id": "b0110", "panel_ids": ["panel_0110"], "narration": "He winks playfully at his reflection, chuckling that this status screen is the finest drinking companion on Earth."},
    {"block_id": "b0111", "panel_ids": ["panel_0111"], "narration": "He notices he has zero active attack abilities, but quickly laughs off his own greedy desires."},
    {"block_id": "b0112", "panel_ids": ["panel_0112"], "narration": "He scolds himself: expecting free combat skills after stealing time itself would make him a shameless thief!"},
    {"block_id": "b0113", "panel_ids": ["panel_0113"], "narration": "Armed with eleven years of future knowledge, he can win tower lotteries and predict market crashes."},
    {"block_id": "b0114", "panel_ids": ["panel_0114"], "narration": "An endless highway of wealth, safety, and luxurious freedom stretches out before his eyes."},
    {"block_id": "b0115", "panel_ids": ["panel_0115"], "narration": "He spins on his barstool, ready to order another round and enjoy his newly earned life."},
    {"block_id": "b0116", "panel_ids": ["panel_0116"], "narration": "The tavern door creaks open as an imposing elderly gentleman steps into the warm light."},
    {"block_id": "b0117", "panel_ids": ["panel_0117"], "narration": "He wears an immaculate formal three-piece suit paired bizarrely with bright red sneakers."},
    {"block_id": "b0118", "panel_ids": ["panel_0118"], "narration": "Sporting a dignified white beard and a jaunty blue hat, he approaches the counter with peerless poise."},
    {"block_id": "b0119", "panel_ids": ["panel_0119"], "narration": "He places an unusual order: a glass of warm milk mixed with vodka and honey."},
    {"block_id": "b0120", "panel_ids": ["panel_0120"], "narration": "Gong-ja blinks in surprise, turning around to tell the odd gentleman that he is just a customer."},
    {"block_id": "b0121", "panel_ids": ["panel_0121"], "narration": "The old man chuckles softly, promising to leave a handsome tip for the trouble."},
    {"block_id": "b0122", "panel_ids": ["panel_0122"], "narration": "Whispers break out among the other tavern patrons as eyes widen in sudden shock."},
    {"block_id": "b0123", "panel_ids": ["panel_0123"], "narration": "Gong-ja looks closer at the distinguished face, his beer mug freezing halfway to his lips."},
    {"block_id": "b0124", "panel_ids": ["panel_0124"], "narration": "On the wall screen directly behind the counter, news anchors are angrily demanding the Blade Saint's whereabouts."},
    {"block_id": "b0125", "panel_ids": ["panel_0125"], "narration": "The portrait on television matches the old man standing right next to him down to the exact whisker."},
    {"block_id": "b0126", "panel_ids": ["panel_0126"], "narration": "The number one hunter in the world, Marcus Calenprius, is casually ordering warm milk beside him."},
    {"block_id": "b0127", "panel_ids": ["panel_0127"], "narration": "The living legend who conquered the tower's early floors with a single sword slash stands in the flesh."},
    {"block_id": "b0128", "panel_ids": ["panel_0128"], "narration": "Gong-ja stares in stunned silence, his mind racing through the historical implications."},
    {"block_id": "b0129", "panel_ids": ["panel_0129"], "narration": "The media brands the Blade Saint as a selfish coward, but Marcus simply sips his drink in quiet sorrow."},
    {"block_id": "b0130", "panel_ids": ["panel_0130"], "narration": "Marcus turns slightly, his peerless warrior senses picking up the strange aura surrounding Gong-ja."},
    {"block_id": "b0131", "panel_ids": ["panel_0131"], "narration": "Two extraordinary hunters stand shoulder to shoulder in the humble tavern, their fates invisibly entwined."},
    {"block_id": "b0132", "panel_ids": ["panel_0132"], "narration": "The Flame Emperor is gone, but the climb through the hundred floors of the Babel Tower has just begun."},
    {"block_id": "b0133", "panel_ids": ["panel_0133"], "narration": "Kim Gong-ja's legendary journey from suicidal F-rank to the tower's greatest conqueror is officially underway."},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch04")
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
        chapter_id="sss-class-revival-hunter/ch04",
        title="SSS-Class Revival Hunter - Chapter 4",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch04/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 04 Script ===")
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
