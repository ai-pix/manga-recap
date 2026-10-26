import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("TOP_TOOLS_AI_API_KEY")
base_url = os.getenv("TOP_TOOLS_AI_BASE_URL", "https://top-tools-ai.com/api/v1")

# List all models
req = urllib.request.Request(f"{base_url}/models", headers={
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    models = [m.get("id") for m in res.get("data", [])]
    print("All models:", models)

# Test chat completions with a few models
chat_url = f"{base_url}/chat/completions"

for model in ["DeepSeek-V4-Flash", "MiMo-V2.5", "GLM-5.2", "Step-5-Preview"]:
    if model not in models:
        continue
    print(f"\n--- Testing Chat with {model} ---")
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with 'Hello World!' and nothing else."}
        ],
        "max_tokens": 50,
        "temperature": 0.1
    }
    body = json.dumps(payload).encode("utf-8")
    creq = urllib.request.Request(chat_url, data=body, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(creq, timeout=20) as cresp:
            cres = json.loads(cresp.read().decode("utf-8"))
            msg = cres.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"Success! Response: {msg.strip()}")
            break
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="ignore")
        print(f"HTTP Error {e.code}: {err}")
    except Exception as e:
        print(f"Error: {e}")
