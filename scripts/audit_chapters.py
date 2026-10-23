import json
from pathlib import Path

def main():
    report = []
    for i in range(1, 21):
        ch = f"barbarian_ch{i:02d}"
        ch_dir = Path("data/chapters") / ch
        desc_p = ch_dir / "03_descriptions.json"
        script_p = ch_dir / "04_script.json"
        if not desc_p.exists() or not script_p.exists():
            continue
        desc = json.loads(desc_p.read_text(encoding="utf-8"))
        script = json.loads(script_p.read_text(encoding="utf-8"))
        
        panels = desc.get("panels", [])
        black_panels = set()
        for p in panels:
            pid = p.get("panel_id")
            setting = str(p.get("setting", "")).lower()
            d_txt = str(p.get("description", "")).lower()
            if "black" in setting or "text" in setting or "monologue" in setting or p.get("is_credits_or_ad"):
                black_panels.add(pid)
            elif len(p.get("characters", [])) == 0 and ("stat" in d_txt or "system" in d_txt or "dialogue only" in d_txt):
                black_panels.add(pid)
                
        script_panels = []
        black_in_script = []
        for b in script.get("blocks", []):
            for pid in b.get("panel_ids", []):
                script_panels.append(pid)
                if pid in black_panels:
                    black_in_script.append(pid)
                    
        blocks = script.get("blocks", [])
        word_count = sum(len(b.get("narration", "").split()) for b in blocks)
        sample = blocks[0].get("narration", "")[:60] if blocks else ""
        print(f"{ch}: total_p={len(panels)}, black_p={len(black_panels)}, art_p={len(panels)-len(black_panels)}, script_blocks={len(blocks)}, words={word_count}, black_in_script={len(black_in_script)}")
        print(f"   Sample: \"{sample}\"")

if __name__ == "__main__":
    main()
