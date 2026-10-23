"""Pipeline runner: ordering, resume, and failure handling."""

from __future__ import annotations

import pytest
from conftest import LAYOUTS, make_page

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths
from manga_recap.stages.s6_pipeline import (
    STAGE_LABELS,
    run_pipeline,
    stage_artifact_exists,
)
from manga_recap.stages.s6_pipeline.status import status


@pytest.fixture
def paths(tmp_path):
    return ChapterPaths.create("ch_test", tmp_path / "chapters")


@pytest.fixture
def config():
    cfg = load_config()
    # The dependency-free detector keeps this test free of model weights.
    cfg._data["crop"]["detector"] = "opencv"
    return cfg


def seed_pages(paths):
    paths.ensure_dirs()
    for page_no, layout in enumerate(LAYOUTS, start=1):
        make_page(layout, seed=page_no).save(paths.input_dir / f"{page_no:03d}.png")


def ingest_and_crop(paths, config, *, force=False):
    """Run stages 0 and 1, the only two that need no credentials."""
    run_pipeline(paths, config, only="s0_ingest", force=force)
    run_pipeline(paths, config, only="s1_crop", force=force)


# -- ordering ---------------------------------------------------------------


def test_stage_order_is_the_data_flow():
    assert list(STAGE_LABELS.values()) == [
        "ingest", "crop", "describe", "script", "speak", "render"
    ]


def test_stages_zero_and_one_produce_pages_and_panels(paths, config):
    seed_pages(paths)
    ingest_and_crop(paths, config)

    assert len(list(paths.pages_dir.glob("page_*.png"))) == 3
    assert len(list(paths.panels_dir.glob("panel_*.png"))) == 6


def test_run_only_rejects_an_unknown_stage(paths, config):
    with pytest.raises(ValueError, match="Unknown stage"):
        run_pipeline(paths, config, only="polish")


def test_stages_find_their_kaggle_kernel_directories():
    """Both Kaggle stages resolve the kernel from the repo root.

    Counting parents off a stage module lands on `src/`, one level too high, and
    the failure is a FileNotFoundError naming a path nobody wrote. preflight.py
    checks the same two directories, so this pins the stages to preflight's
    answer rather than to a second guess about the layout.
    """
    from manga_recap.core.paths import repo_path
    from manga_recap.stages import s4_speech, s5_render

    assert s4_speech.KERNEL_DIR == repo_path("kaggle") / "kernel_tts_align"
    assert s5_render.KERNEL_DIR == repo_path("kaggle") / "kernel_render"


def test_every_kaggle_kernel_directory_that_preflight_checks_exists():
    """preflight reporting a kernel as present is only useful if it is present."""
    import json

    from manga_recap.core.paths import repo_path

    kernel_dir = repo_path("kaggle")
    for kernel in ("kernel_tts_align", "kernel_render"):
        path = kernel_dir / kernel
        assert (path / "main.py").exists(), f"{kernel} is missing main.py"
        assert (path / "kernel-metadata.json").exists(), (
            f"{kernel} is missing kernel-metadata.json, so it cannot be pushed"
        )

        metadata = json.loads((path / "kernel-metadata.json").read_text(encoding="utf-8"))
        # Kaggle parses metadata["id"] as a slug string on push. A placeholder
        # number survives `manga check` and then dies deep inside the kaggle
        # package with a TypeError about `"/" in kernel`.
        assert "id" not in metadata
        assert metadata["code_file"] == "main.py"
        assert metadata["language"] == "python"
        assert metadata["kernel_type"] == "script"


