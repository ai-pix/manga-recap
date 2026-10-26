"""Import Tomb Raider King (Chapters 01-30) from data/downloads/hz7ja.zip into pipeline format."""

from __future__ import annotations

import datetime
import json
import zipfile
from pathlib import Path

from manga_recap.core.paths import ChapterPaths, REPO_ROOT
from manga_recap.core.schema import (
    BBox,
    BodyLanguageEntry,
    DescriptionFile,
    PanelDescription,
    PanelIndex,
    PanelIndexFile,
    save_model,
)

ZIP_PATH = REPO_ROOT / "data" / "downloads" / "hz7ja.zip"


def import_chapter(z: zipfile.ZipFile, ch_num: int) -> None:
    ch_id = f"ch{ch_num:02d}"
    json_path = f"{ch_id}/{ch_id}.json"

    if json_path not in z.namelist():
        print(f"[{ch_id}] Not found in zip, skipping.")
        return

    raw = json.loads(z.read(json_path).decode("utf-8"))
    raw_panels = raw.get("panels", [])

    paths = ChapterPaths.create(ch_id)
    paths.ensure_dirs()

    # 1. Extract panels into 02_panels
    panel_index_entries: list[PanelIndex] = []
    converted_descriptions: list[PanelDescription] = []

    # Keep a dummy page_001 in 01_pages so ingest is marked done
    dummy_page = paths.pages_dir / "page_001.jpg"
    if not dummy_page.exists() and raw_panels:
        first_panel_id = raw_panels[0]["panel_id"]
        dummy_page.write_bytes(z.read(f"{ch_id}/{first_panel_id}.jpg"))

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for idx, p_raw in enumerate(raw_panels, start=1):
        pid = p_raw["panel_id"]
        img_name = f"{pid}.jpg"
        zip_img_path = f"{ch_id}/{img_name}"

        # Write panel image
        out_img_path = paths.panels_dir / img_name
        if not out_img_path.exists() and zip_img_path in z.namelist():
            out_img_path.write_bytes(z.read(zip_img_path))

        # Build BodyLanguage entries
        raw_bl = p_raw.get("body_language", [])
        bl_entries: list[BodyLanguageEntry] = []
        if isinstance(raw_bl, list):
            for b in raw_bl:
                if isinstance(b, dict):
                    bl_entries.append(
                        BodyLanguageEntry(
                            character=str(b.get("character", "")),
                            pose=str(b.get("pose", "")),
                            action=str(b.get("action", "")),
                            expression_detail=str(b.get("expression_detail", "")),
                        )
                    )
                elif isinstance(b, str):
                    bl_entries.append(
                        BodyLanguageEntry(
                            character="",
                            pose="",
                            action=b,
                            expression_detail="",
                        )
                    )

        # Speech bubbles
        raw_speech = p_raw.get("speech_bubbles", [])
        if isinstance(raw_speech, list):
            speech_bubbles = [str(s) for s in raw_speech if s]
        elif isinstance(raw_speech, str) and raw_speech:
            speech_bubbles = [raw_speech]
        else:
            speech_bubbles = []

        # Characters, props, sfx
        characters = [str(x) for x in p_raw.get("characters", []) if x]
        props = [str(x) for x in p_raw.get("props", []) if x]
        sfx_text = [str(x) for x in p_raw.get("sfx_text", []) if x]

        # Action fallback
        action_text = str(p_raw.get("action", "")).strip()
        if not action_text:
            if p_raw.get("setting"):
                action_text = f"Scene showing {p_raw.get('setting')}."
            elif speech_bubbles:
                action_text = "Dialogue exchange takes place."
            elif characters:
                action_text = f"Focus on {', '.join(characters)}."
            else:
                action_text = "Visual scene illustration."

        p_desc = PanelDescription(
            panel_id=pid,
            page_number=1,
            reading_order=idx,
            image_path=f"02_panels/{img_name}",
            characters=characters,
            setting=str(p_raw.get("setting", "")),
            action=action_text,
            expression=str(p_raw.get("expression", "")),
            body_language=bl_entries,
            props=props,
            sfx_text=sfx_text,
            speech_bubbles=speech_bubbles,
            ambient_mood=str(p_raw.get("ambient_mood", "neutral")),
            is_sfx_only=bool(p_raw.get("is_sfx_only", False)),
            is_color_splash=bool(p_raw.get("is_color_splash", False)),
            is_credits_or_ad=bool(p_raw.get("is_credits_or_ad", False)),
            has_detected_text=bool(speech_bubbles),
            transcription_source="panel" if speech_bubbles else "none",
        )
        converted_descriptions.append(p_desc)

        panel_index_entries.append(
            PanelIndex(
                panel_id=pid,
                page_number=1,
                index_on_page=idx,
                reading_order=idx,
                source="opencv",
                bbox=BBox(x1=0, y1=0, x2=100, y2=100),
                image_path=f"02_panels/{img_name}",
                page_width=100,
                page_height=100,
            )
        )

    # Save 03_descriptions.json
    desc_file = DescriptionFile(
        chapter_id=ch_id,
        title=f"Tomb Raider King Chapter {ch_num}",
        series="tomb-raider-king",
        created_at=now_iso,
        model=str(raw_panels[0].get("model", "gemini") if raw_panels else "gemini"),
        panel_count=len(converted_descriptions),
        panels=converted_descriptions,
    )
    save_model(desc_file, paths.descriptions_file)

    # Save 02_panels/panel_index.json
    idx_file = PanelIndexFile(
        chapter_id=ch_id,
        page_count=1,
        panel_count=len(panel_index_entries),
        created_at=now_iso,
        panels=panel_index_entries,
    )
    save_model(idx_file, paths.panels_dir / "panel_index.json")

    print(f"[{ch_id}] Successfully imported {len(converted_descriptions)} panels.")


def main():
    if not ZIP_PATH.exists():
        print(f"Error: {ZIP_PATH} not found.")
        return 1

    print("=" * 60)
    print("IMPORTING TOMB RAIDER KING (CH01 - CH30)")
    print("=" * 60)

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        for ch_num in range(1, 31):
            import_chapter(z, ch_num)

    print("=" * 60)
    print("IMPORT COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    main()
