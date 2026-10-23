"""Upload zip archive to Google Drive using OAuth with auto-refresh/reauth.

- Supports CLI arguments: --archive and --folder
- Resumable chunked upload with progress tracking
- Sets public read permission ('anyone' with link)
- Returns webViewLink and direct download link
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = Path(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json")
LOCAL_TOKEN_PATH = REPO_ROOT / "config" / "gdrive_token.json"
CLIENT_SECRETS_PATH = REPO_ROOT / "client_secrets.json"

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]


def get_drive_service():
    if not CLIENT_SECRETS_PATH.exists():
        raise FileNotFoundError(f"Client secrets not found at {CLIENT_SECRETS_PATH}")

    creds = None

    # 1. Try local config/gdrive_token.json
    if LOCAL_TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(LOCAL_TOKEN_PATH), SCOPES)
        except Exception:
            creds = None

    # 2. Try MCP tokens.json
    if not creds and TOKEN_PATH.exists():
        try:
            with open(TOKEN_PATH, encoding="utf-8") as f:
                tok_data = json.load(f)
            acc = tok_data.get("accounts", {}).get("default")
            if acc:
                with open(CLIENT_SECRETS_PATH, encoding="utf-8") as cs_f:
                    cs = json.load(cs_f)["installed"]
                creds = Credentials(
                    token=acc.get("accessToken"),
                    refresh_token=acc.get("refreshToken"),
                    token_uri=cs["token_uri"],
                    client_id=cs["client_id"],
                    client_secret=cs["client_secret"],
                    scopes=SCOPES,
                )
        except Exception:
            creds = None

    # 3. Proactively verify / refresh credentials
    if creds:
        try:
            creds.refresh(Request())
            print("Successfully verified/refreshed Google Drive token.")
        except Exception as e:
            print(f"Stored token invalid or expired ({e}). Starting browser authorization...")
            creds = None

    # 4. If invalid or missing, run interactive flow
    if not creds or not creds.valid:
        print("\n" + "=" * 65)
        print("STARTING GOOGLE DRIVE OAUTH AUTHORIZATION")
        print("=" * 65)
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CLIENT_SECRETS_PATH),
            scopes=SCOPES,
        )
        creds = flow.run_local_server(
            port=8080,
            open_browser=True,
            authorization_prompt_message=(
                "\n" + "=" * 65 + "\n"
                "PLEASE VISIT THIS URL IN YOUR BROWSER TO AUTHORIZE GOOGLE DRIVE:\n\n"
                "{url}\n\n"
                "=" * 65 + "\nWaiting for authorization...\n"
            ),
            success_message="Authorization successful! You can close this browser tab.",
        )

        # Save refreshed creds to both token locations
        LOCAL_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")

        mcp_data = {
            "version": 2,
            "accounts": {
                "default": {
                    "alias": "default",
                    "email": "user",
                    "accessToken": creds.token,
                    "refreshToken": creds.refresh_token,
                    "scope": " ".join(SCOPES),
                    "tokenType": "Bearer",
                    "expiryDate": int(creds.expiry.timestamp() * 1000) if creds.expiry else None,
                    "isDefault": True,
                }
            },
            "defaultAccount": "default",
        }
        TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_PATH.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")
        print("[SUCCESS] New Google Drive token saved.\n")

    return build("drive", "v3", credentials=creds)


def get_or_create_folder(service, folder_name: str) -> str:
    query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        folder_id = files[0]["id"]
        print(f"Found existing Google Drive folder '{folder_name}' (ID: {folder_id})")
        return folder_id

    file_metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    folder = service.files().create(body=file_metadata, fields="id").execute()
    folder_id = folder.get("id")
    print(f"Created new Google Drive folder '{folder_name}' (ID: {folder_id})")
    return folder_id


def upload_archive(archive_path: Path | str, folder_name: str = "SSS_Class_Revival_Hunter_Panels") -> dict:
    archive = Path(archive_path)
    if not archive.exists():
        print(f"Error: Archive {archive} does not exist.", file=sys.stderr)
        sys.exit(1)

    file_size = archive.stat().st_size
    file_size_mb = file_size / (1024 * 1024)
    print("Connecting to Google Drive...")
    service = get_drive_service()

    # Verify identity & quota
    about = service.about().get(fields="user, storageQuota").execute()
    user_email = about.get("user", {}).get("emailAddress", "Unknown")
    print(f"Connected as: {user_email}")

    folder_id = get_or_create_folder(service, folder_name)

    file_name = archive.name
    file_metadata = {
        "name": file_name,
        "parents": [folder_id],
    }

    # 10 MB chunks for smooth resumable upload
    chunk_size = 10 * 1024 * 1024
    media = MediaFileUpload(
        str(archive),
        mimetype="application/zip",
        resumable=True,
        chunksize=chunk_size,
    )

    print(f"Uploading {file_name} ({file_size_mb:.2f} MB) to folder '{folder_name}'...")
    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink, webContentLink",
    )

    t0 = time.time()
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            progress = status.progress() * 100
            elapsed = time.time() - t0
            uploaded_mb = status.resumable_progress / (1024 * 1024)
            speed = uploaded_mb / max(elapsed, 0.001)
            print(
                f"\r[{progress:5.1f}%] Uploaded {uploaded_mb:.1f} / {file_size_mb:.1f} MB ({speed:.2f} MB/s)",
                end="",
                flush=True,
            )

    print("\nUpload complete! Setting file permissions to public read...")
    file_id = response.get("id")

    # Share with anyone with link
    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    # Re-fetch webViewLink
    file_info = service.files().get(
        fileId=file_id,
        fields="id, name, webViewLink, webContentLink",
    ).execute()

    print("\n" + "=" * 60)
    print("SUCCESSFULLY UPLOADED TO GOOGLE DRIVE!")
    print(f"File Name:     {file_info.get('name')}")
    print(f"File ID:       {file_id}")
    print(f"View Link:     {file_info.get('webViewLink')}")
    print(f"Download Link: {file_info.get('webContentLink')}")
    print("=" * 60)
    return file_info


def main():
    parser = argparse.ArgumentParser(description="Upload zip archive to Google Drive")
    parser.add_argument(
        "--archive",
        default="zips/sss_class_revival_hunter_ch01_ch40_panels.zip",
        help="Path to zip archive",
    )
    parser.add_argument(
        "--folder",
        default="SSS_Class_Revival_Hunter_Panels",
        help="Google Drive destination folder name",
    )
    args = parser.parse_args()
    upload_archive(archive_path=args.archive, folder_name=args.folder)


if __name__ == "__main__":
    main()
