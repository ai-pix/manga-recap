import json
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate

ch_dir = Path("data/chapters/revival_hunter_ch04")
desc_path = ch_dir / "03_descriptions.json"
script_path = ch_dir / "04_script.json"

desc_data = json.load(open(desc_path, encoding="utf-8"))

story_panels = [
    "panel_0003", "panel_0012", "panel_0018", "panel_0020", "panel_0024",
    "panel_0027", "panel_0033", "panel_0039", "panel_0045", "panel_0048",
    "panel_0052", "panel_0060", "panel_0064", "panel_0067", "panel_0070",
    "panel_0073", "panel_0076", "panel_0080", "panel_0083", "panel_0085",
    "panel_0096", "panel_0097", "panel_0098", "panel_0105", "panel_0111",
    "panel_0112", "panel_0117", "panel_0124", "panel_0127", "panel_0131"
]

narrations = [
    "Gong-ja lies breathless on his bed, the deafening silence broken only by the ticking wall clock.",
    "He died an extra thirty times just resting between suicide loops, bringing his total to 4,090 deaths.",
    "But the impossible gamble succeeded: the calendar reads May sixth, eleven years in the past!",
    "It is eleven in the morning on the historic day the Spire first revealed its gates.",
    "Across town, twenty-one-year-old Yoo Soo-ha wakes up nursing a headache in his cheap studio apartment.",
    "At this point in time, the future Flame Emperor is merely an ordinary, lazy young man.",
    "He grumbles through boring slime hunts on the second floor, dreaming of winning the lottery.",
    "But lurking in the surrounding shadows, Gong-ja watches him coldly: that glorious future will never arrive.",
    "Gong-ja buys a teleportation scroll, isolating Yoo Soo-ha on the secluded sixth-floor hunting zone.",
    "Feigning a wounded limb, Gong-ja limps toward the young hunter, begging for medical assistance.",
    "True to his selfish character, Yoo Soo-ha demands every coin Gong-ja owns before handing over a potion.",
    "Yoo Soo-ha grabs Gong-ja by the collar, greedily snatching the pouch of gold.",
    "But in that split second of greed, Yoo Soo-ha leaves his vital neck completely unguarded.",
    "Gong-ja springs forward with terrifying precision, driving a concealed dagger straight into Yoo Soo-ha’s throat!",
    "Blood sprays across the damp earth as Gong-ja executes the lethal strike without blinking.",
    "The young tyrant collapses into the mud, clutching his torn windpipe in bewildered horror.",
    "Gong-ja towers over the dying tyrant, taking zero chances of him ever unlocking his terrifying EX-rank regression skill.",
    "Whispering his own mocking farewell—my name is Yoo Soo-ha, goodbye—Gong-ja watches the life leave his eyes.",
    "With one final agonizing gasp, the future Flame Emperor perishes before his tyranny can even begin.",
    "Gong-ja stands alone in the quiet woods, breathing deeply as the world’s darkest timeline dissolves.",
    "He quickly wraps the corpse in a heavy sack, ensuring no trace of murder remains.",
    "Hauling the body deep into wild monster territory, he leaves the beasts to consume the evidence.",
    "Activating his transit crystal, Gong-ja transports straight back to the safety of Babylon's first floor.",
    "Stepping out into the bustling city square, the phantom burden of 4,090 deaths finally lifts.",
    "Yoo Soo-ha’s name will never terrorize humanity; the legendary Flame Emperor is permanently erased from history.",
    "Gong-ja slips into a quiet tavern, ordering a frosty mug of draft beer to celebrate.",
    "He opens his hunter status screen, smiling at the copied EX-rank regression skill safely in his arsenal.",
    "At the corner of the counter, an elderly gentleman in a crisp suit quietly orders warm milk with vodka.",
    "Gong-ja turns his head in curiosity, only for his jaw to drop in utter disbelief.",
    "Sitting right beside him is Marcus Callenberry—the Blade Saint, the undisputed Rank One Hunter in the world!"
]

assert len(story_panels) == len(narrations)

for p in desc_data["panels"]:
    if p["panel_id"] in story_panels:
        p["is_credits_or_ad"] = False
    else:
        p["is_credits_or_ad"] = True
        p["setting"] = "pruned_for_fast_pacing"

with open(desc_path, "w", encoding="utf-8") as f:
    json.dump(desc_data, f, indent=2, ensure_ascii=False)

blocks = []
total_words = 0
for idx, (pid, text) in enumerate(zip(story_panels, narrations), start=1):
    bid = f"b{idx:03d}"
    words = len(text.split())
    total_words += words
    blocks.append({
        "block_id": bid,
        "panel_ids": [pid],
        "narration": text,
        "direction": "",
        "beats": []
    })

script_data = {
    "chapter_id": "sss-class-revival-hunter/ch04",
    "title": "SSS-Class Revival Hunter - Chapter 04 (The 11-Year Assassination)",
    "series": "sss-class-revival-hunter",
    "created_at": "2026-10-23T12:40:00.000000+00:00",
    "model": "agent",
    "target_words": total_words,
    "blocks": blocks
}

with open(script_path, "w", encoding="utf-8") as f:
    json.dump(script_data, f, indent=2, ensure_ascii=False)

cfg = load_config()
desc_model = load_model(desc_path, DescriptionFile)
script_model = load_model(script_path, ScriptFile)
report = validate(script_model, desc_model, cfg)

print(f"Ch04 Script created: {len(blocks)} blocks, {total_words} words.")
print(f"Validation OK: {report.ok}")
if not report.ok:
    print(report.render())
