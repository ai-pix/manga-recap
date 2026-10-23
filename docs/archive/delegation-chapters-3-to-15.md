# System Prompt & Delegation Guide: Stage 2 Descriptions for Chapters 03 to 15

> **FOR THE INCOMING AI AGENT:**  
> **YOUR ONLY TASK is to generate `03_descriptions.json` for Chapters 03 through 15.**  
> That is the entire assignment. Do **NOT** write scripts (`04_script.json`), do **NOT** run audio (`speak`), do **NOT** render video (`render`).  
> **USE SUBAGENTS AGGRESSIVELY IN PARALLEL** to complete all 14 chapters rapidly.

---

## 1. Context & What is Already Done (DO NOT RE-DO)

1. **Location:** `D:\Python Projects\Manga Recap`
2. **Virtual Environment:** `.venv\Scripts\python.exe`
3. **Chapters 01 and 02:** Fully finished (already have valid `03_descriptions.json` and completed videos).
4. **Stages 0 & 1 are 100% complete for all chapters:**
   - Every chapter has its normalized pages in `01_pages/`.
   - Every chapter has its cropped panels in `02_panels/`.
   - Every chapter has native-resolution speech bubble crops in `02_panels/_text/`.
   - Every chapter has a valid `02_panels/panel_index.json` (the source of truth for panel order and geometry).
5. **Series Bible:** `data/series/only-sense-online/series.md` (defines characters like Shun/Yun, Miu, Magi, Sense mechanics).
6. **Code & Tests:** All 411 unit tests pass (`.venv\Scripts\python.exe -m pytest tests -q`) and `ruff` is clean.

---

## 2. Your Exact Scope: Chapters 03 to 15 (14 Chapters)

Process the following chapters:
`ch003`, `ch004`, `ch005`, `ch005_5`, `ch06` (or `ch006`), `ch007`, `ch008`, `ch009`, `ch010`, `ch011`, `ch012`, `ch013`, `ch014`, `ch015`.

For each chapter, produce exactly one file:
`data/chapters/<chapter_id>/03_descriptions.json`

---

## 3. High-Speed Subagent Architecture (MANDATORY)

Do **NOT** inspect hundreds of panels sequentially in a single context window. You must use **two tiers of parallel subagents**:

```
Primary Coordinator Agent
│
├── Subagent Chapter Worker 1 (Processes ch003)
│   ├── Child Subagents reading batches of 10–15 panels in parallel
│   └── Merges JSON chunks & validates ch003
│
├── Subagent Chapter Worker 2 (Processes ch004 concurrently)
│   ├── Child Subagents reading batches of 10–15 panels in parallel
│   └── Merges JSON chunks & validates ch004
│
├── Subagent Chapter Worker 3 (Processes ch005 concurrently)
│   └── ...
```

### Level 1: Cross-Chapter Parallelism
- Launch subagents to work on **3 to 4 chapters concurrently**.
- Because each chapter lives in its own self-contained directory (`data/chapters/<chapter_id>/`), parallel workers will never conflict or overwrite each other.

### Level 2: Within-Chapter Panel Vision Parallelism
- Each chapter contains ~100–180 panels.
- Split the chapter's panel list into chunks of **10 to 15 panels**.
- Spawn child subagents to inspect the panel images and native speech bubble crops in parallel.
- Each child subagent returns a JSON array of records for its assigned chunk.
- The parent merges the chunks into `03_descriptions.json` in reading order.

---

## 4. Ground Rules & Schema Requirements

### Where to Look:
- **Panel Images:** `02_panels/panel_XXXX.png` (shows overall visual composition, characters, poses).
- **Dialogue Crops:** `02_panels/_text/panel_XXXX_text.png` (tight, undownscaled native crops of speech bubbles — **always read text from these crops**).
- **Index:** `02_panels/panel_index.json` (provides `panel_id`, `page_number`, `reading_order`, `has_detected_text`).

### Required JSON Structure for `03_descriptions.json`:
```json
{
  "chapter_id": "ch003",
  "title": "",
  "series": "only-sense-online",
  "created_at": "2026-10-02T00:00:00",
  "model": "agent",
  "panel_count": 179,
  "panels": [
    {
      "panel_id": "panel_0001",
      "page_number": 1,
      "reading_order": 1,
      "image_path": "02_panels/panel_0001.png",
      "action": "Yun holds his bow in a ready stance while scanning the forest edge.",
      "characters": ["Yun"],
      "setting": "forest_clearing",
      "expression": "focused, slight smile",
      "body_language": [
        {"character": "Yun", "pose": "standing", "action": "aiming bow", "expression_detail": "confident"}
      ],
      "props": ["wooden bow", "quiver"],
      "ambient_mood": "adventurous",
      "speech_bubbles": ["Alright, let's see how much damage this basic arrow can do."],
      "sfx_text": [],
      "has_detected_text": true,
      "transcription_source": "text_crop",
      "is_sfx_only": false,
      "is_color_splash": false,
      "is_credits_or_ad": false
    }
  ]
}
```

### Strict Quality Rules:
1. **Never Invent Dialogue:**
   - If a speech bubble is clipped, too small, or illegible, write `[illegible]`. Never invent text. An invented line poisons the downstream scriptwriter with false motivations.
2. **Never Drop Text-Bearing Panels:**
   - If `has_detected_text: true`, you MUST transcribe the dialogue from `02_panels/_text/panel_XXXX_text.png`.
3. **Prune Non-Story Panels:**
   - Mark gutter margin slivers, black border wedges, scanlation credit cards, donation pages, and duplicate crops with `"is_credits_or_ad": true` or `setting: "page_margin"`.
4. **Stable Character Names:**
   - Use names from `data/series/only-sense-online/series.md` (Yun, Miu, Magi, etc.). For unknown background characters, use consistent descriptive labels (`tall_blond_player`, `shopkeeper_lady`).
5. **Exact Panel Count:**
   - `len(panels)` MUST match `panel_count` and match the count in `panel_index.json`.

---

## 5. Validation Gate for Each Chapter

After writing `03_descriptions.json`, execute the official validator:
```powershell
.venv\Scripts\python.exe -c "from pathlib import Path; from manga_recap.core.schema import DescriptionFile, load_model; from manga_recap.stages.s2_describe.validate import validate; d = load_model(Path('data/chapters/<chapter_id>/03_descriptions.json'), DescriptionFile); rep = validate(d); print('<chapter_id> Describe OK:', rep.ok, rep.problems)"
```

**Passing Criteria:**
- `Describe OK: True []`
- `panel_count` matches `len(panels)`
- 0 unread dialogue errors on text-bearing panels

Confirm status:
```powershell
.venv\Scripts\python.exe -m manga_recap status <chapter_id>
```
*(Should show `ingest: done`, `crop: done`, `describe: done`, `script: pending`).*

---

## 6. What NOT To Do
- Do **NOT** write `04_script.json` or any other file.
- Do **NOT** modify pipeline source code or configuration.
- Do **NOT** run re-crops or delete images.
- Do **NOT** run any compute tasks on GPU/CPU other than reading images and writing `03_descriptions.json`.
- Keep test suite clean: `.venv\Scripts\python.exe -m pytest tests -q` (411 passing).
