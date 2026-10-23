import json
import sys
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate

sys.stdout.reconfigure(encoding="utf-8")
cfg = load_config()

bad_panels = {
    "revival_hunter_ch09": ["panel_0023"],
    "revival_hunter_ch12": ["panel_0020", "panel_0022", "panel_0031"],
    "revival_hunter_ch17": ["panel_0002"],
    "revival_hunter_ch18": ["panel_0018"],
    "revival_hunter_ch20": ["panel_0017", "panel_0024"],
    "revival_hunter_ch30": ["panel_0037"],
    "revival_hunter_ch31": ["panel_0041", "panel_0087"],
    "revival_hunter_ch34": ["panel_0012"],
}

for ch, pids in bad_panels.items():
    desc_p = Path(f"data/chapters/{ch}/03_descriptions.json")
    script_p = Path(f"data/chapters/{ch}/04_script.json")
    
    desc_data = json.load(open(desc_p, encoding="utf-8"))
    script_data = json.load(open(script_p, encoding="utf-8"))
    
    # Mark in descriptions as skippable
    for p in desc_data["panels"]:
        if p["panel_id"] in pids:
            p["is_credits_or_ad"] = True
            p["setting"] = "pruned_title_card"
            
    # Remove or replace blocks in script
    # Filter out blocks whose only panels are in pids
    new_blocks = []
    for b in script_data["blocks"]:
        remaining_pids = [pid for pid in b["panel_ids"] if pid not in pids]
        if remaining_pids:
            b["panel_ids"] = remaining_pids
            new_blocks.append(b)
        else:
            # Block had only the bad panel. Check if we should drop it or merge narration
            # If the narration is meta ("Title flashes..."), drop it completely!
            narr = b["narration"].lower()
            if any(k in narr for k in ["title", "series", "frame heralds", "decorative vine", "card's reveal"]):
                print(f"Dropping meta block {b['block_id']} in {ch}: {b['narration']}")
            else:
                # Narration was actual story (e.g. ch09 b022: 'Gong-ja screams internally...')
                # Bind it to the previous or next block!
                if new_blocks:
                    print(f"Merging story narration of {b['block_id']} into {new_blocks[-1]['block_id']} in {ch}")
                    new_blocks[-1]["narration"] += " " + b["narration"]
                else:
                    print(f"Warning: dropping {b['block_id']} at start of {ch}")

    # Renumber blocks cleanly
    for idx, b in enumerate(new_blocks, start=1):
        b["block_id"] = f"b{idx:03d}"
        
    script_data["blocks"] = new_blocks
    script_data["target_words"] = sum(len(b["narration"].split()) for b in new_blocks)
    
    with open(desc_p, "w", encoding="utf-8") as f:
        json.dump(desc_data, f, indent=2, ensure_ascii=False)
        
    with open(script_p, "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2, ensure_ascii=False)
        
    # Validate
    dm = load_model(desc_p, DescriptionFile)
    sm = load_model(script_p, ScriptFile)
    rep = validate(sm, dm, cfg)
    print(f"{ch}: Cleaned {len(pids)} title panels. Blocks: {len(new_blocks)}, Words: {script_data['target_words']}, Valid: {rep.ok}")
    if not rep.ok:
        print(rep.render())
