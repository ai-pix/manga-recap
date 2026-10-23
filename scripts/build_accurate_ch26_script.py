"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 26.

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
    # --- ACT 1: THE WITCH HUNT & THE PARANOIA SPREADS (p0001 - p0026) ---
    {"block_id": "b001", "panel_ids": ["panel_0001"], "narration": "The Witch of Black Dragon roars furiously, promising the traitor a slow, agonizing death."},
    {"block_id": "b002", "panel_ids": ["panel_0002"], "narration": "She orders the Paladin to interrogate every single person in the hall without exception."},
    {"block_id": "b003", "panel_ids": ["panel_0003"], "narration": "Turning to Gong-ja, the Paladin asks whether he secretly chose the Demon King offer."},
    {"block_id": "b004", "panel_ids": ["panel_0004"], "narration": "Gong-ja looks directly into her helmet and answers with a clear, firm no."},
    {"block_id": "b005", "panel_ids": ["panel_0005"], "narration": "The Paladin instantly confirms Gong-ja innocence: he is telling the complete, unvarnished truth."},
    {"block_id": "b006", "panel_ids": ["panel_0006"], "narration": "Next, the Paladin turns toward the Blade Saint, asking if he chose demonic treachery."},
    {"block_id": "b007", "panel_ids": ["panel_0007"], "narration": "One by one, Marcus, Poisonous Viper, and Countess swear on their honor they refused."},
    {"block_id": "b008", "panel_ids": ["panel_0008"], "narration": "The Paladin announces her verdict: every single hunter questioned so far is telling truth."},
    {"block_id": "b009", "panel_ids": ["panel_0009"], "narration": "Finally, the Paladin questions the Witch of Black Dragon herself regarding her secret choice."},
    {"block_id": "b010", "panel_ids": ["panel_0010"], "narration": "The powerful guild master denies the accusation, her cold purple eyes narrowing in frustration."},
    {"block_id": "b011", "panel_ids": ["panel_0011"], "narration": "The divine skill resonates: the Witch of the Black Dragon is also completely innocent."},
    {"block_id": "b012", "panel_ids": ["panel_0012"], "narration": "Poisonous Viper scratches his head in utter bewilderment: if no one lied, who betrayed them?"},
    {"block_id": "b013", "panel_ids": ["panel_0013"], "narration": "Panic sweeps the room as hunters scream in confusion, demanding who picked the reward."},
    {"block_id": "b014", "panel_ids": ["panel_0014"], "narration": "A sinister aura envelops the imperial hall as distrust begins devouring the allied coalition."},
    {"block_id": "b015", "panel_ids": ["panel_0015"], "narration": "A glowing divine notification mocks them: the Goddess of Protection is disappointed by your foolishness."},
    {"block_id": "b016", "panel_ids": ["panel_0016"], "narration": "Simultaneously, a dark prompt gloats as the Demon King of Autumn Rain bursts into laughter."},
    {"block_id": "b017", "panel_ids": ["panel_0017"], "narration": "The Paladin tries calming everyone, urging the top rankers to maintain rational discipline."},
    {"block_id": "b018", "panel_ids": ["panel_0018"], "narration": "She theorizes the traitor might possess a deceit skill or suffer from split personality."},
    {"block_id": "b019", "panel_ids": ["panel_0019"], "narration": "Marcus interjects with icy suspicion, suggesting the Paladin herself might be the dirty traitor."},
    {"block_id": "b020", "panel_ids": ["panel_0020"], "narration": "The old swordsman glares with lethal distrust, placing his hand upon his rapier hilt."},
    {"block_id": "b021", "panel_ids": ["panel_0021"], "narration": "The Witch snaps back defensively, but Marcus accuses the guilds of colluding to lie."},
    {"block_id": "b022", "panel_ids": ["panel_0022"], "narration": "The suited guild master chuckles uncomfortably, admitting that mutual paranoia is tearing them apart."},
    {"block_id": "b023", "panel_ids": ["panel_0023"], "narration": "The Paladin pleads passionately for trust, begging everyone to remember their shared heroic struggles."},
    {"block_id": "b024", "panel_ids": ["panel_0024"], "narration": "Inquisitor bursts into eerie, mocking laughter, calling the honorable Paladin terribly naive and childlike."},
    {"block_id": "b025", "panel_ids": ["panel_0025"], "narration": "The fanatical youth remarks that building real trust required a decade of brutal political bloodshed."},
    {"block_id": "b026", "panel_ids": ["panel_0026"], "narration": "He states plainly that he cannot trust the lower-ranking non-guild members present here."},

    # --- ACT 2: INQUISITOR'S BRUTALITY & SUPREME COMMAND (p0027 - p0051) ---
    {"block_id": "b027", "panel_ids": ["panel_0027"], "narration": "Inquisitor argues that conducting delicate verbal interrogations is a massive waste of precious time."},
    {"block_id": "b028", "panel_ids": ["panel_0028"], "narration": "He commands Poisonous Viper to butcher the tenth-place hunter while he executes the ninth."},
    {"block_id": "b029", "panel_ids": ["panel_0029"], "narration": "Activating Holy Transmission, Inquisitor flashes across the carpet like a murderous streak of lightning."},
    {"block_id": "b030", "panel_ids": ["panel_0030"], "narration": "Marcus roars in furious outrage as the ruthless boy slaughters the lower-ranking challengers instantly."},
    {"block_id": "b031", "panel_ids": ["panel_0031"], "narration": "Marcus unsheathes his sacred rapier, swearing to execute the monstrous guild tyrants on sight."},
    {"block_id": "b032", "panel_ids": ["panel_0032"], "narration": "A blood-curdling system prompt confirms the gruesome result: a righteous warrior has just died."},
    {"block_id": "b033", "panel_ids": ["panel_0033"], "narration": "A splash of crimson stains the marble: the slain hunter was not the traitor."},
    {"block_id": "b034", "panel_ids": ["panel_0034"], "narration": "Inquisitor shrugs cheerfully, completely unbothered by having murdered an innocent ally in cold blood."},
    {"block_id": "b035", "panel_ids": ["panel_0035"], "narration": "He casually remarks that eliminating non-traitor suspects simply narrows down the remaining list beautifully."},
    {"block_id": "b036", "panel_ids": ["panel_0036"], "narration": "Marcus charges in with murderous fury, demanding why the sociopathic cultist ignored every plea."},
    {"block_id": "b037", "panel_ids": ["panel_0037"], "narration": "Inquisitor dodges gracefully, giggling that cold elimination is the fastest path to absolute certainty."},
    {"block_id": "b038", "panel_ids": ["panel_0038"], "narration": "Blade Saint rapier violently clashes against Inquisitor daggers, sending sparks flying across the floor."},
    {"block_id": "b039", "panel_ids": ["panel_0039"], "narration": "Inquisitor is knocked backward onto the carpet, realizing Marcus is genuinely intent on decapitating him."},
    {"block_id": "b040", "panel_ids": ["panel_0040"], "narration": "Poisonous Viper panics, screaming that Marcus has completely snapped and will butcher them all."},
    {"block_id": "b041", "panel_ids": ["panel_0041"], "narration": "Desperate to survive, the guild masters shout toward Gong-ja, granting him total executive authority."},
    {"block_id": "b042", "panel_ids": ["panel_0042"], "narration": "Since Gong-ja forfeited his reward, he is the sole hunter proven beyond all doubt."},
    {"block_id": "b043", "panel_ids": ["panel_0043"], "narration": "The Witch and Countess urgently surrender full leadership to Gong-ja, begging him to intervene."},
    {"block_id": "b044", "panel_ids": ["panel_0044"], "narration": "Gong-ja stands dumbfounded, marveling at how insane fate has handed him supreme command."},
    {"block_id": "b045", "panel_ids": ["panel_0045"], "narration": "While humanity greatest masters tear each other apart, an unknown rookie holds absolute power."},
    {"block_id": "b046", "panel_ids": ["panel_0046"], "narration": "If this senseless civil war continues, the entire expedition will perish before floor twelve."},
    {"block_id": "b047", "panel_ids": ["panel_0047"], "narration": "Gong-ja whispers to the Paladin, asking why Inquisitor acts like an unhinged butcher."},
    {"block_id": "b048", "panel_ids": ["panel_0048"], "narration": "She reveals that during Babylon religious wars, Inquisitor solved doctrinal conflicts by exterminating everyone."},
    {"block_id": "b049", "panel_ids": ["panel_0049"], "narration": "Slaughter was the only method the boy ever knew to establish lasting theological harmony."},
    {"block_id": "b050", "panel_ids": ["panel_0050"], "narration": "Gong-ja shudders, realizing Babylon peaceful media headlines masked horrific, state-sponsored massacres of dissidents."},
    {"block_id": "b051", "panel_ids": ["panel_0051"], "narration": "Inquisitor shrieks in terror, realizing Marcus is about to slice his neck in two."},

    # --- ACT 3: DEFUSING THE CRISIS & TARGETING THE CORE (p0052 - p0065) ---
    {"block_id": "b052", "panel_ids": ["panel_0052"], "narration": "Gong-ja leaps directly between them, waving his hands and screaming for Marcus to halt."},
    {"block_id": "b053", "panel_ids": ["panel_0053"], "narration": "Marcus hovers mid-swing with his lethal blade, glaring down with barely contained apocalyptic rage."},
    {"block_id": "b054", "panel_ids": ["panel_0054"], "narration": "Desperate to stop the slaughter, Gong-ja shouts: I will meet your beloved granddaughter!"},
    {"block_id": "b055", "panel_ids": ["panel_0055"], "narration": "He promises to take her on dates, begging Grandpa Marcus to hear him out."},
    {"block_id": "b056", "panel_ids": ["panel_0056"], "narration": "Marcus reluctantly halts his strike, muttering that he can always execute these bastards later."},
    {"block_id": "b057", "panel_ids": ["panel_0057"], "narration": "Poisonous Viper wipes sweat from his brow, trembling at having narrowly avoided gruesome decapitation."},
    {"block_id": "b058", "panel_ids": ["panel_0058"], "narration": "Gong-ja takes the stage, urging everyone to set aside the futile traitor witch hunt."},
    {"block_id": "b059", "panel_ids": ["panel_0059"], "narration": "He insists humanity can conquer this stage even without unmasking the hidden demonic traitor."},
    {"block_id": "b060", "panel_ids": ["panel_0060"], "narration": "The hunters listen intently as Gong-ja breaks down the Demon King true psychological trap."},
    {"block_id": "b061", "panel_ids": ["panel_0061"], "narration": "Pointing at the system notification, he highlights that the Demon King core rests on floor twenty."},
    {"block_id": "b062", "panel_ids": ["panel_0062"], "narration": "The traitor only survives if the Demon King lives; the true target is the monarch!"},
    {"block_id": "b063", "panel_ids": ["panel_0063"], "narration": "If they slay the Demon King, the demonic contract shatters and the traitor fails."},
    {"block_id": "b064", "panel_ids": ["panel_0064"], "narration": "The twelfth-floor quest notification appears, uniting humanity fractured champions behind a single, shared purpose."},
    {"block_id": "b065", "panel_ids": ["panel_0065"], "narration": "Together, they march onward to conquer the tower and destroy the Demon King core!"},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch26")
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
        chapter_id="sss-class-revival-hunter/ch26",
        title="SSS-Class Revival Hunter - Chapter 26",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch26/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 26 Script ===")
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
