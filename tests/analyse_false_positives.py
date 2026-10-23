"""Analyse the chapter's detections for fragment and duplicate false positives.

Reports, per page, any detection that looks like a border fragment rather than a
panel: mostly contained inside a larger detection, implausibly thin, or too small
to be worth narrating.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, "src")

from manga_recap.core.schema import PanelIndexFile, load_model

INDEX = Path("data/chapters/ch01/02_panels/panel_index.json")

CONTAINED = 0.60   # share of a small box that falls inside a bigger one
AREA_FLOOR = 0.015  # share of the page a panel must cover
MAX_THINNESS = 0.30  # width/height below this is a sliver, not a panel


def intersection(a, b) -> int:
    return max(0, min(a.x2, b.x2) - max(a.x1, b.x1)) * max(0, min(a.y2, b.y2) - max(a.y1, b.y1))


def analyse(page_height_is_landscape: bool = False):
    index = load_model(INDEX, PanelIndexFile)
    by_page: dict[int, list] = {}
    for panel in index.ordered():
        by_page.setdefault(panel.page_number, []).append(panel)

    suspects = []
    for page_number, panels in sorted(by_page.items()):
        page_area = panels[0].page_width * panels[0].page_height
        for panel in panels:
            reasons = []
            box = panel.bbox
            area_ratio = box.area / page_area

            if area_ratio < AREA_FLOOR:
                reasons.append(f"tiny {area_ratio:.1%} of page")

            thinness = box.width / box.height if box.height else 1.0
            if thinness < MAX_THINNESS:
                reasons.append(f"thin w/h={thinness:.2f}")

            for other in panels:
                if other.panel_id == panel.panel_id:
                    continue
                if other.bbox.area <= box.area:
                    continue
                shared = intersection(box, other.bbox)
                if shared / box.area >= CONTAINED:
                    reasons.append(f"{shared / box.area:.0%} inside {other.panel_id}")
                    break

            if reasons:
                suspects.append((page_number, panel, reasons))

    return index, suspects


def main() -> int:
    index, suspects = analyse()
    print(f"{index.panel_count} panels across {index.page_count} pages")
    print(f"suspect detections: {len(suspects)}\n")
    for page_number, panel, reasons in suspects:
        box = panel.bbox
        print(
            f"p{page_number:02d} #{panel.reading_order:3d} {panel.panel_id}  "
            f"{box.width}x{box.height}  {'; '.join(reasons)}"
        )

    pages = sorted({p for p, _, _ in suspects})
    print(f"\naffected pages: {pages}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
