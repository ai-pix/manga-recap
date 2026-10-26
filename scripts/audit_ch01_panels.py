import json
from pathlib import Path

ch01_desc = json.loads(Path("data/chapters/overgeared/ch01/03_descriptions.json").read_text(encoding="utf-8"))
panels = ch01_desc["panels"]

suspicious = []

for p in panels:
    pid = p["panel_id"]
    setting = p.get("setting", "").lower()
    action = p.get("action", "").lower()
    speech = p.get("speech_bubbles", [])
    chars = p.get("characters", [])

    reasons = []
    # Title / credits
    if any(t in setting or t in action for t in ["title", "credits", "logo", "team argo", "author"]):
        reasons.append("title_or_credits")
    if any("team argo" in s.lower() or "템빨" in s for s in speech):
        reasons.append("title_text")

    # Blank / empty
    if any(t in action for t in ["blank", "no clear action", "almost entirely blank", "white space"]):
        reasons.append("empty_or_blank")
    if not action or action == "visual scene transition or illustration panel.":
        reasons.append("generic_action")

    # Standalone speech bubble crops
    if not chars and ("speech bubble" in action or "caption" in action or "text" in action):
        if "is displayed" in action or "contains" in action or "abstract white background" in setting:
            reasons.append("floating_bubble_or_text_crop")

    # Pure sound effects or speed lines with no characters or story action
    if not chars and not speech and any(t in action for t in ["speed lines", "abstract action background", "close-up view shows a figure's torso"]):
        reasons.append("abstract_sfx_or_wedge")

    if reasons:
        suspicious.append({
            "panel_id": pid,
            "reasons": reasons,
            "setting": setting[:40],
            "action": action[:70],
            "speech": speech
        })

out_path = Path("data/chapters/overgeared/ch01/suspicious_panels.json")
out_path.write_text(json.dumps(suspicious, indent=2), encoding="utf-8")
print(f"Total panels audited: {len(panels)}")
print(f"Suspicious panels flagged: {len(suspicious)}")
for s in suspicious:
    print(f"  {s['panel_id']}: {s['reasons']} | {s['action'][:50]} | Speech: {len(s['speech'])}")
