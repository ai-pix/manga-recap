import json
from pathlib import Path

desc = json.loads(Path("data/chapters/overgeared/ch01/03_descriptions.json").read_text(encoding="utf-8"))
for p in desc["panels"]:
    sett = p.get("setting", "").lower()
    act = p.get("action", "").lower()
    chars = p.get("characters", [])
    speech = p.get("speech_bubbles", [])

    # 1. Pure floating speech bubbles
    is_pure_text = not chars and ("speech bubble" in act or "caption" in act or "dialogue" in act or "abstract white" in sett)
    if is_pure_text and speech:
        clean_speech = speech[0][:60].encode("ascii", errors="ignore").decode("ascii")
        print(f"TEXT BUBBLE: {p['panel_id']} -> {clean_speech}")

    # 2. Blank or empty
    if "blank" in act or "no clear action" in act or not act:
        print(f"BLANK/EMPTY: {p['panel_id']}")

    # 3. Title / credits
    if "title" in sett or "title" in act or any("team argo" in s.lower() or "템빨" in s for s in speech):
        print(f"TITLE/CREDITS: {p['panel_id']}")
