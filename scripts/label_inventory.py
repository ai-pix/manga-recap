"""Inventory every character label across the chapters, for one reconciliation pass.

Batch workers describe disjoint ranges of a chapter in isolation, so they cannot
see each other's labels. The result is that one person ends up as
`smith_girl` in one range, `light_hair_girl` in the next, and `magi` in a third.
That is invisible to the schema and to the dialogue gate, and it is why the
narration would call three different names for one character.

This prints the whole cross-chapter picture in a few hundred lines, which is what
a single reconciliation worker needs in order to produce a rename map that
`merge_descriptions.py --labels` then applies mechanically.

Usage:
    python scripts/label_inventory.py
    python scripts/label_inventory.py --json config/label_map.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter

from manga_recap.core.paths import repo_path

CHAPTERS = (
    "ch003", "ch004", "ch005", "ch005_5", "ch06", "ch007", "ch008",
    "ch009", "ch010", "ch011", "ch012", "ch013", "ch014", "ch015",
)


def collect(chapters: tuple[str, ...]) -> tuple[dict[str, Counter], dict[str, dict]]:
    usage: dict[str, Counter] = {}
    where: dict[str, dict] = {}
    for chapter_id in chapters:
        path = repo_path("data") / "chapters" / chapter_id / "03_descriptions.json"
        if not path.exists():
            parts = repo_path("data") / "chapters" / chapter_id / "_describe_parts"
            if not parts.is_dir():
                continue
            per_chapter: Counter = Counter()
            for part in sorted(parts.glob("*.json")):
                try:
                    payload = json.loads(part.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                panels = payload["panels"] if isinstance(payload, dict) else payload
                for panel in panels:
                    per_chapter.update(panel.get("characters") or [])
            counts = per_chapter
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            counts = Counter()
            for panel in data["panels"]:
                counts.update(panel.get("characters") or [])
        for label, count in counts.items():
            usage.setdefault(label, Counter())[chapter_id] = count
            where.setdefault(label, {})
    return usage, where


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=None, help="Write the inventory as JSON here.")
    args = parser.parse_args()

    usage, _ = collect(CHAPTERS)
    roster = {
        "shun", "miu", "magi", "onee_chan", "takumi", "shop_clerk", "stall_merchant",
    }
    print(f"{len(usage)} distinct labels across {len(CHAPTERS)} chapters\n")
    print("--- established roster ---")
    for label in sorted(roster):
        if label in usage:
            chapters = ", ".join(f"{c}:{n}" for c, n in sorted(usage[label].items()))
            print(f"  {label:28} {chapters}")
    print("\n--- new / drifting labels (all) ---")
    for label in sorted(set(usage) - roster):
        chapters = ", ".join(f"{c}:{n}" for c, n in sorted(usage[label].items()))
        print(f"  {label:28} {chapters}")

    if args.json:
        payload = {
            label: {chapter: count for chapter, count in sorted(counts.items())}
            for label, counts in sorted(usage.items())
        }
        out = repo_path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
