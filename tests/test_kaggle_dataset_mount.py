"""A pushed kernel can only mount a dataset version Kaggle has registered."""

from datetime import datetime

import pytest

from manga_recap.core import kaggle_io
from manga_recap.core.kaggle_io import KaggleClient, KaggleError
from manga_recap.core.logging import get_logger


def _listing(name: str, stamp: str) -> str:
    return (
        "name              size  creationDate\n"
        "----------------  ----  --------------------------\n"
        f"{name}            862   {stamp}.104000\n"
    )


def _client(listings: list[str]) -> tuple[KaggleClient, list[int]]:
    client = KaggleClient.__new__(KaggleClient)
    client.username = "tester"
    client.dry_run = False
    client._log = get_logger("test")
    seen = [0]

    def fake_run(args, **kwargs):
        text = listings[min(seen[0], len(listings) - 1)]
        seen[0] += 1
        return type("Result", (), {"stdout": text, "returncode": 0})()

    client._run = fake_run
    return client, seen


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(kaggle_io.time, "sleep", lambda seconds: None)


def test_an_older_version_is_not_treated_as_ready():
    """The previous version lists the same names, so it must not satisfy a wait."""
    client, seen = _client([_listing("job.json", "2026-11-04 06:00:00")])

    with pytest.raises(KaggleError, match="did not register"):
        client.wait_for_dataset_files(
            "tester/payload",
            ("job.json",),
            not_before=datetime(2026, 11, 4, 7, 0, 0),
            timeout_seconds=6,
            poll_seconds=1,
        )

    assert seen[0] > 1


def test_a_newly_registered_version_satisfies_the_wait():
    client, seen = _client(
        [
            _listing("job.json", "2026-11-04 06:00:00"),
            _listing("job.json", "2026-11-04 07:30:00"),
        ]
    )

    client.wait_for_dataset_files(
        "tester/payload",
        ("job.json",),
        not_before=datetime(2026, 11, 4, 7, 0, 0),
        timeout_seconds=60,
        poll_seconds=1,
    )

    assert seen[0] == 2
