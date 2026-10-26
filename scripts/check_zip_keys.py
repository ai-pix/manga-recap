import json
import zipfile
from pathlib import Path

zip_path = Path("data/downloads/new-series-ch01-ch30-organised.zip")
with zipfile.ZipFile(zip_path, "r") as z:
    for i in range(1, 31):
        ch_name = f"ch{i:02d}"
        json_name = f"organised/{ch_name}/{ch_name}.json"
        data = json.loads(z.read(json_name).decode("utf-8"))
        for p in data.get("panels", []):
            if "speech_bubbles" not in p:
                print(f"{ch_name} {p.get('panel_id')} missing speech_bubbles! Keys: {list(p.keys())}")
                break
