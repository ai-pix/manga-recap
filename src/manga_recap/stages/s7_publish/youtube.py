"""Automated YouTube uploader with resumable upload, thumbnail binding, and metadata parsing."""

from __future__ import annotations

import json
import logging
import random
import re
import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_log = logging.getLogger("manga_recap.publish.youtube")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

DEFAULT_CATEGORY_ID = "24"  # Entertainment (20 = Gaming)
MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]
RETRIABLE_EXCEPTIONS = (
    socket.error,
    socket.timeout,
)


@dataclass
class UploadMetadata:
    title: str
    description: str
    tags: list[str]
    video_path: Path
    thumbnail_path: Path | None = None
    category_id: str = DEFAULT_CATEGORY_ID


def parse_metadata_file(meta_path: Path) -> dict[str, Any]:
    """Parse title, description, and tags from a structured metadata.txt file."""
    text = meta_path.read_text(encoding="utf-8")

    title = ""
    description = ""
    tags: list[str] = []

    title_match = re.search(r"TITLE:\s*\n(.*?)(?=\n\s*DESCRIPTION:|\Z)", text, re.DOTALL)
    if title_match:
        title = title_match.group(1).strip()

    desc_match = re.search(r"DESCRIPTION:\s*\n(.*?)(?=\n\s*TAGS:|\Z)", text, re.DOTALL)
    if desc_match:
        description = desc_match.group(1).strip()

    tags_match = re.search(r"TAGS:\s*\n(.*)", text, re.DOTALL)
    if tags_match:
        raw_tags = tags_match.group(1).strip()
        tags = [t.strip() for t in raw_tags.split(",") if t.strip()]

    return {
        "title": title,
        "description": description,
        "tags": tags,
    }


def find_package_assets(package_dir: Path) -> UploadMetadata:
    """Locate video, metadata, and thumbnail inside a chapter or compilation package directory."""
    if not package_dir.is_dir():
        raise FileNotFoundError(f"Package directory not found: {package_dir}")

    meta_file = package_dir / "metadata.txt"
    if not meta_file.exists():
        raise FileNotFoundError(f"metadata.txt not found in {package_dir}")

    meta_dict = parse_metadata_file(meta_file)

    video_files = list(package_dir.glob("*.mp4"))
    if not video_files:
        raise FileNotFoundError(f"No .mp4 video found in {package_dir}")
    video_path = video_files[0]

    thumb_path = None
    for ext in ("thumbnail.jpg", "thumbnail.png", "thumbnail.jpeg"):
        candidate = package_dir / ext
        if candidate.exists():
            thumb_path = candidate
            break

    return UploadMetadata(
        title=meta_dict["title"] or video_path.stem.replace("_", " "),
        description=meta_dict["description"],
        tags=meta_dict["tags"],
        video_path=video_path,
        thumbnail_path=thumb_path,
    )


