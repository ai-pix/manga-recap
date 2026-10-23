"""Tests for Stage 7 YouTube uploading pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from manga_recap.stages.s7_publish.youtube import (
    YouTubeUploader,
    find_package_assets,
    parse_metadata_file,
)
from scripts.upload_to_youtube import find_chapter_folder


def test_parse_metadata_file(tmp_path: Path):
    meta_file = tmp_path / "metadata.txt"
    meta_file.write_text(
        """TITLE:
Test Catchy Title | Chapter 1 Recap

DESCRIPTION:
This is a rich description of the chapter.
Featuring timestamps:
00:00 - Intro
10:00 - Battle

TAGS:
manga recap, anime recap, only sense online, ch1
""",
        encoding="utf-8",
    )

    parsed = parse_metadata_file(meta_file)
    assert parsed["title"] == "Test Catchy Title | Chapter 1 Recap"
    assert "rich description" in parsed["description"]
    assert "00:00 - Intro" in parsed["description"]
    assert parsed["tags"] == ["manga recap", "anime recap", "only sense online", "ch1"]


def test_find_package_assets(tmp_path: Path):
    pkg_dir = tmp_path / "Chapter_01_Test"
    pkg_dir.mkdir()
    (pkg_dir / "metadata.txt").write_text("TITLE:\nSample Title\nDESCRIPTION:\nDesc\nTAGS:\ntag1, tag2\n", encoding="utf-8")
    (pkg_dir / "video.mp4").write_bytes(b"\x00" * 100)
    (pkg_dir / "thumbnail.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 50)

    assets = find_package_assets(pkg_dir)
    assert assets.title == "Sample Title"
    assert assets.description == "Desc"
    assert assets.tags == ["tag1", "tag2"]
    assert assets.video_path == pkg_dir / "video.mp4"
    assert assets.thumbnail_path == pkg_dir / "thumbnail.jpg"


def test_find_chapter_folder(tmp_path: Path):
    (tmp_path / "00_FULL_SERIES_COMPILATION").mkdir()
    (tmp_path / "Chapter_01_Enter_the_World").mkdir()
    (tmp_path / "Chapter_05_5_Bonus_Strips").mkdir()
    (tmp_path / "Chapter_12_Radiant_Woodland").mkdir()

    assert find_chapter_folder(tmp_path, "ch01").name == "Chapter_01_Enter_the_World"
    assert find_chapter_folder(tmp_path, "ch12").name == "Chapter_12_Radiant_Woodland"
    assert find_chapter_folder(tmp_path, "ch005_5").name == "Chapter_05_5_Bonus_Strips"
    assert find_chapter_folder(tmp_path, "ch99") is None


def test_uploader_state_persistence(tmp_path: Path):
    state_file = tmp_path / "test_uploads.json"
    uploader = YouTubeUploader(
        credentials_path=tmp_path / "creds.json",
        token_path=tmp_path / "token.json",
        state_file=state_file,
    )

    assert uploader.load_upload_state() == {}
    uploader.save_upload_record("ch01", {"video_id": "vid123", "url": "https://youtu.be/vid123"})

    state = uploader.load_upload_state()
    assert "ch01" in state
    assert state["ch01"]["video_id"] == "vid123"


def test_upload_package_skip_existing(tmp_path: Path):
    state_file = tmp_path / "test_uploads.json"
    state_file.write_text(json.dumps({"ch01": {"video_id": "existing123", "url": "https://youtu.be/existing123"}}), encoding="utf-8")

    uploader = YouTubeUploader(
        credentials_path=tmp_path / "creds.json",
        token_path=tmp_path / "token.json",
        state_file=state_file,
    )

    pkg_dir = tmp_path / "Chapter_01"
    pkg_dir.mkdir()
    (pkg_dir / "metadata.txt").write_text("TITLE:\nT\nDESCRIPTION:\nD\nTAGS:\nt\n", encoding="utf-8")
    (pkg_dir / "v.mp4").write_bytes(b"\x00" * 50)

    record = uploader.upload_package(pkg_dir, key="ch01", force=False)
    assert record["video_id"] == "existing123"


@patch.object(YouTubeUploader, "upload_video", return_value="mock_vid_456")
@patch.object(YouTubeUploader, "set_thumbnail", return_value=True)
def test_upload_package_success(mock_thumb, mock_upload, tmp_path: Path):
    state_file = tmp_path / "test_uploads.json"
    uploader = YouTubeUploader(
        credentials_path=tmp_path / "creds.json",
        token_path=tmp_path / "token.json",
        state_file=state_file,
    )

    pkg_dir = tmp_path / "Chapter_02"
    pkg_dir.mkdir()
    (pkg_dir / "metadata.txt").write_text("TITLE:\nTitle 2\nDESCRIPTION:\nDesc 2\nTAGS:\nt2\n", encoding="utf-8")
    (pkg_dir / "video.mp4").write_bytes(b"\x00" * 100)
    (pkg_dir / "thumbnail.jpg").write_bytes(b"\xff\xd8\xff\x00")

    record = uploader.upload_package(pkg_dir, key="ch02", privacy_status="unlisted")
    assert record["video_id"] == "mock_vid_456"
    assert record["thumbnail_uploaded"] is True
    assert record["url"] == "https://youtu.be/mock_vid_456"

    # Verify state was saved
    saved = json.loads(state_file.read_text(encoding="utf-8"))
    assert "ch02" in saved
    assert saved["ch02"]["video_id"] == "mock_vid_456"
