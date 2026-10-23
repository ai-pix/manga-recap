"""High-fidelity neural TTS using Google Gemini 3.8 Flash TTS and Whisper word alignment.

Synthesizes chapter narration with human-grade emotional prosody, authentic breathing,
and dynamic vocal inflection using Gemini's flagship TTS models (e.g. Puck, Charon, Fenrir).
Aligns the resulting audio using OpenAI Whisper to generate millisecond-precision block and
word boundaries in timeline.json.
"""

from __future__ import annotations

import base64
import io
import json
import time
from typing import TYPE_CHECKING

import numpy as np
import requests
import soundfile as sf

from ...core import env
from ...core.logging import get_logger, write_stage_status
from ...core.schema import (
    BlockTiming,
    ScriptFile,
    TimelineFile,
    WordTiming,
    load_model,
    save_model,
)
from .aligner import (
    align_tokens,
    block_boundaries,
    normalise_tokens,
    proportional_boundaries,
)

if TYPE_CHECKING:
    from ...core.config import Config
    from ...core.paths import ChapterPaths

_log = get_logger("stages.s4_speech.gemini_tts")


def run_gemini_tts(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> TimelineFile:
    """Generate chapter audio using Gemini 3.8 Flash TTS and time with Whisper."""
    script = load_model(paths.script_file, ScriptFile)
    if not script.blocks:
        raise ValueError("The storyboard has no blocks. Run `manga script` first.")

    if paths.timeline_file.exists() and paths.narration_file.exists() and not force:
        _log.info("Stage 4: narration and timeline already exist, skipping")
        return load_model(paths.timeline_file, TimelineFile)

    api_key = env.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set in config/.env or the environment.")

    model_name = str(config.get("tts.gemini_model", "gemini-3.8-flash-lite-tts"))
    voice_name = str(config.get("tts.gemini_voice", "Puck"))
    batch_size = int(config.get("tts.gemini_batch_size", 40))
    block_gap_sec = float(config.get("narration.block_gap_seconds", 0.18))
    min_match_ratio = float(config.get("align.min_match_ratio", 0.55))

    _log.info(
        "Stage 4 (Gemini TTS): synthesizing %d blocks with model %s and voice %s (batch_size=%d)",
        len(script.blocks),
        model_name,
        voice_name,
        batch_size,
    )

    # 1. Synthesize batches of blocks with caching and rate pacing
    batches: list[list[str]] = []
    current_batch: list[str] = []
    for b in script.blocks:
        current_batch.append(b.narration.strip())
        if len(current_batch) >= batch_size:
            batches.append(current_batch)
            current_batch = []
    if current_batch:
        batches.append(current_batch)

    cache_dir = paths.root / "_gemini_tts_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    audio_chunks: list[np.ndarray] = []
    sr = 24000
    t0 = time.time()

    for idx, batch_texts in enumerate(batches, start=1):
        batch_cache_file = cache_dir / f"batch_{idx}_{voice_name.lower()}.wav"
        if batch_cache_file.exists() and not force:
            _log.info("Stage 4 (Gemini TTS): loading cached batch %d/%d from disk", idx, len(batches))
            cached_audio, file_sr = sf.read(str(batch_cache_file), dtype="float32")
            if cached_audio.ndim > 1:
                cached_audio = cached_audio[:, 0]
            sr = file_sr
            audio_chunks.append(cached_audio)
            continue

        text_payload = "\n\n".join(batch_texts)
        _log.info(
            "Stage 4 (Gemini TTS): generating batch %d/%d (%d blocks, %d chars)...",
            idx,
            len(batches),
            len(batch_texts),
            len(text_payload),
        )
        chunk_audio, file_sr = _call_gemini_tts_with_retry(
            api_key, model_name, voice_name, text_payload
        )
        sr = file_sr
        audio_chunks.append(chunk_audio)
        sf.write(str(batch_cache_file), chunk_audio, sr, subtype="PCM_16")

        # Rate pace between new network requests (20s spacing)
        if idx < len(batches):
            _log.info("Stage 4 (Gemini TTS): pacing request (waiting 20s)...")
            time.sleep(20)

    # Concatenate batches with clean gap
    gap_samples = int(sr * block_gap_sec)
    silence = np.zeros(gap_samples, dtype=np.float32)
    final_pieces: list[np.ndarray] = []
    for i, chunk in enumerate(audio_chunks):
        final_pieces.append(chunk)
        if i < len(audio_chunks) - 1:
            final_pieces.append(silence)

    final_audio = np.concatenate(final_pieces) if final_pieces else np.zeros(0, dtype=np.float32)
    total_duration = len(final_audio) / float(sr)
    synth_duration = time.time() - t0

    paths.narration_file.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(paths.narration_file), final_audio, sr, subtype="PCM_16")
    _log.info(
        "Stage 4 (Gemini TTS): generated %.1fs audio -> %s in %.1fs",
        total_duration,
        paths.narration_file,
        synth_duration,
    )

    # 2. Transcribe and align with Whisper
    _log.info("Stage 4: running Whisper word alignment flow...")
    heard = _transcribe_whisper(paths.narration_file)
    _log.info("Stage 4: Whisper detected %d words", len(heard))

    block_texts = [b.narration for b in script.blocks]
    words_data: list[WordTiming] = []
    boundaries: list[tuple[float, float]] = []
    method = "fallback_proportional"
    match_ratio = 0.0

    if heard:
        script_tokens = [t for block in block_texts for t in normalise_tokens(block)]
        timings, match_ratio = align_tokens(script_tokens, heard)
        words_data = [
            WordTiming(word=t.token, start=round(t.start, 3), end=round(t.end, 3))
            for t in timings
        ]
        if match_ratio >= min_match_ratio:
            boundaries = block_boundaries(block_texts, timings)
            method = "aligned"
            _log.info(
                "Stage 4: successfully aligned %d blocks (match ratio: %.2f)",
                len(boundaries),
                match_ratio,
            )
        else:
            _log.warning(
                "Stage 4: match ratio %.2f below threshold %.2f; using proportional timing",
                match_ratio,
                min_match_ratio,
            )

    if not boundaries:
        boundaries = proportional_boundaries(block_texts, total_duration)

    block_timings: list[BlockTiming] = []
    for block, (start, end) in zip(script.blocks, boundaries, strict=False):
        start = max(0.0, min(start, total_duration))
        end = max(start, min(end, total_duration))
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
        chapter_id=paths.chapter_id,
        audio_file=paths.narration_file.name,
        sample_rate=sr,
        duration=round(total_duration, 3),
        tts_backend=f"gemini-tts ({model_name} / {voice_name})",
        whisper_model="whisper-base",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        words=words_data,
        blocks=block_timings,
    )
    save_model(timeline, paths.timeline_file)

    debug_data = {
        "method": method,
        "voice": voice_name,
        "match_ratio": round(match_ratio, 4),
        "heard_words": len(heard),
        "synthesis_wall_seconds": round(synth_duration, 2),
        "narration_duration": round(total_duration, 3),
        "block_count": len(block_timings),
    }
    paths.alignment_debug_file.write_text(
        json.dumps(debug_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    write_stage_status(
        paths.chapter_id,
        "s4_speech",
        "completed",
        {
            "duration": timeline.duration,
            "block_count": len(timeline.blocks),
            "fallback_blocks": len(timeline.degraded_blocks()),
            "backend": f"gemini-tts ({voice_name})",
            "synthesis_seconds": round(synth_duration, 2),
        },
    )
    return timeline


def _call_gemini_tts_with_retry(
    api_key: str,
    model_name: str,
    voice_name: str,
    text: str,
    max_retries: int = 5,
) -> tuple[np.ndarray, int]:
    """Call Gemini TTS API with fallback to flash-lite on quota limits."""
    models_to_try = [model_name]
    if "flash-lite" not in model_name:
        models_to_try.append("gemini-3.8-flash-lite-tts")
        models_to_try.append("gemini-2.5-flash-preview-tts")

    last_error: Exception | None = None
    for current_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{current_model}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": voice_name,
                        }
                    }
                },
            },
        }

        delay = 20.0
        for attempt in range(1, max_retries + 1):
            resp = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=180,
            )
            if resp.status_code == 200:
                data = resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                for p in parts:
                    if "inlineData" in p:
                        raw_audio = base64.b64decode(p["inlineData"]["data"])
                        audio_data, file_sr = sf.read(io.BytesIO(raw_audio), dtype="float32")
                        if audio_data.ndim > 1:
                            audio_data = audio_data[:, 0]
                        return audio_data, file_sr
                raise RuntimeError(f"Gemini TTS ({current_model}) response contained no audio inlineData")

            if resp.status_code == 429:
                _log.warning(
                    "Gemini TTS (%s) rate limited (429) on attempt %d/%d; retrying in %.1fs...",
                    current_model,
                    attempt,
                    max_retries,
                    delay,
                )
                time.sleep(delay)
                delay = min(delay * 1.5, 60.0)
                continue

            last_error = RuntimeError(f"Gemini TTS ({current_model}) failed ({resp.status_code}): {resp.text}")
            break

    raise RuntimeError(f"All Gemini TTS attempts and fallback models failed: {last_error}")


def _transcribe_whisper(audio_path) -> list[tuple[str, float, float]]:
    """Run Whisper to extract word timestamps."""
    import whisper

    model = whisper.load_model("base")
    result = model.transcribe(str(audio_path), word_timestamps=True)
    heard: list[tuple[str, float, float]] = []
    for segment in result.get("segments", []):
        for w in segment.get("words", []):
            text = (w.get("word") or "").strip()
            if text:
                heard.append((text, float(w.get("start", 0.0)), float(w.get("end", 0.0))))
    return heard
