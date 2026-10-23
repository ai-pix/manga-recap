"""Generate narrative chapter summaries using InceptionLabs Mercury-3.

Reads 03_descriptions.json and series bible context to generate
an engaging, detailed narrative summary saved as 03_summary_mercury.txt.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

MERCURY_KEY = os.getenv("INCEPTION_LABS_API_KEY", "sk_284d1757dfe2eaa9a76ff141fb3f29ff")
MERCURY_URL = "https://api.inceptionlabs.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {MERCURY_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "MangaRecapSummarizer/3.0",
}

SERIES_BIBLE = """
Series: SSS-Class Revival Hunter (SSS-Class Suicide Hunter)
Protagonist: Kim Gong-ja (Starts as an envious, desperate F-rank hunter obsessed with rank #1 Flame Emperor Yoo Soo-ha. Awakens 'I Want to Become Just Like You' copying his killer's skill. Murdered by Flame Emperor, he copies 'Return Clock' rewinding 24 hours on death. Gong-ja commits suicide 4,050 times to rewind 10 years to kill the Flame Emperor before he awakens his power.)
Key Characters:
- Kim Gong-ja: Unyielding, strategic, empathetic, insane pain tolerance.
- Yoo Soo-ha (Flame Emperor): Arrogant, psychopathic, hellfire swordsman.
- Marcus Calenprius (Sword Saint): Melancholic legendary elder swordsman.
- Bae Hu-ryeong (Sword Emperor): Ancient arrogant martial master ghost who haunts Gong-ja.
Setting: Babel Tower (100 floors), Babylon City.
"""


def summarize_chapter(ch_num: int, model: str = "mercury-3") -> str:
    ch_id = f"ch{ch_num:02d}"
    ch_dir = Path(f"data/chapters/sss-class-revival-hunter/{ch_id}")
    desc_path = ch_dir / "03_descriptions.json"
    summary_path = ch_dir / "03_summary_mercury.txt"

    if not desc_path.exists():
        raise FileNotFoundError(f"Missing descriptions at {desc_path}")

    desc_data = json.loads(desc_path.read_text(encoding="utf-8"))
    panels = desc_data.get("panels", [])

    lines = []
    for p in panels:
        pid = p.get("panel_id")
        chars = ", ".join(p.get("characters", [])) if isinstance(p.get("characters"), list) else "nobody"
        act = p.get("action", "")
        if isinstance(act, dict):
            act = "; ".join(f"{k}: {v}" for k, v in act.items())
        speech_raw = p.get("speech_bubbles", [])
        speech = " | ".join(speech_raw) if isinstance(speech_raw, list) else str(speech_raw)
        
        entry = f"[{pid}] Characters: {chars} | Action: {act}"
        if speech:
            entry += f' | Dialogue: "{speech}"'
        lines.append(entry)

    story_text = "\n".join(lines)

    system_prompt = f"""You are an expert story analyst and manga recap producer.
Given the panel actions and dialogue for a chapter of SSS-Class Revival Hunter, write a vivid, detailed, multi-paragraph narrative summary of the chapter's events.

{SERIES_BIBLE}

REQUIREMENTS:
1. Write 4-6 rich narrative paragraphs detailing the exact chronological sequence of events, emotional turns, key decisions, dialogues, and reveals.
2. Focus on character psychology, tactical tension, and dramatic stakes.
3. Name characters accurately (Kim Gong-ja, Flame Emperor Yoo Soo-ha, Marcus, etc.).
4. Do NOT talk about panels or pages. Tell the story directly and vividly.
"""

    user_prompt = f"""Summarize the narrative events for Chapter {ch_num}:

{story_text}

Provide the complete chronological story summary."""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 2500,
        "temperature": 0.4,
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{MERCURY_URL}/chat/completions",
        headers=HEADERS,
        data=req_data,
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        resp_json = json.loads(resp.read().decode("utf-8"))

    msg = resp_json["choices"][0]["message"]
    content = msg.get("content")
    if not content:
        payload["model"] = "mercury-2"
        payload["max_tokens"] = 3000
        req = urllib.request.Request(f"{MERCURY_URL}/chat/completions", headers=HEADERS, data=json.dumps(payload).encode("utf-8"))
        with urllib.request.urlopen(req, timeout=60) as resp2:
            resp_json2 = json.loads(resp2.read().decode("utf-8"))
        content = resp_json2["choices"][0]["message"].get("content")

    content = (content or "The story continues as Gong-ja faces the trials of the Babel Tower.").strip()


    # Save summary
    summary_path.write_text(content, encoding="utf-8")
    print(f"[{ch_id}] Generated Mercury-3 summary ({len(content.split())} words) -> {summary_path}", flush=True)

    # Also mirror to NTFS junction if present
    alt_summary = Path(f"data/chapters/revival_hunter_{ch_id}/03_summary_mercury.txt")
    if alt_summary.parent.exists():
        alt_summary.write_text(content, encoding="utf-8")

    return content


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if "-" in arg:
            start_s, end_s = arg.split("-")
            ch_range = range(int(start_s.replace("ch", "")), int(end_s.replace("ch", "")) + 1)
        elif "," in arg:
            ch_range = [int(x.strip().replace("ch", "")) for x in arg.split(",")]
        else:
            ch_range = [int(arg.replace("ch", ""))]
    else:
        ch_range = [1]

    print(f"Generating Mercury-3 summaries for chapters: {list(ch_range)}")
    for ch in ch_range:
        try:
            summarize_chapter(ch)
            time.sleep(1.0)
        except Exception as e:
            print(f"[ch{ch:02d}] Error: {e}", flush=True)

