"""Convert external descriptions JSON from Google Drive archive into pipeline standard 03_descriptions.json.

Maps for each chapter ch01 to ch30:
- Reads panel metadata from local data/chapters/overgeared/chXX/02_panels/panel_index.json
- Reads descriptions from organised/chXX/chXX.json
- Builds valid Pydantic DescriptionFile models
- Saves data/chapters/overgeared/chXX/03_descriptions.json
"""

import datetime
import json
import zipfile
from pathlib import Path

from manga_recap.core.schema import BodyLanguageEntry, DescriptionFile, PanelDescription, save_model

REPO_ROOT = Path(__file__).resolve().parent.parent
ZIP_PATH = REPO_ROOT / "data" / "downloads" / "new-series-ch01-ch30-organised.zip"
CHAPTERS_ROOT = REPO_ROOT / "data" / "chapters" / "overgeared"


def convert_all():
    print("=" * 70)
    print("IMPORTING OVERGEARED DESCRIPTIONS (CH01 - CH30)")
    print("=" * 70)

    with zipfile.ZipFile(ZIP_PATH, "r") as z:
        for i in range(1, 31):
            ch_name = f"ch{i:02d}"
            ch_dir = CHAPTERS_ROOT / ch_name
            panels_dir = ch_dir / "02_panels"
            index_path = panels_dir / "panel_index.json"

            if not index_path.exists():
                print(f"[SKIP] {ch_name}: {index_path} not found.")
                continue

            local_index = json.loads(index_path.read_text(encoding="utf-8"))
            local_panels = {p["panel_id"]: p for p in local_index.get("panels", [])}

            json_arc_name = f"organised/{ch_name}/{ch_name}.json"
            if json_arc_name not in z.namelist():
                print(f"[SKIP] {ch_name}: {json_arc_name} not in zip.")
                continue

            arc_data = json.loads(z.read(json_arc_name).decode("utf-8"))
            desc_panels_raw = arc_data.get("panels", [])

            converted_panels: list[PanelDescription] = []

            for p_raw in desc_panels_raw:
                pid = p_raw.get("panel_id")
                loc = local_panels.get(pid, {})

                # Body language parsing
                raw_bl = p_raw.get("body_language", [])
                bl_entries = []
                if isinstance(raw_bl, list):
                    for b in raw_bl:
                        if isinstance(b, dict):
                            bl_entries.append(BodyLanguageEntry(
                                character=str(b.get("character", "")),
                                pose=str(b.get("pose", "")),
                                action=str(b.get("action", "")),
                                expression_detail=str(b.get("expression_detail", ""))
                            ))
                        elif isinstance(b, str):
                            bl_entries.append(BodyLanguageEntry(
                                character="",
                                pose="",
                                action=b,
                                expression_detail=""
                            ))

                # Handle speech bubbles
                raw_speech = p_raw.get("speech_bubbles", [])
                if isinstance(raw_speech, list):
                    speech_bubbles = [str(s) for s in raw_speech if s]
                elif isinstance(raw_speech, str) and raw_speech:
                    speech_bubbles = [raw_speech]
                else:
                    speech_bubbles = []

                # Handle props
                raw_props = p_raw.get("props", [])
                props = [str(x) for x in raw_props if x] if isinstance(raw_props, list) else []

                # Handle characters
                raw_chars = p_raw.get("characters", [])
                characters = [str(x) for x in raw_chars if x] if isinstance(raw_chars, list) else []

                # Handle sfx_text
                raw_sfx = p_raw.get("sfx_text", [])
                sfx_text = [str(x) for x in raw_sfx if x] if isinstance(raw_sfx, list) else []

                # transcription_source must be 'none', 'panel', or 'text_crop'
                ts_source = "panel" if speech_bubbles else "none"

                # Ensure action is non-empty
                action_text = str(p_raw.get("action", "")).strip()
                if not action_text:
                    if p_raw.get("setting"):
                        action_text = f"Scene showing {p_raw.get('setting')}."
                    elif p_raw.get("speech_bubbles"):
                        action_text = "Dialogue exchange takes place."
                    elif p_raw.get("characters"):
                        action_text = f"Focus on {', '.join(p_raw.get('characters'))}."
                    else:
                        action_text = "Visual scene transition or illustration panel."

                # PanelDescription fields
                p_desc = PanelDescription(
                    panel_id=pid,
                    page_number=int(loc.get("page_number", 1)),
                    reading_order=int(loc.get("reading_order", len(converted_panels) + 1)),
                    image_path=loc.get("image_path", f"02_panels/{pid}.webp"),
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
                    has_detected_text=bool(loc.get("text_boxes") or speech_bubbles),
                    transcription_source=ts_source
                )
                converted_panels.append(p_desc)

            desc_file = DescriptionFile(
                chapter_id=ch_name,
                title=f"Overgeared Chapter {i}",
                series="overgeared",
                created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                model=str(arc_data.get("model", "imported")),
                panel_count=len(converted_panels),
                panels=converted_panels
            )

            out_path = ch_dir / "03_descriptions.json"
            save_model(desc_file, out_path)
            print(f"  [{ch_name}] Successfully written {len(converted_panels)} panel descriptions -> {out_path.name}")

    print("=" * 70)
    print("ALL 30 CHAPTER DESCRIPTIONS SUCCESSFULLY IMPORTED!")
    print("=" * 70)


if __name__ == "__main__":
    convert_all()