class YouTubeUploader:
    """Manages YouTube Data API authentication, resumable video upload, and thumbnail binding."""

    def __init__(
        self,
        credentials_path: Path | None = None,
        token_path: Path | None = None,
        state_file: Path | None = None,
    ):
        self.credentials_path = credentials_path or self._find_credentials()
        self.token_path = token_path or Path("config/youtube_token.json")
        self.state_file = state_file or Path("data/youtube_uploads.json")
        self._service = None

    @staticmethod
    def _find_credentials() -> Path:
        candidates = [
            Path("client_secrets.json"),
            Path("credentials.json"),
            *list(Path(".").glob("client_secret*.json")),
            Path("config/client_secrets.json"),
            Path("config/credentials.json"),
            Path.home() / ".youtube" / "client_secrets.json",
        ]
        for p in candidates:
            if p.is_file():
                return p
        return Path("client_secrets.json")

    def get_service(self):
        """Authenticate via OAuth 2.0 and return the YouTube service resource."""
        if self._service is not None:
            return self._service

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        creds = None
        if self.token_path.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
            except Exception as exc:
                _log.warning("Could not read token from %s: %s", self.token_path, exc)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as exc:
                    _log.warning("Token refresh failed: %s. Re-authenticating.", exc)
                    creds = None

            if not creds:
                if not self.credentials_path.is_file():
                    raise FileNotFoundError(
                        f"Google OAuth credentials not found at: {self.credentials_path.resolve()}\n\n"
                        "To set up automated YouTube uploads:\n"
                        "1. Go to Google Cloud Console: https://console.cloud.google.com/\n"
                        "2. Create a project and enable 'YouTube Data API v3'.\n"
                        "3. Go to Credentials -> Create Credentials -> OAuth client ID.\n"
                        "4. Choose 'Desktop App', name it 'Manga Recap Uploader', and click Create.\n"
                        "5. Download the JSON file, rename it to 'client_secrets.json', and place it in the project root.\n"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
                print("\nOpening web browser for YouTube OAuth authorization...", flush=True)
                creds = flow.run_local_server(port=0)

            self.token_path.parent.mkdir(parents=True, exist_ok=True)
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
            _log.info("Saved OAuth token to %s", self.token_path)

        self._service = build("youtube", "v3", credentials=creds)
        return self._service

    def upload_video(
        self,
        meta: UploadMetadata,
        privacy_status: str = "unlisted",
        publish_at: str | None = None,
        progress_callback: Callable[[float], None] | None = None,
    ) -> str:
        """Perform resumable video upload and return the YouTube video ID."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        service = self.get_service()

        body = {
            "snippet": {
                "title": meta.title[:100],  # YouTube max title length is 100
                "description": meta.description[:5000],  # YouTube max desc length is 5000
                "tags": meta.tags[:50],
                "categoryId": meta.category_id,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus": "private" if publish_at else privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        if publish_at:
            body["status"]["publishAt"] = publish_at

        # 10 MB chunk size for reliable resumable upload
        chunk_size = 10 * 1024 * 1024
        media = MediaFileUpload(str(meta.video_path), chunksize=chunk_size, resumable=True)

        insert_request = service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        error = None
        retry = 0

        total_bytes = meta.video_path.stat().st_size
        print(f"\n[YouTube] Starting upload: {meta.video_path.name} ({total_bytes / (1024*1024):.1f} MB)")
        print(f"          Title: {meta.title[:80]}...")
        print(f"          Privacy: {privacy_status}" + (f" (Scheduled for {publish_at})" if publish_at else ""))

        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if status:
                    pct = status.progress() * 100
                    uploaded_mb = (status.progress() * total_bytes) / (1024 * 1024)
                    bar = ("#" * int(pct // 5)).ljust(20, "-")
                    print(
                        f"\r  Uploading: [{bar}] {pct:5.1f}% ({uploaded_mb:.1f} / {total_bytes / (1024*1024):.1f} MB)",
                        end="",
                        flush=True,
                    )
                    if progress_callback:
                        progress_callback(status.progress())
            except HttpError as exc:
                if exc.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"HTTP {exc.resp.status}: {exc}"
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as exc:
                error = f"Network error: {exc}"

            if error:
                retry += 1
                if retry > MAX_RETRIES:
                    raise RuntimeError(f"Max retries exceeded while uploading {meta.video_path.name}: {error}")
                backoff = (2**retry) + random.random()
                print(f"\n  [Retry {retry}/{MAX_RETRIES}] {error}. Retrying in {backoff:.1f}s...", flush=True)
                time.sleep(backoff)
                error = None

        video_id = response["id"]
        print(f"\n  [SUCCESS] Video uploaded! YouTube ID: {video_id} -> https://youtu.be/{video_id}")
        return video_id

    def set_thumbnail(self, video_id: str, thumbnail_path: Path) -> bool:
        """Upload and bind custom thumbnail image to video."""
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload

        service = self.get_service()
        mimetype = "image/png" if thumbnail_path.suffix.lower() == ".png" else "image/jpeg"
        media = MediaFileUpload(str(thumbnail_path), mimetype=mimetype)

        print(f"  Uploading thumbnail: {thumbnail_path.name}...", end="", flush=True)
        try:
            service.thumbnails().set(videoId=video_id, media_body=media).execute()
            print(" [OK]")
            return True
        except HttpError as exc:
            if exc.resp.status == 403:
                print(" [WARNING: Channel must be phone-verified for custom thumbnails]")
                _log.warning("Could not set thumbnail: channel may need phone verification for custom thumbnails.")
            else:
                print(f" [FAILED: {exc}]")
                _log.warning("Setting thumbnail failed: %s", exc)
            return False

    def load_upload_state(self) -> dict[str, Any]:
        """Load history of previously uploaded chapters."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save_upload_record(self, key: str, record: dict[str, Any]):
        """Append an upload entry to data/youtube_uploads.json."""
        state = self.load_upload_state()
        state[key] = record
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def upload_package(
        self,
        package_dir: Path,
        key: str,
        privacy_status: str = "unlisted",
        publish_at: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Upload a package directory (video + metadata + thumbnail)."""
        state = self.load_upload_state()
        if not force and key in state:
            existing = state[key]
            print(f"[SKIP] {key} already uploaded: {existing.get('url')} on {existing.get('uploaded_at')}")
            return existing

        meta = find_package_assets(package_dir)
        video_id = self.upload_video(meta, privacy_status=privacy_status, publish_at=publish_at)

        thumb_ok = False
        if meta.thumbnail_path and meta.thumbnail_path.exists():
            thumb_ok = self.set_thumbnail(video_id, meta.thumbnail_path)

        record = {
            "key": key,
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}",
            "title": meta.title,
            "thumbnail_uploaded": thumb_ok,
            "privacy": privacy_status,
            "published_at": publish_at,
            "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "video_file": meta.video_path.name,
        }
        self.save_upload_record(key, record)
        return record


def upload_package(
    package_dir: Path,
    key: str,
    privacy_status: str = "unlisted",
    publish_at: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    uploader = YouTubeUploader()
    return uploader.upload_package(
        package_dir=package_dir,
        key=key,
        privacy_status=privacy_status,
        publish_at=publish_at,
        force=force,
    )
