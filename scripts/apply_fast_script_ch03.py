import json
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate

ch_dir = Path("data/chapters/revival_hunter_ch03")
desc_path = ch_dir / "03_descriptions.json"
script_path = ch_dir / "04_script.json"

desc_data = json.load(open(desc_path, encoding="utf-8"))

story_panels = [
    "panel_0001", "panel_0003", "panel_0005", "panel_0007", "panel_0011",
    "panel_0012", "panel_0013", "panel_0014", "panel_0015", "panel_0016",
    "panel_0017", "panel_0020", "panel_0023", "panel_0024", "panel_0080",
    "panel_0081", "panel_0083", "panel_0084", "panel_0085", "panel_0088",
    "panel_0089", "panel_0090", "panel_0091", "panel_0093", "panel_0096",
    "panel_0098", "panel_0099", "panel_0100", "panel_0101", "panel_0102"
]

narrations = [
    "Gong-ja sits up in disbelief, clutching his throat where his skull was just incinerated.",
    "His smartphone lights up with the exact same chat messages from yesterday morning.",
    "The television blares the live broadcast of Flame Emperor conquering floor forty.",
    "The exact same words, the exact same headlines—yesterday is repeating itself flawlessly.",
    "Trembling with anticipation, Gong-ja raises his hand and calls upon his hunter status.",
    "His original S-rank skill card floats before him: I Want to Become Just Like You.",
    "But hovering right beside it is a radiant new card bathed in blinding golden light!",
    "EX-Rank Skill: The Time Traveler’s Clock, automatically rewinding time twenty-four hours upon death!",
    "All memories and acquired skills remain completely intact across every single regression.",
    "Gong-ja stares at his wall of clippings in awe—this was Flame Emperor's invincible secret!",
    "Yoo Soo-ha never had godlike instincts; he simply died repeatedly until he mastered every battle.",
    "But dread sets in: if Flame Emperor holds this skill, killing him today accomplishes nothing.",
    "The moment he dies, Flame Emperor would simply rewind twenty-four hours and slaughter Gong-ja first.",
    "Gong-ja clenches his fists: the only way to win is to strike before Flame Emperor awakens.",
    "He pulls up Yoo Soo-ha’s legendary debut interview in the ancient hunter archives.",
    "The article confirms the date: Flame Emperor awakened eleven years ago on his twenty-first birthday!",
    "Eleven full years multiplied by three hundred sixty-five days equals exactly four thousand and fifty days.",
    "Gong-ja draws a cold steel dagger, staring at his reflection with unyielding determination.",
    "To travel eleven years into the past, he must commit suicide over four thousand times.",
    "Without hesitation, he drives the blade deep into his neck, collapsing into his own blood.",
    "Gasping awake twenty-four hours earlier, Gong-ja grits his teeth: four thousand and forty-nine to go!",
    "He grips the bloody hilt once more and plunges the steel back into his flesh.",
    "The system flashes cold blue text: You have died. Rewinding time twenty-four hours.",
    "Die. Rewind. Stab. Die. The agonizing cycle repeats endlessly in the silent room.",
    "Days turn into weeks, weeks into months, rewinding backward through the history of Babylon.",
    "The Tower's system confirms: no penalty incurred. His sanity is pushed to the absolute edge.",
    "Two thousand deaths... three thousand deaths... five hundred days left before the fateful awakening!",
    "Drenched in blood and shivering from unbearable mental agony, Gong-ja refuses to surrender.",
    "Falling forward onto the hardwood floor, he drags his trembling body forward for one last strike.",
    "The crimson clock ticks down to zero: one final death remains to reach the past!"
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
    "chapter_id": "sss-class-revival-hunter/ch03",
    "title": "SSS-Class Revival Hunter - Chapter 03 (The 4,090 Suicides)",
    "series": "sss-class-revival-hunter",
    "created_at": "2026-10-23T12:35:00.000000+00:00",
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

print(f"Ch03 Script created: {len(blocks)} blocks, {total_words} words.")
print(f"Validation OK: {report.ok}")
if not report.ok:
    print(report.render())
