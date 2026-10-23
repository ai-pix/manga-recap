import sys
import json
from pathlib import Path

def get_context(ch_id):
    p = Path(f"data/chapters/{ch_id}/03_descriptions.json")
    if not p.exists():
        print(f"Missing {p}")
        return
    desc = json.loads(p.read_text(encoding="utf-8"))
    panels = desc.get("panels", [])
    
    clean_panels = []
    skipped = []
    for p_info in panels:
        pid = p_info.get("panel_id")
        setting = str(p_info.get("setting", "")).lower()
        desc_txt = str(p_info.get("description", "")).lower()
        is_ad = p_info.get("is_credits_or_ad", False)
        
        is_black = (
            "black" in setting or
            "text" in setting or
            "monologue" in setting or
            is_ad or
            (len(p_info.get("characters", [])) == 0 and ("stat" in desc_txt or "system" in desc_txt or "dialogue only" in desc_txt))
        )
        if is_black:
            skipped.append((pid, p_info))
        else:
            clean_panels.append(p_info)
            
    print(f"=== {ch_id} ===")
    print(f"Total: {len(panels)} | Art panels to narrate: {len(clean_panels)} | Skipped black/text: {len(skipped)}")
    print(f"Skipped IDs: {[s[0] for s in skipped]}")
    
    # Save a clean context file for easy script generation
    out_file = Path(f"data/chapters/{ch_id}/_script_context.json")
    out_file.write_text(json.dumps({
        "chapter_id": ch_id,
        "clean_panels": clean_panels,
        "skipped_panels": [s[0] for s in skipped],
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote context to {out_file}")

if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "barbarian_ch02"
    get_context(ch)
