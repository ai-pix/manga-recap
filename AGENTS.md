# Manga Recap — agent handoff

You are taking over a Python pipeline that turns a manga chapter into a narrated
recap video. Read this whole file before changing anything. Most of it is
"here is what is already solved and why", so that you do not re-derive it or
undo it.

> ⚡ **ACTIVE TASK & STATE:** Check [`MEMORY.md`](file:///D:/Python%20Projects/Manga%20Recap/MEMORY.md) for current system architecture, permanent Kaggle storage datasets, and verified render state.

## Run it

```powershell
.venv\Scripts\python.exe -m manga_recap <command> ch01
```

`<command>` is one of `run`, `status`, `ingest`, `crop`, `describe`, `script`,
`speak`, `render`, `fetch-models`, `check`. `run` skips completed stages;
`--force` redoes everything, `--from script` redoes a stage and everything after.

Always run before and after:

```powershell
.venv\Scripts\python.exe -m pytest tests -q     # 328 passing
.venv\Scripts\python.exe -m ruff check src tests
```

Both must be green. They take about 9 seconds combined.

## STRICT RULE: No Heavy Tasks Locally & 100% Pure GPU Acceleration on Kaggle (Never CPU)

1. **Zero heavy workloads on the user's local machine.** The user's system is a Windows PC with limited VRAM (GTX 1650) and Python 3.14. Under NO circumstances should any agent run heavy compute tasks locally:
   - **TTS Model Synthesis (Chatterbox Turbo, Bark, etc.):** MUST run on Kaggle GPU via `kaggle/kernel_tts_align` (or lightweight cloud APIs like Gemini TTS / Edge-TTS). Never build or run PyTorch neural TTS models locally.
   - **Heavy Alignment (Whisper large-v3):** MUST run on Kaggle GPU.
   - **Video Rendering (FFmpeg compositing with filters/pans):** MUST run on Kaggle GPU kernel (`kaggle/kernel_render`).
   - **Heavy ML Inference / Training:** MUST run on Kaggle GPU.
   - **Local system is ONLY for:**
     - Lightweight pipeline orchestration & Kaggle CLI job submissions
     - External cloud API requests (Gemini API, Kaggle API)
     - Lightweight metadata generation, prompt orchestration, JSON staging, file zipping
     - Unit tests and linting (`pytest`, `ruff`)

2. **Kaggle Execution Must Be 100% Pure GPU/CUDA (NEVER CPU, NO FALLBACKS EVER):**
   - **ABSOLUTE BAN ON KAGGLE CPU:** Under NO circumstances should any script, pipeline stage, or Kaggle kernel run video rendering, audio generation, or alignment on Kaggle CPU.
   - **ZERO CPU FALLBACK EVER:** It is STRICTLY PROHIBITED to include, suggest, or execute any fallback to CPU software encoding (e.g. `libx264`, `veryfast`, `ultrafast`, CPU filtergraphs). If GPU hardware acceleration (NVENC / CUDA) fails to initialize or is unavailable, the execution MUST immediately fail with a hard `RuntimeError` in under 2 seconds. Silently downgrading to CPU software rendering is a critical violation across the entire codebase.
   - Video rendering must strictly leverage NVIDIA T4 hardware NVENC (`h264_nvenc`) and pure CUDA hardware pipelines (`scale_cuda`, `overlay_cuda`, PyTorch GPU memory buffers). Never bottleneck GPU throughput with CPU filtergraphs.
   - Whisper alignment and TTS synthesis must strictly run in PyTorch CUDA (`device="cuda"`).


## Where the work is

- `src/manga_recap/stages/` — the pipeline, one package per stage
- `config/config.yaml` — every tunable, heavily commented
- `config/prompts/` — `panel_description.md`, `panel_transcription.md`,
  `panel_transcription_retry.md`, `storyboard.md`
- `docs/llm-stages.md` — **read before touching stages 2 or 3.** Field-by-field
  schema reference, the gates, and a symptom-to-cause debugging table
- `docs/agent-prompt-describe.md` — system prompt for an agent that replaces
  stage 2, reading the panel images itself instead of calling the Gemini API.
  Paste it as the system prompt. Subagent orchestration is built in.
- `docs/agent-prompt-script.md` — the same, for stage 3. Separate agent.
- `data/chapters/ch01/` — outputs, numbered by stage: `00_input`, `01_pages`,
  `02_panels`, `03_descriptions.json`, `04_script.json`, `06_timeline.json`,
  `07_final.mp4`
- `tests/` — 328 tests

Chapter 001 of *Only Sense Online*: 31 pages, 136 panels, 95 of them with speech
bubbles.

## Current state

All stages 0-5 are complete. Chapter 01 is fully rendered.

- `03_descriptions.json` — 136 panels, 0 unreadable dialogue out of 95
  text-bearing panels, `"model": "agent"`
- `04_script.json` — 101 blocks, 1,727 words, 101 story panels mapped 1:1 with spoken sentences
- `05_narration.wav` — 633.6s (10.56 min) expressive masculine narration (Chatterbox Turbo cloned `Orus` voice on Kaggle GPU)
- `07_final.mp4` — 632.2s (10.54 min), 131.8 MB 1080p video rendered via PyNvVideoCodec zero-copy DLPack engine at 355.6 FPS (53.3s encode) with zero missing panels
- Permanent Kaggle storage dataset `wampireai/manga-recap-voice-orus` stores voice reference
- 35 empty, margin, and duplicate panels correctly pruned as skippable
- 427 tests pass, ruff clean
- See `docs/video-making-process.md` for the complete end-to-end video making standard.
- See `docs/gpu-rendering-journey.md` for the complete architectural breakdown of the 355+ FPS pure GPU rendering engine (`engine: pynv`).

**Status: Chapter 01 complete & verified at 355.6 FPS.**

## The part that matters: audio-panel sync

The video is only watchable if the picture on screen matches the sentence being spoken.
It will not stay that way on its own — audio knows about words, the renderer knows about
panels, and nothing in between used to say when one clause should be replaced by the next.

### The old failure, so it is not reintroduced

The renderer chained every panel through one `xfade` filtergraph and derived each cut from
`sum(durations before it)`. That arithmetic silently discarded the ~30s of silence between
narration blocks. Chapter 01 rendered **603.4s against 633.6s of narration**: the video ran
progressively ahead, and the last 30 seconds of voice were cut off entirely.

**Never derive a cut from a running sum of durations.** The timeline has real gaps, and the
sum has no idea they exist.

### How sync works now

`src/manga_recap/render/sync.py` is the **single owner of shot timing**. Everything
downstream reads it; nothing re-derives timing. Three steps:

1. **Split** — each block's narration is cut into clauses, one panel per clause.
   `render.max_words_per_beat` (default 14) is the budget. Chapter 01's 101 blocks become
   205 beats.
2. **Anchor** — each beat reads its start and end from the word timings already in
   `06_timeline.json`, so the panel changes on the first word of the clause describing it.
3. **Schedule** — shots tile the audio exactly. Each runs until the next begins, the first
   starts at zero, the last ends at the audio's end, and frame counts come from cumulative
   absolute timestamps so rounding cannot accumulate.

Two invariants are enforced in code, not assumed: the shot list **covers the audio with no
gaps**, and starts **never move backwards**. `render.max_words_per_beat` is the dial — lower
it for tighter visual tracking, raise it for longer holds.

### Writing a script that syncs

The engine reads a script clause by clause, so the clause is what decides whether the picture
matches the voice. One clause, one panel: keep sentences to roughly 8–14 words. When a
sentence describes three things in order, name three panels in `panel_ids` in that order and
the engine cuts between them on the spoken word.

A block naming more panels than its narration can be split into is a hard error:
`_check_beat_binding` in `s3_script/validate.py` rejects it, because those extra panels would
otherwise be **silently dropped from the video**. Use explicit `beats` when the natural clause
boundary and the panel change do not line up:

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

After every render, read `data/chapters/<chapter>/07_sync_report.json`. It lists every shot
with its text, its window, and whether the boundary was anchored to a real word or
interpolated. That file answers "is this cut in the right place?" without watching ten
minutes of video.

## The part that matters: render cost

Two rules, both learned the hard way.

**Never compute anything per frame that can be computed once per panel.** The composition
below happens on a *single frame*, written to a still, which the encoder then holds. Per-frame
filtering is the only thing that made this renderer slow.

**The background is a blurred copy of the panel, blurred at 64 pixels wide.** Scale the panel
to `render.blur_width` (64px), `boxblur` it there, scale it back up to full size, darken it,
and lay the sharp panel on top. A blurred backdrop carries no detail by definition, so the
downscale destroys nothing a full-resolution blur would have kept — and it blurs a few
thousand pixels instead of two million.

The earlier version ran `boxblur=20:5` over 1920x1080 on **every frame**. That single choice
was the render's dominant cost.

`render.background_mode` chooses the look:

| mode | result | cost |
|---|---|---|
| `blurred` (default) | soft darkened copy of the art behind the sharp panel, no bars | blur once per panel |
| `solid` | flat `background_color` bars | cheapest |
| `crop` | scale up, cut the overflow, no compositing | cheapest |

Two bugs worth not repeating:

- **Do not pad the foreground in blurred mode.** Padded to the full frame it covers the
  backdrop with the pad colour, so you get solid black bars while every string-level
  assertion still passes. Leave it at its fitted size and let `overlay` centre it.
- **Only oversize the still when there is a Ken Burns move.** Unconditional headroom made
  every static shot render 1% oversized, and with no crop to trim it the encoder emitted the
  video in the wrong resolution. Invisible while Ken Burns was on, because the crop hid it.

Ken Burns, when enabled, is a `crop` sliding across an oversized still, driven by `t` so it
runs at the same speed at any frame rate. Never `zoompan`: it rescales every frame and was the
single most expensive thing in the old render.

### 4. Prune Empty Slivers & Duplicate Crops
Detector outputs from stage 1 contain non-story artifacts. Never force them into the video storyboard:
- Prune gutter margin slivers (`setting: page_margin`), black border wedges, abstract stone metaphors, and partial duplicate crops of larger splash pages.
- Flag them as skippable (`is_credits_or_ad: true` or `setting: page_margin`) in `03_descriptions.json`.

### 5. Chapter Versions & Iteration Archiving
To prevent confusion and preserve earlier work when iterating on scripts and audio:
- `data/chapters/<chapter>/versions/` archives each major generation:
  - `versions/v1_initial/` — The original 92-block, 3,675-word literary analysis pass, its 20-minute audio (`05_narration.wav`), timeline (`06_timeline.json`), and video (`07_final.mp4`).
  - `versions/v2_youtube_recap/` — The current 101-block, 1,684-word YouTube recap script and 1:1 storyboard.
- The active, in-progress files always live at the chapter root (`04_script.json`, `05_narration.wav`, etc.). Archiving previous audio/video out of the root allows `manga status` to correctly track pending stages for the active version.

## The part that matters: dialogue

The original problem was that cropped panels cut speech bubbles, so the vision
model invented motivations the manga never stated. Five mechanisms prevent that.
Keep all five; each was added because something measurably broke without it.

1. **Text boxes are retained, not discarded.** The panel detector reports class 0
   (panel) and class 1 (text). `crop.text_class_ids` keeps both. Discarding
   class 1 was the original bug — those boxes are the only evidence a bubble
   survived a crop.

2. **Panel boxes are grown to contain their own bubbles.** A bubble drawn across
   a border is unioned into *both* neighbouring panels. A flat 6px padding
   under-padded large panels and clipped overhangs, so padding is now a ratio of
   each panel's own longest edge.

3. **Text crops at native resolution.** `02_panels/_text/panel_XXXX_text.png` is
   a tight, undownscaled crop of just the bubbles. Panel text in a downscaled
   panel is 8-12px tall and reads as `[illegible]`; the text crop is the only
   reason the pipeline can read dialogue at all. It must be excluded from
   `panel_images()` or it gets narrated as a second panel.

4. **A text-coverage invariant.** Every detected text region must be ≥90% inside
   the panels that claim it, measured on their *union* so a bubble straddling a
   border is not falsely flagged. Pure geometry, no model call. This is what
   caught the missed panels.

5. **A gate before scripting.** Over `describe.max_untranscribed_ratio` of
   text-bearing panels unread, stage 3 refuses to run. Without it the narrator
   invents motive and nothing crashes — the failure is invisible.

**Never remove a mechanism here to "simplify". Each one corresponds to a real,
observed data loss.**

## The other part that matters: missed panels

YOLO under-detects full-bleed colour pages. Pages 10, 17 and 30 were losing whole
panels, along with their dialogue.

`src/manga_recap/stages/s1_crop/inkmask.py` measures ink instead of trusting
rectangles:

- **`content` mask** — paper reachable from the page edge is background,
  everything else is drawn area. White enclosed by ink counts, so a bubble's
  interior is content. Page coverage is measured against this, not page area.
- **`trace_outlines`** — a panel's border is a connected stroke, and a bubble
  that broke through is connected to it. `findContours` returns one contour
  enclosing the panel and whatever spilled out, and the bounding box of that
  trace is the panel's real extent. The trace is believed only if it closes the
  loop: at least `min_perimeter_coverage` of the box perimeter must be covered.
- **Sibling tie-break** — manga often draws one stroke as the right edge of one
  panel and the left of the next, so a contour can enclose both. The trace has to
  be shown nearer this panel than any other before it may move the box.
- **`missing_panel_candidates`** — drawn area minus detected panels, eroded to
  separate solid blocks from thin gutters. `auto_add_candidates: true` adds them
  as real panels; the log and the contact sheets record what was added either
  way.

This took 136 panels from 118 and took text coverage from 95.6% to 100%.

## Colour pages are the hard case

Do not assume white backgrounds. This chapter is 65-84% non-white per page.

- Paper is **bright and unsaturated**. A pale pink panel background is not paper
  however bright it is. `paper_spread` draws that line, and it is narrow on
  purpose: aged paper must still count as paper.
- Ink is **dark and unsaturated**. A dark red panel at the same luminance as a
  border is artwork, not a border.
- Getting this wrong makes every panel "grow", because the gutter between panels
  is not white and proximity then means nothing. That bug was real; the
  saturation gates and the tie-break are the fix.

## Reviewing the output

`02_panels/_debug/page_XXX_sheet.jpg` is the contact sheet. Colour code:

| Colour | Meaning |
|---|---|
| Red | detected panel, numbered in reading order |
| Blue | speech bubble claimed by a panel |
| Orange | bubble no panel claimed — usually a missed panel |
| Purple | leftover ink offered as a panel candidate |

Read these before changing anything in stage 1. A regression that no test catches
is usually obvious here in two seconds.

Escape hatch for pages detection cannot handle:
`02_panels/manual_boxes.json`, keyed by page filename. It overrides detection
completely.

## LLM layer gotchas

Already fixed, but each one failed silently until a real request went out:

- **The Gemini REST API is camelCase**: `inlineData`, `mimeType`. The Python SDK
  accepts snake_case, which is exactly why the mistake survived.
- **Quota is per model, not per key.** Two models means two independent buckets.
  Vision and script use separate models deliberately.
- **429 is ambiguous.** An exhausted quota and a rate limit share a status code
  and need opposite responses. `is_quota_exhausted()` classifies them by wording;
  quota is fatal, rate limit retries.
- **`batch_size: 20`** — a chapter is 12 requests, not 29. At 8 per batch it
  cannot fit any free tier.
- **`requests_per_minute: 8`** — `RatePacer` spaces calls so 12 requests cannot
  trip a per-minute ceiling. Retry-then-fail is the wrong shape for this.
- **Free tier means no SLA and no privacy.** Google may train on free-tier
  prompts. Fine for a personal project, not for anything else.

## Kaggle layer gotchas

- **`ChatterboxTurboTTS` import path:** In `chatterbox-tts`, the turbo class lives in
  `chatterbox.tts_turbo`, not the root package `__init__.py`.
- **`torchvision::nms` crash on Kaggle:** Kaggle's pre-installed `torchvision`
  conflicts with its `torch` build, which breaks `transformers` during `LlamaModel`
  import. `main.py` uninstalls `torchvision` and disables its check.
- **`sendit.sh` & `upload.sh`:** Provides reliable HTTP PUT upload and plain GET
  download for the payload archive.
- **`uv` & permanent storage:** `ensure_dependencies()` detects cached `.whl`
  files under `/kaggle/input/` for instant offline installs via `uv`.

## Using subagents

Delegate aggressively, and in parallel. Things that split cleanly:

- **Reviewing contact sheets.** Each sheet is independent, and visual review is
  exactly the bottleneck. Spawn one subagent per 8-10 pages with the colour code
  from above and ask for the pages with orange or purple boxes. This is the
  single highest-value use of parallelism here.
- **Evaluating an alternative free provider.** Wiring Groq or NVIDIA NIM into
  `LLMProvider` touches one file each and is fully independent of the other.
  Let one subagent probe availability and rate limits while another reads the
  provider interface.
- **Writing tests for a module while you implement it.** Give the subagent the
  public surface and the failure it must prevent, not the implementation.
- **Auditing prompts against the schema.** A subagent can check every field in
  `PANEL_SCHEMA` is produced by `panel_description.md` and consumed by
  `storyboard.md`. See `docs/llm-stages.md` for the full list of parallel work
  on these two stages.

Do not delegate: the reasoning behind *why* the dialogue mechanisms exist. That
context is above, and a subagent that lacks it will happily delete a mechanism
that looks redundant.

## If you get stuck

- `manga_recap check` — verifies keys, weights, Kaggle, prompts
- `manga_recap status ch01` — what is done, what is next
- The stage docstrings explain *why*, not just what. Read them.
- Stage 2 is the first stage that calls an API. Stages 0, 1, 5, 6 need no
  credentials, so almost everything except `describe` and `script` is testable
  without a working key.
