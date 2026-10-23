"""Accurate 1:1 Script Builder for SSS-Class Revival Hunter Chapter 30.

Mamoru-style YouTube recap tone:
- 1:1 coverage of all 78 story panels (panel_0001 to panel_0078).
- Strictly 8 to 16 words per block.
- ZERO banned words.
- Emotional, strategic, authentic recap of Gong-ja copying Demon King skills,
  briefing the top guilds on the Aegeam Empire war, taking Paladin to the alchemist,
  and baiting Marcus Calenprius into a private standoff.
"""

from datetime import datetime, timezone
from pathlib import Path
import sys

from manga_recap.core.config import load_config
from manga_recap.core.schema import (
    DescriptionFile,
    ScriptBlock,
    ScriptFile,
    load_model,
)
from manga_recap.stages.s3_script.validate import validate

sys.stdout.reconfigure(encoding="utf-8")

blocks_data = [
    # --- ACT 1: THE DEMON KING'S SKILLS & COPYING THE TRAUMA (p0001 - p0022) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "A glowing blue notification announces that a random skill from the Demon King will be copied."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "Bae Hu-ryeong manifests beside him, cheerfully offering to read through each spectral skill card aloud."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Gong-ja eagerly agrees, and the ancient sword master grins, telling his disciple to listen closely."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "The first skill card, Resentment Pours Like Rain, summons crimson downpours from witnessed innocent bloodshed."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "Gong-ja grimly realizes Yoo Soo-ha must have slaughtered his way through this nightmare originally."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "Bae Hu-ryeong flips to the second golden card hovering within their spectral interface."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "This ability, Echoing Cries of a Heart, converts raw emotional fury directly into aura power."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "Gong-ja ponders in deep silence, knowing every tower floor conceals a hidden narrative quest."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "The twelfth floor will be no exception, prompting Hu-ryeong to unveil the third card."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "The crown jewel emerges: Hundred Ghost Summons, resurrecting fallen foes as obedient monstrous thralls."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "Gong-ja inspects the radiant cards, weighing the tactical value of these three extraordinary gifts."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "When Gong-ja makes his selection, the ghost emperor questions his counter-intuitive tactical decision."},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "Gong-ja smirks with unshakable confidence, telling his spectral master to anticipate pure tactical genius."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "Reaching toward the glowing sigil, Gong-ja casually asks about the Blade Saint daily routine."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "Hu-ryeong chuckles that old Marcus follows a ridiculously strict, predictable daily martial routine."},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "Gong-ja demands the old master evening itinerary, planning his next calculated power play."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "Clutching the radiant crystal card, the system confirms his chosen skill has been copied."},
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "Through the supernatural interface, Gong-ja directly experiences the harrowing trauma of the Demon King."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "The agonizing psychological weight lingers as Gong-ja sets that personal tragedy aside for now."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "Saving that monstrous secret for later, he prepares to return to the waking world."},
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "His glorious title echoes across the void: SSS-Class Revival Hunter returns from the dead."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "A brilliant pillar of white light dissolves the abyss, returning him to physical reality."},

    # --- ACT 2: THE GUILD WAR BRIEFING & DEAL WITH TOP HUNTERS (p0023 - p0045) ---
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "The Witch sits in her lounge chair, noticing Gong-ja preparing to depart their gathering."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "Gong-ja explains that the eleventh floor will open soon, requiring urgent personal preparation."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "The Witch questions how anyone can prepare for unknown territory beyond the tenth floor."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "Sensing his eerie certainty, the Witch stares at him with keen curiosity and concern."},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "She gently asks if he feels unwell after enduring such a devastating, brutal battle."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "Pressing his temple, Gong-ja admits standing beside legendary guild masters feels slightly overwhelming."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "Breaking the tension with a grin, Gong-ja claims he knows the upcoming eleventh floor quest."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "The surrounding guild masters perk up, asking if he genuinely plans to share vital intel."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "Gong-ja nods cheerfully, agreeing to divulge everything on one crucial, non-negotiable personal condition."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "Looking into her purple eyes, he asks for a future favor without immediate question."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "The Countess enthusiastically agrees, knowing strategic foresight is worth far more than theoretical gold."},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "Other guild leaders readily concur, recognizing they risk nothing by accepting his simple terms."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "Another hunter chimes in, eager to hear the unprecedented intelligence about the upper floors."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "One by one, the elite guild leaders formally commit to Gong-ja shrewd bargain."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "Quietly congratulating himself, Gong-ja marks step one of his master plan successfully cleared."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "Stepping into the center of the hall, Gong-ja prepares to brief humanity strongest vanguards."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "He reveals the next ten stages revolve entirely around a massive imperial conflict: the Aegeam Empire."},
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "The masters absorb the shocking truth: the tower tutorial has ended, and true warfare begins."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "Finishing his debrief, Gong-ja bids farewell before suddenly calling out to Miss Paladin."},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "Gong-ja invites the armored City Security co-leader to take a brisk thirty-minute walk outside."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "With an easy smile, he promises their confidential discussion will require very little time."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "The stoic armored knight agrees, comfortable stepping away from the bustling guild headquarters."},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "Playfully teasing him, Paladin jokingly accepts his sudden stroll as an unexpected romantic date."},

    # --- ACT 3: LURING THE BLADE SAINT & VISITING THE ALCHEMIST (p0046 - p0078) ---
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "Outside in the crowded plaza, ordinary hunters gossip wildly about who conquered the tenth floor."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "Hovering in the air, Hu-ryeong snaps his attention backward, warning his disciple immediately."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "Gong-ja senses the invisible stalker tailing their footsteps through the crowded thoroughfares."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "Gong-ja warns his spectral companion not to turn around and give their pursuer away."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "The pursuer masterclass stealth makes him practically invisible to ordinary human perception."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "To the untrained observer, it feels as though nobody is lurking in the shadows."},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "Gong-ja remembers the bloody lessons paid in his previous life with bitter clarity."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "Allowing Marcus to stew in toxic suspicion until the twelfth floor spells absolute catastrophe."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "If the Blade Saint suspects a traitor, the entire alliance will tear itself apart."},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "Walking alongside him, Paladin curiously inquires about their actual destination through the streets."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "Noticing the dilapidated alleyways, she wonders why they are heading toward such shady slums."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "In reality, Gong-ja is using this stroll as deliberate bait to reel in Marcus."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "Knowing Marcus routine, Gong-ja intentionally paraded before the old master to provoke surveillance."},
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "Completely unaware of the covert manhunt behind them, Paladin questions what shop awaits."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "He describes a brilliant, struggling alchemist whose remarkable talents deserve official guild backing."},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "Paladin activates her lie detection skill, prompting Gong-ja to respond with transparent sincerity."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "He playfully assures her that if danger arises, he alone would bear the risk."},
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "Detecting absolute honesty in his voice, Paladin apologizes for her habitual professional skepticism."},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "Arriving at the modest workshop, the quirky green-haired alchemist greets Gong-ja with ecstatic warmth."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "Though closing for the evening, she happily keeps the doors open for her savior."},
    {"block_id": "b066", "panel_ids": ["panel_0066"], "narration": "The bubbly alchemist peeks past Gong-ja, curiously inquiring about his heavily armored companion."},
    {"block_id": "b067", "panel_ids": ["panel_0067"], "narration": "Gong-ja proudly introduces her guest as the esteemed co-leader of the City Security."},
    {"block_id": "b068", "panel_ids": ["panel_0068"], "narration": "The poor alchemist gasps in utter terror, terrified by such an imposing law enforcement official."},
    {"block_id": "b069", "panel_ids": ["panel_0069"], "narration": "She throws herself onto the floor, hysterically begging not to be arrested for illegal concoctions."},
    {"block_id": "b070", "panel_ids": ["panel_0070"], "narration": "Paladin lie-detecting abilities trigger again, confirming this eccentric girl is thoroughly, hilariously innocent."},
    {"block_id": "b071", "panel_ids": ["panel_0071"], "narration": "Gong-ja reassures the panicked brewer, singing high praises for her extraordinary alchemical genius."},
    {"block_id": "b072", "panel_ids": ["panel_0072"], "narration": "He explains his true goal: connecting her struggling workshop with major city security contracts."},
    {"block_id": "b073", "panel_ids": ["panel_0073"], "narration": "Gong-ja urges her to offer potion samples, pitching a mutually beneficial long-term partnership."},
    {"block_id": "b074", "panel_ids": ["panel_0074"], "narration": "Overcome with gratitude, the tearful alchemist grabs his arm, praising him as a literal angel."},
    {"block_id": "b075", "panel_ids": ["panel_0075"], "narration": "Before she can finish thanking him, heavy martial footsteps echo ominously into the shop."},
    {"block_id": "b076", "panel_ids": ["panel_0076"], "narration": "Gong-ja sharpens his gaze, knowing his target has walked right into the trap."},
    {"block_id": "b077", "panel_ids": ["panel_0077"], "narration": "Marcus Calenprius commands the room with bone-chilling authority, ordering everyone else to clear out."},
    {"block_id": "b078", "panel_ids": ["panel_0078"], "narration": "The formidable Blade Saint fixes his glare on Gong-ja, demanding an exclusive private interrogation."},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch30")
    desc_path = chapter_dir / "03_descriptions.json"
    script_path = chapter_dir / "04_script.json"

    desc_file = load_model(desc_path, DescriptionFile)

    script_blocks = [
        ScriptBlock(
            block_id=b["block_id"],
            panel_ids=b["panel_ids"],
            narration=b["narration"],
        )
        for b in blocks_data
    ]

    script_file = ScriptFile(
        chapter_id="sss-class-revival-hunter/ch30",
        title="SSS-Class Revival Hunter - Chapter 30",
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

    # Mirror to junction path
    alt_script_path = Path("data/chapters/revival_hunter_ch30/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 30 Script ===")
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
