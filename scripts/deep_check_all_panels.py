import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

for i in range(1, 6):
    ch = f"revival_hunter_ch{i:02d}"
    sc = json.load(open(f"data/chapters/{ch}/04_script.json", encoding="utf-8"))
    desc = json.load(open(f"data/chapters/{ch}/03_descriptions.json", encoding="utf-8"))
    p_map = {p["panel_id"]: p for p in desc["panels"]}
    print(f"\n=================== CH{i} SCRIPT PANELS CHECK ===================")
    for b in sc["blocks"]:
        for pid in b["panel_ids"]:
            p = p_map.get(pid, {})
            act = (p.get("action") or "").lower()
            txt = " ".join(p.get("speech_bubbles") or []).lower()
            if any(k in act for k in ["logo", "title card", "credit", "reminder", "promo", "tapas", "series logo", "manhwa name"]):
                print(f"SUSPECT PANEL IN CH{i}: block={b['block_id']}, panel={pid}")
                print(f"  Action: {p.get('action')}")
                print(f"  Text: {txt}")
