from pathlib import Path

path = Path("kaggle/kernel_render/main.py")
text = path.read_text(encoding="utf-8")

old_marker = '    if job.get("mode") == "batch":'
end_marker = '    script = json.loads(find("script.json").read_text(encoding="utf-8"))'

idx_start = text.find(old_marker)
idx_end = text.find(end_marker)

assert idx_start != -1 and idx_end != -1, "Markers not found!"

new_batch_section = '''    if job.get("mode") == "batch":
        chapters = job.get("chapters", [])
        print(f"[kernel] ===== BATCH MODE: Rendering {len(chapters)} chapters =====", flush=True)
        rendered_outputs: list[tuple[str, Path]] = []
        for idx, ch_name in enumerate(chapters, 1):
            print(f"\\n[kernel] >>> [{idx}/{len(chapters)}] Starting {ch_name}...", flush=True)
            ch_dir = INPUT_ROOT / "chapters" / ch_name
            if not ch_dir.is_dir():
                print(f"[kernel] ERROR: Directory missing for {ch_name}", flush=True)
                continue

            ch_script = json.loads((ch_dir / "script.json").read_text(encoding="utf-8"))
            ch_timeline = json.loads((ch_dir / "timeline.json").read_text(encoding="utf-8"))
            ch_panels = ch_dir / "panels"
            ch_audio = ch_dir / "narration.wav"

            ch_output = WORKING / f"{ch_name}_final.mp4"
            ch_manifest = WORKING / f"{ch_name}_render_manifest.json"
            ch_sync = WORKING / f"{ch_name}_sync_report.json"

            try:
                render_chapter_core(
                    job, ch_script, ch_timeline, ch_panels, ch_audio,
                    ch_output, ch_manifest, ch_sync, exe, ch_name
                )
                print(f"[kernel] [OK] Finished {ch_name}", flush=True)
                if ch_output.exists():
                    rendered_outputs.append((ch_name, ch_output))
            except Exception as exc:  # noqa: BLE001
                print(f"[kernel] [FAIL] Chapter {ch_name} failed: {exc}", flush=True)
                import traceback
                traceback.print_exc()

        # Stitch all rendered chapters into a single movie on Kaggle GPU NVENC
        if job.get("stitch_movie", True) and rendered_outputs:
            movie_filename = str(job.get("movie_filename", "movie_batch.mp4"))
            movie_output = WORKING / movie_filename
            print(f"\\n[kernel] ===== STITCHING {len(rendered_outputs)} CHAPTERS INTO {movie_filename} =====", flush=True)
            concat_list = WORKING / "concat_list.txt"
            with concat_list.open("w", encoding="utf-8") as f:
                for _, vid in rendered_outputs:
                    f.write(f"file '{vid.resolve()}'\\n")

            # Stitch strictly using proven NVENC re-encode standard (Rule 3)
            stitch_cmd = [
                exe,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "28",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                str(movie_output),
            ]
            print(f"[kernel] Running stitch: {' '.join(stitch_cmd)}", flush=True)
            stitch_res = subprocess.run(stitch_cmd, capture_output=True, text=True)
            if stitch_res.returncode != 0:
                print(f"[kernel] ERROR: Stitch failed with code {stitch_res.returncode}:\\n{stitch_res.stderr[-1000:]}", flush=True)
                raise RuntimeError(f"FFmpeg movie stitch failed: {stitch_res.stderr[-500:]}")

            movie_size_mb = movie_output.stat().st_size / (1024 * 1024)
            print(f"[kernel] [SUCCESS] Stitched movie created: {movie_output} ({movie_size_mb:.1f} MB)", flush=True)

            if not job.get("keep_individual", True):
                print("[kernel] Removing individual chapter videos to keep download lightweight...", flush=True)
                for _, vid in rendered_outputs:
                    try:
                        vid.unlink(missing_ok=True)
                    except OSError:
                        pass

        shutil.rmtree(INPUT_ROOT, ignore_errors=True)
        shutil.rmtree(WORKING / "ffmpeg_static", ignore_errors=True)
        print(f"[kernel] All batch chapters finished in {time.time() - started:.0f}s", flush=True)
        return 0

'''

updated_text = text[:idx_start] + new_batch_section + text[idx_end:]
path.write_text(updated_text, encoding="utf-8")
print("Successfully patched kaggle/kernel_render/main.py with NVENC batch stitching!")
