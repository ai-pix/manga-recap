"""Chatterbox Turbo text-to-speech, swapping this file to change the voice.

The whole chapter is narrated in one continuous pass. Per-block synthesis would
give exact timings for free, but it produces audible seams and a robotic cadence
at every block boundary, which is exactly what you do not want in a video whose
entire appeal is the narration. We pay for that with the alignment stage.

The engine is deliberately a thin wrapper: load, synthesise, save. The chunking
and stitching are the part worth knowing about.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

# Chatterbox has a hard per-call character limit. Long text must be split, and
# the split points matter: breaking mid-sentence is audible, so prefer to break
# at punctuation.
MAX_CHARS = 400

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_CLAUSE_SPLIT = re.compile(r"(?<=[,;:])\s+")


@dataclass
class SynthesisResult:
    audio: np.ndarray
    sample_rate: int
    backend: str
    voice: str
    char_count: int


def _worker_process_loop(
    worker_id: int,
    device_str: str,
    voice_mode: str,
    reference_wav_str: str | None,
    language_id: str,
    task_queue,
    result_queue,
) -> None:
    """Worker process bound to a specific GPU device."""
    import torch

    try:
        if device_str.startswith("cuda"):
            dev_idx = int(device_str.split(":")[-1])
            torch.cuda.set_device(dev_idx)

        try:
            from chatterbox.tts_turbo import ChatterboxTurboTTS

            model = ChatterboxTurboTTS.from_pretrained(device=device_str)
        except (ImportError, AttributeError):
            try:
                from chatterbox import ChatterboxTurboTTS

                model = ChatterboxTurboTTS.from_pretrained(device=device_str)
            except (ImportError, AttributeError):
                from chatterbox.tts import ChatterboxTTS

                model = ChatterboxTTS.from_pretrained(device=device_str)

        ref_path = Path(reference_wav_str) if reference_wav_str else None
        voice_tensor = None
        conditionals_ready = False

        if voice_mode == "clone" and ref_path and ref_path.exists():
            if hasattr(model, "prepare_conditionals"):
                try:
                    model.prepare_conditionals(str(ref_path))
                    conditionals_ready = True
                except Exception as e:
                    print(f"[tts-worker-{worker_id}] prepare_conditionals notice: {e}")
            if not conditionals_ready:
                import torchaudio

                voice_tensor, _ = torchaudio.load(str(ref_path))

        sr = int(getattr(model, "sr", 24000))
        print(f"[tts-worker-{worker_id}] ready on {device_str} ({sr}Hz)")
        result_queue.put((worker_id, "READY", sr))

        while True:
            task = task_queue.get()
            if task is None:
                break

            chunk_idx, text_chunk = task
            kwargs = {}
            if language_id:
                kwargs["language_id"] = language_id
            if voice_mode == "clone" and ref_path and ref_path.exists() and not conditionals_ready:
                kwargs["audio_prompt_path"] = str(ref_path)

            with torch.inference_mode():
                try:
                    audio = model.generate(text_chunk.strip(), **kwargs)
                except TypeError:
                    kwargs.pop("language_id", None)
                    try:
                        audio = model.generate(text_chunk.strip(), **kwargs)
                    except TypeError:
                        if "audio_prompt_path" in kwargs:
                            kwargs.pop("audio_prompt_path")
                            if voice_tensor is not None:
                                kwargs["audio_prompt"] = voice_tensor
                        audio = model.generate(text_chunk.strip(), **kwargs)

            audio_np = _as_numpy(audio)
            chunk_sr = int(getattr(model, "sr", 0)) or _infer_sample_rate(audio)
            result_queue.put((chunk_idx, audio_np, chunk_sr))

    except Exception as exc:
        import traceback

        print(f"[tts-worker-{worker_id}] failure: {exc}\n{traceback.format_exc()}")
        result_queue.put((-1, str(exc), 0))
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class TTSEngine:
    """Thin wrapper over Chatterbox Turbo.

    Voice selection:
        builtin  the narrator voice shipped with the model
        clone    a reference clip from assets/voices/
    """

    _CPU_GUIDANCE = (
        "Chatterbox Turbo is running on CPU. This stage belongs on a Kaggle GPU "
        "kernel; a CPU run would take hours. Check that the kernel has GPU enabled."
    )

    def __init__(
        self,
        *,
        voice_mode: str = "builtin",
        reference_wav: str | Path | None = None,
        language_id: str = "en",
        device: str | None = None,
        workers_per_gpu: int = 2,
    ) -> None:
        self.voice_mode = voice_mode
        self.reference_wav = Path(reference_wav) if reference_wav else None
        self.language_id = language_id
        self._device = device
        self.workers_per_gpu = max(1, int(workers_per_gpu))
        self._model = None
        self._voice_tensor = None

    # -- model ------------------------------------------------------------

    def load(self) -> None:
        """Load the model. Called once; the T4 handles this in about a minute."""
        if self._model is not None:
            return

        # Check an explicit CPU request before importing torch, so the message
        # that explains where this stage belongs arrives even on a machine with
        # no torch at all.
        if self._device == "cpu":
            raise RuntimeError(self._CPU_GUIDANCE)

        import torch

        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        if device == "cpu":
            raise RuntimeError(self._CPU_GUIDANCE)

        try:
            from chatterbox.tts_turbo import ChatterboxTurboTTS

            self._log_device(device)
            self._model = ChatterboxTurboTTS.from_pretrained(device=device)
        except (ImportError, AttributeError):
            try:
                from chatterbox import ChatterboxTurboTTS

                self._log_device(device)
                self._model = ChatterboxTurboTTS.from_pretrained(device=device)
            except (ImportError, AttributeError):
                from chatterbox.tts import ChatterboxTTS

                print(f"[tts] ChatterboxTurboTTS not found; using ChatterboxTTS on {device}")
                self._log_device(device)
                self._model = ChatterboxTTS.from_pretrained(device=device)

        if self.voice_mode == "clone":
            self._voice_tensor = self._load_reference_voice()
            if self.reference_wav and hasattr(self._model, "prepare_conditionals"):
                try:
                    self._model.prepare_conditionals(str(self.reference_wav))
                    print(f"[tts] pre-computed voice conditioning from {self.reference_wav.name}")
                    self._conditionals_ready = True
                except Exception as e:
                    print(f"[tts] prepare_conditionals notice: {e}")
                    self._conditionals_ready = False
            else:
                self._conditionals_ready = False

    def _log_device(self, device: str) -> None:
        print(f"[tts] loading Chatterbox Turbo on {device}")

    def _load_reference_voice(self):
        if self.reference_wav is None or not self.reference_wav.exists():
            raise FileNotFoundError(
                f"tts.voice.mode is 'clone' but no reference wav was found at "
                f"{self.reference_wav}. Add a 10-20s clean sample, or set "
                "tts.voice.mode to 'builtin'."
            )
        import torchaudio

        waveform, _ = torchaudio.load(str(self.reference_wav))
        print(f"[tts] cloning voice from {self.reference_wav.name}")
        return waveform

    # -- synthesis --------------------------------------------------------

    def synthesize(self, text: str) -> SynthesisResult:
        """Narrate `text` as one continuous stream.

        Long text is chunked, generated in parallel across available GPUs and
        worker processes, and concatenated with clean silence gaps.
        """
        # Reject empty input before loading any models.
        if not text or not text.strip():
            raise ValueError("Nothing to synthesise: the script text is empty")

        if self._device == "cpu":
            raise RuntimeError(self._CPU_GUIDANCE)

        chunks = chunk_text(text, max_chars=MAX_CHARS)
        print(f"[tts] synthesising {len(text)} chars in {len(chunks)} chunk(s)")

        import torch

        num_gpus = torch.cuda.device_count() if torch.cuda.is_available() else 0

        # If GPU(s) are available and there are multiple chunks, run multi-worker parallel synthesis
        if num_gpus > 0 and len(chunks) > 1 and self._device != "cpu":
            return self._synthesize_parallel(chunks, text_len=len(text), num_gpus=num_gpus)

        return self._synthesize_sequential(chunks, text_len=len(text))

    def _synthesize_sequential(self, chunks: list[str], text_len: int) -> SynthesisResult:
        """Fallback sequential path for single-worker or single-chunk runs."""
        self.load()

        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        gap = 0.18  # seconds of silence between chunks
        pieces: list[np.ndarray] = []
        sample_rate = 0

        for index, chunk in enumerate(chunks, start=1):
            audio = self._generate(chunk)
            if sample_rate == 0:
                sample_rate = int(getattr(self._model, "sr", 0)) or _infer_sample_rate(audio)
            pieces.append(_as_numpy(audio))
            if index < len(chunks):
                pieces.append(np.zeros(int(sample_rate * gap), dtype=np.float32))

        joined = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        return SynthesisResult(
            audio=joined,
            sample_rate=sample_rate,
            backend="chatterbox-turbo",
            voice=self.voice_mode,
            char_count=text_len,
        )

    def _synthesize_parallel(self, chunks: list[str], text_len: int, num_gpus: int) -> SynthesisResult:
        """Parallel multi-GPU chunk synthesis using independent worker processes.

        Distributes workers round-robin across available GPUs (e.g. cuda:0, cuda:1).
        When synthesis completes and workers terminate, 100% of GPU memory is freed
        for subsequent pipeline stages (like Whisper alignment).
        """
        import torch.multiprocessing as mp

        total_workers = min(num_gpus * self.workers_per_gpu, len(chunks))
        print(
            f"[tts] multi-GPU batching enabled: spawning {total_workers} parallel workers "
            f"across {num_gpus} GPU(s) ({self.workers_per_gpu} workers/GPU)"
        )

        ctx = mp.get_context("spawn")
        task_queue = ctx.Queue()
        result_queue = ctx.Queue()
        processes = []

        ref_str = str(self.reference_wav) if self.reference_wav else None

        for worker_id in range(total_workers):
            gpu_id = worker_id % num_gpus
            device_str = f"cuda:{gpu_id}"
            p = ctx.Process(
                target=_worker_process_loop,
                args=(
                    worker_id,
                    device_str,
                    self.voice_mode,
                    ref_str,
                    self.language_id,
                    task_queue,
                    result_queue,
                ),
            )
            p.start()
            processes.append(p)

        # Wait for all workers to signal ready
        sample_rate = 24000
        ready_count = 0
        while ready_count < total_workers:
            wid, status, sr = result_queue.get()
            if wid == -1:
                for p in processes:
                    p.terminate()
                raise RuntimeError(f"TTS Worker failed to initialize: {status}")
            if status == "READY":
                ready_count += 1
                if sr > 0:
                    sample_rate = sr

        # Enqueue all chunks for dynamic work-stealing
        for idx, chunk in enumerate(chunks):
            task_queue.put((idx, chunk))

        # Collect results
        collected: dict[int, np.ndarray] = {}
        for _ in range(len(chunks)):
            chunk_idx, audio_data, sr = result_queue.get()
            if chunk_idx == -1:
                for p in processes:
                    p.terminate()
                raise RuntimeError(f"TTS synthesis error in worker: {audio_data}")
            collected[chunk_idx] = audio_data
            if sr > 0:
                sample_rate = sr
            print(f"[tts] completed chunk {chunk_idx + 1}/{len(chunks)} ({len(collected)}/{len(chunks)} total)")

        # Send poison pills to shut down workers cleanly
        for _ in range(total_workers):
            task_queue.put(None)

        for p in processes:
            p.join(timeout=10)
            if p.is_alive():
                p.terminate()

        # Reconstruct sequential audio in strict chunk order
        gap = 0.18
        gap_samples = np.zeros(int(sample_rate * gap), dtype=np.float32)
        pieces: list[np.ndarray] = []

        for idx in range(len(chunks)):
            pieces.append(collected[idx])
            if idx < len(chunks) - 1:
                pieces.append(gap_samples)

        joined = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
        print(f"[tts] parallel synthesis complete: {len(joined) / float(sample_rate):.2f}s of audio")

        return SynthesisResult(
            audio=joined,
            sample_rate=sample_rate,
            backend="chatterbox-turbo",
            voice=self.voice_mode,
            char_count=text_len,
        )

    def _generate(self, chunk: str):
        import torch

        kwargs = {}
        if self.language_id:
            kwargs["language_id"] = self.language_id
        if self.voice_mode == "clone" and self.reference_wav and self.reference_wav.exists():
            if not getattr(self, "_conditionals_ready", False):
                kwargs["audio_prompt_path"] = str(self.reference_wav)

        with torch.inference_mode():
            try:
                return self._model.generate(chunk.strip(), **kwargs)
            except TypeError:
                kwargs.pop("language_id", None)
                try:
                    return self._model.generate(chunk.strip(), **kwargs)
                except TypeError:
                    if "audio_prompt_path" not in kwargs and self.reference_wav:
                        kwargs["audio_prompt_path"] = str(self.reference_wav)
                        return self._model.generate(chunk.strip(), **kwargs)
                    if "audio_prompt_path" in kwargs:
                        kwargs.pop("audio_prompt_path")
                        if self._voice_tensor is not None:
                            kwargs["audio_prompt"] = self._voice_tensor
                    return self._model.generate(chunk.strip(), **kwargs)

    def save(self, result: SynthesisResult, path: Path) -> Path:
        """Write the narration to a mono wav at the model's native rate."""
        path.parent.mkdir(parents=True, exist_ok=True)
        audio = np.asarray(result.audio, dtype=np.float32).reshape(-1)
        sf.write(str(path), audio, result.sample_rate, subtype="PCM_16")
        return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def chunk_text(text: str, *, max_chars: int = MAX_CHARS) -> list[str]:
    """Split narration into chunks, preferring sentence then clause boundaries.

    A chunk that still overflows is split on whitespace rather than mid-word,
    because cutting a word in half is the one break the listener always hears.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        # A single oversized sentence gets broken up on clauses first.
        for piece in _split_oversized(sentence, max_chars):
            if current and len(current) + 1 + len(piece) > max_chars:
                chunks.append(current)
                current = piece
            elif current:
                current = f"{current} {piece}"
            else:
                current = piece

    if current:
        chunks.append(current)
    return chunks


def _split_oversized(sentence: str, max_chars: int) -> list[str]:
    if len(sentence) <= max_chars:
        return [sentence]

    pieces: list[str] = []
    current = ""
    for clause in _CLAUSE_SPLIT.split(sentence):
        clause = clause.strip()
        if not clause:
            continue
        if len(clause) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.extend(_split_on_whitespace(clause, max_chars))
            continue
        if current and len(current) + 1 + len(clause) > max_chars:
            pieces.append(current)
            current = clause
        else:
            current = f"{current} {clause}".strip()
    if current:
        pieces.append(current)
    return pieces


def _split_on_whitespace(text: str, max_chars: int) -> list[str]:
    words = text.split()
    pieces: list[str] = []
    current = ""
    for word in words:
        if len(word) > max_chars:
            # A single monster token: emit it alone rather than corrupt it.
            if current:
                pieces.append(current)
                current = ""
            pieces.append(word)
            continue
        if current and len(current) + 1 + len(word) > max_chars:
            pieces.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        pieces.append(current)
    return pieces


def _as_numpy(audio) -> np.ndarray:
    if isinstance(audio, np.ndarray):
        arr = audio.astype(np.float32, copy=False)
    else:
        detach = getattr(audio, "detach", None)
        if detach is not None:
            arr = detach().cpu().numpy().astype(np.float32, copy=False)
        else:
            arr = np.asarray(audio, dtype=np.float32)
    return arr.reshape(-1)


def _infer_sample_rate(audio) -> int:
    """Best-effort sample rate for a torch tensor of audio samples."""
    if hasattr(audio, "shape") and len(audio.shape) > 1:
        return int(audio.shape[0])
    return 24000  # Chatterbox Turbo's native rate
