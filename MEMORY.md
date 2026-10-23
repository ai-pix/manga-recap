# Manga Recap — System Memory & Architecture

Status: **Production-ready, all 115 chapters rendered & verified (100% complete across entire series).**
All upstream stages (ingest, crop, describe, script, speak, render) across the entire series (`ch001` through `ch112`, including `ch005_5`, `ch058_5`, and `ch103_5`) are 100% complete with frame-exact audio-panel synchronization, zero drift, and YouTube-ready 1080p video packages (`07_final.mp4`) verified on disk (total 12.60 GB video archive).

---

## 1. STRICT MANDATES & CONSTRAINTS

> ⚠️ **ZERO HEAVY TASKS ON LOCAL MACHINE & 100% PURE GPU/CUDA ON KAGGLE (NEVER CPU, NO FALLBACKS EVER)**
> 1. **Zero heavy compute locally:** The local machine is Windows with GTX 1650 and Python 3.14. Video rendering, TTS model training/inference, and Whisper alignment must NEVER run locally. Local system is strictly for orchestration, API requests, metadata generation, and unit tests.
> 2. **ABSOLUTE BAN ON KAGGLE CPU & ZERO CPU FALLBACKS:** All compute jobs running on Kaggle must be 100% GPU/CUDA accelerated. NEVER run video rendering on Kaggle CPU. NEVER include or execute any fallback to CPU software encoding (`libx264`, `veryfast`, `ultrafast`). If GPU/NVENC fails to initialize, the job MUST raise an immediate fatal `RuntimeError` in under 2 seconds. Silently downgrading to CPU is strictly prohibited.

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

---

## 4. AUDIO-PANEL SYNC ARCHITECTURE

`src/manga_recap/render/sync.py` is the **single owner of shot timing**:
1. **Split:** Each block's narration is split into clauses (max 14 words per beat).
2. **Anchor:** Each beat reads start and end timestamps directly from word-level Whisper alignment in `06_timeline.json`.
3. **Schedule:** Shots tile the audio exactly with zero gaps. Frame counts are calculated from cumulative absolute timestamps so rounding cannot accumulate.
4. **Verification:** Every render outputs `07_sync_report.json` reporting exact shot cuts, text bindings, and cumulative drift (always +0.000s).

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

## 6. PROJECT ARTIFACTS & STATUS
 
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

## 8. UPCOMING MANHWA PRODUCTION QUEUE (30 TITLES)

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
