import json
import time
import urllib.request
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile
from manga_recap.stages.s3_script.validate import validate

desc_path = Path("data/chapters/barbarian_ch02/03_descriptions.json")
summary_path = Path("data/chapters/barbarian_ch02/03_summary_mercury.txt")
desc = json.loads(desc_path.read_text(encoding="utf-8"))
summary = summary_path.read_text(encoding="utf-8")

panels = desc["panels"]
# Filter out title/logo splash panels that are skippable
valid_panels = [p for p in panels if p["panel_id"] not in ["panel_0021", "panel_0022"]]

cache_dir = Path("data/chapters/barbarian_ch02/.script_chunks")
cache_dir.mkdir(parents=True, exist_ok=True)

chunk_size = 20
all_blocks = []
block_counter = 1

for chunk_idx, i in enumerate(range(0, len(valid_panels), chunk_size)):
    chunk_file = cache_dir / f"chunk_{chunk_idx:02d}.json"
    chunk = valid_panels[i : i + chunk_size]

    if chunk_file.exists():
        print(f"Loading cached chunk {chunk_idx + 1} ({len(chunk)} panels)...", flush=True)
        blocks = json.loads(chunk_file.read_text(encoding="utf-8"))
    else:
        chunk_lines = []
        for p in chunk:
            pid = p["panel_id"]
            act = p.get("action", "")
            speech = " | ".join(p.get("speech_bubbles", []))
            chars = ", ".join(p.get("characters", []))
            chunk_lines.append(f"Panel ID: {pid}\nCharacters: {chars}\nAction: {act}\nDialogue: {speech}\n")

        chunk_prompt = f"""You are an elite YouTube manhwa recap narrator (style: Mamoru Manhwa).
We are writing the synchronized recap narration for Chapter 2 of 'Surviving the Game as a Barbarian'.

NARRATIVE ARC CONTEXT:
\"\"\"
{summary}
\"\"\"

Write an individual spoken narration block for EACH panel below (1:1 mapping).
Each panel must receive its own block with:
- "block_id": "b001", ...
- "panel_ids": ["panel_XXXX"]  <-- EXACTLY ONE panel_id per block!
- "narration": 1 to 2 punchy, conversational, spoken sentences (10 to 18 words) that describe what is happening in that panel or explain character reasoning.
- "direction": "beat"
- "beats": []

STRICT VOCABULARY BANS:
NEVER say: 'panel', 'panels', 'chapter', 'page', 'manga', 'manhwa', 'author', 'artist', 'drawing', 'illustration', 'reader', 'viewers'.
Speak about Bjorn, Aynar, Karaq, the Elder, and the game mechanics directly.

PANELS TO SCRIPT (Total {len(chunk)} panels):
\"\"\"
{"".join(chunk_lines)}
\"\"\"

Return ONLY a JSON array of blocks:
[
  {{
    "block_id": "...",
    "panel_ids": ["..."],
    "narration": "...",
    "direction": "beat",
    "beats": []
  }}
]
"""

        payload = {
            "model": "inception/mercury-2.5",
            "messages": [{"role": "user", "content": chunk_prompt}],
            "max_tokens": 8000,
        }

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload).encode(),
        )

        blocks = None
        for attempt in range(4):
            print(f"Generating blocks for chunk {chunk_idx + 1} ({len(chunk)} panels, attempt {attempt + 1})...", flush=True)
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode())
                    if "choices" not in data or not data["choices"]:
                        print(f"No choices in response: {data}", flush=True)
                        time.sleep(3)
                        continue
                    content = data["choices"][0]["message"].get("content", "")
                    if not content:
                        print("Content is empty or null, retrying...", flush=True)
                        time.sleep(3)
                        continue
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].split("```")[0].strip()
                    blocks = json.loads(content)
                    if isinstance(blocks, dict) and "blocks" in blocks:
                        blocks = blocks["blocks"]
                    chunk_file.write_text(json.dumps(blocks, indent=2), encoding="utf-8")
                    break
            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {e}", flush=True)
                time.sleep(4)

        if not blocks:
            raise RuntimeError(f"Failed to generate chunk {chunk_idx + 1}")

    for b in blocks:
        b["block_id"] = f"b{block_counter:03d}"
        block_counter += 1
        all_blocks.append(b)

full_script = {
    "chapter_id": "barbarian_ch02",
    "title": "Chapter 2: The Shield of Survival",
    "series": "barbarian",
    "created_at": "2026-10-06T22:45:00",
    "model": "inception/mercury-2.5",
    "target_words": 1800,
    "blocks": all_blocks,
}

out_path = Path("data/chapters/barbarian_ch02/04_script.json")
out_path.write_text(json.dumps(full_script, indent=2), encoding="utf-8")
print(f"Script saved to {out_path} with {len(all_blocks)} blocks!", flush=True)

# Validate
cfg = load_config()
sc = ScriptFile.model_validate_json(out_path.read_text(encoding="utf-8"))
desc_obj = DescriptionFile.model_validate_json(desc_path.read_text(encoding="utf-8"))
rep = validate(sc, desc_obj, cfg)
print("Validation OK:", rep.ok, flush=True)
if not rep.ok:
    print(rep.render(), flush=True)

