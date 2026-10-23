# Manga / Manhwa Video Recap & Storyboarding Process

This document defines the official standard for scriptwriting, panel selection (storyboarding), and audio-visual synchronization across the Manga Recap pipeline. **Any AI agent or developer generating scripts and videos must strictly follow this methodology.**

---

## 1. Narration Style: The YouTube Recap Persona

The narration must follow the high-retention, engaging style of popular YouTube Manhwa/Manga Recap channels (specifically referencing **Mamoru Manhwa** / `https://youtu.be/UWeHW3mkxmo`).

### Key Voice Principles:
- **Natural, Enthusiastic, and Conversational:** Narrate like a close friend hyping up a story over Discord or in person (*"Our story kicks off with our main character, Shun..."*, *"With pure galaxy-brain logic, he actively hunts down the obscure, unloved Senses..."*, *"Miu's eyes turn into blank white circles as her brain completely fries trying to process the visual"*).
- **Comedy & Knowing Delivery:** Dry, witty, and slightly ahead of the characters. Highlight ridiculous gaming decisions, comedic misunderstandings, and hilarious character reactions.
- **Fair Use & Transformative Commentary:**
  - **Never** read raw dialogue verbatim like an audiobook.
  - Transform dialogue into punchy, paraphrased recap narration combined with analytical commentary on game systems, character motivations, and comedic situations.
- **Snappy Pacing:**
  - Keep chapters tight and concise: **~1,200 to 1,700 words** total (~8–11 minutes of video at 150 wpm).
  - Do NOT write bloated 4,000-word / 25-minute academic essays. Viewers want fast, entertaining pacing.

---

## 2. Strict Vocabulary Bans (Zero Tolerance)

The script must **NEVER** break the immersion or refer to the physical medium. Viewers are watching a story, not an art analysis.

The following words are **STRICTLY BANNED** from all narration:
| Banned Term | Why It Is Banned | What To Say Instead |
|---|---|---|
| `panel` / `panels` | Meta jargon breaking immersion | Describe the character action or scene directly. |
| `chapter` / `chapters` | Meta medium reference | Refer to the story beat, quest, or journey. |
| `page` / `pages` | Meta medium reference | Refer to the scene, location, or moment. |
| `manga` / `manhwa` | Fourth-wall break | Refer to the story, game, or world. |
| `author` / `artist` | Meta medium reference | Focus on the character's choices and destiny. |
| `drawing` / `drawn` | Medium mechanics | Describe what the character is doing or experiencing. |
| `illustration` | Medium mechanics | Describe the event or visual reality. |
| `reader` / `viewers` | Fourth-wall break | Speak directly to the listener as a friend. |

*Incorrect:* "In the next panel, the author drew Shun with eyes as white ovals."  
*Correct:* "Shun freezes in pure disbelief, completely questioning his life choices."

---

## 3. Storyboarding & Clause-to-Panel Synchronization

In this pipeline, `04_script.json` is not just a script—it is the **Storyboard** that dictates which image is rendered on screen during each spoken line.

### How the Video Engine Works (`src/manga_recap/render/sync.py`):

The engine reads the narration **clause by clause**. It splits each block's text at sentence ends, semicolons, dashes, and the conjunctions that introduce a new action, then cuts to a new panel on each clause.

- **One clause, one panel.** A sentence of roughly 8–14 words that describes one visual moment becomes one shot.
- **A sentence describing three actions in order** names three panels in `panel_ids`, in that order. The engine cuts between them **on the spoken word**, not on an equal fraction of the elapsed time.
- **Cuts land on real audio.** Each clause's start and end are read from the word-level timings in `06_timeline.json`. The panel changes on the first word of the clause describing it.
- **Silence holds the current panel.** Each shot runs until the next begins, so the pause between two blocks shows the panel already on screen rather than a black frame.

### The Invariant: The Picture Must Match the Words
1. **The sentence spoken MUST depict what is visible in that panel.** When the voice discusses typing on a keyboard, the keyboard panel is on screen. When it discusses the chosen Senses, the status menu is on screen. When it describes an attack, the impact panel is on screen.
2. **A block may name several panels**, but only if its narration splits into that many clauses. `_check_beat_binding` in `s3_script/validate.py` **rejects** a block whose panels outnumber its clauses, because the surplus panels would otherwise be **silently dropped from the video**—a line about three things would show one picture for all of it.
3. **`render.max_words_per_beat` (default 14) is the dial.** Lower it for tighter visual tracking; raise it for longer holds on one panel.

### Optional explicit `beats`

When the natural clause boundary and the panel change do not line up, bind them by hand:

```json
{
  "block_id": "b042",
  "panel_ids": ["panel_0084", "panel_0085"],
  "narration": "Miu points at his floating name tag. He made a typo and registered as Yun!",
  "beats": [
    {"beat_id": "b042_b00", "text": "Miu points at his floating name tag.", "panel_id": "panel_0084"},
    {"beat_id": "b042_b01", "text": "He made a typo and registered as Yun!", "panel_id": "panel_0085"}
  ]
}
```

