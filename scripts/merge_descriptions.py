"""Merge per-part panel descriptions into a chapter's `03_descriptions.json`.

Stage 2 is done by many small vision agents, each of which writes one part file
holding a handful of panels. This script is the single place where those parts
become the artifact the rest of the pipeline reads.

It exists so the agents never have to get panel metadata right. `page_number`,
`reading_order`, `image_path` and `has_detected_text` are re-attached from the
panel index rather than trusted from a part file, because a vision agent has no
way to know them and a mis-keyed value silently corrupts reading order three
stages later. Unknown fields are dropped instead of rejected, so a stray comment
key in a part file cannot take the whole chapter down.

Usage:
    python scripts/merge_descriptions.py ch003
    python scripts/merge_descriptions.py ch003 --allow-missing
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from manga_recap.core.paths import repo_path
from manga_recap.core.schema import (
    BodyLanguageEntry,
    DescriptionFile,
    PanelDescription,
    PanelIndexFile,
    save_model,
)

PART_DIRNAME = "_describe_parts"
STRING_LIST_FIELDS = ("characters", "props", "sfx_text", "speech_bubbles")
BOOL_FIELDS = ("is_sfx_only", "is_color_splash", "is_credits_or_ad")
TEXT_FIELDS = ("setting", "action", "expression", "ambient_mood")


def chapter_dir(chapter_id: str) -> Path:
    return repo_path("data") / "chapters" / chapter_id


def load_index(chapter_id: str) -> PanelIndexFile:
    path = chapter_dir(chapter_id) / "02_panels" / "panel_index.json"
    return PanelIndexFile.model_validate(json.loads(path.read_text(encoding="utf-8")))


def read_parts(part_dir: Path) -> tuple[dict[str, dict], list[dict]]:
    """Read every part file into `{panel_id: record}` plus the label notes."""
    records: dict[str, dict] = {}
    new_labels: list[dict] = []
    if not part_dir.is_dir():
        return records, new_labels
    for part in sorted(part_dir.glob("*.json")):
        if part.name.startswith("_"):
            continue
        try:
            payload = json.loads(part.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"  part file {part.name} is not valid JSON: {exc}", file=sys.stderr)
            continue
        if isinstance(payload, list):
            payload = {"panels": payload}
        for raw in payload.get("panels") or []:
            panel_id = str(raw.get("panel_id", "")).strip()
            if not panel_id:
                continue
            records[panel_id] = raw
        for label in payload.get("new_labels") or []:
            if isinstance(label, dict):
                new_labels.append(label)
    return records, new_labels


def build_description(raw: dict, panel, renames: dict[str, str] | None = None) -> PanelDescription:  # noqa: ANN001 - pydantic model
    """Turn one part-file record into a validated `PanelDescription`."""
    renames = renames or {}

    def canon(name: str) -> str:
        return renames.get(name.strip(), name.strip())

    body_language = []
    for entry in raw.get("body_language") or []:
        if isinstance(entry, dict):
            body_language.append(
                BodyLanguageEntry(
                    character=canon(str(entry.get("character", ""))) or "unknown",
                    pose=str(entry.get("pose", "")).strip(),
                    action=str(entry.get("action", "")).strip(),
                    expression_detail=str(entry.get("expression_detail", "")).strip(),
                )
            )

    strings = {name: _as_list(raw.get(name)) for name in STRING_LIST_FIELDS}
    flags = {name: bool(raw.get(name, False)) for name in BOOL_FIELDS}
    texts = {name: str(raw.get(name, "") or "").strip() for name in TEXT_FIELDS}

    has_text = panel.has_text
    speech = strings["speech_bubbles"]
    sfx = strings["sfx_text"]
    source = str(raw.get("transcription_source", "") or "").strip()
    if source not in ("none", "panel", "text_crop"):
        source = "text_crop" if (has_text and (speech or sfx)) else "none"

    return PanelDescription(
        panel_id=panel.panel_id,
        page_number=panel.page_number,
        reading_order=panel.reading_order,
        image_path=panel.image_path,
        characters=strings["characters"],
        setting=texts["setting"],
        action=texts["action"] or "Undescribed panel.",
        expression=texts["expression"],
        body_language=body_language,
        props=strings["props"],
        sfx_text=sfx,
        speech_bubbles=speech,
        ambient_mood=texts["ambient_mood"],
        is_sfx_only=flags["is_sfx_only"],
        is_color_splash=flags["is_color_splash"],
        is_credits_or_ad=flags["is_credits_or_ad"],
        has_detected_text=has_text,
        transcription_source=source,
    )


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chapter_id")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Write a partial file covering only the panels that have parts.",
    )
    parser.add_argument("--part-dir", default=None)
    parser.add_argument(
        "--labels",
        default=None,
        help="JSON file mapping old character labels onto canonical ones, e.g. "
        '{"light_hair_girl": "magi"}. Applied to `characters` and to each '
        "`body_language` entry's `character`. Applied at merge time rather than "
        "by editing part files, so the rename is one reviewable step and is "
        "re-applied identically on every re-merge.",
    )
    args = parser.parse_args()

    renames: dict[str, str] = {}
    if args.labels:
        raw = json.loads(Path(args.labels).read_text(encoding="utf-8"))
        renames = {str(k).strip(): str(v).strip() for k, v in raw.items() if str(k).strip() != str(v).strip()}

    root = chapter_dir(args.chapter_id)
    index = load_index(args.chapter_id)
    part_dir = Path(args.part_dir) if args.part_dir else root / PART_DIRNAME
    records, new_labels = read_parts(part_dir)

    ordered = index.ordered()
    missing = [p.panel_id for p in ordered if p.panel_id not in records]
    extra = sorted(set(records) - {p.panel_id for p in ordered})
    if extra:
        print(f"  ignoring {len(extra)} record(s) not in the index: {extra[:5]}")

    if missing and not args.allow_missing:
        print(
            f"FAIL {args.chapter_id}: {len(missing)} of {index.panel_count} panels "
            f"have no part file. Missing: {missing[:12]}"
            f"{' ...' if len(missing) > 12 else ''}"
        )
        return 1

    described = [
        build_description(records[p.panel_id], p, renames)
        for p in ordered
        if p.panel_id in records
    ]

    merged = DescriptionFile(
        chapter_id=args.chapter_id,
        title="",
        series="only-sense-online",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        model="agent",
        panel_count=len(described),
        panels=described,
    )
    out = root / "03_descriptions.json"
    save_model(merged, out)

    with_text = [p for p in described if p.has_detected_text]
    gaps = [p.panel_id for p in with_text if p.is_untranscribed()]
    illegible = [
        p.panel_id
        for p in described
        if any("[illegible]" in b.lower() for b in p.speech_bubbles)
    ]
    skippable = [
        p.panel_id
        for p in described
        if p.is_credits_or_ad or p.setting.strip().lower() == "page_margin"
    ]
    roster = sorted({name for p in described for name in p.characters})

    print(f"WROTE {out}")
    print(f"  panels        : {len(described)} / {index.panel_count}")
    print(f"  missing       : {len(missing)}")
    print(f"  label renames : {len(renames) if renames else 0}")
    print(f"  with text     : {len(with_text)}")
    print(f"  unreadable    : {len(gaps)} ({len(gaps) / max(1, len(with_text)):.1%})")
    print(f"  [illegible]   : {len(illegible)}")
    print(f"  skippable     : {len(skippable)}")
    print(f"  roster ({len(roster)}): {', '.join(roster)}")
    if new_labels:
        notes = ", ".join(
            f"{item.get('label')} = {item.get('description', '')}" for item in new_labels
        )
        print(f"  new labels    : {notes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
