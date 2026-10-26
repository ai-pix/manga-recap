import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TOP_TOOLS_AI_API_KEY")
base_url = os.getenv("TOP_TOOLS_AI_BASE_URL", "https://top-tools-ai.com/api/v1")

# Pick a small panel image from ch01
panel_path = Path("data/chapters/overgeared/ch01/02_panels/panel_0001.webp")
if not panel_path.exists():
    print(f"File {panel_path} not found")
    exit(1)

img_b64 = base64.b64encode(panel_path.read_bytes()).decode("utf-8")
data_uri = f"data:image/webp;base64,{img_b64}"

chat_url = f"{base_url}/chat/completions"

models_to_test = [
    "DeepSeek-V4-Flash-Vision-Exp",
    "gpt-5.6-sol",
    "claude-opus-5",
    "Qwen-3.8-Max"
]

for model in models_to_test:
    print(f"\n--- Testing Vision with {model} ---")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe what is depicted in this manga/manhwa panel in 1-2 concise sentences."},
                    {"type": "image_url", "image_url": {"url": data_uri}}
                ]
            }
        ],
        "max_tokens": 100,
        "temperature": 0.2
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(chat_url, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            msg = res.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"Success with {model}!")
            print(f"Response: {msg.strip()}")
            break
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        print(f"HTTP Error {e.code} on {model}: {err}")
    except Exception as e:
        print(f"Error on {model}: {e}")
