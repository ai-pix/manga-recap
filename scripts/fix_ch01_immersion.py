import json
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate

ch_dir = Path("data/chapters/revival_hunter_ch01")
desc_path = ch_dir / "03_descriptions.json"
script_path = ch_dir / "04_script.json"

desc_data = json.load(open(desc_path, encoding="utf-8"))
script_data = json.load(open(script_path, encoding="utf-8"))

# Update block 25 and 26 in script
for b in script_data["blocks"]:
    if b["block_id"] == "b025":
        b["panel_ids"] = ["panel_0061"]
    elif b["block_id"] == "b026":
        b["panel_ids"] = ["panel_0062"]

# Update descriptions: panel_0061 and 0062 active; 0060, 0063, 0064, 0065 skippable
for p in desc_data["panels"]:
    pid = p["panel_id"]
    if pid in ["panel_0061", "panel_0062"]:
        p["is_credits_or_ad"] = False
    elif pid in ["panel_0060", "panel_0063", "panel_0064", "panel_0065"]:
        p["is_credits_or_ad"] = True
        p["setting"] = "pruned_title_or_ad"

with open(desc_path, "w", encoding="utf-8") as f:
    json.dump(desc_data, f, indent=2, ensure_ascii=False)

with open(script_path, "w", encoding="utf-8") as f:
    json.dump(script_data, f, indent=2, ensure_ascii=False)

cfg = load_config()
desc_model = load_model(desc_path, DescriptionFile)
script_model = load_model(script_path, ScriptFile)
report = validate(script_model, desc_model, cfg)

print(f"Chapter 1 script updated.")
print(f"Validation OK: {report.ok}")
if not report.ok:
    print(report.render())
