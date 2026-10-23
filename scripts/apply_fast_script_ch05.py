import json
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate

ch_dir = Path("data/chapters/revival_hunter_ch05")
desc_path = ch_dir / "03_descriptions.json"
script_path = ch_dir / "04_script.json"

desc_data = json.load(open(desc_path, encoding="utf-8"))

story_panels = [
    "panel_0001", "panel_0004", "panel_0007", "panel_0008", "panel_0017",
    "panel_0019", "panel_0020", "panel_0021", "panel_0027", "panel_0033",
    "panel_0034", "panel_0035", "panel_0058", "panel_0061", "panel_0063",
    "panel_0067", "panel_0070", "panel_0073", "panel_0076", "panel_0077",
    "panel_0078", "panel_0081", "panel_0083", "panel_0086", "panel_0087",
    "panel_0090", "panel_0091", "panel_0093", "panel_0098", "panel_0099"
]

narrations = [
    "Babylon News confirms the legend: Marcus Callenberry, the revered Blade Saint, is the undisputed rank one hunter.",
    "Watching the living legend sip warm milk, Gong-ja ponders the terrifying possibilities of his copied skill.",
    "If he can copy the abilities of anyone who kills him, could he acquire the Blade Saint’s godlike swordsmanship?",
    "With his twenty-four-hour rewind skill active, Gong-ja no longer fears death in the slightest.",
    "Gong-ja accidentally mutters his thoughts out loud, prompting the grumpy old saint to snap at him angrily.",
    "Marcus glares with piercing intensity, demanding to know if this young stranger is stalking him.",
    "Gong-ja quickly pulls up hunter forums to research the eccentric grandmaster’s peculiar personality.",
    "The top community warning flashes brightly: never mention taboo family topics in front of the Blade Saint.",
    "Arrogant hunters who brought up Marcus’s abandoned grandchildren were swiftly punished by his devastating sword.",
    "The warning is crystal clear: mentioning his grandchildren will immediately invoke the sword master’s lethal fury.",
    "Frustrated by the noisy tavern, the Blade Saint tosses his payment onto the counter and leaves.",
    "Marcus storms out into the chilly night, seeking solace in the secluded back alleys of Babylon.",
    "Curious and seeking an opportunity to copy an S-rank skill, Gong-ja quietly follows in his footsteps.",
    "The Blade Saint halts in the shadows, scowling as he turns to confront his young pursuer.",
    "Gong-ja immediately raises empty hands, insisting he is merely an ordinary, unarmed rookie hunter.",
    "Marcus tightens his grip on his sheath, his eyes narrowing: you are a terrifyingly convincing actor.",
    "Gong-ja stammers in confusion: a first-class assassin?! He is just a humble F-class nobody!",
    "The Blade Saint sneers with absolute revulsion: you disgust me, pretending to be an innocent civilian.",
    "Drawing his radiant, blinding holy sword, Marcus illuminates the entire alley in divine brilliance.",
    "He reveals the secret of his transcendent perception: an innate spiritual skill granted by the Tower.",
    "This sacred skill displays the exact number of human souls a hunter has personally slaughtered.",
    "Gong-ja breathes a silent sigh of relief, assuming the old man merely sees a single kill from earlier.",
    "Smiling politely, Gong-ja asks Marcus to listen, explaining there was a righteous reason for that death.",
    "Marcus roars in furious indignation, his holy spiritual pressure shaking the stone foundations of the city!",
    "Plunging his divine blade forward, the old saint trembles with sheer righteous wrath!",
    "He points his shining steel straight at Gong-ja’s forehead, bellowing with unbridled fury!",
    "I see the crimson number burning above your head: you have slaughtered four thousand and ninety-one people!",
    "Horror paralyzes Gong-ja as the truth hits him: one death was Yoo Soo-ha, and the other 4,090 were his own suicides!",
    "The world’s greatest swordsman leaps forward with blinding speed, intent on executing the supposed mass murderer!",
    "A catastrophic divine slash cleaves through the darkness, hurtling straight toward Gong-ja’s neck!"
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
    "chapter_id": "sss-class-revival-hunter/ch05",
    "title": "SSS-Class Revival Hunter - Chapter 05 (The 4,091 Murders & Blade Saint)",
    "series": "sss-class-revival-hunter",
    "created_at": "2026-10-23T12:45:00.000000+00:00",
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

print(f"Ch05 Script created: {len(blocks)} blocks, {total_words} words.")
print(f"Validation OK: {report.ok}")
if not report.ok:
    print(report.render())
