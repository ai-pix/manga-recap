import json
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model, save_model
from manga_recap.stages.s3_script.validate import validate

ch_dir = Path("data/chapters/revival_hunter_ch02")
desc_path = ch_dir / "03_descriptions.json"
script_path = ch_dir / "04_script.json"

desc_data = json.load(open(desc_path, encoding="utf-8"))

story_panels = [
    "panel_0011",
    "panel_0015",
    "panel_0017",
    "panel_0020",
    "panel_0023",
    "panel_0025",
    "panel_0028",
    "panel_0030",
    "panel_0035",
    "panel_0038",
    "panel_0042",
    "panel_0045",
    "panel_0054",
    "panel_0057",
    "panel_0059",
    "panel_0061",
    "panel_0064",
    "panel_0069",
    "panel_0071",
    "panel_0076",
    "panel_0078",
    "panel_0079",
    "panel_0080",
    "panel_0082",
    "panel_0083",
    "panel_0084",
    "panel_0087",
    "panel_0088",
    "panel_0093",
    "panel_0096",
]

narrations = [
    "Gong-ja stumbles out of the bar, cursing his worthless new skill that requires him to die.",
    "Slipping into a dark alley, he suddenly overhears hushed, tense voices cutting through the shadows.",
    "It's the world's greatest hero, the Flame Emperor, violently confronting Saintess Isabelle!",
    "Flame Emperor smirks, revealing he slipped deadly basilisk venom straight into her drink.",
    "The Saintess gasps in disbelief, completely paralyzed by the lethal neurotoxin.",
    "Flame Emperor leans in close, coldly accusing her of plotting to overthrow him.",
    "Before she can utter another word, he brutally delivers a bone-shattering strike!",
    "He pins her down mercilessly, demanding to know who ordered his assassination.",
    "Yoo Soo-ha wraps his fingers tightly around the trembling Saintess's throat.",
    "Without a shred of hesitation, he snaps her neck in cold blood.",
    "Paralyzed in the darkness, Gong-ja watches the horrifying murder in complete disbelief.",
    "But Gong-ja's terrified gasp betrays him, echoing right off the alley walls.",
    "Flame Emperor steps over the Saintess's corpse, locking his predatory eyes directly onto Gong-ja.",
    "He looms over the trembling rookie with a chilling whisper: did you see that?",
    "Gong-ja desperately stammers that he saw nothing, waving his trembling hands in panic.",
    "Yoo Soo-ha lifts Gong-ja effortlessly into the air by the throat, cutting off his airway.",
    "The idol the world worships as a savior reveals his true demonic, sadistic nature.",
    "Gong-ja wheezes for mercy, begging the tyrant to test him with his famous lie-detecting skill.",
    "Flame Emperor bursts out laughing; he never had a lie-detection skill to begin with!",
    "He simply butchers anyone who looks remotely suspicious without a second thought.",
    "Yoo Soo-ha's hand ignites into a searing vortex of blazing crimson fire.",
    "He smiles coldly: my real name is Yoo Soo-ha, and dead men tell no tales.",
    "Flames incinerate Gong-ja's skull, and the world goes completely pitch black.",
    "But in the void of death, the Tower's ancient system suddenly chimed to life!",
    "The lethal condition was fulfilled: Gong-ja can now copy one skill from his killer!",
    "Dozens of glowing cards materialize, floating through the darkness before his fading consciousness.",
    "Gong-ja lunges with all his soul, desperately grabbing the blinding gold EX-rank card!",
    "The system flashes: EX-rank skill successfully copied into his soul!",
    "Gong-ja gasps awake in his bed, drenched in cold sweat and violently hyperventilating!",
    "The morning television blares the raid announcement—he has traveled twenty-four hours back in time!",
]

assert len(story_panels) == len(narrations)

# Update descriptions: mark non-story panels as skippable
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
    "chapter_id": "sss-class-revival-hunter/ch02",
    "title": "SSS-Class Revival Hunter - Chapter 02 (The Alley Murder & 24h Return)",
    "series": "sss-class-revival-hunter",
    "created_at": "2026-10-23T12:30:00.000000+00:00",
    "model": "agent",
    "target_words": total_words,
    "blocks": blocks
}

with open(script_path, "w", encoding="utf-8") as f:
    json.dump(script_data, f, indent=2, ensure_ascii=False)

# Validate
cfg = load_config()
desc_model = load_model(desc_path, DescriptionFile)
script_model = load_model(script_path, ScriptFile)
report = validate(script_model, desc_model, cfg)

print(f"Ch02 Script created: {len(blocks)} blocks, {total_words} words.")
print(f"Validation OK: {report.ok}")
if not report.ok:
    print(report.render())
