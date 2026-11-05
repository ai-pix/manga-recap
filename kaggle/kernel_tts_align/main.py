"""Kaggle kernel A: narrate the chapter and time every narration block.

Runs on a Kaggle GPU. Reads a job description and the storyboard from the input
dataset, writes `narration.wav`, `timeline.json` and `alignment_debug.json` to
/kaggle/working, where `kaggle kernels output` picks them up.

Two jobs, one continuous pass:

    1. synthesise   Chatterbox Turbo speaks the whole script in one go
    2. align        faster-whisper times the words, we map them to blocks

Swap TTS by editing tts_engine.py, or alignment by editing aligner.py. Neither
change touches this file.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

WORKING = Path("/kaggle/working")
# /kaggle/input is mounted read-only, so the payload cannot be unpacked there.
# Everything the kernel reads after the download lives under /kaggle/working.
INPUT_ROOT = WORKING / "payload"

CHUNK_BYTES = 1024 * 1024

# Some free file hosts refuse a bare urllib request and close the connection
# without a response. They serve the file fine to anything that identifies
# itself as a browser, so the download says so. Verified against catbox:
# the default agent gets RemoteDisconnected, this one gets the zip.
FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    )
}

# Replaced with the real URL by the stage when it stages a push. It cannot live
# in a neighbouring file: Kaggle runs a script kernel as `/kaggle/src/script.py`,
# so nothing the push put beside main.py is next to the running code.
#
# The sentinel is a separate constant on purpose. The stage rewrites only the
# right-hand side of the assignment below, and if the token also appeared in the
# comparison that detects an unset URL, that comparison would be rewritten too
# and the kernel would never see a URL as set.
PAYLOAD_UNSET = "__PAYLOAD_URL__"
PAYLOAD_URL = PAYLOAD_UNSET

NARRATION_NAME = "narration.wav"
TIMELINE_NAME = "timeline.json"
DEBUG_NAME = "alignment_debug.json"
FAILURE_NAME = "failure.txt"


def _payload_url() -> str:
    """Where this run's inputs are hosted.

    Normally the URL is substituted into PAYLOAD_URL by the stage before the push.
    A `payload_url.txt` beside the script is accepted as a fallback for a manual
    push, though under Kaggle a script kernel runs as /kaggle/src/script.py so
    that file will not normally be found.

    Alignment-only runs use a private Kaggle dataset instead. Those runs have no
    URL and discover their payload from the mounted dataset.
    """
    if PAYLOAD_URL != PAYLOAD_UNSET and PAYLOAD_URL:
        return PAYLOAD_URL.strip()

    for candidate in (
        Path(__file__).resolve().parent / "payload_url.txt",
        Path("/kaggle/src/payload_url.txt"),
        Path("/kaggle/working/payload_url.txt"),
    ):
        if candidate.exists():
            value = candidate.read_text(encoding="utf-8").strip()
            if value:
                return value

    mounted_job = next(Path("/kaggle/input").rglob("job.json"), None)
    if mounted_job is not None:
        return ""

    raise FileNotFoundError(
        "This kernel has no payload URL. `manga speak` writes one into the "
        "kernel it pushes; pushing this directory by hand will not work."
    )


def _download(request, attempts: int = 4):
    """Open a URL, retrying a few times.

    A single dropped connection on a 27 MB transfer costs the whole kernel run,
    and these hosts drop connections for reasons that are not worth diagnosing
    from inside a container: a cold cache, a flaky hop, a rate limiter. Backing
    off and trying again turns all of those into a short wait.
    """
    delay = 5
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return urllib.request.urlopen(request, timeout=900)
        except Exception as exc:  # noqa: BLE001
            last = exc
            print(f"  download attempt {attempt}/{attempts} failed: {exc}", flush=True)
            if attempt < attempts:
                time.sleep(delay)
                delay = min(delay * 2, 60)
    raise RuntimeError(f"could not download the payload after {attempts} attempts: {last}")


def find_input() -> Path:
    """Locate the payload, either by downloading an archive or using a dataset.

    One archive rather than a Kaggle Dataset is the original design: one request
    instead of a dataset per chapter, and no dependence on Kaggle's mount layout.
    Forced alignment uses a private dataset because its audio should not be
    placed on a public file host.
    """
    url = _payload_url()
    if not url:
        for job in sorted(Path("/kaggle/input").rglob("job.json")):
            return job.parent
        raise FileNotFoundError("No mounted payload job.json was found under /kaggle/input")

    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    archive = INPUT_ROOT / "payload.zip"

    print(f"downloading payload from {url}", flush=True)
    request = urllib.request.Request(url, headers=FETCH_HEADERS)
    with _download(request) as response, archive.open("wb") as out:
        shutil.copyfileobj(response, out, CHUNK_BYTES)
    print(f"payload is {archive.stat().st_size / 1_000_000:.1f} MB, unpacking", flush=True)

    with zipfile.ZipFile(archive) as bundle:
        bundle.extractall(INPUT_ROOT)
    archive.unlink()

    for job in sorted(INPUT_ROOT.rglob("job.json")):
        return job.parent

    raise FileNotFoundError(
        f"The archive unpacked but contained no job.json. Top level now holds: "
        f"{sorted(p.name for p in INPUT_ROOT.iterdir())}"
    )


def load_job(root: Path) -> dict:
    return json.loads((root / "job.json").read_text(encoding="utf-8"))


def ensure_dependencies(root: Path) -> None:
    """Install what the TTS and alignment steps need using uv and permanent storage.

    Kaggle's GPU image ships CUDA-enabled torch, which is the expensive part and
    must not be replaced, so nothing here pins torch. We use `uv` for 10-50x faster
    installs and support persistent wheel datasets mounted under `/kaggle/input`.
    """
    import shutil
    import subprocess

    requirements = next(root.glob("**/requirements-kaggle.txt"), None)
    if requirements is None:
        print("[kernel] no requirements file in the payload; skipping install", flush=True)
        return

    wanted = [
        line.strip()
        for line in requirements.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    wanted = [w for w in wanted if not w.startswith("av")]
    wanted.append("av<18")
    if not wanted:
        return

    # Check for permanently mounted wheel storage under /kaggle/input
    cached_wheels = list(Path("/kaggle/input").glob("**/*.whl"))
    wheel_dirs = {p.parent for p in cached_wheels}

    # Ensure uv is available
    if not shutil.which("uv"):
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "uv"], check=False)
    has_uv = shutil.which("uv") is not None

    if wheel_dirs and has_uv:
        find_links_args = []
        for wd in sorted(wheel_dirs):
            find_links_args.extend(["--find-links", str(wd)])
        print(f"[kernel] installing {len(wanted)} packages from permanent storage with uv...", flush=True)
        res = subprocess.run(
            ["uv", "pip", "install", "--system", "--no-index", *find_links_args, *wanted],
            check=False,
        )
        if res.returncode == 0:
            print("[kernel] installed from permanent storage in seconds!", flush=True)
            _cleanup_torchvision()
            return

    if has_uv:
        print(f"[kernel] installing {len(wanted)} packages via uv...", flush=True)
        res = subprocess.run(
            ["uv", "pip", "install", "--system", *wanted],
            check=False,
        )
        if res.returncode == 0:
            _cleanup_torchvision()
            return

    print(f"[kernel] ensuring via pip: {', '.join(wanted)}", flush=True)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-input", *wanted],
        check=True,
    )
    _cleanup_torchvision()


def _cleanup_torchvision() -> None:
    """Remove incompatible torchvision ops that break transformers on Kaggle."""
    import subprocess

    subprocess.run(
        [sys.executable, "-m", "pip", "uninstall", "-y", "torchvision"],
        check=False,
    )


def main() -> int:
    started = time.time()
    WORKING.mkdir(parents=True, exist_ok=True)

    root = find_input()
    job = load_job(root)
    print(f"[kernel] input dataset: {root.name}")
    print(f"[kernel] job: {json.dumps(job, indent=2)}")

    lib_dir = root / "lib"
    if lib_dir.is_dir():
        sys.path.insert(0, str(lib_dir))
        print(f"[kernel] helper modules from {lib_dir.name}/", flush=True)

    ensure_dependencies(root)

    mode = str(job.get("mode", "tts_align"))
    if mode == "batch_align":
        return _run_batch_align(root, job)

    script = json.loads((root / "script.json").read_text(encoding="utf-8"))
    blocks = script.get("blocks", [])
    if not blocks:
        raise ValueError("script.json has no blocks. Nothing to narrate.")
    print(f"[kernel] {len(blocks)} blocks to narrate")
    block_texts = [block["narration"] for block in blocks]
    full_text = _join_narration(block_texts, gap_paragraph=True)
    tts_settings = job.get("tts", {})
    expected = None

    if mode == "align":
        import soundfile as sf

        narration_path = root / NARRATION_NAME
        if not narration_path.exists():
            raise FileNotFoundError(f"Alignment payload has no {NARRATION_NAME}")
        audio, sample_rate = sf.read(str(narration_path), dtype="float32")
        if audio.ndim > 1:
            audio = audio[:, 0]
        duration = len(audio) / float(sample_rate)
        tts_backend = str(job.get("tts_backend", "fish-audio-continuous"))
        print(f"[kernel] aligning {duration:.1f}s of continuous narration", flush=True)
    else:
        try:
            import transformers.utils.import_utils

            transformers.utils.import_utils.is_torchvision_available = lambda: False
        except (ImportError, AttributeError):
            pass

        from tts_engine import TTSEngine

        voice = tts_settings.get("voice", {})
        engine = TTSEngine(
            voice_mode=voice.get("mode", "builtin"),
            reference_wav=_resolve_reference(root, voice.get("reference_wav")),
            language_id=tts_settings.get("language_id", "en"),
            workers_per_gpu=int(tts_settings.get("workers_per_gpu", 2)),
        )

        print(f"[kernel] narrating {len(full_text)} characters")
        result = engine.synthesize(full_text)
        narration_path = engine.save(result, WORKING / NARRATION_NAME)
        duration = len(result.audio) / float(result.sample_rate)
        sample_rate = result.sample_rate
        tts_backend = result.backend
        print(f"[kernel] narration: {duration:.1f}s at {sample_rate}Hz")

        expected = _plausible_duration(full_text, tts_settings)
        if expected and not (expected[0] <= duration <= expected[1]):
            print(
                f"[kernel] WARNING: narration is {duration:.1f}s but {len(full_text)} "
                f"characters at {tts_settings.get('duration_words_per_minute', 150)} wpm "
                f"implies {expected[0]:.0f}-{expected[1]:.0f}s. The script may have been "
                "truncated, or the voice may be running fast."
            )

    # -- 2. align ---------------------------------------------------------
    from aligner import align_tokens, normalise_tokens, proportional_boundaries

    align_settings = job.get("align", {})
    strict = bool(align_settings.get("strict", False))
    min_match_ratio = float(align_settings.get("min_match_ratio", 0.55))
    max_words_per_beat = int(job.get("render", {}).get("max_words_per_beat", 14))

    script_tokens: list[str] = []
    block_token_counts: list[int] = []
    beat_count = 0

    if mode == "align":
        from recap_sync import alignment_tokens, beats_for_blocks

        beats = beats_for_blocks(blocks, max_words=max_words_per_beat)
        beat_count = len(beats)
        for block in blocks:
            block_id = str(block.get("block_id", ""))
            count = 0
            for beat in beats:
                if beat.block_id != block_id:
                    continue
                tokens = alignment_tokens(beat.text)
                script_tokens.extend(tokens)
                count += len(tokens)
            block_token_counts.append(count)
    else:
        for text in block_texts:
            tokens = normalise_tokens(text)
            script_tokens.extend(tokens)
            block_token_counts.append(len(tokens))

    words: list[dict] = []
    heard: list[tuple[str, float, float]] = []
    boundaries: list[tuple[float, float]] = []
    method = "fallback_proportional"
    match_ratio = 0.0

    try:
        heard = transcribe(narration_path, align_settings)
        print(f"[kernel] whisper heard {len(heard)} words")
    except Exception as exc:  # noqa: BLE001
        if strict:
            raise RuntimeError(f"Strict forced alignment could not transcribe the audio: {exc}") from exc
        print(f"[kernel] transcription failed ({exc}); using proportional timing")

    if heard:
        timings, match_ratio = align_tokens(script_tokens, heard)
        words = [
            {"word": timing.token, "start": round(timing.start, 3), "end": round(timing.end, 3)}
            for timing in timings
        ]
        if len(timings) == len(script_tokens) and match_ratio >= min_match_ratio:
            boundaries = _beat_block_boundaries(timings, block_token_counts, duration)
            method = "aligned"
            print(
                f"[kernel] aligned {len(boundaries)} blocks / {beat_count} beats, "
                f"ratio {match_ratio:.2f}"
            )
        elif strict:
            raise RuntimeError(
                f"Strict forced alignment produced {len(timings)}/{len(script_tokens)} "
                f"token timings at ratio {match_ratio:.2f}, below {min_match_ratio:.2f}."
            )
        else:
            print(
                f"[kernel] match ratio {match_ratio:.2f} is below "
                f"{min_match_ratio:.2f}; using proportional timing"
            )
    elif strict:
        raise RuntimeError("Strict forced alignment received no Whisper word timings.")

    if not boundaries:
        if strict:
            raise RuntimeError("Strict forced alignment produced no usable boundaries.")
        boundaries = proportional_boundaries(block_texts, duration)
        match_ratio = 0.0

    # -- 3. emit -----------------------------------------------------------
    block_timings = []
    prev_end = 0.0
    for block, (start, end) in zip(blocks, boundaries, strict=False):
        start = max(prev_end, min(start, duration))
        end = max(start, min(end, duration))
        prev_end = end
        block_timings.append(
            {
                "block_id": block.get("block_id"),
                "start": round(start, 3),
                "end": round(end, 3),
                "method": method,
                "match_ratio": round(match_ratio, 4),
            }
        )



    timeline = {
        "chapter_id": job.get("chapter_id", ""),
        "audio_file": NARRATION_NAME,
        "sample_rate": sample_rate,
        "duration": round(duration, 3),
        "tts_backend": tts_backend,
        "whisper_model": align_settings.get("whisper_model", ""),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "words": words,
        "blocks": block_timings,
    }
    (WORKING / TIMELINE_NAME).write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    debug = {
        "method": method,
        "mode": mode,
        "match_ratio": round(match_ratio, 4),
        "script_char_count": len(full_text),
        "script_token_count": len(script_tokens),
        "beat_count": beat_count,
        "narration_duration": round(duration, 3),
        "expected_duration_range": list(expected) if expected else None,
        "heard_word_count": len(heard),
        "blocks": [
            {"block_id": b["block_id"], "text": b["narration"][:120]} for b in blocks
        ],
    }
    (WORKING / DEBUG_NAME).write_text(
        json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[kernel] done in {time.time() - started:.0f}s -> {WORKING}")
    print(f"[kernel] outputs: {NARRATION_NAME}, {TIMELINE_NAME}, {DEBUG_NAME}")
    return 0


def transcribe(narration_path: Path, settings: dict) -> list[tuple[str, float, float]]:
    """Run faster-whisper or openai-whisper and return (word, start, end) triples."""
    model_name = settings.get("whisper_model", "large-v3-turbo")
    device = settings.get("device", "cuda")
    compute_type = settings.get("compute_type", "float16")

    # 1. Try faster-whisper
    try:
        from faster_whisper import WhisperModel

        print(f"[kernel] loading faster-whisper {model_name} on {device}")
        model = WhisperModel(model_name, device=device, compute_type=compute_type)

        segments, info = model.transcribe(
            str(narration_path),
            word_timestamps=True,
            beam_size=int(settings.get("beam_size", 5)),
            vad_filter=True,
        )
        print(f"[kernel] detected language: {info.language} ({info.language_probability:.2f})")

        heard: list[tuple[str, float, float]] = []
        for segment in segments:
            for word in segment.words or []:
                text = (word.word or "").strip()
                if text:
                    heard.append((text, float(word.start), float(word.end)))
        if heard:
            return heard
    except Exception as exc:
        print(f"[kernel] faster-whisper failed ({exc}); trying openai-whisper...")

    # 2. Resilient fallback: openai-whisper
    try:
        import whisper

        whisper_variant = "turbo" if "turbo" in model_name else "large-v3"
        print(f"[kernel] loading openai-whisper {whisper_variant} on {device}")
        wmodel = whisper.load_model(whisper_variant, device=device)
        res = wmodel.transcribe(str(narration_path), word_timestamps=True)
        heard = []
        for segment in res.get("segments", []):
            for word in segment.get("words", []):
                text = (word.get("word") or "").strip()
                if text:
                    heard.append((text, float(word.get("start", 0)), float(word.get("end", 0))))
        print(f"[kernel] openai-whisper heard {len(heard)} words")
        return heard
    except Exception as exc:
        print(f"[kernel] openai-whisper fallback failed ({exc})")
        raise


def _join_narration(block_texts: list[str], *, gap_paragraph: bool = True) -> str:
    """Join block narrations into the one string TTS will speak.

    A blank line between blocks gives the voice model a natural pause at the
    beat boundary, which is what makes a continuous pass sound intentional
    rather than continuous.
    """
    separator = "\n\n" if gap_paragraph else " "
    return separator.join(t.strip() for t in block_texts if t and t.strip())


def _beat_block_boundaries(
    timings: list,
    block_token_counts: list[int],
    duration: float,
) -> list[tuple[float, float]]:
    """Turn beat-token timings into block windows without re-deriving beats here."""
    boundaries: list[tuple[float, float]] = []
    cursor = 0
    previous_end = 0.0

    for count in block_token_counts:
        window = timings[cursor : cursor + count]
        cursor += count

        if not window:
            boundaries.append((previous_end, previous_end))
            continue

        start = max(previous_end, float(window[0].start))
        end = max(start, min(float(window[-1].end), duration))
        start = min(start, end)
        previous_end = end
        boundaries.append((start, end))

    return boundaries


def _plausible_duration(text: str, tts_settings: dict) -> tuple[float, float] | None:
    """Expected narration length, used only to catch a truncated synthesis."""
    wpm = float(tts_settings.get("duration_words_per_minute", 150))
    tolerance = float(tts_settings.get("duration_tolerance", 0.6))
    words = len(text.split())
    if words == 0 or wpm <= 0:
        return None
    nominal = words / wpm * 60.0
    return (nominal * (1 - tolerance), nominal * (1 + tolerance))


def _resolve_reference(root: Path, reference: str | None) -> Path | None:
    """Point a cloned voice reference at the uploaded copy, not a local path."""
    if not reference:
        return None
    ref_name = Path(reference).name
    candidate = root / ref_name
    if candidate.exists():
        return candidate
    for inp in Path("/kaggle/input").rglob(ref_name):
        if inp.is_file():
            return inp
    if Path(reference).exists():
        return Path(reference)
    print(f"[kernel] reference wav {reference} not found; falling back to builtin voice")
    return None



def _run_batch_align(root: Path, job: dict) -> int:
    started = time.time()
    align_settings = job.get("align", {})
    max_words_per_beat = int(job.get("render", {}).get("max_words_per_beat", 14))

    import soundfile as sf
    from aligner import align_tokens
    from faster_whisper import WhisperModel
    from recap_sync import alignment_tokens, beats_for_blocks

    model_name = align_settings.get("whisper_model", "large-v3-turbo")
    device = align_settings.get("device", "cuda")
    compute_type = align_settings.get("compute_type", "float16")

    print(f"[kernel] loading WhisperModel {model_name} on {device} ({compute_type})...", flush=True)
    whisper = WhisperModel(model_name, device=device, compute_type=compute_type)

    chapters_dir = root / "chapters"
    chapter_list = job.get("chapters", [])
    if not chapter_list:
        chapter_list = sorted([p.name for p in chapters_dir.iterdir() if p.is_dir()])

    print(f"[kernel] batch aligning {len(chapter_list)} chapters: {chapter_list}", flush=True)

    for ch_name in chapter_list:
        ch_dir = chapters_dir / ch_name
        script_file = ch_dir / "script.json"
        audio_file = ch_dir / "narration.wav"
        if not (script_file.exists() and audio_file.exists()):
            print(f"[kernel] skipping {ch_name}: missing script or audio", flush=True)
            continue

        script = json.loads(script_file.read_text(encoding="utf-8"))
        blocks = script.get("blocks", [])
        audio, sample_rate = sf.read(str(audio_file), dtype="float32")
        if audio.ndim > 1:
            audio = audio[:, 0]
        duration = len(audio) / float(sample_rate)

        # Resample to 16kHz float32 mono for Whisper (bypasses av.open completely)
        import numpy as np
        import torch
        import torchaudio.functional as F
        audio_t = torch.from_numpy(audio).float()
        if sample_rate != 16000:
            audio_16k = F.resample(audio_t, orig_freq=sample_rate, new_freq=16000).numpy()
        else:
            audio_16k = audio_t.numpy()
        audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)

        beats = beats_for_blocks(blocks, max_words=max_words_per_beat)
        script_tokens = []
        block_token_counts = []
        for block in blocks:
            b_id = str(block.get("block_id", ""))
            count = 0
            for beat in beats:
                if beat.block_id != b_id:
                    continue
                tokens = alignment_tokens(beat.text)
                script_tokens.extend(tokens)
                count += len(tokens)
            block_token_counts.append(count)

        print(f"[kernel] [{ch_name}] transcribing {duration:.1f}s on GPU...", flush=True)
        segments, info = whisper.transcribe(
            audio_16k,
            word_timestamps=True,
            beam_size=int(align_settings.get("beam_size", 5)),
            vad_filter=True,
        )
        heard = []
        for segment in segments:
            for word in segment.words or []:
                w_text = (word.word or "").strip()
                if w_text:
                    heard.append((w_text, float(word.start), float(word.end)))

        timings, match_ratio = align_tokens(script_tokens, heard)
        words = [
            {"word": t.token, "start": round(t.start, 3), "end": round(t.end, 3)}
            for t in timings
        ]
        boundaries = _beat_block_boundaries(timings, block_token_counts, duration)

        block_timings = []
        prev_end = 0.0
        for block, (start, end) in zip(blocks, boundaries, strict=False):
            start = max(prev_end, min(start, duration))
            end = max(start, min(end, duration))
            prev_end = end
            block_timings.append({
                "block_id": block.get("block_id"),
                "start": round(start, 3),
                "end": round(end, 3),
                "method": "aligned",
                "match_ratio": round(match_ratio, 4),
            })

        timeline = {
            "chapter_id": ch_name,
            "audio_file": "05_narration.wav",
            "sample_rate": sample_rate,
            "duration": round(duration, 3),
            "tts_backend": f"fish-audio-continuous ({model_name})",
            "whisper_model": model_name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "words": words,
            "blocks": block_timings,
        }
        out_timeline = WORKING / f"{ch_name}_timeline.json"
        out_timeline.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[kernel] [{ch_name}] SUCCESS: ratio={match_ratio:.2f}, words={len(words)}, duration={duration:.1f}s", flush=True)

    print(f"[kernel] batch alignment complete in {time.time() - started:.1f}s!", flush=True)
    return 0


if __name__ == "__main__":
    # Kaggle's own log download returned a zero-byte file for this kernel, which
    # makes every failure blind: the run dies, the stage reports "status error",
    # and the reason is somewhere nobody can read. Writing the traceback into
    # /kaggle/working means it comes back with the kernel's outputs instead.
    try:
        sys.exit(main())
    except BaseException:
        import traceback

        detail = traceback.format_exc()
        print(detail, flush=True)
        try:
            (WORKING / FAILURE_NAME).write_text(detail, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        raise


