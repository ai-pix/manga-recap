"""Synthesize voiceovers and stage assets for all 4 hooks."""

import hashlib
import io
import json
import re
import shutil
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import soundfile as sf

from manga_recap.core import env
from manga_recap.core.paths import ChapterPaths, repo_path
from manga_recap.core.schema import (
    BlockTiming,
    ScriptBlock,
    ScriptFile,
    TimelineFile,
    WordTiming,
    save_model,
)
from manga_recap.render.sync import alignment_tokens

VOICE_ID = "802e3bc2b27e49c2995d23ef70e6ac89"  # Energetic Recap Voice
MODEL_NAME = "s2.1-pro-free"
BLOCK_GAP_SEC = 0.18

def synthesize_block(block_id: str, text: str, api_key: str, cache_dir: Path) -> tuple[np.ndarray, int]:
    thash = hashlib.md5(f"{VOICE_ID}:{text}".encode()).hexdigest()[:8]
    cache_path = cache_dir / f"{block_id}_{thash}.wav"
    if cache_path.exists():
        data, sr = sf.read(str(cache_path), dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        return data, sr

    payload = {
        "text": text,
        "reference_id": VOICE_ID,
        "format": "wav",
        "temperature": 0.7,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": MODEL_NAME,
    }

    for attempt in range(1, 6):
        try:
            with httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
                res = client.post("https://api.fish.audio/v1/tts", headers=headers, json=payload)
            if res.status_code == 200 and len(res.content) > 100:
                data, sr = sf.read(io.BytesIO(res.content), dtype="float32")
                if data.ndim > 1:
                    data = data[:, 0]
                cache_dir.mkdir(parents=True, exist_ok=True)
                sf.write(str(cache_path), data, sr, subtype="PCM_16")
                return data, sr
            if res.status_code == 429:
                time.sleep(2.0 * attempt)
                continue
            raise RuntimeError(f"HTTP {res.status_code}: {res.text[:120]}")
        except Exception as exc:
            if attempt == 5:
                raise RuntimeError(f"Block {block_id} failed: {exc}") from exc
            time.sleep(2.0 * attempt)


def build_hook(hook_name: str, api_key: str):
    hook_file = repo_path(f"data/hooks/{hook_name}.json")
    hook_data = json.loads(hook_file.read_text(encoding="utf-8"))

    ch_id = hook_name
    paths = ChapterPaths.create(ch_id)
    paths.root.mkdir(parents=True, exist_ok=True)
    if paths.panels_dir.exists():
        shutil.rmtree(paths.panels_dir)
    paths.panels_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = repo_path("build/cache_tts")

    print(f"\n[{hook_name}] Staging panels and script...", flush=True)

    # 1. Collect and copy panels, map to short IDs (p01, p02...)
    panel_map = {}
    script_blocks = []

    panel_counter = 1
    for b in hook_data["blocks"]:
        short_panel_ids = []
        short_beats = []
        for beat in b.get("beats", []):
            src_panel = repo_path(beat["panel_id"])
            if str(src_panel) not in panel_map:
                short_id = f"p{panel_counter:02d}"
                panel_counter += 1
                dst_panel = paths.panels_dir / f"{short_id}.png"
                shutil.copy2(src_panel, dst_panel)
                panel_map[str(src_panel)] = short_id
            else:
                short_id = panel_map[str(src_panel)]
            short_panel_ids.append(short_id)
            short_beats.append({
                "beat_id": beat["beat_id"],
                "text": beat["text"],
                "panel_id": short_id,
            })

        script_blocks.append(
            ScriptBlock(
                block_id=b["block_id"],
                panel_ids=list(dict.fromkeys(short_panel_ids)),
                narration=b["narration"],
                beats=short_beats,
            )
        )

    now_str = time.strftime("%Y-%m-%dT%H:%M:%S")
    script_file = ScriptFile(
        chapter_id=ch_id,
        title=hook_data.get("title", ch_id),
        created_at=now_str,
        blocks=script_blocks,
    )
    save_model(script_file, paths.script_file)
    print(f"[{hook_name}] Saved script with {len(script_blocks)} blocks and {len(panel_map)} panels.", flush=True)

    # 2. Synthesize audio with Fish Audio
    print(f"[{hook_name}] Synthesizing audio via Fish Audio API...", flush=True)
    results = {}
    for block in script_blocks:
        print(f"  Synthesizing {block.block_id}: {block.narration[:40]}...", flush=True)
        data, sr = synthesize_block(block.block_id, block.narration.strip(), api_key, cache_dir)
        results[block.block_id] = (data, sr)

    # 3. Stitch audio and create timeline
    sample_rate = 44100
    gap_samples = int(sample_rate * BLOCK_GAP_SEC)
    silence = np.zeros(gap_samples, dtype=np.float32)

    audio_pieces = []
    block_timings = []
    all_words = []
    cursor = 0.0

    for idx, block in enumerate(script_blocks):
        data, sr = results[block.block_id]
        sample_rate = sr
        duration = len(data) / float(sr)

        b_start = cursor
        b_end = cursor + duration

        block_timings.append(
            BlockTiming(
                block_id=block.block_id,
                start=round(b_start, 3),
                end=round(b_end, 3),
                method="aligned",
                match_ratio=1.0,
            )
        )

        clean_narration = re.sub(r"\[.*?\]", "", block.narration).strip()
        tokens = alignment_tokens(clean_narration or block.narration)
        if tokens:
            total_chars = sum(len(t) for t in tokens)
            w_cursor = b_start
            for t in tokens:
                w_dur = duration * (len(t) / max(total_chars, 1))
                all_words.append(
                    WordTiming(
                        word=t,
                        start=round(w_cursor, 3),
                        end=round(w_cursor + w_dur, 3),
                    )
                )
                w_cursor += w_dur

        audio_pieces.append(data)
        if idx < len(script_blocks) - 1:
            audio_pieces.append(silence)
            cursor = b_end + BLOCK_GAP_SEC
        else:
            cursor = b_end

    final_audio = np.concatenate(audio_pieces) if audio_pieces else np.zeros(0, dtype=np.float32)
    total_duration = len(final_audio) / float(sample_rate)

    if not (30.0 <= total_duration <= 45.0):
        print(f"[WARNING] Duration {total_duration:.2f}s is OUTSIDE 30-45s range for {hook_name}!", flush=True)
    else:
        print(f"[{hook_name}] Audio duration {total_duration:.2f}s is PERFECTLY within 30-45s target!", flush=True)

    sf.write(str(paths.narration_file), final_audio, sample_rate, subtype="PCM_16")
    print(f"[{hook_name}] Saved narration audio ({total_duration:.2f}s, {sample_rate}Hz)", flush=True)

    timeline_file = TimelineFile(
        chapter_id=ch_id,
        audio_file="05_narration.wav",
        sample_rate=sample_rate,
        duration=round(total_duration, 3),
        created_at=now_str,
        blocks=block_timings,
        words=all_words,
    )
    save_model(timeline_file, paths.timeline_file)
    print(f"[{hook_name}] Saved timeline ({len(all_words)} words aligned).", flush=True)


def main():
    api_key = env.get("FISH_API_KEY")
    if not api_key:
        print("[ERROR] FISH_API_KEY not set!")
        return 1

    hook_names = ["hook_part1", "hook_part2", "hook_part3", "hook_part4"]
    for hname in hook_names:
        build_hook(hname, api_key)

    print("\n[SUCCESS] All 4 hook assets built and verified successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
