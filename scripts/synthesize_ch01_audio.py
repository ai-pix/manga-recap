"""Robust Chapter Narration Synthesizer for Overgeared Chapter 1:
Uses Google Gemini 2.5 Flash TTS with PCM-16 decoding:
- Batches narration blocks (4 blocks per batch)
- Respects Gemini free-tier rate limits (3 requests per minute -> 22s pause between calls)
- Concatenates audio into data/chapters/overgeared/ch01/05_narration.wav
- Generates 06_timeline.json with word-level timestamps using local Whisper
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

import numpy as np
import requests
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
CACHE_DIR = CH_DIR / "_gemini_tts_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 1. Load API Key
env_lines = (REPO_ROOT / "config" / ".env").read_text(encoding="utf-8").splitlines()
gemini_key = [l.split("=", 1)[1].strip() for l in env_lines if l.startswith("GEMINI_API_KEY")][0]

script: ScriptFile = load_model(SCRIPT_PATH, ScriptFile)
blocks = script.blocks
print(f"Total blocks to synthesize: {len(blocks)} ({script.target_words} words)")

# 2. Divide into batches of 4 blocks
BATCH_SIZE = 4
batches: list[list[str]] = []
batch_blocks: list[list[str]] = []
cur_texts = []
cur_ids = []
for b in blocks:
    cur_texts.append(b.narration.strip())
    cur_ids.append(b.block_id)
    if len(cur_texts) >= BATCH_SIZE:
        batches.append(cur_texts)
        batch_blocks.append(cur_ids)
        cur_texts = []
        cur_ids = []
if cur_texts:
    batches.append(cur_texts)
    batch_blocks.append(cur_ids)

print(f"Total batches: {len(batches)}")

audio_chunks = []
sr = 24000
model_name = "gemini-2.5-flash-preview-tts"
voice_name = "Puck"
url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"

for idx, (b_texts, b_ids) in enumerate(zip(batches, batch_blocks), start=1):
    cache_file = CACHE_DIR / f"batch_{idx:02d}.wav"
    if cache_file.exists():
        print(f"  [Batch {idx:02d}/{len(batches)}] Loading cached audio ({b_ids[0]}..{b_ids[-1]})...")
        c_audio, c_sr = sf.read(str(cache_file), dtype="float32")
        audio_chunks.append(c_audio)
        continue

    text_payload = "\n\n".join(b_texts)
    print(f"  [Batch {idx:02d}/{len(batches)}] Synthesizing {len(b_texts)} blocks ({b_ids[0]}..{b_ids[-1]}, {len(text_payload)} chars)...", flush=True)

    payload = {
        "contents": [{"parts": [{"text": text_payload}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            }
        }
    }

    success = False
    for attempt in range(1, 6):
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
                raw = base64.b64decode(b64)
                chunk_audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                sf.write(str(cache_file), chunk_audio, sr, subtype="PCM_16")
                audio_chunks.append(chunk_audio)
                success = True
                print(f"    -> Done: {len(chunk_audio)/sr:.1f}s audio.")
                break
            elif resp.status_code == 429:
                print(f"    -> Rate limited (429), waiting 25s (attempt {attempt}/5)...", flush=True)
                time.sleep(25)
            else:
                print(f"    -> Error {resp.status_code}: {resp.text[:150]}, waiting 10s...", flush=True)
                time.sleep(10)
        except Exception as e:
            print(f"    -> Exception: {e}, waiting 10s...", flush=True)
            time.sleep(10)

    if not success:
        raise RuntimeError(f"Failed to synthesize batch {idx}")

    # Rate pacing for Gemini Free Tier (max 3 req/min)
    if idx < len(batches):
        time.sleep(22)

# Concatenate all chunks with 180ms gap
gap = np.zeros(int(sr * 0.18), dtype=np.float32)
final_pieces = []
for i, c in enumerate(audio_chunks):
    final_pieces.append(c)
    if i < len(audio_chunks) - 1:
        final_pieces.append(gap)

final_audio = np.concatenate(final_pieces)
total_dur = len(final_audio) / float(sr)
sf.write(str(NARRATION_PATH), final_audio, sr, subtype="PCM_16")
print(f"\nSaved full narration: {NARRATION_PATH.name} ({total_dur:.1f}s / {total_dur/60:.2f} mins)")

# Whisper alignment
print("\nRunning Whisper alignment...")
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
    tts_backend="gemini-2.5-flash-preview-tts (Puck)",
    whisper_model="whisper-base",
    created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
    words=words_data,
    blocks=block_timings,
)
save_model(timeline, TIMELINE_PATH)
print(f"Saved timeline: {TIMELINE_PATH.name} ({len(block_timings)} blocks, match_ratio={match_ratio:.2f})")
print("\nSTAGE 4 COMPLETE!")
