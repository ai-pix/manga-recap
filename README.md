# Manga Recap

Turns manga chapter pages into a narrated recap video, automatically.

Point it at a folder of chapter pages or a PDF. It cuts the pages into panels, has
a vision model read every panel, writes a funny third-person storyboard against
those panels, narrates the whole chapter in one continuous pass with Chatterbox
Turbo, times each narration beat against the audio, and renders a 1080p video
with the right panel on screen at the right moment.

```
pages in ──▶ panels ──▶ descriptions ──▶ storyboard ──▶ narration ──▶ video out
           (local)     (VLM API)        (LLM API)      (Kaggle)    (Kaggle)
```

---

## How the pieces fit

The hard part of this project is not any single stage. It is that the audio is a
stream of time while the pictures are seventy separate files, and nothing
connects them. The design decisions below all follow from that.

**The script is a storyboard, not prose.** Each narration line names the panels
it plays over, decided while the story is being written, when the panel
descriptions are still in context. A separate "match the narration to panels"
pass afterwards would be guessing from memory.

**The vision model describes before the writer writes.** `03_descriptions.json`
is a strictly factual record of what is in each panel. The script stage is the
only one allowed to be funny. Keeping them apart is what stops the vision stage
from editorialising and the writer from inventing panels that do not exist.

**Narration is one continuous pass.** Synthesising per block would give exact
timings for free, but it produces audible seams and a robotic cadence at every
boundary. One pass sounds like a person. The cost is that the audio no longer
knows where block twelve starts, so `aligner.py` works that out afterwards.

**Whisper is used for timing, not for truth.** It will render "Kidan" as
"Kidding" and drop filler words, so its transcript is not the source of truth;
the script is. The aligner matches the known script text against the recognised
words as sequences, which absorbs isolated recognition errors instead of
propagating them. When the match ratio is poor, blocks fall back to
character-ratio timing and are marked so you can see which parts to redo.

**The video cuts on clauses, and every cut is anchored to a spoken word.**
`render/sync.py` is the only place allowed to decide when a panel appears. It
splits each narration block at sentence ends and clause boundaries, binds each
clause to one panel, and reads that clause's window from the word-level timings
in `06_timeline.json`. So the picture changes on the word that introduces it,
rather than on a fraction of elapsed time. The shot list is then made to tile
the audio exactly — every shot runs until the next one starts, the last ends at
the audio's end — which is why the video cannot drift away from the narration.

The failure this replaces is worth naming: an earlier renderer derived each cut
from the sum of the durations before it, which silently discarded the silence
between blocks. Chapter 01 rendered 603.4s against 633.6s of narration, running
progressively ahead and cutting off the last 30 seconds of voice.

**Rendering does no work per frame.** Each panel is composed once into a single
finished frame — scaled to size, with a blurred copy of itself as the backdrop
so there are no letterbox bars — and the encoder then holds that still. Ken
Burns, when enabled, is a `crop` sliding across an oversized still. Blurring a
64-pixel-wide copy of the panel and scaling it back up looks identical to a
full-resolution blur and costs almost nothing, because a blurred backdrop has no
detail to lose. An earlier version ran `boxblur` over two megapixels on every
frame and it dominated the entire render.

**TTS and render are separate Kaggle GPU kernels.** Re-rendering after a visual
tweak is routine, and audio synthesis is the expensive half. Splitting them means
tweaking the visual look only takes a quick ~30-45s GPU NVENC render pass.

---

## STRICT MANDATE: 100% PURE GPU / ZERO CPU ON KAGGLE
- **Zero Heavy Compute Locally:** Your machine only runs panel detection, metadata staging, and API requests.
- **ABSOLUTE BAN ON KAGGLE CPU:** All Kaggle workloads (video rendering, TTS synthesis, Whisper alignment) must run 100% on NVIDIA GPU.
- **ZERO CPU FALLBACK:** It is strictly forbidden to fall back to CPU software encoding (`libx264`). If GPU NVENC fails, the pipeline immediately halts with an error.

---

## Requirements

- Python 3.10+ (3.12 recommended)
- A Kaggle account, with `~/.kaggle/kaggle.json` in place
- `pip install kaggle` and the Kaggle CLI on your PATH
- An API key for at least one LLM provider

