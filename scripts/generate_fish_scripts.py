"""Generate dedicated expressive Fish TTS scripts (04_script_fish.json) from raw 04_script.json.

Preserves raw 04_script.json completely untouched. Reads 03_descriptions.json to analyze
panel expressions, actions, ambient mood, and dialogue, then injects natural, dynamic Fish Audio
inline tags ([excited], [chuckle], [sighs], [shocked], [whispering], etc.) to give the narration
vibrant, engaging YouTube-recap prosody.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

CHAPTERS_1_TO_30 = [
    "ch01", "ch02", "ch003", "ch004", "ch005", "ch005_5", "ch06", "ch007", "ch008", "ch009",
    "ch010", "ch011", "ch012", "ch013", "ch014", "ch015", "ch016", "ch017", "ch018", "ch019",
    "ch020", "ch021", "ch022", "ch023", "ch024", "ch025", "ch026", "ch027", "ch028", "ch029", "ch030"
]

# Keyword-to-tag mappings
EMOTION_RULES = [
    # (Regex pattern, Tag)
    (r"\b(scream|shriek|shout|yell|roar|bellow|charge)\b", "[shouting]"),
    (r"\b(panic|freak out|terrified|horrif|alarmed)\b", "[panicked]"),
    (r"\b(shock|stunned|gasp|jaw drop|eyes wide|disbelief|unbelievable)\b", "[shocked]"),
    (r"\b(laugh|chuckle|giggle|snicker|cackle|wheeze)\b", "[laughing]"),
    (r"\b(smirk|smug|teas|mock|grin|cocky)\b", "[smug]"),
    (r"\b(sigh|exhaust|wiped out|tired|collapse|slump|groan|passed out)\b", "[sighs]"),
    (r"\b(confus|puzzl|wonder|baffl|what the|huh\?|tilt head)\b", "[confused]"),
    (r"\b(curious|examin|inspect|analyz|study|look closer)\b", "[curious]"),
    (r"\b(whisper|murmur|mutter|quiet|hush|sneak|secret)\b", "[whispering]"),
    (r"\b(proud|triumph|cheer|rejoic|victor|celebrat|beaming)\b", "[proud]"),
    (r"\b(nervous|fluster|stammer|stutter|sweat|awkward|hesitat)\b", "[nervous]"),
    (r"\b(deadpan|flat|unimpressed|blank stare|sarcas|ironic)\b", "[deadpan]"),
    (r"\b(serious|grim|fierce|glare|frown|dark|danger|warn)\b", "[serious]"),
    (r"\b(excit|eager|thrill|hyped|delight|enthusias)\b", "[excited]"),
    (r"\b(relie|thankfully|safe|dodged|whew)\b", "[relieved]"),
    (r"\b(warm|gentle|kind|soft|friendly|fond)\b", "[warm tone]"),
]

MOOD_RULES = [
    (r"\b(comedic|funny|humor|silly|goofy)\b", "[amused]"),
    (r"\b(intense|action|battle|explosive|high-impact)\b", "[intense]"),
    (r"\b(tense|suspense|dramatic|peril)\b", "[intense]"),
    (r"\b(mysterious|eerie|shadowy)\b", "[mysterious]"),
    (r"\b(cheerful|upbeat|lighthearted|joyful)\b", "[cheerful]"),
    (r"\b(sad|melanchol|depress|gloomy)\b", "[gloomy]"),
]

DIRECTION_RULES = {
    "establishing": "[excited]",
    "intro": "[excited]",
    "action": "[intense]",
    "comedic": "[amused]",
    "punchline": "[laughing]",
    "reaction": "[shocked]",
    "climax": "[intense]",
    "transition": "[curious]",
}


def _detect_tag_from_context(text: str, panel_descs: list[dict[str, Any]], direction: str) -> str:
    """Analyze context text, panel expressions, actions, and directions to choose best tag."""
    # Combine panel info
    context_corpus = " ".join([
        f"{p.get('expression', '')} {p.get('ambient_mood', '')} {p.get('action', '')} {' '.join(p.get('speech_bubbles', []))}"
        for p in panel_descs
    ]).lower()

    text_lower = text.lower()

    # 1. Match from explicit character expressions & actions in the panels
    for pattern, tag in EMOTION_RULES:
        if re.search(pattern, context_corpus):
            return tag

    # 2. Match from ambient mood
    for pattern, tag in MOOD_RULES:
        if re.search(pattern, context_corpus):
            return tag

    # 3. Match from narration text cues
    for pattern, tag in EMOTION_RULES:
        if re.search(pattern, text_lower):
            return tag

    # 4. Fallback to direction or general tone
    if direction in DIRECTION_RULES:
        return DIRECTION_RULES[direction]

    if "!" in text:
        return "[excited]"
    if "?" in text:
        return "[curious]"
    if "..." in text or "—" in text:
        return "[thoughtful]"

    return "[cheerful]"


def add_expressions_to_narration(
    narration: str,
    panel_descs: list[dict[str, Any]],
    direction: str,
) -> str:
    """Inject natural, expressive Fish Audio tags into the narration text."""
    if not narration.strip():
        return narration

    # If already tagged, don't double tag
    if "[" in narration and "]" in narration:
        return narration

    # Determine lead emotion tag
    primary_tag = _detect_tag_from_context(narration, panel_descs, direction)

    # Break into sentences or clauses
    # Look for quotes, dramatic breaks like '—', or sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", narration.strip())

    tagged_parts = []
    current_tag = primary_tag

    for i, s in enumerate(sentences):
        if not s.strip():
            continue

        part = s.strip()

        # Handle intra-sentence contrast (e.g. em-dash or 'However,')
        if "—" in part and not part.startswith("—"):
            halves = part.split("—", 1)
            first_half = halves[0].strip()
            second_half = halves[1].strip()

            tag1 = current_tag
            # Determine contrast tag for second half
            if re.search(r"\b(wiped out|exhaust|slump|fail|dead|die|collapsed|zero|nope|nobody)\b", second_half.lower()):
                tag2 = "[sighs]"
            elif re.search(r"\b(suddenly|whoa|surprise|boom|blast|attack|wait)\b", second_half.lower()):
                tag2 = "[shocked]"
            elif re.search(r"\b(turns out|of course|classic|naturally|laugh)\b", second_half.lower()):
                tag2 = "[chuckle]"
            else:
                tag2 = "[amused]"

            part = f"{tag1} {first_half}—{tag2} {second_half}"
            tagged_parts.append(part)
            current_tag = tag2
            continue

        # Handle quotes within the sentence
        quote_match = re.search(r'(".*?"|\'.*?\')', part)
        if quote_match and len(quote_match.group(0)) > 6:
            quote_text = quote_match.group(0)
            quote_tag = _detect_tag_from_context(quote_text, panel_descs, "reaction")
            before_quote = part[:quote_match.start()].strip()
            after_quote = part[quote_match.end():].strip()

            lead = f"{current_tag} {before_quote} " if before_quote else ""
            quoted = f"{quote_tag} {quote_text}"
            trail = f" {after_quote}" if after_quote else ""
            tagged_parts.append(f"{lead}{quoted}{trail}".strip())
            continue

        # Regular sentence
        if i == 0:
            tagged_parts.append(f"{primary_tag} {part}")
        else:
            # Subtle variation for subsequent sentences
            sub_tag = _detect_tag_from_context(part, panel_descs, direction)
            if sub_tag != current_tag:
                tagged_parts.append(f"{sub_tag} {part}")
                current_tag = sub_tag
            else:
                tagged_parts.append(part)

    result = " ".join(tagged_parts)
    # Clean up double spaces or awkward spacing
    result = re.sub(r"\s+", " ", result)
    result = re.sub(r"\[\w+(\s+\w+)*\]\s*\[\w+(\s+\w+)*\]", lambda m: m.group(0).split("]")[0] + "]", result)
    return result


def process_chapter(chapter_dir: Path) -> Path | None:
    """Generate 04_script_fish.json for a chapter if raw script exists."""
    script_file = chapter_dir / "04_script.json"
    desc_file = chapter_dir / "03_descriptions.json"

    if not script_file.exists():
        print(f"[{chapter_dir.name}] No 04_script.json found, skipping.")
        return None

    with open(script_file, encoding="utf-8") as f:
        script_data = json.load(f)

    panel_map = {}
    if desc_file.exists():
        with open(desc_file, encoding="utf-8") as f:
            desc_data = json.load(f)
            for p in desc_data.get("panels", []):
                panel_map[p.get("panel_id")] = p

    fish_blocks = []
    for block in script_data.get("blocks", []):
        p_ids = block.get("panel_ids", [])
        descs = [panel_map[pid] for pid in p_ids if pid in panel_map]
        direction = block.get("direction", "beat")
        raw_narration = block.get("narration", "")

        expressive_narration = add_expressions_to_narration(raw_narration, descs, direction)

        new_block = dict(block)
        new_block["narration"] = expressive_narration

        # If beats exist, adapt them as well
        if "beats" in block and block["beats"]:
            new_beats = []
            for b in block["beats"]:
                b_copy = dict(b)
                b_pid = b.get("panel_id")
                b_descs = [panel_map[b_pid]] if b_pid in panel_map else descs
                b_copy["text"] = add_expressions_to_narration(b.get("text", ""), b_descs, direction)
                new_beats.append(b_copy)
            new_block["beats"] = new_beats

        fish_blocks.append(new_block)

    fish_script_data = dict(script_data)
    fish_script_data["blocks"] = fish_blocks
    fish_script_data["tts_target"] = "fish-audio (s2.1-pro-free)"

    out_file = chapter_dir / "04_script_fish.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(fish_script_data, f, indent=2, ensure_ascii=False)

    print(f"[{chapter_dir.name}] Created {out_file.name} with {len(fish_blocks)} expressive blocks.")
    return out_file


def main() -> None:
    chapters_root = Path("data/chapters")
    processed = 0
    for ch in CHAPTERS_1_TO_30:
        ch_dir = chapters_root / ch
        if ch_dir.is_dir():
            res = process_chapter(ch_dir)
            if res:
                processed += 1
    print(f"\nAll done! Successfully generated 04_script_fish.json for {processed} chapters.")


if __name__ == "__main__":
    main()
