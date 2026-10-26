"""Manually exchange an authorization URL or code from the browser into youtube_token.json."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/exchange_oauth_code.py <REDIRECT_URL_OR_CODE>")
        return 1

    user_input = sys.argv[1].strip()
    secrets_path = REPO_ROOT / "client_secrets.json"
    token_path = REPO_ROOT / "config" / "youtube_token.json"

    flow = InstalledAppFlow.from_client_secrets_file(
        str(secrets_path),
        scopes=SCOPES,
        redirect_uri="http://localhost:8080/",
    )

    if user_input.startswith("http"):
        # Fix http -> https for oauthlib
        auth_response = user_input.replace("http://", "https://")
        flow.fetch_token(authorization_response=auth_response)
    else:
        flow.fetch_token(code=user_input)

    creds = flow.credentials
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"[SUCCESS] OAuth token saved to {token_path}!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