All heavy GPU work happens on Kaggle GPU, never locally and never on Kaggle CPU.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[yolo]"       # the [yolo] extra pulls ultralytics for panel detection
manga fetch-models              # download the panel detector weights (~15 MB)
```

Copy `config/.env.example` to `config/.env` and add your keys. `config/.env` is
gitignored; never commit it. A real `config/.env` ships with the project, ready
to paste into.

```bash
# config/.env
GEMINI_API_KEY=...          # https://aistudio.google.com/apikey
KAGGLE_USERNAME=...         # https://kaggle.com/settings/account
KAGGLE_KEY=...
```

Then confirm everything resolves:

```bash
manga check
```

```
ok    llm.vision    gemini / gemini-2.5-flash (key AIzaS...4nOp)
ok    llm.script    gemini / gemini-2.5-flash (key AIzaS...4nOp)
ok    prompt storyboard.md
warn  series bible (only-sense-online)  absent
ok    panel detector  yolo weights at panel_detector.pt
ok    kaggle credentials  found
```

Keys are masked in the output. `KAGGLE_USERNAME` and `KAGGLE_KEY` are only
needed if you would rather not use `~/.kaggle/kaggle.json`; that file takes
precedence when both exist.

Review `config/config.yaml`. It is the single source of truth for the whole
pipeline, and every value in it is commented with what it does and when you
would change it.

## First run

```bash
# 1. Put your pages somewhere
mkdir data/chapters/ch01/00_input
copy D:/manga/01.png data/chapters/ch01/00_input/
copy D:/manga/02.png data/chapters/ch01/00_input/

#    Or a whole folder or a PDF:
manga ingest ch01 --input D:/manga/ch01

# 2. Check the cuts before spending any API money
manga crop ch01
```

Step 2 is the one worth pausing on. Open `data/chapters/ch01/02_panels/_debug/`.
Each contact sheet shows every detected panel numbered in reading order, drawn
over a faint copy of the full page so a misaligned crop is obvious. If the
numbering is wrong, the whole video is wrong. Fix `crop.detector` in
`config/config.yaml` and re-run, or hand-correct the boxes (see
[When panel detection fails](#when-panel-detection-fails)).

```bash
# 3. Once the cuts look right, run the rest
manga run ch01

# 4. Check on progress at any time
manga status ch01
```

`manga run` skips any stage whose output already exists, so it is safe to
re-run after a failure and cheap to re-run after a config change.

## Commands

| Command | What it does |
|---|---|
| `manga run <id>` | Every stage, skipping what is already done |
| `manga run <id> --from script` | Start at the script and continue to the end |
| `manga run <id> --only crop` | One stage, for iterating in isolation |
| `manga run <id> --force` | Redo everything |
| `manga status <id>` | What is done, what is next, and headline numbers |
| `manga check` | Verify API keys, model weights and Kaggle are configured |
| `manga fetch-models` | Download the panel detector weights |
| `manga ingest <id> --input D:/pages` | Normalise pages or a PDF into `01_pages/` |
| `manga crop <id> --detector opencv` | Cut panels, overriding the detector |
| `manga describe <id>` | Vision model only |
| `manga script <id>` | Storyboard only |
| `manga speak <id>` | Kaggle TTS and alignment only |
| `manga render <id>` | Kaggle render only |

## What lands where

```
data/chapters/ch01/
├── 00_input/             your pages, untouched
├── 01_pages/             normalised pages
├── 02_panels/            cropped panels, numbered in reading order
│   ├── panel_index.json  every panel's box and reading-order rank
│   └── _debug/           contact sheets - review these
├── 03_descriptions.json  what the vision model saw, panel by panel
├── 04_script.json        the storyboard: blocks, each bound to panels
├── 05_narration.wav      the continuous narration
├── 06_timeline.json      when each block is spoken
├── 06_alignment_debug.json   match ratio, expected vs actual duration
└── 07_final.mp4          the video
```

## Changing one part without touching the rest

| To change | Edit |
|---|---|
| The narrator's voice, jokes, references | `config/prompts/storyboard.md` |
| What the vision model records | `config/prompts/panel_description.md` |
| Which LLM, and which model | `llm.vision.*` / `llm.script.*` in `config.yaml` |
| Script length, pacing | `script.target_words` in `config.yaml` |
| Panel detection, and how it reads the page | `crop.*` and `yolo_crop.*` in `config.yaml` |
| The TTS voice | `tts.voice` in `config.yaml`, or `kaggle/kernel_tts_align/tts_engine.py` |
| How narration is timed | `kaggle/kernel_tts_align/aligner.py` |
| The look of the video | `src/manga_recap/render/kenburns.py` |
| The ffmpeg graph | `src/manga_recap/render/ffmpeg.py` |
| Resolution, fps, quality | `render.*` in `config.yaml` |

Vision and script providers are independent, so you can read panels with one
vendor and write with another:

```yaml
llm:
  vision: { provider: gemini,  model: gemini-2.5-flash }
  script: { provider: anthropic, model: claude-opus-4-5 }
