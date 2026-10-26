import json
from pathlib import Path

from PIL import Image

idx = json.loads(Path("data/chapters/overgeared/ch01/02_panels/panel_index.json").read_text(encoding="utf-8"))
for p in idx["panels"]:
    if p["panel_id"] in ("panel_0004", "panel_0007", "panel_0008", "panel_0010", "panel_0017", "panel_0025", "panel_0045", "panel_0047", "panel_0059", "panel_0069", "panel_0087"):
        img_p = Path("data/chapters/overgeared/ch01") / p["image_path"]
        im = Image.open(img_p)
        print(f"{p['panel_id']}: size={im.size}, bbox={p['bbox']}")
