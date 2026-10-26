import json
import urllib.parse
import urllib.request

tokens = json.loads(open(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json", encoding="utf-8").read())
token = tokens["accounts"]["default"]["accessToken"]

q = "'1XLaH-NxhXwRrOdfHaOpEQNniNBcvE6OE' in parents and trashed = false"
url = "https://www.googleapis.com/drive/v3/files?q=" + urllib.parse.quote(q)
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    print("Contents of SSS_Class_Revival_Hunter_Panels:")
    for f in res.get("files", [])[:15]:
        print(f"  {f['name']} ({f['mimeType']})")
