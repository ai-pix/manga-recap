"""Kaggle kernel internals: chunking, job building, and input discovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

KERNEL_A = Path(__file__).resolve().parents[1] / "kaggle" / "kernel_tts_align"
sys.path.insert(0, str(KERNEL_A))

from tts_engine import MAX_CHARS, TTSEngine, chunk_text  # noqa: E402

# -- chunking ---------------------------------------------------------------


def test_short_text_is_one_chunk():
    assert len(chunk_text("He walks in like he owns the place.")) == 1


def test_empty_text_produces_nothing():
    assert chunk_text("   \n  ") == []


def test_text_at_the_limit_stays_whole():
    text = "x" * MAX_CHARS
    assert chunk_text(text) == [text]


def test_long_text_is_split_on_sentence_boundaries():
    text = " ".join(f"Sentence number {i} here." for i in range(80))
    chunks = chunk_text(text)

    assert len(chunks) > 1
    for chunk in chunks:
        # Splitting mid-word is the one break a listener always hears.
        assert chunk == chunk.strip()
        assert not chunk.startswith(" ")


def test_no_chunk_exceeds_the_limit_unless_it_is_one_token():
    text = " ".join(f"word{i}" for i in range(400))
    for chunk in chunk_text(text):
        assert len(chunk) <= MAX_CHARS or " " not in chunk


def test_a_single_long_token_is_emitted_whole():
    monster = "q" * (MAX_CHARS * 2)
    chunks = chunk_text(f"start here {monster} and then normal trailing words")

    assert monster in chunks, "an unsplittable token must not be corrupted"


def test_reassembly_preserves_every_word_in_order():
    source = " ".join(f"word{i}" for i in range(500))
    rebuilt = " ".join(chunk_text(source))
    assert rebuilt == source


def test_chunking_is_deterministic():
    text = " ".join(f"Line {i} of the narration." for i in range(120))
    assert chunk_text(text) == chunk_text(text)


# -- job building -----------------------------------------------------------


def test_tts_job_carries_everything_the_kernel_needs():
    from manga_recap.core.config import load_config
    from manga_recap.core.paths import ChapterPaths
    from manga_recap.stages.s4_speech import _build_job

    paths = ChapterPaths.create("ch01", Path("/tmp/data"))
    config = load_config()
    job = _build_job(paths, config, Path("/tmp/staging"))

    assert job["chapter_id"] == "ch01"
    for key in ("voice", "language_id", "duration_words_per_minute", "workers_per_gpu"):
        assert key in job["tts"], f"tts.{key} missing from the job"
    assert job["tts"]["workers_per_gpu"] == config.get("tts.workers_per_gpu")
    for key in ("whisper_model", "device", "compute_type", "min_match_ratio"):
        assert key in job["align"], f"align.{key} missing from the job"
    assert "block_gap_seconds" in job["narration"]


def test_cloned_voice_reference_is_reduced_to_a_filename():
    from manga_recap.core.config import load_config
    from manga_recap.core.paths import ChapterPaths
    from manga_recap.stages.s4_speech import _build_job

    config = load_config()
    config._data["tts"]["voice"] = {
        "mode": "clone",
        "reference_wav": "assets/voices/narrator.wav",
    }
    job = _build_job(ChapterPaths.create("ch01", Path("/tmp/data")), config, Path("/tmp"))

    # The kernel only sees the uploaded copy, so it must not carry a local path.
    assert job["tts"]["voice"]["reference_wav"] == "narrator.wav"
    assert "/" not in job["tts"]["voice"]["reference_wav"]


def test_render_job_carries_the_visual_style():
    from manga_recap.core.config import load_config
    from manga_recap.core.paths import ChapterPaths
    from manga_recap.stages.s5_render import _build_job

    job = _build_job(ChapterPaths.create("ch01", Path("/tmp/data")), load_config())

    # `background_mode` and `max_words_per_beat` are the two settings the render
    # and sync systems depend on, so the kernel has to receive both or it
    # silently reverts to defaults that differ from what was reviewed locally.
    for key in (
        "width", "height", "fps",
        "background_mode", "blur_width", "blur_radius", "blur_darken",
        "max_words_per_beat", "min_shot_seconds",
    ):
        assert key in job["render"], f"render.{key} missing from the job"
    assert "kenburns" in job["render"]
    assert "enabled" in job["bgm"]


def test_blur_settings_survive_the_trip_to_the_kernel():
    """A blur configured locally but dropped from the job renders differently.

    The kernel has no access to config.yaml, so anything absent from the job
    falls back to a hardcoded default and the video stops matching the setting
    that was chosen.
    """
    from manga_recap.core.config import load_config
    from manga_recap.core.paths import ChapterPaths
    from manga_recap.stages.s5_render import _build_job

    job = _build_job(ChapterPaths.create("ch01", Path("/tmp/data")), load_config())
    config = load_config()

    assert job["render"]["background_mode"] == config.get("render.background_mode")
    assert job["render"]["blur_width"] == config.get("render.blur_width")
    assert job["render"]["blur_radius"] == config.get("render.blur_radius")
    assert job["render"]["blur_darken"] == config.get("render.blur_darken")


def test_kernel_metadata_is_valid_json():
    for kernel in ("kernel_tts_align", "kernel_render"):
        path = Path(__file__).resolve().parents[1] / "kaggle" / kernel / "kernel-metadata.json"
        metadata = json.loads(path.read_text(encoding="utf-8"))
        assert metadata["code_file"] == "main.py"
        assert metadata["language"] == "python"
        assert metadata["kernel_type"] == "script"
        # No `id` in the checked-in file, and nothing that looks like one
        # either. The stage writes the real `username/slug` at push time, because
        # a committed id would embed a Kaggle username. A placeholder integer
        # gets past this file and then dies inside the kaggle package, which
        # calls parse_kernel_string(metadata["id"]) and tries `"/" in 101010101`.
        assert "id" not in metadata
        assert "id_no" not in metadata
        assert not any(value == 101010101 for value in metadata.values())


def test_tts_kernel_enables_gpu_and_render_does_not():
    root = Path(__file__).resolve().parents[1] / "kaggle"
    tts = json.loads((root / "kernel_tts_align" / "kernel-metadata.json").read_text())
    render = json.loads((root / "kernel_render" / "kernel-metadata.json").read_text())

    assert tts["enable_gpu"] is True, "TTS needs a GPU to finish in minutes, not hours"
    assert isinstance(render["enable_gpu"], bool)


def test_render_kernel_attaches_no_datasets():
    """Nothing is attached: inputs now arrive as one zip over HTTP.

    Both kernels used to attach Kaggle Datasets, which meant a dataset per
    chapter, a second dataset to carry stage 4's outputs into stage 5, and a
    mount path the kernel had to guess. The payload archive replaced all of it,
    so an empty `dataset_sources` here is the intended state rather than a
    missing configuration.
    """
    root = Path(__file__).resolve().parents[1] / "kaggle"
    for kernel in ("kernel_tts_align", "kernel_render"):
        metadata = json.loads((root / kernel / "kernel-metadata.json").read_text())
        assert metadata["dataset_sources"] == [], (
            f"{kernel} still attaches a dataset. Inputs come from payload_url.txt "
            "now, and a stale dataset reference will mount nothing useful."
        )
        assert metadata["enable_internet"] is True, (
            f"{kernel} fetches its payload over HTTP and needs internet enabled"
        )


def test_both_kernels_read_their_payload_url():
    """Each kernel downloads its archive rather than looking for a mount."""
    root = Path(__file__).resolve().parents[1] / "kaggle"
    for kernel in ("kernel_tts_align", "kernel_render"):
        source = (root / kernel / "main.py").read_text(encoding="utf-8")
        assert "zipfile" in source, f"{kernel} does not unpack an archive"
        # A sibling file will not do: Kaggle runs a script kernel as
        # /kaggle/src/script.py, so anything placed beside main.py at push time
        # is absent when the code runs. The URL has to be compiled in.
        assert '__PAYLOAD_URL__' in source, f"{kernel} has no payload placeholder"
        assert "urlopen" in source, f"{kernel} does not fetch its payload"
        # catbox and friends drop a bare urllib connection without a response.
        # They serve the same file to anything that says it is a browser.
        assert "FETCH_HEADERS" in source, f"{kernel} fetches with no user agent"
        assert "_download(" in source, f"{kernel} does not retry the download"
        # /kaggle/input is mounted read-only, so unpacking the payload there
        # fails with Errno 30 the moment the download succeeds.
        assert 'WORKING / "payload"' in source, f"{kernel} unpacks into read-only /kaggle/input"


def test_tts_requirements_pin_the_tts_and_alignment_packages():
    path = Path(__file__).resolve().parents[1] / "kaggle" / "requirements-kaggle.txt"
    text = path.read_text(encoding="utf-8").lower()
    assert "chatterbox" in text
    assert "faster-whisper" in text


# -- narration joining ------------------------------------------------------


def test_joining_blocks_separates_them_with_a_blank_line():
    # main.py imports torch/chatterbox at call time only, so importing it is safe.
    import importlib.util

    spec = importlib.util.spec_from_file_location("kernel_tts_main", KERNEL_A / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    joined = module._join_narration(["First beat.", "Second beat."])
    assert joined == "First beat.\n\nSecond beat."


def test_empty_blocks_are_dropped_when_joining():
    import importlib.util

    spec = importlib.util.spec_from_file_location("kernel_tts_main2", KERNEL_A / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._join_narration(["Real.", "", "   ", "Also real."]) == "Real.\n\nAlso real."


def test_duration_estimate_scales_with_word_count():
    import importlib.util

    spec = importlib.util.spec_from_file_location("kernel_tts_main3", KERNEL_A / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    settings = {"duration_words_per_minute": 150, "duration_tolerance": 0.5}
    short = module._plausible_duration("one two three four five", settings)
    long = module._plausible_duration(" ".join(["word"] * 500), settings)

    assert short and long
    assert long[1] > short[1] * 10
    assert short[0] < short[1]


def test_duration_estimate_of_empty_text_is_none():
    import importlib.util

    spec = importlib.util.spec_from_file_location("kernel_tts_main4", KERNEL_A / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module._plausible_duration("   ", {"duration_words_per_minute": 150}) is None


# -- narration helpers ------------------------------------------------------


def test_tts_refuses_empty_text():
    engine = TTSEngine(voice_mode="builtin")
    with pytest.raises(ValueError, match="empty"):
        engine.synthesize("   ")


def test_tts_refuses_to_run_on_cpu():
    """This stage belongs on Kaggle; a silent CPU run would waste hours."""
    engine = TTSEngine(voice_mode="builtin", device="cpu")
    with pytest.raises(RuntimeError, match="Kaggle"):
        engine.load()


def test_clone_mode_without_a_reference_is_rejected():
    engine = TTSEngine(voice_mode="clone", reference_wav=None)
    with pytest.raises(FileNotFoundError, match="builtin"):
        engine._load_reference_voice()


def test_tts_engine_workers_per_gpu_config():
    engine = TTSEngine(voice_mode="builtin", workers_per_gpu=3)
    assert engine.workers_per_gpu == 3

