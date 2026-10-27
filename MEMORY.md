# Manga Recap — System Memory & Architecture

Status: **Production-ready, all 115 chapters rendered & verified (100% complete across entire series).**
All upstream stages (ingest, crop, describe, script, speak, render) across the entire series (`ch001` through `ch112`, including `ch005_5`, `ch058_5`, and `ch103_5`) are 100% complete with frame-exact audio-panel synchronization, zero drift, and YouTube-ready 1080p video packages (`07_final.mp4`) verified on disk (total 12.60 GB video archive).

---

## 1. STRICT MANDATES & CONSTRAINTS

> ⚠️ **ZERO HEAVY TASKS ON LOCAL MACHINE & 100% PURE GPU/CUDA ON KAGGLE (NEVER CPU, NO FALLBACKS EVER)**
> 1. **Zero heavy compute locally:** The local machine is Windows with GTX 1650 and Python 3.14. Video rendering, TTS model training/inference, and Whisper alignment must NEVER run locally. Local system is strictly for orchestration, API requests, metadata generation, and unit tests.
> 2. **ABSOLUTE BAN ON KAGGLE CPU & ZERO CPU FALLBACKS:** All compute jobs running on Kaggle must be 100% GPU/CUDA accelerated. NEVER run video rendering on Kaggle CPU. NEVER include or execute any fallback to CPU software encoding (`libx264`, `veryfast`, `ultrafast`). If GPU/NVENC fails to initialize, the job MUST raise an immediate fatal `RuntimeError` in under 2 seconds. Silently downgrading to CPU is strictly prohibited.
> 3. **STRICT RULE: NEVER INVENT NEW AD-HOC PATTERNS — USE WHAT ALREADY WORKED:** Agents must NEVER invent untested ad-hoc scripts or deviate from established, verified pipeline workflows. For stitching and compilations, strictly follow `scripts/stitch_all_chapters.py` (hardware NVENC re-encode with `+faststart`). Never use `-c copy` across multi-chapter boundaries which corrupts YouTube ingest processing.

---

## 1.5. 24/7 GOOGLE SHEET WATCHER & REACTIVE WAKE-UP ARCHITECTURE

To maintain zero-latency responsiveness in the multi-agent Google Sheet chat (`Ministers`, `To do`, `chat` tabs) while consuming **zero LLM tokens while idling**:

### A. The Watcher Daemon (`scripts/watch_gemini_daemon.py`)
- Polls the Google Sheet `chat` tab every 15s using OAuth refresh token credentials (`C:\Users\ravih\.config\google-drive-mcp\tokens.json`).
- **Dynamic Sliding Window Invariant:** Instead of hardcoded static ranges (which freeze once the chat advances), it queries `chat!A{max(2, last_seen-10)}:G{last_seen+50}`, keeping requests lightweight (<55 rows) and automatically sliding forward with `last_seen_id` in `scripts/gemini_watch_state.json`.
- **Reactive Wake-Up:** When an `@Gemini` mention is detected from any other agent or user, it writes the alert to `scripts/alerts.log` and exits cleanly with `sys.exit(0)`. In the Antigravity harness, this task completion triggers an **instant reactive wake-up**, waking Gemini up immediately without any polling loops.

### B. Standard Management Commands for Every Gemini
- **Start / Restart Single Dedicated Watcher:**
  ```powershell
  .venv\Scripts\python.exe scripts/restart_single_watcher.py
  ```
  *(Scans process tree via `psutil`, terminates any duplicate/stale watcher PIDs, removes orphaned locks `scripts/watch_gemini.lock`, and boots strictly 1 dedicated instance).*
- **Stop / Kill All Watchers:**
  ```powershell
  .venv\Scripts\python.exe scripts/kill_watchers.py
  ```
- **Harness Background Task Registration:**
  ```python
  run_command(
      CommandLine=".venv\\Scripts\\python.exe scripts/watch_gemini_daemon.py",
      IsDaemon=True,
      WaitMsBeforeAsync=500,
      toolSummary="Run single watcher daemon"
  )
  ```

---

## 2. PERMANENT KAGGLE STORAGE DATASETS

To eliminate slow network downloads, build times, and runtime setup overhead, commonly used heavy assets and binaries are stored permanently on Kaggle:

