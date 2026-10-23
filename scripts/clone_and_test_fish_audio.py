"""Synthesize a 1-minute YouTube recap test narration using Fish Audio API."""

import io
import os
import sys
import time
from pathlib import Path
import httpx
import soundfile as sf
import numpy as np

def get_fish_api_key() -> str:
    key = os.environ.get("FISH_API_KEY", "")
    for env_path in [Path("config/.env"), Path(".env")]:
        if not key and env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("FISH_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip("\"'")
                        break
    return key

def list_user_models(api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        r = httpx.get("https://api.fish.audio/model?self=true", headers=headers, timeout=10.0)
        if r.status_code == 200:
            data = r.json()
            return data.get("items", []) if isinstance(data, dict) else data
    except Exception as e:
        print(f"Error fetching models: {e}")
    return []

def synthesize_1min_test(voice_id: str):
    api_key = get_fish_api_key()
    if not api_key:
        print("ERROR: FISH_API_KEY not found in config/.env or .env")
        return False

    print(f"\n=== Synthesizing 1-Minute Test Audio with Voice ID: {voice_id} ===")
    
    test_narration_paragraphs = [
        "Kim Gong-ja stares at the towering holographic status window hovering in the dead of night. For ten grueling years, he scraped by as a bottom-tier hunter in the grand spire, desperately envious of the legendary Flame Emperor Yoo Soo-ha.",
        "Every single day, Gong-ja prayed for an S-rank miracle, anything to drag him out of the gutter. But when the system finally answered his desperate plea, it didn't bestow glory or invincible martial power.",
        "Instead, it branded him with an insidious, cursed ability: I Want to Become Just Like You. A skill that only activates upon death, copying a single ability from the very butcher who executed him.",
        "A wicked smirk crosses his face amidst the pouring rain. If surviving this brutal tower demands death, then he will gladly die a thousand times over to conquer the spire!"
    ]

    tts_headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": "s2.1-pro-free",
    }

    combined_audio = []
    output_sr = 44100

    for i, para in enumerate(test_narration_paragraphs, 1):
        print(f"Synthesizing block {i}/{len(test_narration_paragraphs)}...")
        payload = {
            "text": para,
            "reference_id": voice_id,
            "format": "wav",
            "temperature": 0.7,
        }

        success = False
        for attempt in range(1, 4):
            try:
                res = httpx.post("https://api.fish.audio/v1/tts", headers=tts_headers, json=payload, timeout=35.0)
                if res.status_code == 200 and len(res.content) > 100:
                    data, sr = sf.read(io.BytesIO(res.content), dtype="float32")
                    if data.ndim > 1:
                        data = data[:, 0]
                    output_sr = sr
                    combined_audio.append(data)
                    # 0.28s natural beat pause
                    pause = np.zeros(int(sr * 0.28), dtype="float32")
                    combined_audio.append(pause)
                    success = True
                    break
                else:
                    print(f"  Attempt {attempt} HTTP {res.status_code}: {res.text[:80]}")
                    time.sleep(2.0)
            except Exception as e:
                print(f"  Attempt {attempt} error: {e}")
                time.sleep(2.0)

        if not success:
            print(f"Failed to synthesize paragraph {i}")
            return False

    final_waveform = np.concatenate(combined_audio)
    duration_s = len(final_waveform) / output_sr
    out_path = Path("data/voice_cloning/test_1min_narration.wav")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), final_waveform, output_sr, subtype="PCM_16")

    print(f"\nSUCCESS! 1-Minute Test Audio Generated:")
    print(f"- Output file: {out_path.resolve()}")
    print(f"- Total duration: {duration_s:.1f} seconds")
    print(f"- Sample rate: {output_sr} Hz")
    print(f"- Voice Model ID: {voice_id}")
    return True

if __name__ == "__main__":
    api_key = get_fish_api_key()
    if not api_key:
        print("ERROR: FISH_API_KEY not found in config/.env or .env")
        sys.exit(1)

    if len(sys.argv) > 1:
        target_voice_id = sys.argv[1].strip()
    else:
        models = list_user_models(api_key)
        print(f"Found {len(models)} custom models under your account:")
        for m in models:
            print(f" - {m.get('title')}: {m.get('_id')}")
        if models:
            target_voice_id = models[0].get("_id")
            print(f"\nDefaulting to latest model: {target_voice_id}")
        else:
            print("No voice model specified and none found.")
            sys.exit(1)

    ok = synthesize_1min_test(target_voice_id)
    sys.exit(0 if ok else 1)
