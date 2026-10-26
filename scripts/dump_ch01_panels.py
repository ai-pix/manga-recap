import json
from pathlib import Path

desc = json.loads(Path("data/chapters/overgeared/ch01/03_descriptions.json").read_text(encoding="utf-8"))
out_lines = []
for p in desc["panels"]:
    chars = ", ".join(p["characters"]) if p["characters"] else "None"
    speech = " // ".join(p["speech_bubbles"]) if p["speech_bubbles"] else "None"
    setting = p.get("setting", "")[:40]
    action = p.get("action", "")[:90]
    out_lines.append(f"{p['panel_id']}: [{chars}] | {setting} | {action} | Text: {speech}")

Path("data/chapters/overgeared/ch01/panel_dump.txt").write_text("\n".join(out_lines), encoding="utf-8")
print(f"Dumped {len(out_lines)} panels to panel_dump.txt successfully.")
