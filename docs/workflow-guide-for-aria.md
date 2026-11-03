# Production Workflow Guide for Aria (Voiceover, Timeline & Rendering)

This guide is the **single operational standard** for Aria when executing Stage 4 (Voiceover & Timelines), Stage 5 (GPU Rendering), and multi-chapter compilation stitching.

---

## 🚫 The 4 Critical Traps to Avoid

1. **NEVER use Proportional Length Division for Timing:**
   - Panel cuts MUST be anchored to the Whisper forced alignment word timestamps in `06_timeline.json`.
   - Proportional interpolation shifts cuts by 1–3s, making the screen show the wrong character while speaking.
2. **NEVER Discard Inter-Block Silence Gaps:**
   - Videos must account for the 0.3s silence pauses between blocks. Summing panel durations without silence gaps causes the video to finish 30–60 seconds before the audio ends.
3. **NEVER Fall Back to CPU Encoding (`libx264`, `veryfast`):**
   - Rendering on Kaggle MUST use NVIDIA T4 hardware NVENC (`engine: pynv`, `h264_nvenc`) at 355+ FPS.
   - If GPU NVENC fails, fail immediately—never allow a 10-hour CPU fallback.
4. **NEVER Re-Encode Pre-Rendered Chapters:**
   - Pre-rendered chapters already share identical 1080p 24fps NVENC specs.
   - Always use `scripts/instant_stitch.py` (`-c copy`) for compiling full movies in seconds.

---

## 📋 The 3-Step Production Workflow

### Step 1: Voiceover & Forced Word Alignment (Stage 4)
* **Script Input:** Finalized `04_script.json` (certified by Gemini & AI Gatekeeper).
* **Synthesis:** Concurrently dispatch Fish Audio API (`s2.1-pro-free` or approved voice ID):
  ```powershell
  .venv\Scripts\python.exe scripts/batch_speak_<series>_parallel.py
  ```
* **Alignment:** Whisper large-v3 generates `06_timeline.json` with word-level millisecond timestamps for every spoken beat.
* **Invariant:** Every `beat.text` is anchored to its spoken start word.

### Step 2: Quad-Instance Kaggle GPU NVENC Batch Render (Stage 5)
* **Standard:** Follow `kaggle/MASTER_RENDER_STANDARD.md`.
* **Execution:** Partition chapters equally across 4 GPU slots (`fabricatevisuals` + `ravidevai`):
  ```powershell
  .venv\Scripts\python.exe scripts/batch_render_<series>_quad.py
  ```
* **Speed:** 355+ FPS pure GPU NVENC (`pynv` zero-copy DLPack engine).
* **Verification:** Check `07_sync_report.json` per chapter. Must show:
  - `drift: 0.000s`
  - `problems: 0`

### Step 3: Instant Multi-Chapter Stitching (`-c copy`)
* **Tool:** `scripts/instant_stitch.py`
* **Syntax:**
  ```powershell
  .venv\Scripts\python.exe scripts/instant_stitch.py --series <series_prefix> --start 1 --end 30 --output data/movies/<series>_full_movie_ch01_ch30.mp4
  ```
* **Runtime:** ~4.5 seconds for 30 chapters (Instant stream copy with `-movflags +faststart`).
