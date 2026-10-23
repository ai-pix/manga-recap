import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

for i in range(1, 6):
    ch = f"revival_hunter_ch{i:02d}"
    sc = json.load(open(f"data/chapters/{ch}/04_script.json", encoding="utf-8"))
    desc = json.load(open(f"data/chapters/{ch}/03_descriptions.json", encoding="utf-8"))
    p_map = {p["panel_id"]: p for p in desc["panels"]}
    print(f"\n=================== CH{i} LAST 4 BLOCKS ===================")
    for b in sc["blocks"][-4:]:
        pid = b["panel_ids"][0]
        p = p_map.get(pid, {})
        act = (p.get("action") or "").replace("\n", " ")
        txt = " ".join(p.get("speech_bubbles") or []).replace("\n", " ")
        print(f"[{b['block_id']}] {pid}: {act[:60]} | txt: {txt[:40]}")
