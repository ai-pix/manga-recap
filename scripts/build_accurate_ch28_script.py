"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 28.

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
    # --- ACT 1: ENEMY TRAUMA & CHRONICLE OF THE CRIMSON RAIN (p0001 - p0024) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "A solemn voice echoes across the void, declaring Gong-ja a true and valiant warrior."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "A system notification triggers: re-enacting the horrific trauma of the enemy who killed you."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Glitching black static consumes reality, plunging his consciousness into an ancient, tragic memory."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "No one in recorded history knew when, why, or where the nightmare first originated."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "Because penalty severity is low, Gong-ja retains full waking consciousness throughout the memory."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "Whenever the demonic calamity manifested, an unholy deluge of crimson rain suffocated the sky."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "A terrifying dark silhouette sneers down at humanity, mocking their fragile and pathetic existence."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "Wherever the demonic red drops fell, rivers of innocent human blood followed in ruin."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "The demon king mocks mortals for birthing hatred and self-sabotaging their own kindred races."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "With each conquered kingdom, the surviving territories of humanity shrank toward total extinction."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "Noble dynasties vanished one after another, extinguishing thousand-year-old royal legacies in ash."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "Helpless imperial soldiers wept beneath the crimson storm, realizing their glorious empire was doomed."},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "Yet through every defeat, destruction, and massacre, the apocalyptic sky simply rained..."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "The Demon King coldly questioned whether such pathetic, self-destructive creatures deserved to survive."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "Distorted darkness warped the earth as heaven weeping downpour drowned entire generations."},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "Desperate citizens begged toward empty thrones, crying for emperors who had already abandoned them."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "And through centuries of unrelenting sorrow, the cursed crimson clouds simply rained..."},
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "A lone priest slumped over stone tiles, whispering desperate prayers to the Goddess."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "Imperial historians penned their chronicles in trembling ink, recording the end of civilization."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "They calmly accepted their tragic fate, documenting the final days of human history."},
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "An elderly scholar closes the empire last leather-bound history tome with heavy finality."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "The cruel entity gloats over the ashes of kingdoms, mocking their futile resistance."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "His trembling quill seals the title: The Demon King of Autumn Rain."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "The vision violently shatters, snapping Gong-ja awareness back into the present tower battle."},

    # --- ACT 2: RAIN CEASES & THE SUICIDAL STRATEGY (p0025 - p0062) ---
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "Standing upon the ramparts, imperial soldiers blink in utter shock at the clearing skies."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "A thunderous shout of disbelief ripples across the fortress: the crimson rain has stopped!"},
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "Knights collapse to their knees weeping tears of joy, praising the Goddess of Protection."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "A jubilant roar echoes through the ranks: the holy goddess has shielded our kingdom!"},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "Gong-ja observes quietly, knowing the sacred barrier is only a temporary respite."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "Soldiers cheer wildly, their shattered spirits reignited by the holy light of salvation."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "Gong-ja notes that allied troops had previously abandoned hope and retreated from duty."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "Now, seeing the miraculous holy light, soldiers proudly raise their shields to fight."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "Commanding officers scream across the ramparts, ordering men to reform defensive shield walls."},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "Veteran knights reprimand trembling recruits, demanding they stand tall before their imperial flag."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "The Witch of Black Dragon walks through the lines, exhaling a quiet, relieved breath."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "Noticing Gong-ja stare, she asks why he is looking at her so strangely."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "She dryly asks if this is his first time hearing a Ukrainian deliver speeches."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "She quips about political history back home, explaining how speeches shape national resolve."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "Bae Hu-ryeong sighs, concluding that the stern guild master attempted a joke and failed."},
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "Turning toward Gong-ja, the Witch asks for his tactical plan to conquer this stage."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "Gong-ja analyzes her S-class skill, recognizing her spatial magic as their ultimate trump card."},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "He explains they must isolate the enemy supreme commander into a pure duel."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "While the garrison pins down the demon vanguard, an assassin must strike the core."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "Gong-ja makes a jaw-dropping demand: teleport me directly to the Demon King himself!"},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "The Witch stares in disbelief, asking if he is purposely trying to get killed."},
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "Gong-ja replies with unshakable conviction: I plan to win; death does not mean defeat."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "He reassures her that he possesses a secret ace capable of securing absolute victory."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "Accepting that every top hunter carries secrets, the Witch agrees to trust his resolve."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "Across the battlefield, the Demon King looms in black sludge, mocking their holy game."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "Imperial guards struggle against demonic shadows as the siege turns into a bloodbath."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "The monstrous entity sneers at humanity pitiful champions, preparing to crush them completely."},
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "A radiant burst of divine power flares as Countess unleashes her golden arsenal."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "A catastrophic explosion rocks the main hall as demonic shockwaves obliterate the defenses."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "A chilling system notification announces a tragic casualty: a human warrior has perished!"},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "The system prompt confirms the fallen champion was not the Demon King pawn."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "The Witch realizes that Countess fell defending the throne room against the demonic onslaught."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "Countess died fighting bravely for humanity; she was never the hidden traitor among them."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "The Witch clutches her fists, cursing the fallen businesswoman for dying ahead of her."},
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "With Countess gone, their gold supply shatters and the defensive front collapses rapidly."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "Gong-ja urges the grieving leader to stay focused on the immediate tactical objective."},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "Even the Demon King cannot maintain high-intensity assaults indefinitely without leaving vital openings."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "Gazing over the crumbling battlements, the Witch prepares to unleash her spatial magic."},

    # --- ACT 3: TIME ACCELERATION & HERO'S AWAKENING (p0063 - p0076) ---
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "She firmly clasps Gong-ja hands, chanting the ancient invocation for ultimate long-range teleportation."},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "Reality blurs into blinding violet light, dropping Gong-ja directly onto the chaotic frontlines."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "Here on the frontlines, there are no allied troops to watch his back."},
    {"block_id": "b066", "panel_ids": ["panel_0066"], "narration": "Bae Hu-ryeong manifests beside his solitary disciple, addressing him with unusual, serious intensity."},
    {"block_id": "b067", "panel_ids": ["panel_0067"], "narration": "Three colossal goblin berserkers rush forward through the mud, brandishing spiked iron clubs."},
    {"block_id": "b068", "panel_ids": ["panel_0068"], "narration": "The ancient master commands Gong-ja to step forward and become a true hero."},
    {"block_id": "b069", "panel_ids": ["panel_0069"], "narration": "Gong-ja retrieves Celine body-tempering elixir from his inventory, chugging the dense crimson fluid."},
    {"block_id": "b070", "panel_ids": ["panel_0070"], "narration": "Bae Hu-ryeong reminds him that a hero isn merely someone who stays alive; a hero wins!"},
    {"block_id": "b071", "panel_ids": ["panel_0071"], "narration": "The ghost martial master dictates form: angle the back foot and balance front weight."},
    {"block_id": "b072", "panel_ids": ["panel_0072"], "narration": "Two demonic vanguards charge ahead, their bloodshot eyes locked onto the solitary boy."},
    {"block_id": "b073", "panel_ids": ["panel_0073"], "narration": "In elite swordsmanship, subtracting one second of enemy time claims a second of victory."},
    {"block_id": "b074", "panel_ids": ["panel_0074"], "narration": "Flaring with boiling mana, Gong-ja internal clock accelerates beyond his pounding heartbeat rhythm."},
    {"block_id": "b075", "panel_ids": ["panel_0075"], "narration": "He turns to his ghostly mentor with burning crimson eyes: Let go, partner!"},
    {"block_id": "b076", "panel_ids": ["panel_0076"], "narration": "Stepping fearlessly into the slaughter, Confucius Kim declares: It time to be a hero!"},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch28")
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
        chapter_id="sss-class-revival-hunter/ch28",
        title="SSS-Class Revival Hunter - Chapter 28",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch28/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 28 Script ===")
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
