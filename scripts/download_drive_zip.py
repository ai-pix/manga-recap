import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLIENT_SECRETS_PATH = REPO_ROOT / "client_secrets.json"
TOKENS_PATH = Path(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json")

tokens = json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
refresh_token = tokens["accounts"]["default"]["refreshToken"]
client_info = json.loads(CLIENT_SECRETS_PATH.read_text(encoding="utf-8"))
installed = client_info.get("installed", client_info.get("web", {}))

params = urllib.parse.urlencode({
    "client_id": installed["client_id"],
    "client_secret": installed["client_secret"],
    "refresh_token": refresh_token,
    "grant_type": "refresh_token",
}).encode("utf-8")

req = urllib.request.Request("https://oauth2.googleapis.com/token", data=params)
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read().decode("utf-8"))["access_token"]

file_id = "1z_QZ0qQofocVO47Xhhrtdw90jVQ9atKt"
dst_path = REPO_ROOT / "data" / "downloads" / "new-series-ch01-ch30-organised.zip"
dst_path.parent.mkdir(parents=True, exist_ok=True)

print(f"Downloading {file_id} to {dst_path}...")
url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
dl_req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})

t0 = time.time()
with urllib.request.urlopen(dl_req) as resp, open(dst_path, "wb") as out_f:
    total_size = int(resp.headers.get("Content-Length", 0))
    downloaded = 0
    chunk_size = 1024 * 1024 * 4  # 4MB chunks
    while True:
        chunk = resp.read(chunk_size)
        if not chunk:
            break
        out_f.write(chunk)
        downloaded += len(chunk)
        if total_size > 0:
            pct = (downloaded / total_size) * 100
            sys.stdout.write(f"\rDownloaded {downloaded / (1024*1024):.1f}/{total_size / (1024*1024):.1f} MB ({pct:.1f}%)")
        else:
            sys.stdout.write(f"\rDownloaded {downloaded / (1024*1024):.1f} MB")
        sys.stdout.flush()

print(f"\nDownload finished in {time.time() - t0:.1f}s!")
print(f"File size on disk: {dst_path.stat().st_size / (1024*1024):.2f} MB")
