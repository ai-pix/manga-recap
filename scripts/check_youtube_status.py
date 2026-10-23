import json
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

TOKEN_FILE = Path("config/youtube_token.json")
if TOKEN_FILE.exists():
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE))
    yt = build("youtube", "v3", credentials=creds)

    vids = yt.videos().list(part="snippet,status,statistics", id="Rm0reT5PBtg,osF7thqyDPg").execute()
    for v in vids.get("items", []):
        vid_id = v["id"]
        title = v["snippet"]["title"]
        privacy = v["status"]["privacyStatus"]
        upload_status = v["status"]["uploadStatus"]
        views = v.get("statistics", {}).get("viewCount", "0")
        likes = v.get("statistics", {}).get("likeCount", "0")
        comments = v.get("statistics", {}).get("commentCount", "0")
        print(f"[{vid_id}] {privacy.upper()} | Upload: {upload_status}")
        print(f"Title: {title}")
        print(f"Views: {views} | Likes: {likes} | Comments: {comments}")
        print("-" * 60)
