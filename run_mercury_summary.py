import json
import urllib.request
from pathlib import Path

desc = json.loads(Path("data/chapters/barbarian_ch02/03_descriptions.json").read_text(encoding="utf-8"))
panel_summaries = []
for p in desc["panels"]:
    pid = p["panel_id"]
    act = p.get("action", "")
    speech = " | ".join(p.get("speech_bubbles", []))
    chars = ", ".join(p.get("characters", []))
    panel_summaries.append(f"[{pid}] Chars: {chars}; Action: {act}; Dialogue: {speech}")

full_context = "\n".join(panel_summaries)
prompt = (
    "You are a master manhwa recap storyteller. Below are the sequential panel descriptions for "
    "Chapter 2 of 'Surviving the Game as a Barbarian'.\n"
    "Provide an engaging, detailed narrative summary of Chapter 2 that captures all story beats, "
    "character dialogues, barbarian lore/customs, and dramatic stakes.\n\n"
    f"PANEL DESCRIPTIONS:\n{full_context}\n"
)

payload = {
    "model": "inception/mercury-2.5",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 3000,
    "reasoning": {"max_tokens": 0},
}

req = urllib.request.Request(
    "https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}",
        "Content-Type": "application/json",
    },
    data=json.dumps(payload).encode(),
)

print("Requesting Mercury 2.5 summary for Chapter 2...")
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode())
    summary = data["choices"][0]["message"].get("content", "")
    out_file = Path("data/chapters/barbarian_ch02/03_summary_mercury.txt")
    out_file.write_text(summary, encoding="utf-8")
    print(f"Mercury 2.5 summary saved to {out_file}! Length: {len(summary)} chars.")
    print("Preview:\n", summary[:300])