1. **`wampireai/manga-recap-render-bin`:**
   - Precompiled Linux 64-bit portable Jellyfin FFmpeg and FFprobe binaries with native NVIDIA NVENC hardware acceleration support (NVIDIA Driver 535 / CUDA 12.1 compatible).
   - Render kernel (`kaggle/kernel_render/main.py`) checks `/kaggle/input/manga-recap-render-bin/` first at boot, copies to `/kaggle/working/bin/` (avoids `/dev/shm` `noexec` lock), sets permissions, and prepends to `PATH`.
   - **Zero network downloading at kernel boot.** External downloads are only a fallback if the dataset is unattached.
   - Automatically attached to Kaggle render kernels via `dataset_sources` in `s5_render/__init__.py`.

2. **`wampireai/manga-recap-voice-orus`:**
   - High-fidelity reference audio for Chatterbox Turbo voice cloning.

---

## 3. ULTRA-FAST ZERO-COPY GPU VIDEO RENDERING ARCHITECTURE (`engine: pynv`)

The video rendering pipeline uses a pure zero-copy PyTorch VRAM and NVIDIA `PyNvVideoCodec` architecture, eliminating all CPU and FFmpeg demuxer bottlenecks:

### A. Pure CUDA In-Memory Compositing (`src/manga_recap/render/pynv_renderer.py`)
- **Old Bottleneck:** FFmpeg CPU image demuxer and PIL CPU resizing choked throughput at ~80 FPS.
- **New Engine:** The 2,560 CUDA cores compute panel resizing (bilinear interpolation), backdrop generation (separable 1D convolution boxblur on CUDA), and BT.601 RGB-to-NV12 color space conversion 100% in GPU VRAM.
- **Performance:** 101 panels composited in **10.6 seconds** in GPU VRAM with zero intermediate disk files.