def test_push_writes_the_kernel_id_as_a_username_slug(tmp_path):
    """The push stages a copy, so the tracked metadata stays username-free."""
    from manga_recap.core import payload

    source = tmp_path / "kernel"
    source.mkdir()
    (source / "main.py").write_text(
        'PAYLOAD_UNSET = "__PAYLOAD_URL__"\n'
        "PAYLOAD_URL = PAYLOAD_UNSET\n"
        "def url():\n"
        "    if PAYLOAD_URL != PAYLOAD_UNSET:\n"
        "        return PAYLOAD_URL\n"
        "    return None\n",
        encoding="utf-8",
    )
    (source / "kernel-metadata.json").write_text(
        '{"code_file": "main.py", "dataset_sources": []}', encoding="utf-8"
    )

    work = payload.stage_from_url(
        kernel_dir=source,
        url="https://example.invalid/payload.zip",
        work_dir=tmp_path / "push",
        metadata={"id": "wampireai/manga-recap-tts", "title": "manga-recap-tts"},
    )

    import json

    staged = json.loads((work / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert staged["id"] == "wampireai/manga-recap-tts"
    assert staged["dataset_sources"] == []

    # The URL is compiled into the script, not left beside it: Kaggle runs a
    # script kernel as /kaggle/src/script.py, so a sibling file is not there
    # when the code runs.
    code = (work / "main.py").read_text(encoding="utf-8")
    assert 'PAYLOAD_URL = "https://example.invalid/payload.zip"' in code

    # The sentinel survives, so the kernel's own "was a URL set?" test still
    # works. Replacing the bare token everywhere rewrites that comparison into
    # `PAYLOAD_URL != "<the url>"`, which is always false, and the kernel then
    # reports that it has no URL after it was just handed one.
    assert 'PAYLOAD_UNSET = "__PAYLOAD_URL__"' in code
    assert "if PAYLOAD_URL != PAYLOAD_UNSET:" in code

    namespace: dict = {}
    exec(compile(code, "staged_main.py", "exec"), namespace)
    assert namespace["url"]() == "https://example.invalid/payload.zip"

    # The original is untouched, so a checked-in file never gains a username.
    original = (source / "kernel-metadata.json").read_text(encoding="utf-8")
    assert "wampireai" not in original


def test_staging_refuses_a_kernel_with_no_payload_placeholder(tmp_path):
    """A kernel and a stage that disagree should fail loudly, not at runtime."""
    from manga_recap.core import payload

    source = tmp_path / "kernel"
    source.mkdir()
    (source / "main.py").write_text("# no placeholder here\n", encoding="utf-8")
    (source / "kernel-metadata.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match="PAYLOAD_URL"):
        payload.stage_from_url(
            kernel_dir=source,
            url="https://example.invalid/p.zip",
            work_dir=tmp_path / "push",
        )


def test_kernel_status_is_parsed_out_of_the_cli_sentence():
    """The CLI never prints a bare status, so comparing raw output never matches.

    Left unparsed, an errored kernel is not recognised as an error and the poller
    spins until the six-hour ceiling instead of raising.
    """
    from manga_recap.core.kaggle_io import (
        STATUS_DONE,
        STATUS_FAILED,
        normalise_status,
    )

    assert normalise_status(
        'wampireai/manga-recap-tts has status "KernelWorkerStatus.ERROR"'
    ) in STATUS_FAILED
    assert normalise_status(
        'wampireai/manga-recap-tts has status "KernelWorkerStatus.COMPLETE"'
    ) in STATUS_DONE
    assert normalise_status(
        'wampireai/manga-recap-tts has status "KernelWorkerStatus.RUNNING"'
    ) == "running"
    assert normalise_status("garbage") == "garbage"


def test_from_accepts_a_stage_label(paths, config, set_env):
    """The label has to resolve to a real stage, and the run has to stop there.

    Credentials are cleared so that "describe" fails for a known reason instead
    of reaching the network. Without that, a developer machine with a real key
    quietly turns this into a live API call, which is slow when it works and a
    503 when the provider is busy.
    """
    from manga_recap.core.config import ConfigError

    set_env({})
    seed_pages(paths)
    ingest_and_crop(paths, config)

    with pytest.raises(ConfigError):
        run_pipeline(paths, config, from_stage="describe")


# -- resume -----------------------------------------------------------------


def test_completed_stages_are_skipped(paths, config):
    seed_pages(paths)
    ingest_and_crop(paths, config)

    results = run_pipeline(paths, config, only="s1_crop")
    assert results["s1_crop"] == "skipped"


def test_force_reruns_a_completed_stage(paths, config):
    seed_pages(paths)
    ingest_and_crop(paths, config)

    results = run_pipeline(paths, config, only="s1_crop", force=True)
    assert results["s1_crop"] == "completed"


def test_artifact_detection_for_directories_and_files(paths):
    from manga_recap.stages.s6_pipeline import _build_stages

    stages = {s.name: s for s in _build_stages()}

    assert not stage_artifact_exists(stages["s0_ingest"], paths)
    paths.pages_dir.mkdir(parents=True)
    (paths.pages_dir / "page_001.png").write_bytes(b"x")
    assert stage_artifact_exists(stages["s0_ingest"], paths)

    assert not stage_artifact_exists(stages["s3_script"], paths)
    paths.script_file.write_text("{}", encoding="utf-8")
    assert stage_artifact_exists(stages["s3_script"], paths)


def test_an_empty_directory_does_not_count_as_done(paths):
    from manga_recap.stages.s6_pipeline import _build_stages

    stages = {s.name: s for s in _build_stages()}
    paths.pages_dir.mkdir(parents=True)
    assert not stage_artifact_exists(stages["s0_ingest"], paths)


# -- status -----------------------------------------------------------------


def test_status_reports_the_next_stage(paths):
    report = status(paths, load_config())
    assert report["next_stage"] == "ingest"
    assert not report["complete"]
    assert all(not entry["done"] for entry in report["stages"])


def test_status_advances_as_artifacts_appear(paths, config):
    seed_pages(paths)
    ingest_and_crop(paths, config)

    report = status(paths, config)
    assert report["next_stage"] == "describe"
    assert report["details"]["panels"] == 6
    assert report["details"]["pages"] == 3


def test_status_surfaces_a_failed_stage(paths, config):
    # Cropping with no ingested pages must fail, and must be recorded.
    paths.ensure_dirs()
    with pytest.raises(FileNotFoundError):
        run_pipeline(paths, config, only="s1_crop")

    from manga_recap.core.paths import REPO_ROOT

    status_file = REPO_ROOT / "logs" / paths.chapter_id / "s1_crop.json"
    assert status_file.exists(), "a failure must be recorded for debugging"
    assert "failed" in status_file.read_text(encoding="utf-8")


# -- resilience -------------------------------------------------------------


def test_a_failing_stage_halts_the_chain(paths, config, monkeypatch):
    """One failure must stop the run, not let later stages run on bad data."""
    from manga_recap.stages import s0_ingest

    calls = []
    monkeypatch.setattr(
        s0_ingest, "run",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        "manga_recap.stages.s1_crop.run",
        lambda *a, **k: calls.append("crop") or None,
    )

    with pytest.raises(RuntimeError, match="boom"):
        run_pipeline(paths, config)

    assert calls == [], "no stage may run after a failure"


# -- kernel artifact selection -----------------------------------------------


def test_locate_prefers_the_newest_artifact(tmp_path):
    """A download can hold artifacts from more than one kernel run.

    Walking in name order picked up the previous run's manifest and left the
    chapter describing a video that no longer existed, so the newest file wins.
    """
    import os
    import time

    from manga_recap.stages.s5_render import _locate

    download = tmp_path / "out"
    (download / "old").mkdir(parents=True)
    (download / "new").mkdir(parents=True)

    stale = download / "old" / "07_render_manifest.json"
    fresh = download / "new" / "07_render_manifest.json"
    stale.write_text("{}", encoding="utf-8")
    fresh.write_text("{}", encoding="utf-8")

    now = time.time()
    os.utime(stale, (now - 600, now - 600))
    os.utime(fresh, (now, now))

    found = _locate(download, "07_render_manifest.json")
    assert found is not None
    assert found.parent.name == "new"


def test_locate_prefers_a_direct_hit_over_a_nested_one(tmp_path):
    from manga_recap.stages.s5_render import _locate

    download = tmp_path / "out"
    download.mkdir()
    (download / "nested").mkdir()
    (download / "file.json").write_text("{}", encoding="utf-8")
    (download / "nested" / "file.json").write_text("{}", encoding="utf-8")

    found = _locate(download, "file.json")
    assert found is not None and found.parent == download


def test_locate_returns_none_when_absent(tmp_path):
    from manga_recap.stages.s5_render import _locate

    assert _locate(tmp_path, "nothing.json") is None
    assert _locate(tmp_path / "missing", "nothing.json") is None