### Verifying sync without watching the video

After every render, read `data/chapters/<chapter>/07_sync_report.json`. It lists every shot with its text, its window, whether the boundary was **anchored** to a real word or **interpolated**, plus the measured `drift` and any `gaps`. A healthy chapter reports `drift: 0.0000`, zero gaps, and every shot anchored.

**Never derive a cut from a running sum of durations.** An earlier renderer did exactly that and silently discarded ~30s of silence between blocks; chapter 01 rendered 603.4s against 633.6s of narration, ending 30 seconds of voice early.

---

## 4. Visual Style: Blurred Backdrop

Panels are manga crops in mixed aspect ratios, so most are not 16:9. `render.background_mode` decides how they fill the frame.

| mode | result | cost |
|---|---|---|
| `blurred` (default) | a soft, darkened copy of the panel fills the frame, sharp art centred on top | one blur per panel |
| `solid` | flat `background_color` bars | cheapest |
| `crop` | scale up and cut the overflow, no compositing | cheapest |

### Why the blur is cheap

**The composition happens on a single frame, not per frame.** The panel is scaled to `render.blur_width` (64px) wide, `boxblur`ed there, scaled back up to full size, darkened, and composited under the sharp panel. The result is written to a single still, which the encoder then holds.

That is not a shortcut that merely looks similar: a blurred backdrop carries no detail by definition, so the downscale destroys nothing a full-resolution blur would have kept, and the blur runs on a few thousand pixels instead of two million.

**An earlier version ran `boxblur=20:5` over 1920x1080 on every frame** and was the render's dominant cost.

### Two bugs worth not repeating

- **Do not pad the foreground in blurred mode.** Padded to the full frame it covers the backdrop with the pad colour, giving solid black bars while every string-level assertion still passes. Leave it at its fitted size and let `overlay` centre it. A pixel-level test now guards this.
- **Only oversize the still when Ken Burns is on.** Unconditional headroom made every static shot render 1% oversized, and with no crop to trim it the encoder emitted the video in the wrong resolution.

### Ken Burns

When enabled, the move is a `crop` sliding across an oversized still, driven by `t` so it runs at the same speed at any frame rate. **Never `zoompan`** — it rescales every frame and was the single most expensive thing in the old render.

---

## 5. Panel Pruning: Dropping Empty & Redundant Crops

Detector outputs from stage 1 (`02_panels/`) frequently contain non-story artifacts. **Do NOT force non-story crops into the video storyboard.**

### Always Exclude:
1. **Gutter Margin Slivers:** Narrow vertical or horizontal crops containing only grey screentone or paper margins (`setting: page_margin`). Showing these causes ugly 1–2 second screen flashes of blank grey tone.
2. **Black Border Wedges:** Triangular black lines from page edges.
3. **Duplicate / Overlapping Crops:** Partial crops of larger splash panels (e.g., when a single low-angle splash was split into an upper crop, lower crop, and full crop—keep only the best full crop).
4. **Abstract Impact Metaphors:** Standalone panels showing cracked boulders or black backgrounds with no characters.
5. **Partial Body Slices:** Slivers showing only a hand, knee, or cropped hair when an adjacent panel shows the full character.

### How to Exclude Them in the Pipeline:
- Mark them with `"is_credits_or_ad": true` in `03_descriptions.json`, or set `setting: "page_margin"`.
- This informs `s3_script/validate.py` that these panels are skippable chrome, allowing the storyboard to focus 100% on the genuine, expressive story panels without throwing coverage validation errors.

---

## 6. Stage 4: Ultra-Fast Neural TTS & Word-Level Timing Flow

Manga recap channels live and die by pacing and vocal delivery. The pipeline supports two TTS engines:

### 1. High-Speed Edge-TTS Backend (Recommended Default)
- **Engine:** Microsoft Neural Speech API via `edge-tts`.
- **Speed:** Synthesizes an entire 10-11 minute recap (~1,700 words) in **~12–15 seconds** locally (over 100x faster than Kaggle container spin-up).
- **Voice:** `en-US-GuyNeural` (relaxed, energetic, authentic YouTube recap tone matching *Mamoru Manhwa*), `en-US-ChristopherNeural` (warmer storytelling), or `en-US-AndrewNeural`.
- **Exact Word Timing ("Whisperflow"):** Passes `boundary="WordBoundary"`, capturing native millisecond-precision timestamps for every word and sentence directly from the neural vocoder.
- **Zero Drift / Invariant:** Concatenates block audio with a natural pause (0.18s), yielding a 100% synchronized `06_timeline.json` where each block has `match_ratio: 1.0` and **0 degraded blocks**.

