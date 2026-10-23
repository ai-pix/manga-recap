import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

for i in range(1, 6):
    ch = f"revival_hunter_ch{i:02d}"
    sc = json.load(open(f"data/chapters/{ch}/04_script.json", encoding="utf-8"))
    desc = json.load(open(f"data/chapters/{ch}/03_descriptions.json", encoding="utf-8"))
    p_map = {p["panel_id"]: p for p in desc["panels"]}
    print(f"\n=================== CH{i} ALL SCRIPT BLOCKS AUDIT ===================")
    flagged = []
    for b in sc["blocks"]:
        pid = b["panel_ids"][0]
        p = p_map.get(pid, {})
        act = (p.get("action") or "").lower()
        txt = " ".join(p.get("speech_bubbles") or []).lower()
        sfx_val = p.get("sfx_text") or ""
        sfx = " ".join(sfx_val).lower() if isinstance(sfx_val, list) else str(sfx_val).lower()
        
        # Check for title/logo/credits/ad
        bad_words = ["logo", "title", "series logo", "tapas", "reminder", "support the official", "revival hunter"]
        found = [w for w in bad_words if w in act or w in txt or w in sfx]
        if found:
            flagged.append((b["block_id"], pid, found, act[:70], b["narration"][:60]))
            
    if flagged:
        print(f"FLAGGED {len(flagged)} BLOCKS IN CH{i}:")
        for f in flagged:
            print(f"  Block: {f[0]} | Panel: {f[1]} | Bad words: {f[2]}")
            print(f"    Action: {f[3]}")
            print(f"    Narration: {f[4]}")
    else:
        print(f"CH{i}: All blocks clean! No title/logo/credits detected.")
