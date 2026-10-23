"""Batch summary generator using Inception Labs Mercury-2.5 for Chapters 44 to 112."""

import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

KEY = "sk_284d1757dfe2eaa9a76ff141fb3f29ff"
BASE_URL = "https://api.inceptionlabs.ai/v1"
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
}

SYSTEM_PROMPT = """You are a senior anime/manga recap script supervisor and game mechanics analyst.
Your job is to read raw manga panel descriptions and generate a structured, highly actionable Narrative & Strategic Tactics Summary for our recap narrator.

Structure your Markdown summary as follows:
# Chapter XX Recap: [Chapter Title / Core Theme]

### 1. Core Plot Arc
High-level overview of what happens from beginning to end in 3-4 sentences.

### 2. Key Game Mechanics & Strategic Tactics
- Bullet points detailing any specific game skills, craft recipes, boss mechanics, or combat exploits introduced or used in this chapter.

### 3. Character Motives & Dynamics
- Bullet points covering character goals, comedic friction, and interpersonal highlights (e.g. Shun/Yun's avatar dynamics, sisterly teasing, party banter).

### 4. Section-by-Section Beat Outline
Divide the chapter chronologically into 5 to 6 distinct phases/scenes, specifying the exact panel range for each (e.g., Phase 1: Panels 0001–0025, Phase 2: Panels 0026–0050, etc.), summarizing what visually happens and what dialogue reveals.
"""


def get_all_target_chapters():
    data_dir = Path("data/chapters")
    chapters = []

    # Standard chapters 41 to 112
    for i in range(41, 113):
        ch = f"ch{i:03d}" if i < 100 else f"ch{i}"
        if (data_dir / ch).is_dir():
            chapters.append(ch)

    # Include special chapters
    for special in ["ch058_5", "ch103_5"]:
        if (data_dir / special).is_dir() and special not in chapters:
            chapters.append(special)

    def sort_key(name):
        # Sort numerically: ch058 -> 58.0, ch058_5 -> 58.5
        clean = name.replace("ch0", "").replace("ch", "")
        if "_" in clean:
            parts = clean.split("_")
            return float(parts[0]) + float(parts[1]) / 10.0
        return float(clean)

    chapters.sort(key=sort_key)
    return chapters


def summarize_chapter(ch_id: str, timeout: int = 50, max_retries: int = 3) -> bool:
    desc_path = Path(f"data/chapters/{ch_id}/03_descriptions.json")
    summary_path = Path(f"data/chapters/{ch_id}/04_summary.md")

    if not desc_path.exists():
        print(f"[{ch_id}] Error: {desc_path} does not exist!", flush=True)
        return False

    # Check if already done
    if summary_path.exists() and summary_path.stat().st_size > 200:
        print(
            f"[{ch_id}] Already summarized ({summary_path.stat().st_size} bytes), skipping.",
            flush=True,
        )
        return True

    try:
        with open(desc_path, encoding="utf-8") as f:
            desc_data = json.load(f)
    except Exception as e:
        print(f"[{ch_id}] Error loading JSON: {e}", flush=True)
        return False

    panels = desc_data.get("panels", [])
    if not panels:
        print(f"[{ch_id}] Error: no panels found in descriptions!", flush=True)
        return False

    lines = []
    for p in panels:
        pid = p.get("panel_id", "")
        chars = ", ".join(p.get("characters", [])) or "nobody"
        action = p.get("action", "")
        speech = " | ".join(p.get("speech_bubbles", []))
        line = f"[{pid}] {chars}: {action}"
        if speech:
            line += f' -> Dialogue: "{speech}"'
        lines.append(line)

    panels_text = "\n".join(lines)
    user_prompt = f"Here are the raw panel descriptions for {ch_id} ({len(panels)} panels):\n\n{panels_text}\n\nAnalyze the panels and generate the complete structured Narrative & Strategic Tactics Summary in Markdown format."

    payload = {
        "model": "mercury-2.5",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4000,
        "temperature": 0.3,
    }

    req_data = json.dumps(payload).encode("utf-8")

    for attempt in range(1, max_retries + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(
                f"{BASE_URL}/chat/completions",
                headers=HEADERS,
                data=req_data,
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            content = data["choices"][0]["message"]["content"]
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(content.strip() + "\n")

            elapsed = time.time() - t0
            print(
                f"[{ch_id}] Generated in {elapsed:.2f}s ({len(content)} chars) -> {summary_path}",
                flush=True,
            )
            return True
        except Exception as e:
            elapsed = time.time() - t0
            if attempt < max_retries:
                wait_sec = attempt * 3
                print(
                    f"[{ch_id}] Attempt {attempt} failed ({e}) in {elapsed:.1f}s, retrying in {wait_sec}s...",
                    flush=True,
                )
                time.sleep(wait_sec)
            else:
                print(f"[{ch_id}] FAILED after {max_retries} attempts: {e}", flush=True)
                return False


def main():
    chapters = get_all_target_chapters()
    pending = []
    data_dir = Path("data/chapters")
    for ch in chapters:
        s_path = data_dir / ch / "04_summary.md"
        if not s_path.exists() or s_path.stat().st_size <= 200:
            pending.append(ch)

    print(f"Total target chapters: {len(chapters)}")
    print(f"Already completed: {len(chapters) - len(pending)}")
    print(f"Pending generation: {len(pending)} chapters: {pending}\n", flush=True)

    if not pending:
        print("All chapter summaries are already complete!")
        return

    # Use 2 workers for steady, reliable throughput without rate limit pressure
    success_count = 0
    fail_count = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_ch = {executor.submit(summarize_chapter, ch): ch for ch in pending}
        for future in as_completed(future_to_ch):
            ch = future_to_ch[future]
            try:
                ok = future.result()
                if ok:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"[{ch}] Unhandled exception: {e}", flush=True)
                fail_count += 1

    total_time = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"Batch Summary Generation Complete in {total_time:.1f}s ({total_time / 60:.2f}m)")
    print(f"Success: {success_count}, Failed: {fail_count}")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