```

### The series bible

`data/series/<name>/series.md` is optional and is the single biggest lever on
narration quality. It carries character names, running gags, tone boundaries,
and a running summary of what has happened so far. Without it the writer cannot
use a real name or set up a callback from three chapters ago. It ships with a
template explaining what each section is for.

## When panel detection fails

Two detectors, selected by `crop.detector`:

- **`yolo`** (the default) uses `models/panel_detector.pt`, a manga panel and
  text detector trained on Manga109. It handles colour pages, splash pages and
  irregular layouts, and it filters to the panel class so detected text regions
  never become panels. Fetch the weights with `manga fetch-models`.
- **`opencv`** uses a recursive XY-cut over the white gutters. No weights, no
  download. It only works on clean B/W pages with drawn panel borders: it merges
  adjacent panels in the same row and fails on full-bleed art. Kept as a
  dependency-free fallback.

When both fail on a specific page, hand-author the boxes in
`data/chapters/<id>/02_panels/manual_boxes.json`:

```json
{
  "005.png": [[24, 24, 632, 244], [662, 24, 976, 244]]
}
```

Boxes are `[x1, y1, x2, y2]` in reading order. Re-run `manga crop <id> --force`
and it uses yours for that page and the detector for the rest.

## Troubleshooting

**`No API key for provider 'x'`** — copy `config/.env.example` to `config/.env`
and fill it in. Real environment variables override the file.

**`Chatterbox Turbo is running on CPU`** — stage 4 is meant to run on a Kaggle
GPU kernel. Confirm `enable_gpu: true` in
`kaggle/kernel_tts_align/kernel-metadata.json` and that your Kaggle account has
GPU quota left.

**Panels are out of order** — reading order is derived, so check the contact
sheets. `crop.reading_direction: ltr` flips it for left-to-right sources.

**Panels desync from the narration** — check
`06_alignment_debug.json`. If `match_ratio` is low, Whisper struggled with the
audio and the timing is a fallback estimate. Blocks that fell back are recorded
as `method: fallback_proportional` in `06_timeline.json`. Raising
`align.whisper_model` quality, or lowering `tts.voice.mode` pacing, usually helps.

**A Kaggle kernel failed** — stage 4 and 5 log the kernel id and write a failure
note to `logs/`. Get the full log with:

```bash
kaggle kernels output YOUR_USERNAME/manga-recap-tts -p logs/
```

**Kaggle quota exhausted** — reported clearly rather than hanging. Wait for the
weekly GPU quota to reset.

## Tests

```bash
pip install -e ".[dev]"
pytest -q
```

The suite covers the parts where a silent failure would be expensive: right-to-
left reading order, panel detection against synthetic manga pages, the aligner
against known ground-truth timings including misheard words, the storyboard
validator, schema round-trips, the ffmpeg graph (including a real encode when
ffmpeg is installed), and pipeline resume.

## Scope

Built for roughly 15-page chapters, about 70 panels, around 4,000 words of
narration, and a 20-minute 16:9 video. Larger chapters work but approach Kaggle's
12-hour session limit during narration.

Deliberately not in this version: burned-in captions, background music (wired
and off), sound effects, voice cloning (the hook is in `tts_engine.py`), 9:16
output, and thumbnails.