### 2. Kaggle Chatterbox Turbo Backend (Voice Cloning)
- **Zero Local Heavy Compute Rule:** Chatterbox Turbo, Tortoise, and large PyTorch neural speech models must NEVER run on the local user machine (saving local GPU VRAM and CPU cycles).
- Used when cloning a custom reference voice from a 10–20s `.wav` sample (`tts.voice.mode: clone`).
- Runs remotely on Kaggle T4 GPU kernel (`kaggle/kernel_tts_align`) with `faster-whisper` speech-to-text token alignment. All audio generation and alignment happen on Kaggle, downloading the final `narration.wav` and `timeline.json`.

---

## 7. Pre-Render Validation Checklist

Before submitting a chapter for audio generation (`speak`) and video rendering (`render`), verify:
1. `04_script.json` contains **0** occurrences of banned words (`panel`, `chapter`, `page`, etc.).
2. Word count is within target range (~1,200 to 1,700 words).
3. Every block maps to a valid, visually matching story panel.
4. **No block names more panels than its narration can be split into.** Those panels would be dropped from the video entirely.
5. All empty gutter slivers and duplicate crops have been dropped.
6. Validator passes with `rep.ok == True` and `rep.problems == []`:
   ```powershell
   .venv\Scripts\python.exe -c "from pathlib import Path; from manga_recap.core.config import load_config; from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model; from manga_recap.stages.s3_script.validate import validate; cfg = load_config(); d = load_model(Path('data/chapters/ch01/03_descriptions.json'), DescriptionFile); s = load_model(Path('data/chapters/ch01/04_script.json'), ScriptFile); rep = validate(s, d, cfg); print('Validation OK?', rep.ok, rep.problems)"
   ```
7. Dry-run the shot planner and confirm the timeline is a clean cover **before** spending GPU time:
   ```powershell
   .venv\Scripts\python.exe -c "import json; from manga_recap.render.sync import plan_shots, coverage_gaps; from manga_recap.core.schema import ScriptFile, TimelineFile, load_model; from pathlib import Path; s=load_model(Path('data/chapters/ch01/04_script.json'),ScriptFile); t=load_model(Path('data/chapters/ch01/06_timeline.json'),TimelineFile); r=plan_shots(s.blocks,t.words,audio_duration=t.duration); print('shots',len(r.shots),'drift',r.drift,'gaps',len(coverage_gaps(r.shots,t.duration)),'problems',r.problems)"
   ```
8. Run test suite:
   ```powershell
   .venv\Scripts\python.exe -m pytest tests -q
   .venv\Scripts\python.exe -m ruff check src tests
   ```

### After rendering

Read `07_sync_report.json` and confirm:

| Field | Healthy value |
|---|---|
| `drift` | `0.0` (within one frame) |
| `gaps` | `[]` |
| `problems` | `[]` |
| `anchored` | every shot `true` |

`drift` well above zero means the video does not cover the audio. `anchored: false` means the timeline had no word timings and every cut was interpolated by word count.

---

## 8. Chapter Versioning & Iteration Archiving

When rewriting scripts, testing alternative voiceovers, or updating storyboards, previous artifacts must be preserved rather than overwritten blindly.

### Folder Structure:
```
data/chapters/<chapter_id>/
  ├── 00_input/
  ├── 01_pages/
  ├── 02_panels/
  ├── 03_descriptions.json
  ├── 04_script.json            # Active script / storyboard
  ├── 05_narration.wav          # Active narration audio
  ├── 06_timeline.json          # Active timeline (block + word timings)
  ├── 07_final.mp4              # Active rendered video
  ├── 07_sync_report.json       # Per-shot timing, drift, gaps, anchoring
  ├── 07_render_manifest.json   # Encoded shots with frame counts
  └── versions/
      ├── v1_initial/           # Archived v1 (e.g. initial literary pass, 92 blocks, 20m)
      │   ├── 04_script.json
      │   ├── 05_narration.wav
      │   ├── 06_timeline.json
      │   ├── 07_final.mp4
      │   └── README.md
      └── v2_youtube_recap/     # Archived v2 (e.g. YouTube recap 101 blocks, 11m)
          ├── 04_script.json
          └── README.md
```

### Invariant Rules:
1. **Active Files Stay at Root:** The pipeline command line tools (`manga speak`, `manga render`, `manga status`) always operate on root files (`04_script.json`, `05_narration.wav`, etc.).
2. **Archive Before Retrying:** When starting a new iteration, move the previous narration, timeline, and video into `versions/v<N>_<label>/`. This prevents cross-version contamination and ensures `manga status` correctly detects that downstream stages are pending for the new script.
3. **Document Each Version:** Each version folder must contain a short `README.md` summarizing word count, style, block count, and audio duration.
4. **100% Pure GPU Execution (Zero CPU Fallback):** Video rendering and TTS model execution must NEVER run on CPU. Kaggle rendering must strictly use NVIDIA hardware NVENC (`h264_nvenc`) and PyTorch CUDA pipelines. If NVENC fails to initialize on Kaggle, the pipeline MUST immediately raise a hard fatal error in under 2 seconds. Silently falling back to CPU software encoding (`libx264`) is strictly prohibited.
