import json
import sys
from pathlib import Path

def inspect(ch_num):
    ch_id = f"ch{ch_num:02d}"
    p = Path(f"data/chapters/sss-class-revival-hunter/{ch_id}/03_descriptions.json")
    if not p.exists():
        print(f"Not found: {p}")
        return
    data = json.loads(p.read_text(encoding="utf-8"))
    panels = data.get("panels", [])
    print(f"=== {ch_id}: {len(panels)} panels ===")
    for idx, p in enumerate(panels):
        if p.get("is_credits_or_ad"):
            continue
        pid = p.get("panel_id")
        pg = p.get("page_number")
        chars = ", ".join(p.get("characters", []))
        act = p.get("action", "")
        if isinstance(act, dict):
            act = str(act)
        speech = p.get("speech_bubbles", [])
        line = f"[{pid}] (P{pg}) {act[:75]}"
        if speech:
            speech_clean = " | ".join(speech)[:100].encode("ascii", errors="replace").decode("ascii")
            line += f" || Sp: {speech_clean}"
        print(line[:160])

if __name__ == "__main__":
    ch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    inspect(ch)

