import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

ch = sys.argv[1] if len(sys.argv) > 1 else "revival_hunter_ch02"
path = f"data/chapters/{ch}/03_descriptions.json"
d = json.load(open(path, encoding="utf-8"))

print(f"Total panels in {ch}: {len(d['panels'])}")
for p in d["panels"]:
    txt = " ".join(p.get("speech_bubbles") or []).replace("\n", " ")
    act = (p.get("action") or "").replace("\n", " ")
    chars = ",".join(p.get("characters") or [])
    pid = p["panel_id"]
    print(f"{pid} | {chars[:20]} | {act[:45]} | {txt[:65]}")
