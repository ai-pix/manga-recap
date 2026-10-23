import json
from pathlib import Path

import httpx

content_path = Path(r"C:\Users\ravih\.gemini\antigravity-cli\brain\59794e4f-3eb2-4993-ba8a-27f7bd85692e\.system_generated\steps\1853\content.md")
content = content_path.read_text(encoding="utf-8", errors="ignore")

idx = content.find("var ytInitialData =")
end_idx = content.find(";</script>", idx)
data = json.loads(content[idx + len("var ytInitialData ="):end_idx].strip())

thumbs = []
def find_thumbs(obj):
    if isinstance(obj, dict):
        if "lockupViewModel" in obj:
            lm = obj["lockupViewModel"]
            meta = lm.get("metadata", {}).get("lockupMetadataViewModel", {})
            title = meta.get("title", {}).get("content", "")

            # thumbnail
            cimg = lm.get("contentImage", {}).get("collectionThumbnailViewModel", {}) or lm.get("contentImage", {}).get("thumbnailViewModel", {})
            sources = cimg.get("image", {}).get("sources", [])
            if sources:
                best_url = sources[-1].get("url", "")
                thumbs.append((title, best_url))
        for k, v in obj.items():
            find_thumbs(v)
    elif isinstance(obj, list):
        for item in obj:
            find_thumbs(item)

find_thumbs(data)
print(f"Found {len(thumbs)} thumbnails with titles:")

out_dir = Path("build/sample_thumbs")
out_dir.mkdir(parents=True, exist_ok=True)

with httpx.Client(timeout=15.0) as client:
    for i, (title, url) in enumerate(thumbs[:5]):
        print(f"{i+1}. {title[:50]} -> {url}")
        res = client.get(url)
        if res.status_code == 200:
            thumb_file = out_dir / f"thumb_{i+1}.jpg"
            thumb_file.write_bytes(res.content)
            print(f"   Saved {thumb_file.name} ({len(res.content)//1024} KB)")
