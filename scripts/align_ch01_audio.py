"""Align Overgeared Chapter 1 full narration audio with Whisper and generate 06_timeline.json."""

import time
from pathlib import Path

import soundfile as sf
import whisper

from manga_recap.core.schema import (
    BlockTiming,
    ScriptFile,
    TimelineFile,
    WordTiming,
    load_model,
    save_model,
)
from manga_recap.stages.s4_speech.aligner import (
    align_tokens,
    block_boundaries,
    normalise_tokens,
    proportional_boundaries,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CH_DIR = REPO_ROOT / "data" / "chapters" / "overgeared" / "ch01"
SCRIPT_PATH = CH_DIR / "04_script.json"
NARRATION_PATH = CH_DIR / "05_narration.wav"
TIMELINE_PATH = CH_DIR / "06_timeline.json"

script: ScriptFile = load_model(SCRIPT_PATH, ScriptFile)
blocks = script.blocks
info = sf.info(str(NARRATION_PATH))
total_dur = info.duration
sr = info.samplerate

print(f"Aligning {NARRATION_PATH.name} ({total_dur:.1f}s, {len(blocks)} blocks)...")

w_model = whisper.load_model("base")
res = w_model.transcribe(str(NARRATION_PATH), word_timestamps=True)
heard = []
for segment in res.get("segments", []):
    for w in segment.get("words", []):
        t = (w.get("word") or "").strip()
        if t:
            heard.append((t, float(w.get("start", 0.0)), float(w.get("end", 0.0))))

print(f"Whisper detected {len(heard)} words.")

block_texts = [b.narration for b in blocks]
script_tokens = [t for blk in block_texts for t in normalise_tokens(blk)]
timings, match_ratio = align_tokens(script_tokens, heard)
words_data = [
    WordTiming(word=t.token, start=round(t.start, 3), end=round(t.end, 3))
    for t in timings
]

method = "aligned" if match_ratio >= 0.50 else "fallback_proportional"
boundaries = block_boundaries(block_texts, timings) if method == "aligned" else proportional_boundaries(block_texts, total_dur)

block_timings = []
for block, (start, end) in zip(blocks, boundaries, strict=False):
    start = max(0.0, min(start, total_dur))
    end = max(start, min(end, total_dur))
    block_timings.append(
        BlockTiming(
            block_id=block.block_id,
            start=round(start, 3),
            end=round(end, 3),
            method=method,
            match_ratio=round(match_ratio, 4),
        )
    )

timeline = TimelineFile(
    chapter_id="ch01",
    audio_file=NARRATION_PATH.name,
    sample_rate=sr,
    duration=round(total_dur, 3),
    tts_backend="gemini-3.8-flash-lite-tts (Puck)",
    whisper_model="whisper-base",
    created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    words=words_data,
    blocks=block_timings,
)
save_model(timeline, TIMELINE_PATH)
print(f"SUCCESS: Saved {TIMELINE_PATH.name} ({len(block_timings)} blocks, match_ratio={match_ratio:.2f})")
