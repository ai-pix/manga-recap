"""Automatically update the YouTube video title and description once uploaded."""

import time
import json
from pathlib import Path
from manga_recap.stages.s7_publish.youtube import YouTubeUploader, parse_metadata_file

def update_metadata():
    uploader = YouTubeUploader()
    meta_path = Path("data/export/revival_hunter_movie_package/metadata.txt")
    meta_dict = parse_metadata_file(meta_path)
    
    print("Waiting for video upload to complete and record video_id...")
    video_id = None
    for _ in range(120): # wait up to 60 minutes
        state = uploader.load_upload_state()
        rec = state.get("revival_hunter_4hour_movie")
        if rec and rec.get("video_id"):
            video_id = rec["video_id"]
            break
        time.sleep(15)
        
    if not video_id:
        print("Video ID not found in upload state.")
        return

    print(f"Found uploaded video_id: {video_id}. Updating snippet...")
    service = uploader.get_service()
    
    # Update snippet with sanitized title and description
    body = {
        "id": video_id,
        "snippet": {
            "title": meta_dict["title"],
            "description": meta_dict["description"],
            "tags": meta_dict["tags"],
            "categoryId": "24"
        }
    }
    res = service.videos().update(part="snippet", body=body).execute()
    print("SUCCESS: Video title & description updated cleanly on YouTube!")
    print(f"New Title: {res['snippet']['title']}")
    print(f"URL: https://youtu.be/{video_id}")

if __name__ == "__main__":
    update_metadata()
