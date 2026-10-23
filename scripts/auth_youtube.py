"""One-time interactive YouTube OAuth authorization helper."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
]

def main():
    secrets_path = REPO_ROOT / "client_secrets.json"
    if not secrets_path.exists():
        print(f"Error: client_secrets.json not found at {secrets_path}")
        return 1

    token_path = REPO_ROOT / "config" / "youtube_token.json"
    token_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70, flush=True)
    print("STARTING YOUTUBE OAUTH AUTHENTICATION", flush=True)
    print("=" * 70, flush=True)

    flow = InstalledAppFlow.from_client_secrets_file(
        str(secrets_path),
        scopes=SCOPES,
    )

    prompt = (
        "\n" + "=" * 70 + "\n"
        "PLEASE VISIT THIS URL IN YOUR BROWSER TO AUTHORIZE:\n\n"
        "{url}\n\n"
        "=" * 70 + "\n"
        "Waiting for authorization...\n"
    )

    creds = flow.run_local_server(
        port=8080,
        open_browser=True,
        authorization_prompt_message=prompt,
        success_message="Authorization successful! You can close this browser tab.",
    )

    token_path.write_text(creds.to_json(), encoding="utf-8")
    print("\n[SUCCESS] Token saved to config/youtube_token.json", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())
