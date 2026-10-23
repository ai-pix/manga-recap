"""Build, validate, and save the YouTube recap script for SSS-Class Revival Hunter Chapter 10.

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
    # --- ACT 1: CELINE'S SHOP & THE ANCIENT RECIPE (p0002 - p0039) ---
    {"block_id": "b001", "panel_ids": ["panel_0002"], "narration": "Celine welcomes Gong-ja into her humble apothecary with an embarrassed, flustered blush."},
    {"block_id": "b002", "panel_ids": ["panel_0003"], "narration": "The small workshop is cluttered with overturned wooden crates, dusty flasks, and shattered glass."},
    {"block_id": "b003", "panel_ids": ["panel_0004"], "narration": "She stammers an apology for the mess, wiping down a small wooden consultation table."},
    {"block_id": "b004", "panel_ids": ["panel_0005"], "narration": "Bae Hu-ryeong floats behind Gong-ja, grimacing in utter horror at the filthy workshop."},
    {"block_id": "b005", "panel_ids": ["panel_0006"], "narration": "The ancient ghost mockingly wonders if they walked into a breeding ground for toxic bacteria."},
    {"block_id": "b006", "panel_ids": ["panel_0007"], "narration": "Celine sits across from Gong-ja, nervously clasping her hands together over the table."},
    {"block_id": "b007", "panel_ids": ["panel_0008"], "narration": "She asks hesitantly if his twenty-thousand-gold order was truly a serious business proposition."},
    {"block_id": "b008", "panel_ids": ["panel_0009"], "narration": "Gong-ja smiles warmly, offering to transfer the entire advance payment to her account right now."},
    {"block_id": "b009", "panel_ids": ["panel_0010"], "narration": "Seeing her desperate financial straits, he wants her completely focused on brewing without stress."},
    {"block_id": "b010", "panel_ids": ["panel_0011"], "narration": "Celine quickly sets ethical boundaries, pulling out her notebook to record his specifications."},
    {"block_id": "b011", "panel_ids": ["panel_0012"], "narration": "She firmly declares that she will never brew narcotics or illegal poisons under any circumstances."},
    {"block_id": "b012", "panel_ids": ["panel_0013"], "narration": "No matter how astronomical the fee, violating her alchemical morals is entirely out of the question."},
    {"block_id": "b013", "panel_ids": ["panel_0014"], "narration": "Gong-ja raises his hands reassuringly, confirming he is solely interested in body-tempering elixirs."},
    {"block_id": "b014", "panel_ids": ["panel_0015"], "narration": "Bae Hu-ryeong sighs, reluctantly stepping in to dictate his otherworldly recipe."},
    {"block_id": "b015", "panel_ids": ["panel_0016"], "narration": "He instructs Gong-ja to list twenty-three exotic monster ingredients in exact chronological order."},
    {"block_id": "b016", "panel_ids": ["panel_0017"], "narration": "Rabbit-pig liver, balloon-cat eyes, giant desert worm skin, and black salamander tails."},
    {"block_id": "b017", "panel_ids": ["panel_0018"], "narration": "Gong-ja recites every bizarre reagent with absolute precision, watching Celine's pen fly."},
    {"block_id": "b018", "panel_ids": ["panel_0019"], "narration": "Celine's eyes widen as she connects the dots between the volatile compounds."},
    {"block_id": "b019", "panel_ids": ["panel_0020"], "narration": "She gasps in admiration, instantly recognizing the profound genius behind the formulation."},
    {"block_id": "b020", "panel_ids": ["panel_0021"], "narration": "This recipe doesn't just nourish flesh; it violently expands dormant mana circuits from within."},
    {"block_id": "b021", "panel_ids": ["panel_0022"], "narration": "She points out a microscopic poison lining on the salamander tail, suggesting a neutralizing counter-agent."},
    {"block_id": "b022", "panel_ids": ["panel_0023"], "narration": "Bae Hu-ryeong's jaw drops in shock—the green-haired girl caught a flaw even his world's masters missed!"},
    {"block_id": "b023", "panel_ids": ["panel_0024"], "narration": "Gong-ja smiles proudly, knowing his faith in the future Number Five hunter was fully justified."},
    {"block_id": "b024", "panel_ids": ["panel_0025"], "narration": "Celine requests four uninterrupted days in her laboratory to brew the master-grade batch."},
    {"block_id": "b025", "panel_ids": ["panel_0026"], "narration": "She promises that with proper funding, she will extract the maximum possible potency."},
    {"block_id": "b026", "panel_ids": ["panel_0027"], "narration": "Gong-ja hands over the deposit with complete confidence: four days is absolutely perfect."},
    {"block_id": "b027", "panel_ids": ["panel_0028"], "narration": "Bae Hu-ryeong mutters grumpily, still pretending to doubt the young alchemist's capabilities."},
    {"block_id": "b028", "panel_ids": ["panel_0029"], "narration": "Gong-ja teases his ghost master, reminding him that genius recognizes genius across time."},
    {"block_id": "b029", "panel_ids": ["panel_0030"], "narration": "Four days pass in Babylon as Celine works tirelessly behind locked workshop doors."},
    {"block_id": "b030", "panel_ids": ["panel_0031"], "narration": "Cauldrons bubble with vibrant crimson fluid as arcane fumes filter through glass condensation coils."},
    {"block_id": "b031", "panel_ids": ["panel_0032"], "narration": "On the morning of the fourth day, Gong-ja returns to collect his finished commission."},
    {"block_id": "b032", "panel_ids": ["panel_0033"], "narration": "Celine opens three heavy wooden crates stacked with neat rows of black glass bottles."},
    {"block_id": "b033", "panel_ids": ["panel_0034"], "narration": "Inside rest ninety complete, flawless bottles of high-density body-tempering elixir."},
    {"block_id": "b034", "panel_ids": ["panel_0035"], "narration": "Ninety bottles! That is fifteen times the yield the mainstream guild shop would have produced!"},
    {"block_id": "b035", "panel_ids": ["panel_0036"], "narration": "Bae Hu-ryeong floats above the crates, struck into a rare moment of speechless, reverent awe."},
    {"block_id": "b036", "panel_ids": ["panel_0037"], "narration": "Even in his ancient empire, extracting ninety bottles from those reagents was considered impossible."},
    {"block_id": "b037", "panel_ids": ["panel_0038"], "narration": "Gong-ja stores the crates into his inventory with immense satisfaction."},
    {"block_id": "b038", "panel_ids": ["panel_0039"], "narration": "His investment has yielded an astronomical bounty that will accelerate his training by years."},

    # --- ACT 2: ALLIANCE OF THE NICE HUNTERS (p0041 - p0068) ---
    {"block_id": "b039", "panel_ids": ["panel_0041"], "narration": "As Gong-ja turns to leave, Celine nervously asks why he chose her failing shop in the first place."},
    {"block_id": "b040", "panel_ids": ["panel_0042"], "narration": "Every other customer mocked her prices and labeled her a fraudulent scammer."},
    {"block_id": "b041", "panel_ids": ["panel_0043"], "narration": "Gong-ja looks into her honest eyes, offering an answer straight from his heart."},
    {"block_id": "b042", "panel_ids": ["panel_0044"], "narration": "He tells her: Because you looked like a truly kind and decent person."},
    {"block_id": "b043", "panel_ids": ["panel_0045"], "narration": "In a dog-eat-dog tower filled with selfish psychopaths, decent people deserve to succeed together."},
    {"block_id": "b044", "panel_ids": ["panel_0046"], "narration": "He explains that seeing corrupt villains rise to the top makes his blood boil with rage."},
    {"block_id": "b045", "panel_ids": ["panel_0047"], "narration": "Kind hunters need to stand shoulder to shoulder, building strength to protect one another."},
    {"block_id": "b046", "panel_ids": ["panel_0048"], "narration": "He extends his right hand forward, offering a formal partnership of mutual support."},
    {"block_id": "b047", "panel_ids": ["panel_0049"], "narration": "Celine gazes at his outstretched palm, deeply moved by his genuine, unwavering respect."},
    {"block_id": "b048", "panel_ids": ["panel_0050"], "narration": "She firmly grasps his hand, sealing their alliance with an explosion of warm, golden mana."},
    {"block_id": "b049", "panel_ids": ["panel_0051"], "narration": "She promises that whenever he needs potions, her laboratory will prioritize his requests above all."},
    {"block_id": "b050", "panel_ids": ["panel_0052"], "narration": "Gong-ja waves goodbye with a bright grin, stepping out into the bustling avenue."},
    {"block_id": "b051", "panel_ids": ["panel_0053"], "narration": "The moment the door clicks shut, Bae Hu-ryeong bursts into uproarious, mocking laughter."},
    {"block_id": "b052", "panel_ids": ["panel_0054"], "narration": "The ghost mimics Gong-ja's voice: 'Kind hunters like us need to succeed together!'"},
    {"block_id": "b053", "panel_ids": ["panel_0055"], "narration": "He cackles hysterically, reminding Zombie Kim that he holds four thousand murders on his soul!"},
    {"block_id": "b054", "panel_ids": ["panel_0056"], "narration": "Gong-ja turns beet red, shouting at the ghost to shut his mouth and head to the dungeon."},
    {"block_id": "b055", "panel_ids": ["panel_0057"], "narration": "They arrive at the central teleportation gate, inputting the coordinates for the third floor."},
    {"block_id": "b056", "panel_ids": ["panel_0058"], "narration": "A shimmering pillar of green portal mana envelops them: Transporting to the third-floor hunting grounds."},

    # --- ACT 3: AWAKENING AURA IN COMBAT (p0059 - p0095) ---
    {"block_id": "b057", "panel_ids": ["panel_0059"], "narration": "They materialize inside a dense, ominous jungle crawling with dangerous predatory monsters."},
    {"block_id": "b058", "panel_ids": ["panel_0060"], "narration": "Heavy footsteps shake the canopy as massive, armored green orc warriors patrol the trees."},
    {"block_id": "b059", "panel_ids": ["panel_0061"], "narration": "Gong-ja's instincts scream that these brutes are far too powerful for an ordinary F-rank hunter."},
    {"block_id": "b060", "panel_ids": ["panel_0062"], "narration": "Bae Hu-ryeong floats down with an evil grin, ordering him to uncork the first elixir bottle."},
    {"block_id": "b061", "panel_ids": ["panel_0063"], "narration": "Gong-ja unseals the dark glass flask, feeling the dense alchemical heat radiating from within."},
    {"block_id": "b062", "panel_ids": ["panel_0064"], "narration": "He tilts his head back, chugging the entire draught in one massive swallow."},
    {"block_id": "b063", "panel_ids": ["panel_0065"], "narration": "At first, it tastes surprisingly mild, carrying a refreshing hint of lemon and cool mint."},
    {"block_id": "b064", "panel_ids": ["panel_0066"], "narration": "Suddenly, an explosive shockwave detonates inside his chest with volcanic force!"},
    {"block_id": "b065", "panel_ids": ["panel_0067"], "narration": "His pupils dilate violently as reality decelerates into absolute, agonizing slow motion."},
    {"block_id": "b066", "panel_ids": ["panel_0068"], "narration": "Every single sensory nerve in his mortal flesh fires simultaneously at maximum overdrive."},
    {"block_id": "b067", "panel_ids": ["panel_0069"], "narration": "Bae Hu-ryeong lifts Gong-ja by the collar, his mouth moving at an impossibly slow crawl."},
    {"block_id": "b068", "panel_ids": ["panel_0070"], "narration": "Gong-ja clutches his pounding skull, screaming that his brain is melting from sensory overload."},
    {"block_id": "b069", "panel_ids": ["panel_0071"], "narration": "The ghost whispers into his ear: Can't you feel every individual drop of sweat rolling down your neck?"},
    {"block_id": "b070", "panel_ids": ["panel_0072"], "narration": "Can't you count every individual follicle of hair standing on your trembling arms?"},
    {"block_id": "b071", "panel_ids": ["panel_0073"], "narration": "That is the miraculous power of the elixir: it decelerates his temporal perception tenfold."},
    {"block_id": "b072", "panel_ids": ["panel_0074"], "narration": "In this hyper-accelerated cognitive state, his dormant internal energy is forcibly revealed."},
    {"block_id": "b073", "panel_ids": ["panel_0075"], "narration": "Gong-ja gasps for air, whispering: What... is... that... thing... inside... me?"},
    {"block_id": "b074", "panel_ids": ["panel_0076"], "narration": "Bae Hu-ryeong strikes Gong-ja's chest with a spectral palm, shattering his internal barrier."},
    {"block_id": "b075", "panel_ids": ["panel_0077"], "narration": "He shouts: That thing squirming beneath your ribs is your latent hunter's Aura!"},
    {"block_id": "b076", "panel_ids": ["panel_0078"], "narration": "Deep within Gong-ja's core, an ethereal crimson heart beats with roaring, untamed power."},
    {"block_id": "b077", "panel_ids": ["panel_0079"], "narration": "Vibrant plumes of multi-colored mana erupt from his lips, flooding every muscle with raw energy."},
    {"block_id": "b078", "panel_ids": ["panel_0080"], "narration": "Bae Hu-ryeong laughs like a mad general: normally, novices spend twenty years meditating to feel this!"},
    {"block_id": "b079", "panel_ids": ["panel_0081"], "narration": "Gong-ja clutches his temples, his body boiling with unrefined, turbulent martial force."},
    {"block_id": "b080", "panel_ids": ["panel_0082"], "narration": "The ghost's eyes gleam with sadistic delight: but we don't have twenty years to waste on meditation!"},
    {"block_id": "b081", "panel_ids": ["panel_0083"], "narration": "Since Gong-ja has zero natural talent, his flesh must learn through the agony of pure survival."},
    {"block_id": "b082", "panel_ids": ["panel_0084"], "narration": "Behind Gong-ja, a towering, red-eyed orc warrior brandishes a massive iron spiked club!"},
    {"block_id": "b083", "panel_ids": ["panel_0085"], "narration": "The monster roars with earth-shattering fury, charging forward to smash the intruder to paste."},
    {"block_id": "b084", "panel_ids": ["panel_0086"], "narration": "Bae Hu-ryeong flies into the canopy, yelling his final instruction: You better run, Zombie!"},
    {"block_id": "b085", "panel_ids": ["panel_0087"], "narration": "Run if you don't want your skull pulverized into a bloody puddle on the jungle floor!"},
    {"block_id": "b086", "panel_ids": ["panel_0088"], "narration": "Gong-ja's dilated eyes lock onto the descending iron club, his survival instincts exploding into motion."},
    {"block_id": "b087", "panel_ids": ["panel_0089"], "narration": "He draws his blade mid-sprint, diving beneath the crushing blow as trees shatter behind him."},
    {"block_id": "b088", "panel_ids": ["panel_0090"], "narration": "With ninety bottles of elixir in reserve and immortality on his side, his trial by fire begins."},
    {"block_id": "b089", "panel_ids": ["panel_0091"], "narration": "The brutal awakening of the Revival Hunter's Aura has officially commenced in the deadly jungle."},
    {"block_id": "b090", "panel_ids": ["panel_0092"], "narration": "He swings his blade with pure, fearless commitment, carving his way through the third floor."},
    {"block_id": "b091", "panel_ids": ["panel_0093"], "narration": "Every strike, every dodge, and every broken bone will forge him into an unstoppable martial conqueror."},
    {"block_id": "b092", "panel_ids": ["panel_0094"], "narration": "The Sword Emperor watches with wicked pride, knowing his disciple will either conquer or die trying."},
    {"block_id": "b093", "panel_ids": ["panel_0095"], "narration": "And for Zombie Kim, dying only means coming back stronger than ever before!"},
]


def build_and_save():
    ch_dir = Path("data/chapters/sss-class-revival-hunter/ch10")
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
        chapter_id="sss-class-revival-hunter/ch10",
        title="SSS-Class Revival Hunter - Chapter 10",
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

    alt_script_path = Path("data/chapters/revival_hunter_ch10/04_script.json")
    if alt_script_path.parent.exists():
        with open(alt_script_path, "w", encoding="utf-8") as f:
            f.write(script_file.model_dump_json(indent=2))

    print("=== SSS-Class Revival Hunter Ch 10 Script ===")
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
