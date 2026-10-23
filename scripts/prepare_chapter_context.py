"""Prepare clean panel context and flag ad/credits panels for any chapter."""

import json
import sys
from pathlib import Path


def process_chapter_context(ch_num: int):
    ch_id = f"ch{ch_num:02d}"
    ch_dir = Path(f"data/chapters/sss-class-revival-hunter/{ch_id}")
    desc_p = ch_dir / "03_descriptions.json"
    if not desc_p.exists():
        print(f"Error: {desc_p} not found")
        return

    data = json.loads(desc_p.read_text(encoding="utf-8"))
    panels = data.get("panels", [])

    art_panels = []
    ad_panels = []

    for idx, p in enumerate(panels, start=1):
        pid = p.get("panel_id")
        setting = str(p.get("setting", "")).lower()
        speech = p.get("speech_bubbles", [])
        speech_txt = " ".join(speech).lower()

        # Check for promo/ad/credit keywords
        is_promo = (
            "tapas" in speech_txt
            or "patreon" in speech_txt
            or "discord" in speech_txt
            or "invite code" in speech_txt
            or "repost in other socmed" in speech_txt
            or "support the official" in speech_txt
            or "promotional banner" in setting
            or "title card / logo" in setting
        )

        if is_promo:
            p["is_credits_or_ad"] = True
            ad_panels.append(pid)
        else:
            art_panels.append(p)

    # Save updated descriptions with ad flags
    desc_p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Also sync to NTFS junction
    alt_desc = Path(f"data/chapters/revival_hunter_{ch_id}/03_descriptions.json")
    if alt_desc.parent.exists():
        alt_desc.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[{ch_id}] Total: {len(panels)} | Art: {len(art_panels)} | Promo/Ad: {len(ad_panels)} ({ad_panels})")
    return art_panels, ad_panels


if __name__ == "__main__":
    if len(sys.argv) > 1:
        chs = [int(x.replace("ch", "")) for x in sys.argv[1:]]
    else:
        chs = list(range(2, 11))
    for c in chs:
        process_chapter_context(c)
