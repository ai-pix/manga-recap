"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 6.

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
    # --- ACT 1: OUTCLASSED BY THE BLADE SAINT (p0002 - p0020) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "A deafening metallic clang rings out as cold steel clashes against glowing blue sword aura."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "Marcus lunges with blinding speed, astonished that the hooded youth barely dodged his initial strike."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "Gong-ja recoils backward, realizing the old master's reflexes border on absolute supernatural madness."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Before he can even plant his feet, a heavy leather boot slams violently into his ribs."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "The concussive kick sends him hurtling through the night air like a ragdoll."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "He crashes heavily into the tall grass, choking for breath as dirt fills his mouth."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "The sheer physical gap between an F-rank novice and the world's strongest swordsman is astronomical."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "Gong-ja clutches his bruised chest, acknowledging that surviving the first swing was pure dumb luck."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "There will be no miraculous second evasion against the peerless Blade Saint."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Marcus stands above him with sword drawn, barking sharply into thin air to remain silent."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "He mutters to an invisible companion, asking if he should interrogate the devil before executing him."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "He snaps irritably at the empty breeze, declaring that he will handle the extermination his own way."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "Gong-ja watches in bewilderment, realizing the old man is actively arguing with a phantom voice."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "Marcus looks upward, suspecting Gong-ja possesses a telepathic link with outside syndicates."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "He brings up a floating interface, intending to transmit Gong-ja's kill record to Babylon City Security."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "Gong-ja's heart turns to ice as holographic icons begin broadcasting his profile."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "If a four-thousand-murder bounty hits the Hunter Bureau, every elite guild will hunt him down."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "He will be dragged to Babylon's central plaza and publicly executed before the entire world."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "He must die right now, within the current twenty-four-hour window, to erase this catastrophic timeline."},

    # --- ACT 2: PROVOKING THE TABOO (p0021 - p0039) ---
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "Scrambling to his feet, Gong-ja drops all pretense of innocence and deploys the forbidden weapon."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "He loudly mentions Marcus's aristocratic family living in the wealthy estates of Northern Europe."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "He smirks, remarking that prominent bloodlines always draw dangerous, unsavory crowds."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "Gong-ja stands tall in the clearing, deliberately walking into the lion's open jaws."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "He delivers the lethal provocation: you should tell your precious grandchildren to be extra careful."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "Marcus's face freezes into a mask of pure, apocalyptic murder intent."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "The old master steps forward, his blade igniting with blinding, azure sword aura."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "A downward vertical slash rips through the moonlight faster than the human eye can track."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "Gong-ja feels zero pain as the world tilts, wondering why the moon is suddenly upside down."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "His severed head tumbles through the air, looking up at the inverted silver crescent."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "His body collapses into the grass as his consciousness drifts into peaceful detachment."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "In his final dying gaze, he marvels at the terrifying, breathtaking beauty of Marcus's swordplay."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "The strike was so overwhelmingly fast and pure that he couldn't even see the blade land."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "A familiar, burning envy floods his dying soul: I want to be just like him."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "He envies that absolute mastery with every fiber of his being, yearning for that peerless strength."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "The intense desire to possess that power triggers the cosmic mechanics of his awakening."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "He reaches out toward the fading moon, demanding that martial greatness for himself."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "A brilliant shockwave of golden system energy bursts across the endless dark void."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "A loud digital chime sounds as his soul enters the skill selection dimension."},

    # --- ACT 3: NO GOLD CARDS & THE A+ BLESSING (p0040 - p0066) ---
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "The system window confirms: The requirements for your skill have been fulfilled."},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "Skill cards materialize in the darkness, spinning around his spiritual avatar."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "Gong-ja rubs his hands together eagerly, hunting for the radiant golden gleam of an S-rank card."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "Just like when he stole the Flame Emperor's clock, he expects an overpowered cheat ability."},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "He reaches his finger out toward the storm of floating cards, scanning the ranks."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "He blinks in sudden confusion, cocking his head as cards spin past his vision."},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "He inspects every single card floating in the cosmic void, but something is terribly wrong."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "Why isn't there a single golden card among the Blade Saint's personal deck?"},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "Not a single gold border, not a single S-rank ability, and no mythical cheat codes."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "Gong-ja gasps in utter disbelief as the staggering truth of the Blade Saint is revealed."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "This is completely impossible—how could the number one hunter have no S-rank skill?"},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "Marcus Callenberry conquered the Babel Tower through pure, agonizing human dedication."},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "While others relied on miraculous system gifts, Marcus achieved godhood through raw discipline alone."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "He became the living Blade Saint purely by honing his own flesh, mind, and steel."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Gong-ja collapses onto his knees in the void, filled with profound, overwhelming respect."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "He inspects the cards available: three bronze cards and four gleaming silver cards."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "The three bronze cards are mundane utility skills, completely useless for combat."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "His choice must come from one of the four silver cards hovering before him."},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "One of them holds that troublesome kill-count vision, which Gong-ja desperately avoids."},
    {"block_id": "b058", "panel_ids": ["panel_0059"], "narration": "He focuses all his mental willpower, pleading with the cosmos for the old man's greatest technique."},
    {"block_id": "b059", "panel_ids": ["panel_0060"], "narration": "He lunges forward, seizing the brightest silver card radiating with sharp sword intent."},
    {"block_id": "b060", "panel_ids": ["panel_0061"], "narration": "He remembers the terrifying downward slash that severed his head in the tall grass."},
    {"block_id": "b061", "panel_ids": ["panel_0062"], "narration": "He begs the system to bestow the Blade Saint's true martial inheritance upon him."},
    {"block_id": "b062", "panel_ids": ["panel_0063"], "narration": "He clutches the card tightly against his chest as blinding silver light envelops his avatar."},
    {"block_id": "b063", "panel_ids": ["panel_0064"], "narration": "A resounding chime echoes through eternity: Selection completed, copying skill."},
    {"block_id": "b064", "panel_ids": ["panel_0065"], "narration": "The temporal clock engages: You will respawn twenty-four hours back in time."},
    {"block_id": "b065", "panel_ids": ["panel_0066"], "narration": "Digital static rips through reality, resetting history before the confrontation ever occurred."},

    # --- ACT 4: WAKING UP WITH THE BLADE (p0067 - p0078) ---
    {"block_id": "b066", "panel_ids": ["panel_0067"], "narration": "Gong-ja gasps loudly, sitting bolt upright in his own bed in Babylon."},
    {"block_id": "b067", "panel_ids": ["panel_0068"], "narration": "He touches his intact neck with both hands, confirming that his head is firmly attached."},
    {"block_id": "b068", "panel_ids": ["panel_0069"], "narration": "He immediately commands his hunter ability interface to open to check his rewards."},
    {"block_id": "b069", "panel_ids": ["panel_0070"], "narration": "A third skill gleams in his status menu: Master of the Blade, ranked A-plus."},
    {"block_id": "b070", "panel_ids": ["panel_0071"], "narration": "He slumps back onto his mattress, groaning that he managed to pull another passive skill."},
    {"block_id": "b071", "panel_ids": ["panel_0072"], "narration": "Still, acquiring an A-plus sword mastery from humanity's greatest warrior is an enormous triumph."},
    {"block_id": "b072", "panel_ids": ["panel_0073"], "narration": "He activates the card, feeling foreign martial knowledge and instinct settle deep into his muscles."},
    {"block_id": "b073", "panel_ids": ["panel_0074"], "narration": "Suddenly, a series of heavy, rhythmic thuds rattles the floorboards above his ceiling."},
    {"block_id": "b074", "panel_ids": ["panel_0075"], "narration": "He winces in irritation, wondering what lunatic is doing intense weight training in the middle of the night."},
    {"block_id": "b075", "panel_ids": ["panel_0076"], "narration": "Before he can stand, a furious woman with fiery red hair and bandaged fists looms over him."},
    {"block_id": "b076", "panel_ids": ["panel_0077"], "narration": "She glares down with menacing authority, telling him to keep his nightly training quiet and respectful."},
    {"block_id": "b077", "panel_ids": ["panel_0078"], "narration": "Gong-ja stares up in complete bewilderment as another chaotic encounter enters his resurrected life."},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch06")
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
        chapter_id="sss-class-revival-hunter/ch06",
        title="SSS-Class Revival Hunter - Chapter 6",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch06/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print(f"=== SSS-Class Revival Hunter Ch 06 Script ===")
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
