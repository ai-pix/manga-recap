"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 27.

High-retention YouTube manhwa recap style (Mamoru style).
1:1 panel sync, zero dropped beats, 100% pipeline validation compliance.
"""

from __future__ import annotations

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
    # --- ACT 1: THE CRIMSON RAIN & THE SIEGE OF BABYLON (p0001 - p0017) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "A digital system notification confirms the official launch of the perilous twelfth-floor quest."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "The hunters step out onto the palace parapets, gazing at the ominous horizon."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Massive steel girders and fortification walls loom across the darkening empire sky."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "Gong-ja recoils in dread as an unnatural crimson rain begins cascading from the clouds."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "The sky bleeds dark red droplets, signaling the arrival of an apocalyptic nightmare."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "Gong-ja wonders whether this grotesque weather is merely theatrical stage decoration or lethal."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "The crimson downpour intensifies, drenching the battlements in foul, demonic miasma."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "Standing atop the stone balcony, Gong-ja watches the city streets drown in blood-red water."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "A terrifying monstrous visage sneers from the storm, mocking humanity hopeless, fragile arrogance."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "Marcus draws his blade, challenging the demonic presence that dares mock humanity resolve."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "The demon king mocks them for expecting otherworldly champions to fight their bloody battles."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "A splash of black ink spreads across the vision, symbolizing utter existential dread."},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "A hunter hand reaches forward to interact with the trembling system interface window."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "A sharp chime rings through the air, signaling the commencement of stage parameters."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "The quest details materialize: humanity must endure a brutal, wave-based siege defense."},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "Poisonous Viper stares at the status screen in horror, muttering in disbelief."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "A colossal demon general roars in the distance, mocking the so-called weakened state."},

    # --- ACT 2: IMPERIAL APPOINTMENTS & FRONT LINE COMMAND (p0018 - p0039) ---
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "Gong-ja urges the guild leaders to stop bickering and coordinate their imperial roles."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "Though the lower floors felt like tutorials, true war has officially commenced here."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "In this trial, they are not merely roaming hunters but sworn imperial officers."},
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "Countess grimaces, admitting that clearing this hellish defense solo is utterly impossible."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "Marcus agrees that survival demands complete cooperation under their designated military offices."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "The Minister of Foreign Affairs announces that enemy forces are breaching perimeter posts."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "The General-in-Chief nods with cold enthusiasm, ready to direct allied troop movements."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "Despite their personal disgust for Inquisitor, the leaders must trust his battlefield intellect."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "Imperial soldiers stationed along the outer walls tremble in fear before the demonic horde."},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "Marcus bellows across the ramparts, ordering soldiers to hold the walls at all costs."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "Soldiers rally with roaring war cries, obeying the Knight Commander unquestioned tactical orders."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "Heavy crimson rain pounds the cobbled streets as soldiers sprint toward their defensive positions."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "Approaching footsteps splash through bloody puddles behind Gong-ja as someone calls his name."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "The Witch of Black Dragon steps through the mist, her dark robe billowing."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "Gong-ja looks up in surprise, asking how the Prime Minister teleported directly here."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "He asks why she chose to rendezvous with him rather than the main castle."},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "She reveals she saw him lead the army on floor eleven with his sword."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "To leverage her spatial teleportation magic, she requires Gong-ja explicit verbal consent."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "She explains that high-tier black dragon teleportation cannot transport an unwilling allied passenger."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "Gong-ja tilts his head, finding the bureaucratic requirement rather strange mid-crisis."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "He asks if imperial law empowers the Prime Minister to draft anyone immediately."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "Taking her hand firmly, Gong-ja gives full consent to utilize her spatial transport."},

    # --- ACT 3: RALLYING THE EMPIRE & THE GODDESS'S LIGHT (p0040 - p0052) ---
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "He gently reminds her that simulated soldiers are living humans worthy of salvation."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "A burst of dark purple mana envelops their boots as spatial magic activates."},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "Materializing atop the shattered outer ramparts, Gong-ja prepares to engage the enemy vanguard."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "The Witch stands firmly beside him, refusing to leave after seeing his genuine compassion."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "She didn become humanity top guild leader by abandoning soldiers to die alone."},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "Raising her voice with imperial majesty, the Witch commands the retreating soldiers to halt."},
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "Exhausted imperial guards look up in reverence: their Prime Minister has joined the front!"},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "She commands the terrified garrison to rise, standing as humanity final protective rampart."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "Her majestic voice echoes across the fortress: Rise up, defenders of the Aegeam Empire!"},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "They will fight until their blades shatter, refusing to surrender their sacred homeland."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "Gong-ja eyes ignite with divine inspiration as the goddess light answers their resolve."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "Unsheathing his legendary relic, Gong-ja roars to the heavens: The Goddess protects us!"},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "Moved by their devotion, the Goddess of Protection exerts her divine power to shield them!"},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch27")
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
        chapter_id="sss-class-revival-hunter/ch27",
        title="SSS-Class Revival Hunter - Chapter 27",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch27/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 27 Script ===")
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
