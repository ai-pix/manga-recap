"""Publish and update uploaded Overgeared movie on YouTube with metadata, thumbnail, and public status."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.stages.s7_publish.youtube import (  # noqa: E402
    YouTubeUploader,
    parse_metadata_file,
)


def get_authenticated_service():
    """Ensure a valid YouTube API service or trigger OAuth browser login."""
    uploader = YouTubeUploader()
    token_path = uploader.token_path
    secrets_path = uploader.credentials_path

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube",
    ]

    creds = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            print("=" * 70, flush=True)
            print("OPENING BROWSER FOR YOUTUBE OAUTH AUTHORIZATION...", flush=True)
            print("=" * 70, flush=True)
            from google_auth_oauthlib.flow import InstalledAppFlow

            class AuthFlow(InstalledAppFlow):
                def authorization_url(self, **kwargs):
                    url, state = super().authorization_url(**kwargs)
                    (REPO_ROOT / "data" / "youtube_auth_url.txt").write_text(url, encoding="utf-8")
                    print(f"\nAUTH_URL: {url}\n", flush=True)
                    return url, state

            flow = AuthFlow.from_client_secrets_file(
                str(secrets_path),
                scopes=SCOPES,
            )
            prompt = (
                "\n" + "=" * 70 + "\n"
                "PLEASE VISIT THIS URL TO AUTHORIZE IF BROWSER DOES NOT OPEN:\n\n"
                "{url}\n\n"
                "=" * 70 + "\n"
            )
            creds = flow.run_local_server(
                port=8080,
                open_browser=True,
                authorization_prompt_message=prompt,
                success_message="Authorization successful! You can close this browser tab.",
            )
            token_path.write_text(creds.to_json(), encoding="utf-8")
            print("[SUCCESS] New YouTube OAuth token saved!", flush=True)

    return build("youtube", "v3", credentials=creds)


def find_target_video(service, hint: str = "overgeared") -> str | None:
    """Find the target video among recent uploads (checking uploads playlist and search)."""
    channels = service.channels().list(mine=True, part="contentDetails").execute()
    if not channels.get("items"):
        return None
    uploads_id = channels["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    items = service.playlistItems().list(playlistId=uploads_id, part="snippet,status", maxResults=20).execute()

    print("\nRecent channel uploads:", flush=True)
    candidates = []
    for item in items.get("items", []):
        snippet = item.get("snippet", {})
        vid = snippet.get("resourceId", {}).get("videoId")
        title = snippet.get("title", "")
        status = item.get("status", {}).get("privacyStatus", "unknown")
        print(f"  - [{status.upper()}] {vid}: {title}", flush=True)
        candidates.append((vid, title, status))

    # 1. Match title containing hint (e.g. "overgeared")
    for vid, title, _status in candidates:
        if hint.lower() in title.lower():
            print(f"-> Selected video by title match '{hint}': {vid} ({title})", flush=True)
            return vid

    # 2. Look for any unlisted or private video
    for vid, title, status in candidates:
        if status in ("unlisted", "private"):
            print(f"-> Selected unlisted/private video: {vid} ({title})", flush=True)
            return vid

    # 3. Fallback to latest item
    if candidates:
        latest_vid, latest_title, _ = candidates[0]
        print(f"-> Fallback to latest video: {latest_vid} ({latest_title})", flush=True)
        return latest_vid

    return None


def main():
    parser = argparse.ArgumentParser(description="Publish Overgeared video on YouTube")
    parser.add_argument("--video-id", type=str, help="YouTube Video ID or full URL")
    parser.add_argument("--thumbnail", type=str, default="data/export/overgeared_movie_package/thumbnail.jpg")
    parser.add_argument("--metadata", type=str, default="data/export/overgeared_movie_package/metadata.txt")
    parser.add_argument("--public", action="store_true", default=True, help="Set privacy status to public")
    args = parser.parse_args()

    meta_path = Path(args.metadata)
    if not meta_path.exists():
        print(f"Error: Metadata file not found at {meta_path}", flush=True)
        return 1

    meta_dict = parse_metadata_file(meta_path)
    thumb_path = Path(args.thumbnail)

    service = get_authenticated_service()

    vid = args.video_id
    if vid:
        if "youtu.be/" in vid:
            vid = vid.split("youtu.be/")[1].split("?")[0]
        elif "v=" in vid:
            vid = vid.split("v=")[1].split("&")[0]
    else:
        print("Searching for uploaded video on channel...", flush=True)
        vid = find_target_video(service, hint="overgeared")

    if not vid:
        print("ERROR: Could not automatically detect video ID. Please pass --video-id <ID>", flush=True)
        return 1

    print(f"\nTarget YouTube Video ID: {vid}", flush=True)
    print(f"Applying Title: {meta_dict['title']}", flush=True)
    print("Applying Description with full 30-chapter timestamps...", flush=True)
    print(f"Applying {len(meta_dict['tags'])} tags...", flush=True)

    # First fetch existing video details to check current status
    existing = service.videos().list(id=vid, part="snippet,status").execute()
    existing_status = "unknown"
    if existing.get("items"):
        existing_status = existing["items"][0].get("status", {}).get("privacyStatus", "unknown")
        print(f"Current Video Privacy Status: {existing_status}", flush=True)

    # Update snippet (title, description, tags) and status
    body = {
        "id": vid,
        "snippet": {
            "title": meta_dict["title"],
            "description": meta_dict["description"],
            "tags": meta_dict["tags"],
            "categoryId": "24",  # Entertainment
        },
    }
    if args.public:
        body["status"] = {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False,
        }

    res = service.videos().update(part="snippet,status" if args.public else "snippet", body=body).execute()
    print("\n[SUCCESS] Video snippet & public status updated!", flush=True)
    print(f"New Title: {res['snippet']['title']}", flush=True)
    print(f"New Status: {res.get('status', {}).get('privacyStatus', 'public')}", flush=True)

    # Set thumbnail
    if thumb_path.exists():
        print(f"\nUploading thumbnail from: {thumb_path} ({thumb_path.stat().st_size / 1024:.1f} KB)...", flush=True)
        from googleapiclient.http import MediaFileUpload

        service.thumbnails().set(
            videoId=vid,
            media_body=MediaFileUpload(str(thumb_path), mimetype="image/jpeg"),
        ).execute()
        print("[SUCCESS] Thumbnail uploaded and attached to video!", flush=True)

    print("\n" + "=" * 70, flush=True)
    print("OVERGEARED MOVIE IS NOW PUBLIC & LIVE:", flush=True)
    print(f"https://youtu.be/{vid}", flush=True)
    print("=" * 70, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