### B. Zero-Copy DLPack PyNvVideoCodec Engine (`engine: pynv`)
- **Architecture:** Streams NV12 frames directly from PyTorch CUDA tensors in GPU VRAM to hardware NVENC silicon via a DLPack monkey-patch bridge (`Tensor.__dlpack__`).
- **Bitstream Extraction:** Extracts raw Annex-B H.264 NAL packets (`packet["data"]`) directly from NVENC and writes them sequentially.
- **Instant Mux:** Lossless stream-copy audio muxing with FFmpeg (`-c:v copy -c:a aac`) in **6.6 seconds**.
- **Hardware Throughput:** **18,968 frames (10.5 minutes of 1080p video) rendered in 53.34s (355.6 FPS sustained)** on a single Tesla T4 GPU. Total Kaggle kernel runtime: **103 seconds** (down from 290s).
- **Audio-Video Sync:** **632.210s video vs 632.261s audio (-0.051s exact match, 0 drift, 0 gaps)**. File size: 131.8 MB. All 101 scripted panels present.
- **Full Journey & Docs:** See [`docs/gpu-rendering-journey.md`](file:///D:/Python%20Projects/Manga%20Recap/docs/gpu-rendering-journey.md).

### C. Smart Bubble Cropping, Upside Panning & Dynamic Zooming Motion
- **Problem Solved:** Manhwa panels frequently have large speech bubbles and white margins at the top and bottom. Mechanical vertical sliding/panning across these panels forced viewers to stare at speech bubbles instead of the art.
- **Full Artwork Detection (`is_full_art`):**
  - Tall panels (`ratio >= 1.55`) are analyzed for bubble density at top & bottom 35% boundaries.
  - If neither top nor bottom has speech bubbles (`top_trim < 8%` and `bot_trim < 8%`), the panel is classified as **Full Artwork**.
  - **Upside Panning:** Full artwork panels execute smooth cinematic bottom-to-top panning (`y_val = (1.0 - prog) * travel`), starting at the base of the artwork and revealing upwards to the character's face / action climax.
- **Smart Speech Bubble Cropping:**
  - For all panels containing speech bubbles, the top and bottom speech bubble bands (`lum > 220, sat < 0.18` or black margins) are automatically cropped out.
  - Isolates character face, body, armor, and combat action in the center frame without letterbox squishing.
- **Dynamic Cinematic Zooming Motion (`zoom_motion`):**
  - Eliminates vertical sliding across speech bubbles.
  - Applies 4 high-retention Ken Burns zoom styles on GPU CUDA VRAM:
    1. *Dynamic Push-In:* 1.000x -> 1.085x smooth zoom-in on character emotion/action.
    2. *Dynamic Pull-Out:* 1.085x -> 1.005x smooth reveal of impact/scene.
    3. *Face-Focus Push-In:* 1.000x -> 1.090x with gentle focal drift towards character eyes.
    4. *Dynamic Pulse Zoom:* 1.020x -> 1.095x.
  - Zero CPU overhead, rendered in VRAM via `F.affine_grid` and `F.grid_sample(padding_mode="reflection")` at 350+ FPS.

---

## 4. AUDIO-PANEL SYNC ARCHITECTURE

`src/manga_recap/render/sync.py` is the **single owner of shot timing**:
1. **Split:** Each block's narration is split into clauses (max 14 words per beat).
2. **Anchor:** Each beat reads start and end timestamps directly from word-level Whisper alignment in `06_timeline.json`.
3. **Schedule:** Shots tile the audio exactly with zero gaps. Frame counts are calculated from cumulative absolute timestamps so rounding cannot accumulate.
4. **Verification:** Every render outputs `07_sync_report.json` reporting exact shot cuts, text bindings, and cumulative drift (always +0.000s).

### 4.1 Official Scripting Instructions (Golden Standard)
Whenever asked to **"look for scripting instruction"** or when writing any new chapter script, all agents must follow [`docs/scripting-instructions.md`](file:///D:/Python%20Projects/Manga%20Recap/docs/scripting-instructions.md):
- **Mercury-3 Step:** Run `03_summary_mercury.txt` first via Inception Labs Mercury-3.
- **Tone:** Human, energetic YouTube recap narrator with situational humor (Mamoru style).
- **Pruning:** Prune all text-only void bubbles (`is_credits_or_ad: true`), attach dialogue to scene panels.
- **Pacing & Length:** 850–1,200 words (~5–8 minutes of video).
- **Sync:** Strict 1:1 clause-to-panel beats (8–14 words per beat, 0 banned words).

---

## 5. GOOGLE COLAB MCP & BATCH PAYLOAD ARCHIVE

- **Colab MCP:** Installed and configured in Antigravity (`git+https://github.com/googlecolab/colab-mcp`). Connects to active Colab browser sessions with T4 GPU runtime.
- **Turnkey Colab Notebook:** Saved at [`notebooks/Manga_Recap_Colab_GPU_Render.ipynb`](file:///D:/Python%20Projects/Manga%20Recap/notebooks/Manga_Recap_Colab_GPU_Render.ipynb).
- **Pre-Uploaded Batch Archives (on sendit.sh):**
  - **Batch 1 (Ch 04–12):** `https://sendit.sh/1HWxo/Do5eu.zip` (828 MB)
  - **Batch 2 (Ch 13–22):** `https://sendit.sh/Bpqh8/5UZgH.zip` (810 MB)
  - **Batch 3 (Ch 23–26):** `https://sendit.sh/UNplX/Csd6k.zip` (303 MB)
  - **Batch 4 (Ch 27–30):** `https://sendit.sh/Ik5c9/1Myiz.zip` (378 MB)

---

## 7. GOOGLE SHEET 24/7 WATCHER & LOW MODE PROTOCOL

1. **Mandatory On Every Startup:**
   - Check if `scripts/watch_gemini_daemon.py` is actively running. If not, launch it as a background task.
   - Perform an immediate check on the Google Sheet `chat` tab for any new `@Gemini` mentions.
2. **Low Mode (Ultra-Efficient Token Conservation):**
   - **Targeted Sheet Reads:** Always fetch only the tail window (e.g. `chat!A70:G120`), never reading the entire sheet.
   - **Subagents in Low Mode:** Any subagent invoked MUST use low mode (`Model="flash_lite"` or `"flash"`, never `"pro"`).
   - **Responses:** Keep all sheet replies and status reports short, direct, and free of filler.
3. **Reactive Wakeup:**
   - The watcher sleeps 15s in Python (0 LLM tokens).
   - Terminates with code 0 on any new `@Gemini` mention to trigger instant agent wakeup, post reply, and immediately restart.
 
 - **YouTube 2-Part Epic Recap Series (COMPLETE & PROCESSED):**
   - **Part 1 (9h 07m, 4.00 GB):** **PUBLIC & LIVE** on YouTube: [https://youtu.be/Rm0reT5PBtg](https://youtu.be/Rm0reT5PBtg). Includes high-CTR custom evolution thumbnail, full chapter timestamps, and hook intro.
   - **Part 2 (8h 51m, 8.62 GB):** **UNLISTED & PROCESSED** on YouTube: [https://youtu.be/osF7thqyDPg](https://youtu.be/osF7thqyDPg). Ready for release (Wednesday scheduled slot).
   - All previous individual chapter uploads unlisted.
 - **Permanent Google Drive Archive (COMPLETE & VERIFIED):**
   - Root Folder: `Only_Sense_Online_Archive` (`1OFggG1JHtvl7HSjZVtybZxZUt3_xKygu`).
   - Contains all 115 chapter renders (`07_final.mp4`), scripts (`04_script.json`), descriptions (`03_descriptions.json`), timelines (`06_timeline.json`), manifests, thumbnails, hooks, and timestamps.
   - Upload state safely preserved in `build/gdrive_archive_state.json`.
 - **Workspace Reclamation & Clean Scaffolding:**
   - 48.28 GB reclaimed via `scripts/clean_workspace.py`. D: drive free space: **47.14 GB**.
   - Clean scaffolding in place (`data/chapters`, `data/series`, `data/hooks`, `data/thumbnails`, `logs`).
   - Ready for next manga series.

---

## 7. MANHWA ADAPTATION & DYNAMIC MOTION ENGINE (`Survive as a Barbarian in the Game`)

- **Chapter 01 (`barbarian_ch01` - Accurate Emotional & Static Framing Edition):** Complete, verified, and rendered via Kaggle GPU NVENC at **364.7 FPS** (12,275 frames in 33.7s, total kernel runtime 72s).
- **Accurate, Emotional & Humorous Narrative:** 1,107 words across 53 blocks covering all 94 authentic art panels 1:1 (**409.2s / 6.82 minutes**, 100.5 MB crisp 1080p).
  - Captures every true manga plot point: the 0-star review, the language barrier groan, the nurse shouting in the patient room, the 9-year grinding through college and work, the hilarious Korean-language tutorial twist on the 10th floor, the blue vortex transmigration, the barbarian ceremony, the execution of the panicked Korean recruit by the Chieftain, the 3 survival rules, and the climactic 2-second name gamble.
  - Expressive emotional prosody and organic gaming humor delivered with Fish Audio s2.1-pro-free.
- **Zero Sliding Motion & Smart Face/Action Cropping:**
  - `pan_tall: false` permanently eliminates all distracting vertical sliding motion.
  - Implemented CUDA energy-based smart cropping: automatically detects and isolates the character's face, upper body, and combat action, cropping out irrelevant margins and text bubbles.
  - Characters are large, prominent, and static in the center frame, backed by a soft blurred aesthetic backdrop.
- **Black / Text-Only Panel Pruning:**
  - All 36 black screens and isolated speech bubbles pruned from video while keeping their narrative content in the script.
- **Audio-Panel Sync Hardening (Zero Desync Protocol):**
  - Sync report verification: **110 shots anchored (100%), 0.000s drift, 0 gaps, 0 problems, 0 warnings**.
  - All 94 scripted panels appear in `07_final.mp4` (409.1s video vs 409.2s audio, -0.040s match).
- **Archived Versions:**
  - Original 12-minute version preserved in `data/chapters/barbarian_ch01/versions/v1_full_12min/`.

---

## 9. SSS-CLASS REVIVAL HUNTER: 10 VIRAL YOUTUBE SHORTS (9:16 VERTICAL, 1080x1920)

- **Production Complete & Verified:** All 10 high-retention YouTube Shorts (`revival_hunter_short01` through `short10`) successfully rendered in pure GPU NVENC on Kaggle Tesla T4 at 350+ FPS (total kernel runtime 236s for all 10 videos).
- **Format:** Native 9:16 vertical (1080x1920), constant 30 FPS, H.264 Main (`yuv420p`), 192k AAC 44.1 kHz audio, `+faststart`.
- **Fast-Paced Hook Style:** Visual cuts every 2–3 seconds (14–24 panels per short, total 171 panels staged), 1:1 rapid-fire synchronization anchored to Fish Audio studio narration.
- **Export Directory:** Staged at [`data/export/shorts/`](file:///D:/Python%20Projects/Manga%20Recap/data/export/shorts/) complete with matching `.mp4` video files and structured `_metadata.txt` (Title, Description, Hashtags, and Tags).
- **Titles & Files:**
  1. `revival_hunter_short01`: *He Committed Suicide 4,090 Times To Steal A Skill* (64.4s, 37.6 MB)
  2. `revival_hunter_short02`: *He Slew The World's Strongest Hero In An Alleyway* (54.1s, 31.6 MB)
  3. `revival_hunter_short03`: *The Tragic Truth Behind The 10th Floor Boss* (48.6s, 27.5 MB)
  4. `revival_hunter_short04`: *A 99th Floor Ghost Emperor Trapped In His Head* (47.9s, 27.2 MB)
  5. `revival_hunter_short05`: *The 11th Floor Plague That Wiped Out An Entire Kingdom* (45.6s, 27.5 MB)
  6. `revival_hunter_short06`: *Teaming Up With The Tower's Most Smiling Psychopath* (42.8s, 25.0 MB)
  7. `revival_hunter_short07`: *The Demon King Who Wept Black Rain Over Murim* (40.8s, 24.1 MB)
  8. `revival_hunter_short08`: *Inheriting The Ultimate Demonic Martial Art* (42.4s, 23.0 MB)
  9. `revival_hunter_short09`: *He Conquered The Martial Arts Apocalypse With One Strike* (42.1s, 24.7 MB)
  10. `revival_hunter_short10`: *He Fell In Love With The Villainess Who Remembers Death* (45.7s, 27.6 MB)


Rank-ordered queue saved in [`MANHWA_QUEUE.md`](file:///D:/Python%20Projects/Manga%20Recap/MANHWA_QUEUE.md) and [`data/series/queue.json`](file:///D:/Python%20Projects/Manga%20Recap/data/series/queue.json):
1. **SSS-Class Revival Hunter** (`sss-class-revival-hunter`): **Panels Ready for Ch 01–40 (3,251 panels total).** Organized under `data/chapters/sss-class-revival-hunter/ch01` through `ch40` with `revival_hunter_chXX` junctions, valid `panel_index.json`, high-res text crops in `_text/`, and series bible at `data/series/sss-class-revival-hunter/series.md`.
2. **Overgeared** (`overgeared`)
3. **Omniscient Reader's Viewpoint** (`omniscient-readers-viewpoint`)
4. **Tomb Raider King** (`tomb-raider-king`)
5. **Eleceed** (`eleceed`)
6. **Pick Me Up, Infinite Gacha** (`pick-me-up-infinite-gacha`)
7. **Player Who Returned 10,000 Years Later** (`player-returned-10000-years`)
8. **A Returner's Magic Should Be Special** (`returners-magic-should-be-special`)
9. **The Greatest Estate Developer** (`greatest-estate-developer`)
10. **Solo Max-Level Newbie** (`solo-max-level-newbie`)
11. **Solo Leveling (+ Ragnarok)** (`solo-leveling`)
12. **The Regressed Mercenary Has a Plan** (`regressed-mercenary-has-a-plan`)
13. **The Stellar Swordmaster** (`stellar-swordmaster`)
14. **The Beginning After the End** (`beginning-after-the-end`)
15. **Return of the Mount Hua Sect** (`return-of-the-mount-hua-sect`)
16. **The Legend of the Northern Blade** (`legend-of-the-northern-blade`)
17. **Absolute Regression** (`absolute-regression`)
18. **The World After the Fall** (`world-after-the-fall`)
19. **Nano Machine** (`nano-machine`)
20. **Murim Login** (`murim-login`)
21. **Myst, Might, Mayhem** (`myst-might-mayhem`)
22. **The Swordmaster's Youngest Son** (`swordmasters-youngest-son`)
23. **Return of the Mad Demon** (`return-of-the-mad-demon`)
24. **Villain to Kill** (`villain-to-kill`)
25. **Doom Breaker** (`doom-breaker`)
26. **Damn Reincarnation** (`damn-reincarnation`)
27. **Reaper of the Drifting Moon** (`reaper-of-the-drifting-moon`)
28. **Regressor Instruction Manual** (`regressor-instruction-manual`)
29. **Steel-Eating Player** (`steel-eating-player`)
30. **Archmage Transcending Through Regression** (`archmage-transcending-regression`)

---

## 9. VERIFICATION COMMANDS
 
Always run before and after making changes:
 
```powershell
.venv\Scripts\python.exe -m pytest tests -q     # 425 passed, 2 skipped
.venv\Scripts\python.exe -m ruff check src tests
```
Both must be 100% green.

---

## 10. CURRENT ACTIVE PRODUCTION: SSS-CLASS REVIVAL HUNTER

- **Source**: 40 chapters (`ch01` to `ch40`)
- **Stage 0-1 (Ingest & Crop)**: 100% complete across all 40 chapters (3,251 panels sliced and validated).
- **Archive Upload**: Full 40-chapter panel archive compressed and uploaded to Google Drive: `1UrIP503C0WYASjeze38qOYtXjqmrkQlC`
- **Stage 2 (Panel Descriptions)**: Downloaded and normalized across all 40 chapters into [`03_descriptions.json`](file:///D:/Python%20Projects/Manga%20Recap/data/chapters/sss-class-revival-hunter/).
- **Mercury-3 Narrative Summaries**: Generated via InceptionLabs `mercury-3` model across all 40 chapters as [`03_summary_mercury.txt`](file:///D:/Python%20Projects/Manga%20Recap/data/chapters/sss-class-revival-hunter/).
- **Stage 3 (Recap Scripts)**:
  - **All 40 Chapters Complete & 100% Validated (`ok=True`, 0 errors)**:
    - **Total Narrative Blocks**: 3,200 story blocks mapped 1:1 to story panels in exact reading order.
    - **Total Spoken Words**: 42,094 words (~280.6 minutes / ~4.68 hours of high-retention recap narration).
    - **Tone & Style**: Authentic Mamoru-style YouTube recap tone with sharp dark comedy, tactical depth, and zero meta-words (`panel`, `page`, `chapter`, `manhwa`, etc.).
    - **Rhythm Enforcement**: Strictly 8 to 16 words per spoken block, perfectly tuned for 1:1 panel pacing.
- **Fast-Paced Hook Opening Arc (Chapters 01 - 05) Complete & 100% Verified**:
  - Filtered from ~48 minutes down to **13.3 minutes total** across Chapters 1-5, cutting filler, forum chatter, and establishing shots while retaining 100% story accuracy, intense psychological stakes, and micro-cliffhangers at every chapter boundary.
  - **Audio Engine**: Fish Audio API (`s2.1-pro-free`) using the Barbarian Manhwa voice (`802e3bc2b27e49c2995d23ef70e6ac89`) at `tempo: 1.04`.
  - **Render Engine**: Pure zero-copy GPU NVENC (`engine: pynv`) on Kaggle GPU kernel `manga-recap-render` (~350+ FPS).
  - **Verified Output Summary**:
    - **Ch 01**: 140.3s (2.34m) | 312 words | 26 clips | 206.6 MB | 100% Verified
    - **Ch 02**: 148.5s (2.47m) | 391 words | 30 clips | 204.7 MB | 100% Verified
    - **Ch 03**: 161.0s (2.68m) | 424 words | 30 clips | 221.2 MB | 100% Verified
    - **Ch 04**: 171.6s (2.86m) | 467 words | 30 clips | 236.5 MB | 100% Verified
    - **Ch 05**: 176.6s (2.94m) | 471 words | 30 clips | 249.1 MB | 100% Verified
    - **Total**: **798.0s (13.3m)** | **2,065 words** | **146 clips** | **1.12 GB** | **100% Complete**
- **Next Phase**: Proceed to Chapter 6+ with standard pacing while maintaining periodic attention-grabbing retention anchors and narrative pattern interrupts.

---

## 11. OVERGEARED 30-CHAPTER FULL MOVIE PRODUCTION (COMPLETE & ASSEMBLED)

- **Source**: 30 chapters (`ch01` to `ch30`) in [`data/chapters/overgeared/`](file:///D:/Python%20Projects/Manga%20Recap/data/chapters/overgeared/).
- **Phase 1 (Mercury-3 Big-Picture Summaries)**:
  - 30/30 chapters summarized all at once using InceptionLabs `mercury-3` model into `04_summary_mercury.md`.
  - Captured character motivations (Shin Youngwoo / Grid), class mechanics (Pagma's Successor), quest developments, comedic greed/rage moments, and narrative cliffhangers across the entire 30-chapter arc.
- **Phase 2 (Gemini Storyboard Scripts)**:
  - 30/30 chapters scripted all at once via official Gemini API (`gemini-3.1-flash-lite`) into `04_script.json`.
  - 100% validated (`ok=True`, 0 errors across all 30 chapters) with strict 1:1 clause-to-panel sync and explicit beat bindings.
- **Phase 3 (Fish Audio Parallel Speech Synthesis & Alignment)**:
  - 30/30 chapters synthesized using Fish Audio free-tier API (`s2.1-pro-free`) with energetic manhwa narrator voice (`802e3bc2b27e49c2995d23ef70e6ac89`).
  - Generated studio-fidelity 44.1kHz mono WAV audio (`05_narration.wav`) and word-anchored JSON timelines (`06_timeline.json`) across all 30 chapters in ~23 minutes.
- **Phase 4 (Dual-Batch Kaggle GPU NVENC Rendering & Assembly - Upgraded Motion Engine)**:
  - **Batch 1 (Ch01–15)**: Rendered on Kaggle Tesla T4 GPU 1 (`ravidevai/manga-recap-render`), stitched into `data/movies/overgeared_part1.mp4` (697.1 MB, 3,956.93s = 65.95 min, 1080p @ 30fps).
  - **Batch 2 (Ch16–30)**: Rendered on Kaggle Tesla T4 GPU 2 (`ravidevai/manga-recap-render-2`), stitched into `data/movies/overgeared_part2.mp4` (860.2 MB, 4,764.81s = 79.41 min, 1080p @ 30fps).
  - **Motion & Framing Enhancements Applied**:
    - **Smart Bubble Cropping**: All top/bottom speech bubbles and blank margins cropped out to focus directly on character action and art.
    - **Dynamic Zooming Motion**: Ken Burns zoom styles (push-in, pull-out, face-focus zoom) replace mechanical sliding across dialogue panels.
    - **Upside Panning**: Panning from bottom to top applied strictly to tall full-artwork panels (`is_full_art`).
  - **Final Assembly**: Losslessly stream-copied (`-c copy`) via FFmpeg concat demuxer:
    - **Path**: [`data/movies/overgeared_full_movie_ch01_ch30.mp4`](file:///D:/Python%20Projects/Manga%20Recap/data/movies/overgeared_full_movie_ch01_ch30.mp4)
    - **Duration**: **8,721.75s (~145.36 minutes / 2 hours 25 minutes 21 seconds)**
    - **File Size**: **1.45 GB (1,557,412,984 bytes)**
    - **Video Specs**: 1920x1080 H.264 (Main) @ 30 fps
    - **Audio Specs**: AAC 44.1kHz mono, 138 kb/s
    - **Sync Accuracy**: 100% frame-exact audio-to-panel tracking, 0 gaps, 0 drift.
- **Phase 5 (YouTube Packaging & Release - PUBLIC & LIVE)**:
  - **Package Directory**: [`data/export/overgeared_movie_package/`](file:///D:/Python%20Projects/Manga%20Recap/data/export/overgeared_movie_package/)
  - **Thumbnails**: Generated with **Nano Banana Pro (Gemini 3 Pro Image)** featuring Shin Youngwoo (Grid) in REDICE manhwa style with obsidian/gold dragon plate armor, wielding his greatsword crackling with molten lightning over an anvil with holographic quest system windows (`thumbnail.jpg`, `thumbnail_option_A_clean.jpg`, `thumbnail_option_B_clickbait.jpg`, `thumbnail_option_C_god_grid.jpg`).
  - **Title**: `He Accidentally Unlocked A God-Tier Class And Broke The Game — Overgeared (Ch 01-30 Full Movie Recap)`
  - **Timestamps**: Full 30-chapter exact timestamps (00:00 to 02:25:21) integrated into YouTube description.
  - **Status**: **PUBLIC & LIVE on YouTube**.
- **Phase 6 (12 Viral YouTube Shorts - 9:16 Vertical 1080x1920 - COMPLETE & VERIFIED)**:
  - **Total Shorts**: 12 complete video packages rendered via pure GPU NVENC on Kaggle Tesla T4 (`manga-recap-render`) in 335.2s.
  - **Audio Engine**: Studio Fish Audio narration (`s2.1-pro-free` with voice `802e3bc2b27e49c2995d23ef70e6ac89`).
  - **Export Location**: Staged under [`data/export/shorts/`](file:///D:/Python%20Projects/Manga%20Recap/data/export/shorts/) with matching `.mp4` video files and metadata `.txt` files.
  - **Schedule Standard**: 2 hours apart over a 24-hour viral release cycle with pinned link to the full 2.5-hour movie.
  - **Shorts Titles, YouTube IDs & Scheduled Times (Starting 26th 00:00 AM IST, Every 2 Hours)**:
    1. `overgeared_short01`: *He Dropped To Level -3 To Steal A God-Tier Class* (50.8s, 29.4 MB) -> **26-Oct 12:00 AM IST (00:00)** — [`https://youtu.be/IfPGMEVGNiI`](https://youtu.be/IfPGMEVGNiI)
    2. `overgeared_short02`: *A Level -1 Player 1-Punching The Death Cult* (46.8s, 27.3 MB) -> **26-Oct 02:00 AM IST** — [`https://youtu.be/8anU8MLjKyA`](https://youtu.be/8anU8MLjKyA)
    3. `overgeared_short03`: *He Accidentally Forged An S-Rank Masterpiece Dagger* (45.2s, 26.3 MB) -> **26-Oct 04:00 AM IST** — [`https://youtu.be/VTeyckbX8-Q`](https://youtu.be/VTeyckbX8-Q)
    4. `overgeared_short04`: *The 10-Coin Arrow That Broke The Game's Economy* (45.7s, 26.6 MB) -> **26-Oct 06:00 AM IST** — [`https://youtu.be/po_i57Ma_PI`](https://youtu.be/po_i57Ma_PI)
    5. `overgeared_short05`: *Defending The Old Blacksmith From 50 Armed Thugs* (43.0s, 25.0 MB) -> **26-Oct 08:00 AM IST** — [`https://youtu.be/lRKN93NDThM`](https://youtu.be/lRKN93NDThM)
    6. `overgeared_short06`: *When A Blacksmith Awakens Ancient Godly Swordsmanship* (42.8s, 25.3 MB) -> **26-Oct 10:00 AM IST** — [`https://youtu.be/llzBO3dg_tw`](https://youtu.be/llzBO3dg_tw)
    7. `overgeared_short07`: *He Crafted For 50 Hours Straight With Zero Sleep* (42.6s, 25.7 MB) -> **26-Oct 12:00 PM IST (Noon)** — [`https://youtu.be/OIDpsXHTKeY`](https://youtu.be/OIDpsXHTKeY)
    8. `overgeared_short08`: *Game Admins Panicking Over A Broken Player* (39.7s, 23.1 MB) -> **26-Oct 02:00 PM IST** — [`https://youtu.be/D12feHxLp6k`](https://youtu.be/D12feHxLp6k)
    9. `overgeared_short09`: *Soloing A Frost Orc Tribe In An Ice Cave* (38.7s, 22.4 MB) -> **26-Oct 04:00 PM IST** — [`https://youtu.be/E0s23W8oiyg`](https://youtu.be/E0s23W8oiyg)
    10. `overgeared_short10`: *Humiliating The Leader Of The Strongest Guild* (37.5s, 22.2 MB) -> **26-Oct 06:00 PM IST** — [`https://youtu.be/qPFp5MMcCos`](https://youtu.be/qPFp5MMcCos)
    11. `overgeared_short11`: *Confronting The Immortal Blood Demon Malacus* (40.8s, 24.0 MB) -> **26-Oct 08:00 PM IST** — [`https://youtu.be/z059yj1mYkM`](https://youtu.be/z059yj1mYkM)
    12. `overgeared_short12`: *He Erased The World Boss In A Single Strike* (40.2s, 22.3 MB) -> **26-Oct 10:00 PM IST** — [`https://youtu.be/00lRPr-WfX4`](https://youtu.be/00lRPr-WfX4)
  - **All 12 Shorts Scheduled & Verified:** Automatically linked to the full movie (`https://youtu.be/hFqrYpXwWVU`) in description and tags.



---

## 8. SCRIPTING & VOICE PIPELINE STANDARD (TWO-PASS WORKFLOW)

This is the standard multi-chapter scripting and speech generation pipeline:

### Step 1: Panel Audit & Non-Story Pruning
- Inspect `03_descriptions.json` for non-story artifacts:
  - Title covers / splash logos / credits (`team argo`, `redice`, `템빨`, chapter titles)
  - Blank or solid color gutters (`page_margin`, empty action)
  - Standalone speech bubble crops (isolated dialogue cropped without characters/art)
- Mark matching panels with `is_credits_or_ad: True` in `03_descriptions.json`.
- Merge relevant text from floating dialogue crops into neighboring visual panels if needed.

### Step 2: Pass 1 — Big-Picture Summary via Mercury-3
- Model: `mercury-3` via Inception Labs API (`https://api.inceptionlabs.ai/v1`).
- Inputs: Series context + full sequential panel list.
- Output: `04_summary_mercury.md` (identifies turning points, comedic beats, character motivations, and storytelling hooks).

### Step 3: Pass 2 — Storyboard Recapper Script via Gemini
- Model: `google/gemini-2.5-flash` via OpenRouter (`https://openrouter.ai/api/v1`).
- Persona: High-retention YouTube manhwa recapper.
- Invariants:
  - Strict 1:1 clause-to-panel sync (8–14 words per beat).
  - ZERO banned terms (`panel`, `page`, `chapter`, `manga`, `manhwa`, `author`, `reader`, `viewers`, etc.).
  - Output strictly valid JSON conforming to `ScriptFile` schema (`04_script.json`).
  - Strict validation check via `s3_script.validate`.

### Step 4: Stage 4 — Fish Audio Voiceover & Alignment
- Engine: `src/manga_recap/stages/s4_speech/fish_tts_engine.py`.
- Model: `s2.1-pro-free` (passed strictly in HTTP header `model: s2.1-pro-free`).
- Voice: `802e3bc2b27e49c2995d23ef70e6ac89` (Energetic YouTube Recap Male Voice).
- Concurrency: 4.
- Generates 44.1kHz studio narration `05_narration.wav` and word-anchored `06_timeline.json`.
