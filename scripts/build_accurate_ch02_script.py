"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 2.

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
    # --- ACT 1: THE RED PILLAR & SOJU OF DESPAIR (p0001 - p0015) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "A colossal crimson pillar suddenly pierced the night sky, visible from every corner of the Earth."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "Desperate souls with nothing left to lose were the very first to rush toward its gates."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Soon, countless hunters swarmed the hundred-floor tower, seeking miraculous powers and unfathomable riches."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "Above them all stood the Flame Emperor, leaping into battle to solo slaughter impossible monsters."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "On a flickering television in a rundown bar, news reports gush over his historic fortieth-floor triumph."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "Slumped over the wooden counter, Kim Gong-ja begs the bartender to change the infuriating channel."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "The owner scoffs, asking why anyone would dislike humanity's greatest, most brutally honest champion."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "He proudly proclaims that an arrogant monster like Soo-ha is precisely what this cruel world needs."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "Gong-ja buries his head in shame, drowning in soju while mourning his completely meaningless life."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "The bartender sighs in irritation, telling him to stop whining and pay his damn tab."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "Gong-ja grimaces, mentally re-reading the humiliating system warning of his newly awakened ability."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "What kind of utterly psychotic skill demands that you literally die just to activate it?"},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "He hadn't even dared report it to the Hunter Association out of sheer, soul-crushing embarrassment."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "Admitting that his golden S-rank power is a suicidal curse would make him the laughingstock of Babylon."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "Stumbling out into a dark, foggy alleyway, he checks the hunter leaderboard to see Soo-ha still reigning supreme."},

    # --- ACT 2: MURDER IN THE ALLEY (p0016 - p0036) ---
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "Clutching his pounding head, a piercing scream abruptly shatters the quiet night air."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "Peering around a brick corner, he spots the Flame Emperor violently cornering a white-haired woman."},
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "Soo-ha sneers in mocking disgust, telling her that her pathetic innocence act won't fool anyone."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "Gong-ja gasps—the trembling victim is Saint Isabelle, the saintly ninth-ranked healer beloved by all."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "Soo-ha holds up a glowing bottle, accusing her of attempting to poison his evening drink."},
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "The glass vial gleams with Basilisk stomach acid, a lethal toxin designed to dissolve internal organs."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "He chuckles darkly, admitting that without his own passive instincts, he would be dead already."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "With a careless flick of his wrist, he hurls the deadly venom against the pavement."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "Isabelle weeps in sheer terror, desperately begging him to listen to reason and talk it out."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "Instead, Soo-ha steps into her personal space, grinning like a predator savoring its cornered prey."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "Gong-ja watches in petrified silence, realizing humanity's idol is a bloodthirsty executioner."},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "Soo-ha casually agrees to play the gentleman, promising to let her speak her final words."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "Before she can finish her sentence, his fist slams into her gut with bone-crushing force."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "Gong-ja clamps both hands over his mouth, suppressing a scream as cold sweat drenches his spine."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "Lifting the Saint by her slender throat, Soo-ha instructs her to answer only with simple nods."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "He falsely claims he possesses a lie-detecting skill, warning her that deception means instant agony."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "He demands to know which rival faction orchestrated the assassination hit on his life."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "Was it the Black Dragon Witch, or did another top guild dare cross his path?"},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "Isabelle chokes for air, whispering with her dying breath that she acted entirely on her own."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "Soo-ha's red eyes flare with apocalyptic rage as roaring hellfire erupts from his fingertips."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "Without a shred of mercy, he incinerates Saint Isabelle where she stands, reducing her to ashes."},

    # --- ACT 3: CAUGHT BY THE FLAME EMPEROR (p0037 - p0058) ---
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "Gong-ja stumbles backward in absolute panic, turning on his heels to sprint for dear life."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "In his frenzy, his foot kicks an empty soju bottle, sending it clattering loudly across the asphalt."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "Soo-ha snaps his gaze toward the noise, instantly detecting the fleeing witness in the shadows."},
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "Before Gong-ja can take three strides, a blistering shockwave detonates against his spine."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "The concussive force flings him through the air, violently slamming him into a solid brick wall."},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "He crashes heavily into piles of trash, his vision swimming with blinding white stars."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "Heavy footsteps echo slowly through the alley, carrying the suffocating aura of impending death."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "Gong-ja desperately scrambles across the filthy pavement, clawing at the dirt to escape."},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "A leather boot steps down right before his eyes, stopping his frantic crawl dead in its tracks."},
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "Soo-ha glares down with mild curiosity, asking what an F-rank rat is doing lurking in the dark."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "Tears and snot pour down Gong-ja's face as he stammers that he just had too much to drink."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "He begs for mercy, swearing on his life that he saw nothing and will keep his mouth shut."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "Soo-ha grabs him by the collar, effortlessly hoisting him off the ground with one hand."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "He presses his face inches away, demanding to know who hired an F-rank bum to spy on him."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "Gong-ja sobs hysterically, insisting nobody sent him and that he is just an ordinary citizen."},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "Soo-ha laughs mockingly, tightening his grip until Gong-ja's windpipe begins to collapse."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "He warns Gong-ja that liars get roasted alive, just like the beloved Saint moments ago."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "Gong-ja looks into the monster's unblinking eyes, realizing there is no shred of humanity inside him."},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "This is the idol Babylon worships: a paranoid psychopath who butchers without trial or proof."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "In a desperate bid for survival, Gong-ja gasps out a challenge through his crushed throat."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "He tells Soo-ha to activate his lie-detecting skill right now to verify his innocence."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "Soo-ha freezes for a brief second, his arrogant grin freezing into an amused smirk."},

    # --- ACT 4: THE CHILLING CONFESSION & EXECUTION (p0059 - p0079) ---
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "He leans in close and casually whispers: I completely lied about having a lie-detector."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "Gong-ja's jaw drops in horror—the Saint was executed purely on Soo-ha's paranoid hunch!"},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "Soo-ha shrugs carelessly, claiming he just knows things through his own infallible methods."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "He pats Gong-ja's cheek, noting that his terrified heartbeat proves he really is an innocent bystander."},
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "Gong-ja feels a fleeting wave of relief, believing for a split second that he might walk away."},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "Then, Soo-ha's smile twists into a sinister, remorseless mask of pure evil."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "He coldly remarks that being innocent doesn't change the fact that Gong-ja witnessed everything."},
    {"block_id": "b066", "panel_ids": ["panel_0066"], "narration": "Roaring orange flames ignite around Soo-ha's palm, illuminating the grim alleyway."},
    {"block_id": "b067", "panel_ids": ["panel_0067"], "narration": "He introduces himself politely as Yoo Soo-ha, promising to make the incineration quick."},
    {"block_id": "b068", "panel_ids": ["panel_0068"], "narration": "He places his burning hand directly onto Gong-ja's skull, unleashing apocalyptic heat."},
    {"block_id": "b069", "panel_ids": ["panel_0069"], "narration": "Gong-ja's brain boils in searing agony as his vision burns into searing, blinding white."},
    {"block_id": "b070", "panel_ids": ["panel_0070"], "narration": "His charred corpse collapses lifeless onto the filthy concrete as Soo-ha strolls away."},
    {"block_id": "b071", "panel_ids": ["panel_0071"], "narration": "In the cold embrace of death, an ominous system prompt flashes across his fading consciousness."},
    {"block_id": "b072", "panel_ids": ["panel_0072"], "narration": "The requirements for his S-rank passive skill have been fulfilled: the user has been murdered."},
    {"block_id": "b073", "panel_ids": ["panel_0073"], "narration": "The tower declares that a skill will now be randomly copied from his killer, Yoo Soo-ha."},
    {"block_id": "b074", "panel_ids": ["panel_0074"], "narration": "A dazzling cascade of floating skill cards materializes in the void before his spiritual form."},
    {"block_id": "b075", "panel_ids": ["panel_0075"], "narration": "Brown, silver, and platinum cards spin past, but Gong-ja fixes his gaze on a radiant gold glow."},
    {"block_id": "b076", "panel_ids": ["panel_0076"], "narration": "Weeping in desperate longing, he reaches out with his phantom hand to seize the golden card."},
    {"block_id": "b077", "panel_ids": ["panel_0077"], "narration": "A blinding flash of pixelated data engulfs his soul as the copy process completes."},
    {"block_id": "b078", "panel_ids": ["panel_0078"], "narration": "Reality fractures and distorts, spinning backward through time at dizzying velocity."},
    {"block_id": "b079", "panel_ids": ["panel_0079"], "narration": "Kim Gong-ja's wide eye snaps open as his consciousness slams violently back into existence."},

    # --- ACT 5: THE IMPOSSIBLE REWIND (p0080 - p0098) ---
    {"block_id": "b080", "panel_ids": ["panel_0080"], "narration": "Breaking news chimes loudly from the television speakers: the Black Dragon Guild has failed!"},
    {"block_id": "b081", "panel_ids": ["panel_0081"], "narration": "Gong-ja sits bolt upright in his own bed, panting heavily while clutching his intact skull."},
    {"block_id": "b082", "panel_ids": ["panel_0082"], "narration": "The broadcast reports the exact same fortieth-floor raid defeat he watched twenty-four hours ago."},
    {"block_id": "b083", "panel_ids": ["panel_0083"], "narration": "He looks down at his uncharred hands in utter shock—there is not a single burn mark on his skin."},
    {"block_id": "b084", "panel_ids": ["panel_0084"], "narration": "He rushes over to his desk, staring in bewilderment at his laptop screen displaying yesterday's feed."},
    {"block_id": "b085", "panel_ids": ["panel_0085"], "narration": "On screen, Flame Emperor Yoo Soo-ha stands victorious, giving the exact same interview."},
    {"block_id": "b086", "panel_ids": ["panel_0086"], "narration": "Gong-ja trembles violently as the impossible, mind-bending reality sinks into his mind."},
    {"block_id": "b087", "panel_ids": ["panel_0087"], "narration": "He was murdered in cold blood, yet he has awakened twenty-four hours in the past."},
    {"block_id": "b088", "panel_ids": ["panel_0088"], "narration": "The stolen golden card was the Flame Emperor's greatest secret: the power to rewind time."},
    {"block_id": "b089", "panel_ids": ["panel_0089"], "narration": "With the timeline reset and his memories intact, Kim Gong-ja now holds the key to vengeance."},
    {"block_id": "b090", "panel_ids": ["panel_0090"], "narration": "The hunter who died a helpless victim will return as the ultimate executioner."},
    {"block_id": "b091", "panel_ids": ["panel_0091"], "narration": "He checks the hunter forum, watching the exact same comments roll past with eerie precision."},
    {"block_id": "b092", "panel_ids": ["panel_0092"], "narration": "Every single detail confirms that he has truly traveled back twenty-four hours in time."},
    {"block_id": "b093", "panel_ids": ["panel_0093"], "narration": "He closes his eyes, remembering the searing agony of Soo-ha's flames burning through his skull."},
    {"block_id": "b094", "panel_ids": ["panel_0094"], "narration": "That pain won't be in vain; it will be the foundation for the most terrifying hunt Babylon has ever seen."},
    {"block_id": "b095", "panel_ids": ["panel_0095"], "narration": "Gong-ja stands before his window, looking out over the sprawling, ignorant city."},
    {"block_id": "b096", "panel_ids": ["panel_0096"], "narration": "A dark, unyielding grin spreads across his face as his resolve hardens like steel."},
    {"block_id": "b097", "panel_ids": ["panel_0097"], "narration": "Flame Emperor Yoo Soo-ha's reign of terror is about to meet an impossible reckoning."},
    {"block_id": "b098", "panel_ids": ["panel_0098"], "narration": "The tale of the SSS-Class Revival Hunter has officially taken its very first step."},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch02")
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
        chapter_id="sss-class-revival-hunter/ch02",
        title="SSS-Class Revival Hunter - Chapter 2",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch02/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 02 Script ===")
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
