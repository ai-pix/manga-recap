"""Report which stage-2 batches are still missing, per chapter.

`merge_descriptions.py` refuses to write a partial chapter, which is right, but
it only tells you about one chapter at a time. This lists every chapter and
every absent batch in one pass so a wave can be relaunched in a single step.

Usage:
    python scripts/part_status.py
    python scripts/part_status.py ch003 ch007
"""

from __future__ import annotations

import sys

from manga_recap.core.paths import repo_path

BATCH_SIZE = 15
CHAPTERS = (
    "ch003", "ch004", "ch005", "ch005_5", "ch06", "ch007", "ch008",
    "ch009", "ch010", "ch011", "ch012", "ch013", "ch014", "ch015",
)


def main() -> int:
    wanted = set(sys.argv[1:]) or set(CHAPTERS)
    total_missing = 0
    for chapter_id in CHAPTERS:
        if chapter_id not in wanted:
            continue
        root = repo_path("data") / "chapters" / chapter_id
        index_path = root / "02_panels" / "panel_index.json"
        if not index_path.exists():
            print(f"{chapter_id}: no panel_index.json")
            continue
        panel_count = int(index_path.read_text(encoding="utf-8").split('"panel_count":')[1].split(",")[0])
        expected = (panel_count + BATCH_SIZE - 1) // BATCH_SIZE
        parts = root / "_describe_parts"
        have = {p.stem for p in parts.glob("part_*.json")} if parts.is_dir() else set()
        missing = [f"part_{n:02d}" for n in range(1, expected + 1) if f"part_{n:02d}" not in have]
        surplus = sorted(have - {f"part_{n:02d}" for n in range(1, expected + 1)})
        total_missing += len(missing)
        status = "COMPLETE" if not missing else f"missing {len(missing)}"
        print(
            f"{chapter_id:8} {status:14} panels={panel_count:3} "
            f"batches={expected:2} have={len(have):2}"
        )
        if missing:
            print(f"         -> {', '.join(missing)}")
        if surplus:
            print(f"         -> UNEXPECTED FILES: {', '.join(surplus)}")
    print(f"total missing batches: {total_missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
