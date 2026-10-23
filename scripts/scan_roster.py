"""List panels whose text contradicts the series character roster.

Reads the raw part files rather than a merged chapter, so it can be run while
batches are still landing. `check_chapter.py` runs the same rule against the
merged file; this is the part-file view used mid-flight.

Usage:
    python scripts/scan_roster.py ch005_5
    python scripts/scan_roster.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from manga_recap.core.paths import repo_path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_chapter import (  # noqa: E402
    FRINGE_MARKERS,
    LIGHT_HAIR_RE,
    NOT_SHUN,
    _entry_text,
)


def main() -> int:
    chapters = sys.argv[1:]
    roots = sorted((repo_path("data") / "chapters").glob("ch*"))
    found = 0
    for chapter in roots:
        if chapters and chapter.name not in chapters:
            continue
        for part in sorted((chapter / "_describe_parts").glob("*.json")):
            try:
                payload = json.loads(part.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(f"{part}: not valid JSON ({exc})")
                continue
            panels = payload["panels"] if isinstance(payload, dict) else payload
            for panel in panels:
                where = f"{chapter.name}/{part.name} {panel['panel_id']}"
                cast = {str(n).strip().lower() for n in panel.get("characters", [])}
                panel_text = f"{panel.get('action', '')} {panel.get('expression', '')}".lower()
                for entry in panel.get("body_language") or []:
                    name = str(entry.get("character", "")).strip().lower()
                    text = _entry_text(entry)
                    if name == "shun" and LIGHT_HAIR_RE.search(text):
                        print(f"{where}: `shun` described with light hair")
                        found += 1
                    if name in NOT_SHUN and any(m in text for m in FRINGE_MARKERS):
                        print(f"{where}: `{entry.get('character')}` wears the eyes-out fringe")
                        found += 1
                if cast == {"shun"} and LIGHT_HAIR_RE.search(panel_text):
                    print(f"{where}: Shun alone in frame but described light-haired")
                    found += 1
    print(f"total suspects: {found}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
