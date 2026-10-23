"""Generate a 1-minute YouTube recap test narration using Fish Audio s2.1-pro-free zero-shot voice cloning."""

import io
import time
from pathlib import Path
import httpx
import numpy as np
import ormsgpack
import soundfile as sf

# 1. Load API Key
api_key = ""
for env_path in [Path("config/.env"), Path(".env")]:
    if not api_key and env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("FISH_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip("\"'")
                    break

if not api_key:
    raise ValueError("FISH_API_KEY not found in config/.env or .env")

# 2. Load clean reference voice audio
ref_path = Path("data/voice_cloning/reference_voice_clean.mp3")
with open(ref_path, "rb") as f:
    ref_audio_bytes = f.read()

ref_transcript = "Playing the prototype of Plants vs. Zombies the board game with the creator."

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/msgpack",
    "model": "s2.1-pro-free",
}

# 3. 1-Minute YouTube recap narration script (~150 words across 5 beats)
script_blocks = [
    {
        "id": "block_01",
        "text": "Kim Gong-ja stares at the towering holographic status window hovering in the dead of night.",
    },
    {
        "id": "block_02",
        "text": "For ten grueling years, he scraped by as a bottom-tier hunter in the grand spire, desperately envious of the legendary Flame Emperor Yoo Soo-ha.",
    },
    {
        "id": "block_03",
        "text": "Every single day, Gong-ja prayed for an S-rank miracle, anything to drag him out of the gutter.",
    },
    {
        "id": "block_04",
        "text": "Instead, it branded him with an insidious, cursed ability: I Want to Become Just Like You. A skill that only triggers upon death, copying a single ability from the butcher who murdered him.",
    },
    {
        "id": "block_05",
        "text": "A wicked smirk crosses his face amidst the pouring rain. If conquering this tower demands dying, then he will gladly die a thousand times over to reach the top!",
    },
]

print(f"=== Synthesizing 1-Minute Cloned Narration using Fish Audio S2.1-Pro-Free ===")
print(f"Reference Audio: {ref_path.name} ({len(ref_audio_bytes)} bytes)")
print(f"Total Blocks: {len(script_blocks)}")

audio_segments = []
output_sr = 44100

for i, block in enumerate(script_blocks, 1):
    print(f"\n[Block {i}/{len(script_blocks)}] Synthesizing: \"{block['text'][:50]}...\"")
    payload = {
        "text": block["text"],
        "model": "s2.1-pro-free",
        "references": [
            {
                "audio": ref_audio_bytes,
                "text": ref_transcript,
            }
        ],
        "format": "wav",
        "temperature": 0.7,
    }

    packed = ormsgpack.packb(payload)

    success = False
    for attempt in range(1, 4):
        try:
            r = httpx.post(
                "https://api.fish.audio/v1/tts",
                headers=headers,
                content=packed,
                timeout=45.0,
            )
            if r.status_code == 200 and len(r.content) > 1000:
                data, sr = sf.read(io.BytesIO(r.content), dtype="float32")
                if data.ndim > 1:
                    data = data[:, 0]
                output_sr = sr
                audio_segments.append(data)
                # Add natural 0.28s pause between narrative beats
                pause = np.zeros(int(sr * 0.28), dtype="float32")
                audio_segments.append(pause)
                print(f"  -> Generated {len(data)/sr:.2f}s of audio (Sample rate: {sr} Hz)")
                success = True
                break
            else:
                print(f"  Attempt {attempt} returned HTTP {r.status_code}: {r.text[:80]}")
                time.sleep(2.0)
        except Exception as e:
            print(f"  Attempt {attempt} failed: {e}")
            time.sleep(2.0)

    if not success:
        raise RuntimeError(f"Failed to synthesize block {block['id']}")

# Assemble final narration track
final_waveform = np.concatenate(audio_segments)
total_duration = len(final_waveform) / output_sr

out_file = Path("data/voice_cloning/cloned_youtube_voice_1min_test.wav")
sf.write(str(out_file), final_waveform, output_sr, subtype="PCM_16")

print("\n" + "="*60)
print(f"CLONED VOICE TEST NARATION COMPLETE!")
print(f"Output File: {out_file.resolve()}")
print(f"Total Duration: {total_duration:.2f} seconds (~{total_duration/60:.2f} minutes)")
print(f"Audio Quality: {output_sr} Hz, 16-bit PCM WAV (Studio Quality)")
print("="*60)
