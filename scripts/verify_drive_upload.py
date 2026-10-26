import json
import urllib.parse
import urllib.request

tokens = json.loads(open(r"C:\Users\ravih\.config\google-drive-mcp\tokens.json", encoding="utf-8").read())
token = tokens["accounts"]["default"]["accessToken"]

q = "'1QkwyhZh38gwAh6Gk_yNrJBnXpUZ9iOzZ' in parents and trashed = false"
url = "https://www.googleapis.com/drive/v3/files?pageSize=100&fields=files(id,name,mimeType)&q=" + urllib.parse.quote(q)
req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
with urllib.request.urlopen(req) as resp:
    res = json.loads(resp.read().decode("utf-8"))
    files = res.get("files", [])
    print(f"Total chapter folders in Overgeared_Manhwa: {len(files)}")
    for f in sorted(files, key=lambda x: x["name"])[:10]:
        print(f"  {f['name']} (ID: {f['id']})")
