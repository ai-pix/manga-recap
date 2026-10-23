"""High-speed neural TTS and exact word/block alignment using Edge-TTS.

Synthesizes each storyboard narration block with millisecond-precision WordBoundary
events directly from the neural vocoder. Concatenates block audios with natural
conversational pauses, yielding an exact 1:1 timeline synchronization with zero
fallback degradation and zero drift.
"""

from __future__ import annotations

import asyncio
import io
import json
import time
from typing import TYPE_CHECKING

import numpy as np
import soundfile as sf

from ...core.logging import get_logger, write_stage_status
from ...core.schema import (
    BlockTiming,
    ScriptFile,
    TimelineFile,
    WordTiming,
    load_model,
    save_model,
)

if TYPE_CHECKING:
    from ...core.config import Config
    from ...core.paths import ChapterPaths

_log = get_logger("stages.s4_speech.edge_tts")


async def _synthesize_block(
    block_id: str,
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    semaphore: asyncio.Semaphore,
) -> tuple[str, bytearray, list[tuple[str, float, float]]]:
    """Synthesize a single block's text and collect WordBoundary timestamps."""
    import edge_tts

    async with semaphore:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
        audio_bytes = bytearray()
        words: list[tuple[str, float, float]] = []

        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                audio_bytes.extend(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset and duration are in 100ns units (1e-7 seconds)
                w_start = chunk["offset"] / 1e7
                w_end = (chunk["offset"] + chunk["duration"]) / 1e7
                words.append((chunk["text"], w_start, w_end))

        return block_id, audio_bytes, words


async def _synthesize_all(
    script: ScriptFile,
    voice: str,
    rate: str,
    pitch: str,
    concurrency: int,
) -> dict[str, tuple[bytearray, list[tuple[str, float, float]]]]:
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _synthesize_block(b.block_id, b.narration.strip(), voice, rate, pitch, semaphore)
        for b in script.blocks
    ]
    results = await asyncio.gather(*tasks)
    return {block_id: (audio, words) for block_id, audio, words in results}


def run_edge_tts(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> TimelineFile:
    """Generate chapter audio and timeline using the fast Edge-TTS neural engine."""
    script = load_model(paths.script_file, ScriptFile)
    if not script.blocks:
        raise ValueError("The storyboard has no blocks. Run `manga script` first.")

    if paths.timeline_file.exists() and paths.narration_file.exists() and not force:
        _log.info("Stage 4: narration and timeline already exist, skipping")
        return load_model(paths.timeline_file, TimelineFile)

    voice_name = str(config.get("tts.voice.name", "en-US-GuyNeural") or "en-US-GuyNeural")
    rate = str(config.get("tts.voice.rate", "+0%") or "+0%")
    pitch = str(config.get("tts.voice.pitch", "+0Hz") or "+0Hz")
    gap_seconds = float(config.get("narration.block_gap_seconds", 0.18))
    concurrency = int(config.get("tts.concurrency", 8))

    _log.info(
        "Stage 4 (Edge-TTS): synthesizing %d blocks with male voice %s (rate=%s, pitch=%s, workers=%d)",
        len(script.blocks),
        voice_name,
        rate,
        pitch,
        concurrency,
    )

    t0 = time.time()
    synth_map = asyncio.run(
        _synthesize_all(script, voice=voice_name, rate=rate, pitch=pitch, concurrency=concurrency)
    )
    synth_duration = time.time() - t0
    _log.info("Stage 4 (Edge-TTS): audio synthesis completed in %.2fs", synth_duration)

    audio_pieces: list[np.ndarray] = []
    block_timings: list[BlockTiming] = []
    all_words: list[WordTiming] = []
    cursor = 0.0
    sr = 24000
    gap_samples = int(sr * gap_seconds)
    silence = np.zeros(gap_samples, dtype=np.float32)

    for block in script.blocks:
        audio_bytes, words = synth_map[block.block_id]
        if not audio_bytes:
            raise RuntimeError(f"Edge-TTS returned no audio for block {block.block_id}")

        data, file_sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
        if data.ndim > 1:
            data = data[:, 0]
        sr = file_sr
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

        for w_text, w_s, w_e in words:
            all_words.append(
                WordTiming(
                    word=w_text,
                    start=round(b_start + w_s, 3),
                    end=round(b_start + w_e, 3),
                )
            )

        audio_pieces.append(data)
        audio_pieces.append(silence)
        cursor = b_end + gap_seconds

    # Drop trailing silence
    if audio_pieces:
        audio_pieces = audio_pieces[:-1]

    final_audio = np.concatenate(audio_pieces) if audio_pieces else np.zeros(0, dtype=np.float32)
    total_duration = len(final_audio) / float(sr)

    paths.narration_file.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(paths.narration_file), final_audio, sr, subtype="PCM_16")

    timeline = TimelineFile(
        chapter_id=paths.chapter_id,
        audio_file=paths.narration_file.name,
        sample_rate=sr,
        duration=round(total_duration, 3),
        tts_backend=f"edge-tts ({voice_name})",
        whisper_model="edge-tts-word-timing",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        words=all_words,
        blocks=block_timings,
    )
    save_model(timeline, paths.timeline_file)

    debug_data = {
        "method": "edge-tts-exact",
        "voice": voice_name,
        "match_ratio": 1.0,
        "synthesis_wall_seconds": round(synth_duration, 2),
        "narration_duration": round(total_duration, 3),
        "block_count": len(block_timings),
        "word_count": len(all_words),
    }
    paths.alignment_debug_file.write_text(
        json.dumps(debug_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    _log.info(
        "Stage 4: narration %.1fs (%.2f min), %d blocks -> %s",
        timeline.duration,
        timeline.duration / 60.0,
        len(timeline.blocks),
        paths.narration_file,
    )

    write_stage_status(
        paths.chapter_id,
        "s4_speech",
        "completed",
        {
            "duration": timeline.duration,
            "block_count": len(timeline.blocks),
            "fallback_blocks": 0,
            "backend": f"edge-tts ({voice_name})",
            "synthesis_seconds": round(synth_duration, 2),
        },
    )
    return timeline
