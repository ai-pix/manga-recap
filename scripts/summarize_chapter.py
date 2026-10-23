import sys
import json
from pathlib import Path

def summarize(ch_id):
    desc_p = Path(f"data/chapters/{ch_id}/03_descriptions.json")
    if not desc_p.exists():
        print(f"Error: {desc_p} not found")
        return
    desc = json.loads(desc_p.read_text(encoding="utf-8"))
    panels = desc.get("panels", [])
    
    black_panels = []
    art_panels = []
    for p in panels:
        pid = p.get("panel_id")
        setting = str(p.get("setting", "")).lower()
        desc_txt = str(p.get("description", "")).lower()
        if "black" in setting or "text" in setting or "monologue" in setting or p.get("is_credits_or_ad"):
            black_panels.append(pid)
        elif len(p.get("characters", [])) == 0 and ("stat" in desc_txt or "system" in desc_txt or "dialogue only" in desc_txt):
            black_panels.append(pid)
        else:
            art_panels.append(p)
            
    print(f"=== {ch_id} ===")
    print(f"Total panels: {len(panels)} | Art panels: {len(art_panels)} | Black/skippable: {len(black_panels)}")
    print(f"Black panel IDs: {black_panels}")
    print("\n--- Story Highlights ---")
    for idx, p in enumerate(art_panels):
        pid = p.get("panel_id")
        dialogue = " | ".join(f"{d.get('speaker', '')}: {d.get('text', '')}" for d in p.get("dialogue", []))
        action = p.get("action", "")
        desc_t = p.get("description", "")
        if dialogue or idx % 5 == 0:
            print(f"[{pid}] {action} | {desc_t} => {dialogue}")

if __name__ == "__main__":
    ch = sys.argv[1] if len(sys.argv) > 1 else "barbarian_ch02"
    summarize(ch)
