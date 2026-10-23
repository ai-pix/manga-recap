"""Google Drive OAuth re-authorization helper."""

import json
import os
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENT_SECRETS = REPO_ROOT / "client_secrets.json"
TOKEN_PATH = Path(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json")

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]


def main():
    if not CLIENT_SECRETS.exists():
        print(f"Error: {CLIENT_SECRETS} not found", file=sys.stderr)
        sys.exit(1)

    print("=" * 65)
    print("GOOGLE DRIVE OAUTH AUTHORIZATION")
    print("=" * 65)

    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRETS),
        scopes=SCOPES,
    )

    creds = flow.run_local_server(
        port=8080,
        open_browser=True,
        authorization_prompt_message=(
            "\n" + "=" * 65 + "\n"
            "PLEASE VISIT THIS URL IN YOUR BROWSER TO AUTHORIZE GOOGLE DRIVE:\n\n"
            "{url}\n\n"
            "=" * 65 + "\n"
            "Waiting for authorization...\n"
        ),
        success_message="Google Drive Authorization successful! You may close this tab.",
    )

    # Save to both token locations:
    # 1. MCP tokens.json
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
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
    TOKEN_PATH.write_text(json.dumps(mcp_data, indent=2), encoding="utf-8")

    # 2. Local config/gdrive_token.json
    local_tok = REPO_ROOT / "config" / "gdrive_token.json"
    local_tok.write_text(creds.to_json(), encoding="utf-8")

    print("\n[SUCCESS] Google Drive token authorized and saved successfully!")


if __name__ == "__main__":
    main()
