"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 29.

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
    # --- ACT 1: SWORDSMANSHIP AGAINST TIME & THE RANK UP (p0001 - p0020) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "Bae Hu-ryeong coaches sharply from behind, commanding his disciple to immediately engage the next target."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "Kim Gong-ja swings his blade relentlessly, cutting down monsters in seamless, unbroken succession."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "His translucent crystalline hilt gleams brightly as lethal aura arcs across the battlefield."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "The ancient sword emperor counts aloud: that single lethal exchange took exactly one second."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "He screams at Gong-ja never to pause; every cut must flow directly into another."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "A downward slash must instantly transition into an upward horizontal cleave without hesitation."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "Wielding a sword at the highest pinnacle is fundamentally a desperate fight against time."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "The ghost martial master barks sternly: never lose track of a single fleeting microsecond!"},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "Killing one monster means nothing; true survival demands vigilance for the next strike."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "A hulking green brute charges forward, swinging an enormous stone club with bone-crushing force."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "Leaping backward through the air, Gong-ja ponders why the tower gave Yoo Soo-ha an EX-rank skill."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "Did the tower believe only selfish, psychopathic butchers had the ruthlessness to conquer it?"},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "Was this twisted spire built solely for vile monsters who trample upon the weak?"},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "Gong-ja burning indignation roars from the bottom of his soul against such cynical injustice."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "He furiously rejects that worldview: do not dare feed me such disgusting bullshit!"},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "He vows to conquer floor twenty instead of the Flame Emperor, rectifying history mistakes."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "He will conquer the fiftieth floor, then seventieth, scaling all the way to floor one hundred!"},
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "A golden system chime echoes through his soul: a layer of hunter existence has shattered."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "The system declares that Confucius Kim has officially ranked up on the tower registry."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "Standing blood-soaked amid monster corpses, Gong-ja watches the thirty-second milestone flash across his vision."},

    # --- ACT 2: BROTHERS IN ARMS & BATTLE TRANCE (p0021 - p0043) ---
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "A distinguished older figure steps through the raining mist, gazing upon the rookie with reverence."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "Silver steel flashes across the mud, effortlessly bisecting another charging wave of green monsters."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "Marcus Calenprius smiles warmly, praising the boy breathtaking combat technique with genuine admiration."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "The venerable master introduces himself with absolute humility: My name is Marcus Calenprius."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "Gong-ja remembers his previous life, where the Flame Emperor murdered him without a second thought."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "It suddenly dawns upon him how fundamentally he has grown and transformed since then."},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "Bowing respectfully with a determined glint in his eyes, he replies: My name is Confucius Kim."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "The iconic title blazes across destiny: SSS-Class Revival Hunter marches toward his future."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "Extending his blade beside Gong-ja, Marcus declares with pride: Let us fight together, young warrior!"},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "Humanity top-ranked hunter, the legendary Blade Saint, now stands as his sworn battlefield ally."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "A joyful shout rings out as General-in-Chief Inquisitor arrives with allied relief battalions."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "The eccentric blonde youth apologizes for the delay, having mobilized troops across the city."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "He thanks Gong-ja profusely for buying crucial time to secure the outer imperial perimeter."},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "Inquisitor commands the newly deployed imperial platoons to unleash total firepower upon the vanguard."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "Armored knights charge the horde with roaring fury: Stand firm, for the Goddess protects us!"},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "Poisonous Viper dashes past Gong-ja, slapping his shoulder in rough, brotherly approval."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "Viper brandishes his twin silver blades, eager to demonstrate why his guild rules the underworld."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "Seeing Gong-ja intense focus, Viper realizes the young prodigy is fully immersed in battle trance."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "The veteran introduces his real name as Liao Fan, recognizing Gong-ja as a true comrade."},
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "Viper leaps into the demonic tide, promising to clear a direct path toward the demon monarch."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "Viper yells over the roar of clashing steel: Push forward, rising star; I will protect you!"},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "The Minister of Foreign Affairs sprints up, announcing he located the emperor amidst the ruins."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "The monarch is trembling in catatonic shock, weeping helplessly as his imperial legacy collapses."},

    # --- ACT 3: THE SUICIDE GAMBIT & ROUND TWO (p0044 - p0072) ---
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "From the darkened storm above, a monstrous sneer echoes down: Pathetic, fragile fools!"},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "The Demon King of Autumn Rain emerges from the abyss, mocking their borrowed, fleeting hope."},
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "The demonic sovereign demands what remaining salvation humanity can possibly cling to in despair."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "Dark miasma surges outward like black tsunami waves, threatening to swallow the entire royal palace."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "Marcus screams for the Witch to activate her spatial mirrors and evacuate the vanguard."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "The Witch commands the battlefield with regal authority, barking a single tactical directive: Scatter!"},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "She coordinates defensive maneuvers, positioning Marcus and Poisonous Viper to counter the shockwave."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "The two legendary fighters clash in mid-air, repelling the demonic tendrils with dazzling martial precision."},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "The Witch summons her spatial circle, ordering the hunters to gather for mass emergency teleportation."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "Noticing Gong-ja standing outside the circle, the guild masters scream his name in sheer panic."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "They frantically urge him to jump inside the portal before the spatial magic closes."},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "Gong-ja turns his back on safety, walking directly toward the towering demonic abyss."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "He recalls Marcus heartfelt apology and the allied champions who staked their lives for him."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "Bae Hu-ryeong whispers softly beside him, preparing his disciple for the ultimate gambit."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "The ghost smiles proudly: it is time to take down the final boss, partner."},
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "Gong-ja smirks back, embracing the insane superpower that turns death into his greatest weapon."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "Just like a desperate man resets to square one, he prepares to rewrite fate!"},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "Blinding violet spatial light flashes as the guild leaders teleport away to safety."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "The Demon King gazes down upon the solitary boy remaining behind, amused by his audacity."},
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "The colossal monster scoffs: do the Goddess warriors truly believe one mortal can oppose me?"},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "The demon monarch warns that a traitor lurks among humanity, doomed to betray their trust."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "Does Gong-ja truly believe placing faith in treacherous allies can change his gruesome destiny?"},
    {"block_id": "b066", "panel_ids": ["panel_0066"], "narration": "Towering walls of black stone crumble around them as apocalyptic pressure crushes the earth."},
    {"block_id": "b067", "panel_ids": ["panel_0067"], "narration": "The Demon King laughs menacingly: how utterly foolish to stand alone before a god."},
    {"block_id": "b068", "panel_ids": ["panel_0068"], "narration": "The shadowy sovereign looms over Gong-ja, sneering: Have you come to kill me, warrior?"},
    {"block_id": "b069", "panel_ids": ["panel_0069"], "narration": "Kim Gong-ja smiles calmly, shaking his head with razor-sharp irreverence: Nope."},
    {"block_id": "b070", "panel_ids": ["panel_0070"], "narration": "Leaping forward with unhinged swagger, he roars: I came for you to kill me, fucker!"},
    {"block_id": "b071", "panel_ids": ["panel_0071"], "narration": "Death is not his end; death is merely the beginning of his hunt."},
    {"block_id": "b072", "panel_ids": ["panel_0072"], "narration": "As darkness claims his vision, Gong-ja grins: Now then, it is time for round two!"},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch29")
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
        chapter_id="sss-class-revival-hunter/ch29",
        title="SSS-Class Revival Hunter - Chapter 29",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch29/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 29 Script ===")
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