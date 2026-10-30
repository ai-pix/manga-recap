# MASTER KAGGLE BATCH RENDERING STANDARD (IMMUTABLE LAW)

This document is the **single source of truth** for video rendering across all manga recap pipelines. All agents, scripts, and Kaggle kernels MUST follow this architecture. Any deviation is a critical violation.

---

## 1. The Core Rules of Batch Distribution

### A. Quad-Instance Distribution (Default: 2 Kaggle Accounts Available)
Whenever 2 Kaggle accounts are active (`fabricatevisuals` and `ravidevai`), there are **4 concurrent GPU instances** available:
1. `fabricatevisuals/manga-recap-render`
2. `fabricatevisuals/manga-recap-render-2`
3. `ravidevai/manga-recap-render`
4. `ravidevai/manga-recap-render-2`

**Workload Rule:** Divide all chapters **equally into 4 batches** across all 4 instances.
* Example (20 chapters): 5 + 5 + 5 + 5
* Example (30 chapters): 8 + 8 + 7 + 7

### B. Dual-Instance Distribution (Fallback: Only 1 Kaggle Account Available)
If only 1 Kaggle account is available, divide all chapters **equally into 2 batches** across the 2 GPU slots of that account:
1. `<username>/manga-recap-render` (Slot 1)
2. `<username>/manga-recap-render-2` (Slot 2)

* Example (20 chapters): 10 + 10
* Example (30 chapters): 15 + 15

### C. ABSOLUTE BAN ON SINGLE-CHAPTER RENDERS
* **NEVER** render single chapters individually.
* Single-chapter jobs waste GPU queue times, exhaust quotas prematurely, and cause massive pipeline stalls.
* Always batch multiple chapters into unified payloads.

---

## 2. Continuous In-Memory GPU Pipeline (Zero Reloading)

### The Anti-Pattern (DO NOT DO THIS)
Do **NOT** render Chapter 1, destroy the encoder, tear down the CUDA context, re-import Python modules, re-initialize PyTorch, and then start Chapter 2. This creates massive overhead and pipeline stutter.

### The Master Pattern (MANDATORY)
* **Single Warm CUDA Context:** PyTorch CUDA tensors and GPU device buffers remain allocated and warm throughout the entire run.
* **Continuous NVENC Pipeline:** The PyNvVideoCodec hardware encoder and memory buffers stay open across chapters.
* **Continuous Frame Flow:** Chapters in the batch are rendered sequentially in a continuous in-memory stream without stopping or destroying the GPU pipeline between chapters.
* **Output Isolation:** Each chapter's encoded bitstream is cleanly written to its dedicated output file (`{chapter_id}_final.mp4`) or stitched directly into the batch compilation.

---

## 3. WebP Panel Standard (Mandatory Lightweight Assets)

* **WebP Only:** All extracted panels, crops, and staged datasets MUST strictly be stored and processed in **WebP format** (`.webp`, quality 90).
* **ABSOLUTE BAN ON RAW UNCOMPRESSED PNGs:** Storing or packaging raw uncompressed `.png` panels is strictly prohibited. Uncompressed PNGs bloat archives by 300–400%, leading to massive payloads (7+ GB), network timeouts, and storage exhaustion.
* **Size Reduction:** WebP preserves 100% of visual recap clarity at 1080p while shrinking total dataset footprints by 60% to 75%.

---

## 4. 100% Pure GPU NVENC / CUDA (Zero CPU Fallback)

* **Hardware Accelerated Only:** Video rendering MUST use NVIDIA T4 hardware NVENC (`h264_nvenc`) and PyNvVideoCodec zero-copy DLPack memory buffers.
* **355+ FPS Standard:** The pure GPU pipeline must sustain 355+ frames per second on Kaggle Tesla T4.
* **HARD ERROR ON FAILURE:** If GPU hardware acceleration or CUDA fails to initialize, the kernel MUST immediately fail with a hard `RuntimeError` within 2 seconds. Silently falling back to CPU software rendering (`libx264`, `veryfast`, etc.) is strictly forbidden.

---

## 4. Execution Checklist for Any Batch Render

1. **Calculate Split:**
   - 4 instances available $\rightarrow$ Divide $N$ chapters into 4 equal sets.
   - 1 account (2 instances) available $\rightarrow$ Divide $N$ chapters into 2 equal sets.
2. **Build Payloads:** Bundle the chapter datasets (panels, script, audio, timeline) into batch zips and upload to cloud storage (`sendit.sh`).
3. **Push Kernels Concurrently:** Push all batch kernels simultaneously using isolated Kaggle credentials.
4. **Continuous GPU Execution:** The kernel executes all assigned chapters continuously in a single warm session.
5. **Download & Verify:** Fetch the final rendered `.mp4` outputs directly into the chapter folders and verify file sizes and audio sync.
