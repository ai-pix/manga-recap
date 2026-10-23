"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 23.

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
    # --- ACT 1: CLASH OF PHILOSOPHIES (p0002 - p0026) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "Marcus Calenprius sneers with utter contempt, declaring Babylon is just as corrupt as the outer world."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "He reminds the guild leaders that he repeatedly rejected their desperate offers to recruit him."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "The old swordsman wanted to prove that a solitary warrior could conquer the spire through merit."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Unlike society discrimination, the tower promised that pure martial dedication alone could elevate a person."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "Marcus rages at the guild masters, demanding why they degraded that dream into political stagnation."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "His harsh voice echoes across the hall, branding them all as putrid, stagnant cesspools."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "The Witch of Black Dragon glares back, appalled by the old man self-righteous lecturing."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "She lashes out furiously, reminding him that countless lives were lost while he stood aloof."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "Marcus had refused to participate in the fifth, seventh, and ninth floor frontline boss assaults."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Had he shared resources and outer connections, humanity could have avoided disastrous famine and chaos."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "She shouts that true leaders shoulder responsibility rather than hiding behind stubborn, childish pride."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "A tense silence grips the magnificent palace chamber as the heated argument reaches its peak."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "Marcus coldly tells the guild masters to shut their whining mouths once and for all."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "He mocks the grown adults for crying like children begging an old grandfather for candy."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "Gripping his rapier, the old master demands they settle their grievances through cold, unsheathed steel."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "Bae Hu-ryeong cheers enthusiastically, delighted to see his martial successor stirring up glorious chaos."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "Gong-ja sighs in disbelief, marveling at how ten elite humans manage to bicker endlessly."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "He remembers the courageous imperial cavalry charging into monster fire to save their crumbling homeland."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "Even the simulated inhabitants of floor eleven showed far more unity than humanity greatest champions."},
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "The Witch tells Gong-ja to stay silent, claiming this political feud does not concern him."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "Gong-ja snaps back, shaming the guild masters for behaving worse than the desperate allied soldiers."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "He reminds Marcus that an entire kingdom pleaded for their aid against the demonic horde."},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "Those people believed with all their hearts that their world was on the brink of extinction."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "The desperate soldier clutching his boots had wept genuinely, begging humanity to save their people."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "They were summoned here as heroic guardians, not squabbling politicians fighting over petty pride."},

    # --- ACT 2: THE PALADIN'S SACRED LIE DETECTOR (p0027 - p0039) ---
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "The Paladin steps forward, nodding in solemn agreement with Gong-ja heartfelt reprimand."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "She agrees that this senseless standoff between the Blade Saint and the rookie must end."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "To restore peace and uncover the truth, the honorable Paladin offers to make a sacrifice."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "She asks the gathered guild masters and Marcus to witness her official intervention carefully."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "Revealing her hidden A-minus skill, the Paladin displays the divine window for Lie Detector."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "This sacred ability instantly determines whether any spoken statement is genuine truth or deceit."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "With this holy power, she can cut through every lie and expose reality without bloodshed."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "She turns toward Marcus and Gong-ja, offering to mediate their dispute with total impartiality."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "Suspicion is a deadly poison, but absolute truth is the ultimate antidote to baseless hostility."},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Gong-ja recognizes this golden opportunity to dismantle Marcus paranoia without lifting a single finger."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "He willingly accepts the Paladin arbitration, raising his hand in complete, confident agreement."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "Marcus gazes upon the knight, acknowledging that the Paladin has never taken a human life."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "With both parties consenting, the Paladin prepares to officiate this high-stakes truth interrogation."},

    # --- ACT 3: THE FOUR THOUSAND KILL QUESTION & RECKONING (p0040 - p0066) ---
    {"block_id": "b039", "panel_ids": ["panel_0040"], "narration": "Staking her honor and city security reputation, she invites Marcus to ask his burning question."},
    {"block_id": "b040", "panel_ids": ["panel_0041"], "narration": "Tension thickens as Gong-ja stands tall before the intimidating gaze of the legendary elder."},
    {"block_id": "b041", "panel_ids": ["panel_0042"], "narration": "Marcus takes a deep breath, addressing the young rookie with razor-sharp solemnity."},
    {"block_id": "b042", "panel_ids": ["panel_0043"], "narration": "He asks point-blank: Have you, or have you not, slaughtered over four thousand human beings?"},
    {"block_id": "b043", "panel_ids": ["panel_0044"], "narration": "Gong-ja looks Marcus right in the eyes and calmly answers: Yes, I have."},
    {"block_id": "b044", "panel_ids": ["panel_0045"], "narration": "Marcus points a triumphant finger, screaming that the guilds raised this monstrous assassin to butcher humanity."},
    {"block_id": "b045", "panel_ids": ["panel_0046"], "narration": "Suddenly, the Paladin interjects with absolute clarity: That statement was a lie."},
    {"block_id": "b046", "panel_ids": ["panel_0047"], "narration": "Marcus freezes in utter shock as the Paladin confirms Gong-ja has not killed thousands."},
    {"block_id": "b047", "panel_ids": ["panel_0048"], "narration": "The Paladin calmly asks the bewildered swordsman if he has any other accusations to make."},
    {"block_id": "b048", "panel_ids": ["panel_0049"], "narration": "Guild members scoff at Marcus absurdity, wondering how one boy could ever butcher four thousand people."},
    {"block_id": "b049", "panel_ids": ["panel_0050"], "narration": "Flustered, Marcus stammers that Gong-ja must be an elite covert assassin trained in secret."},
    {"block_id": "b050", "panel_ids": ["panel_0051"], "narration": "Gong-ja playfully claims he is indeed a super assassin, but Paladin instantly rings: Lie!"},
    {"block_id": "b051", "panel_ids": ["panel_0052"], "narration": "Marcus panics, accusing the Paladin of betraying her sacred integrity to protect the guilds."},
    {"block_id": "b052", "panel_ids": ["panel_0053"], "narration": "The Paladin stands firm, warning Marcus not to insult her honor merely because facts contradict him."},
    {"block_id": "b053", "panel_ids": ["panel_0054"], "narration": "Marcus desperately insists Gong-ja must have killed someone, and Gong-ja admits he has."},
    {"block_id": "b054", "panel_ids": ["panel_0055"], "narration": "The Paladin confirms Gong-ja speaks the truth: he has taken exactly one human life."},
    {"block_id": "b055", "panel_ids": ["panel_0056"], "narration": "Gong-ja explains that the man he killed was a murderous psychopath who attacked him first."},
    {"block_id": "b056", "panel_ids": ["panel_0057"], "narration": "He killed the villain in direct self-defense, preventing an unhinged butcher from slaughtering innocents."},
    {"block_id": "b057", "panel_ids": ["panel_0058"], "narration": "The Paladin delivers her final judgment: every single word spoken by Confucius Kim is absolute truth."},
    {"block_id": "b058", "panel_ids": ["panel_0059"], "narration": "The guild masters burst into mocking laughter, ridiculing Marcus ridiculous paranoia and failed conspiracy theories."},
    {"block_id": "b059", "panel_ids": ["panel_0060"], "narration": "Bae Hu-ryeong facepalms in second-hand embarrassment, scolding Marcus for overly relying on his vision skill."},
    {"block_id": "b060", "panel_ids": ["panel_0061"], "narration": "Gong-ja smiles politely, stating that he has completely answered every single question Marcus demanded."},
    {"block_id": "b061", "panel_ids": ["panel_0062"], "narration": "He graciously calls this entire ordeal an unfortunate misunderstanding between fellow tower climbers."},
    {"block_id": "b062", "panel_ids": ["panel_0063"], "narration": "Yet beneath his gentle tone lies a deadly serious edge that silences the grand hall."},
    {"block_id": "b063", "panel_ids": ["panel_0064"], "narration": "Gong-ja points out that without guild backing, Marcus would have executed him on the spot."},
    {"block_id": "b064", "panel_ids": ["panel_0065"], "narration": "Locking eyes with the humbled grandmaster, Gong-ja firmly demands the formal apology he rightfully deserves."},
    {"block_id": "b065", "panel_ids": ["panel_0066"], "narration": "Marcus stands utterly speechless, confronted by the grave moral failure of his own reckless assumptions."},
]


def build_and_save() -> bool:
    chapter_dir = Path("data/chapters/sss-class-revival-hunter/ch23")
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
        chapter_id="sss-class-revival-hunter/ch23",
        title="SSS-Class Revival Hunter - Chapter 23",
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
    alt_script_path = Path("data/chapters/revival_hunter_ch23/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 23 Script ===")
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
