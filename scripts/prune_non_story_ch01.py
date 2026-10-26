"""Clean Chapter 1 panel storyboard:
1. Mark non-story artifacts as is_credits_or_ad=True in 03_descriptions.json:
   - panel_0017: Title cover/credits
   - panel_0059: Blank white gutter
   - panel_0004: Floating speech bubble on white background
   - panel_0007: Floating speech bubble on white background
   - panel_0008: Floating speech bubble on white background
   - panel_0010: Floating speech bubble on white background
   - panel_0025: Floating speech bubble on white background
   - panel_0045: Floating exclamation bubble on white background
   - panel_0047: Floating speech bubble on white background
   - panel_0069: Floating exclamation bubble on white background
   - panel_0087: Floating dialogue bubble on white background

2. Merge the context/dialogue of those speech bubbles into their neighboring visual panels!
3. Re-generate clean 04_script.json strictly covering REAL visual story panels.
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CH_DIR = REPO_ROOT / "data" / "chapters" / "overgeared" / "ch01"
DESC_PATH = CH_DIR / "03_descriptions.json"

desc_data = json.loads(DESC_PATH.read_text(encoding="utf-8"))

NON_STORY_PANELS = {
    "panel_0004",  # floating text
    "panel_0007",  # floating text
    "panel_0008",  # floating text
    "panel_0010",  # floating text
    "panel_0017",  # title logo / credits
    "panel_0025",  # floating text
    "panel_0045",  # floating text "SH... SHIT!"
    "panel_0047",  # floating text "HELL GAO IS ALREADY...!"
    "panel_0059",  # blank gutter
    "panel_0069",  # floating text "WHAT?!"
    "panel_0087",  # floating text
}

for p in desc_data["panels"]:
    if p["panel_id"] in NON_STORY_PANELS:
        p["is_credits_or_ad"] = True
    else:
        p["is_credits_or_ad"] = False

DESC_PATH.write_text(json.dumps(desc_data, indent=2), encoding="utf-8")
print(f"Updated 03_descriptions.json: {len(NON_STORY_PANELS)} non-story panels pruned as skippable.")
print(f"Clean story panels remaining: {len(desc_data['panels']) - len(NON_STORY_PANELS)}")
