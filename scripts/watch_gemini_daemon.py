"""24/7 background watcher for @Gemini mentions in Google Sheet chat.

Zero LLM tokens while idling.
Polls every 15s.
Tracks strictly ascending sheet row numbers so blank or out-of-order IDs never cause duplicate alerts.
Filters out courtesy pass-through tags (e.g., '@Gemini @Foxy @Aria — no action on this message').
Exits immediately upon detecting a genuine @Gemini mention to trigger reactive agent wake-up.
"""

import json
import time
import sys
import requests
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SHEET_ID = "1sHI3qIU9y6Aiznfo9_d8Ari8Bu0WWqW6UHzNhsSnfxA"
SECRET_PATH = Path(r"C:\Users\ravih\Downloads\client_secret_532039068995-k60ntg8pgpnr1nn04asb31r8q9uisp78.apps.googleusercontent.com.json")
TOKENS_PATH = Path(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json")
STATE_FILE = Path(r"scripts\gemini_watch_state.json")
ALERTS_LOG = Path(r"scripts\alerts.log")

def get_access_token():
    with open(SECRET_PATH) as f:
        secret_data = json.load(f)["installed"]
    with open(TOKENS_PATH) as f:
        token_data = json.load(f)
    
    refresh_token = token_data["accounts"]["default"]["refreshToken"]
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": secret_data["client_id"],
        "client_secret": secret_data["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }, timeout=15)
    return resp.json()["access_token"]

def load_last_seen_row():
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text())
            return data.get("last_seen_row") or data.get("last_seen_id", 517)
        except Exception:
            pass
    return 517

def save_last_seen_row(row_idx):
    STATE_FILE.write_text(json.dumps({"last_seen_row": row_idx}))

def is_actionable_gemini_mention(message: str) -> bool:
    """Return True only if @Gemini is mentioned outside of courtesy 'no action' lines."""
    for line in message.splitlines():
        if "@gemini" in line.lower():
            if "no action" in line.lower():
                continue
            return True
    return False

def poll_for_mentions():
    last_seen_row = load_last_seen_row()
    print(f"Watcher started for @Gemini. Baseline row: {last_seen_row}. Polling every 15s...", flush=True)

    token = None
    token_time = 0

    while True:
        try:
            # Refresh token every 45 mins
            if token is None or time.time() - token_time > 2700:
                token = get_access_token()
                token_time = time.time()

            headers = {"Authorization": f"Bearer {token}"}
            # Sliding tail window based on last_seen_row
            start_row = max(2, last_seen_row - 2)
            end_row = last_seen_row + 50
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/chat!A{start_row}:G{end_row}"
            resp = requests.get(url, headers=headers, timeout=15)
            
            if resp.status_code == 200:
                values = resp.json().get("values", [])
                for offset, row in enumerate(values):
                    current_row = start_row + offset
                    while len(row) < 7:
                        row.append("")
                    
                    author = row[2].strip()
                    message = row[3].strip()
                    
                    if not author and not message:
                        continue
                    
                    if current_row > last_seen_row:
                        last_seen_row = current_row
                        save_last_seen_row(last_seen_row)
                        
                        # Check for actionable @Gemini mention (excluding self)
                        if author.lower() != "gemini" and is_actionable_gemini_mention(message):
                            msg_id = row[0].strip() or f"row-{current_row}"
                            alert_line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] PING! @Gemini mentioned by {author} (msg #{msg_id}, row {current_row}): {message}\n"
                            print(f"\n{'!'*60}\n{alert_line.strip()}\n{'!'*60}", flush=True)
                            with open(ALERTS_LOG, "a", encoding="utf-8") as af:
                                af.write(alert_line)
                            # Exit so background task completes and triggers instant reactive wakeup
                            sys.exit(0)
            elif resp.status_code == 401:
                token = None  # Force re-auth on next loop
            else:
                print(f"[warn] Sheet poll returned status {resp.status_code}", flush=True)

        except Exception as e:
            print(f"[warn] Poll error: {e}", flush=True)

        time.sleep(15)

if __name__ == "__main__":
    poll_for_mentions()
