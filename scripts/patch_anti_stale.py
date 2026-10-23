from pathlib import Path

# 1. Update kaggle_io.py
kio_path = Path("src/manga_recap/core/kaggle_io.py")
content = kio_path.read_text(encoding="utf-8")

old_wait = """        # Give Kaggle API a moment to process the push and transition status
        time.sleep(6)
        deadline = time.time() + max_wait
        reported_queue = False
        has_started = False

        while time.time() < deadline:
            status = self.kernel_status(kernel_id)
            run.status = status

            if status in STATUS_RUNNING:
                has_started = True

            # Require seeing running/queued state or a minimum elapsed time before accepting complete
            if status in STATUS_DONE and (has_started or (time.time() - run.started_at) > 45):"""

new_wait = """        # Give Kaggle API a moment to process the push and transition status
        time.sleep(10)
        deadline = time.time() + max_wait
        reported_queue = False
        has_started = False

        while time.time() < deadline:
            status = self.kernel_status(kernel_id)
            run.status = status

            if status in STATUS_RUNNING:
                has_started = True

            # Under NO circumstance accept complete unless has_started was observed
            if status in STATUS_DONE and has_started:"""

if old_wait in content:
    content = content.replace(old_wait, new_wait, 1)
    kio_path.write_text(content, encoding="utf-8")
    print("Updated kaggle_io.py")
else:
    print("kaggle_io.py target not found")

# 2. Update s5_render/__init__.py
s5_path = Path("src/manga_recap/stages/s5_render/__init__.py")
s5_content = s5_path.read_text(encoding="utf-8")

old_s5 = """    video = _locate(download_dir, paths.final_file.name) or _locate(download_dir, "final.mp4")
    if video is None:
        failure_txt = _locate(download_dir, "failure.txt")
        details = ""
        if failure_txt and failure_txt.exists():
            details = f"\\nKernel failure trace:\\n{failure_txt.read_text(encoding='utf-8')}"
        raise KaggleError(
            f"Kernel finished but produced no {paths.final_file.name}. Check "
            f"{paths.root / '_kaggle_output'} and the kernel log.{details}"
        )
    shutil.copy2(video, paths.final_file)"""

new_s5 = """    video = _locate(download_dir, paths.final_file.name) or _locate(download_dir, "final.mp4")
    if video is None:
        failure_txt = _locate(download_dir, "failure.txt")
        details = ""
        if failure_txt and failure_txt.exists():
            details = f"\\nKernel failure trace:\\n{failure_txt.read_text(encoding='utf-8')}"
        raise KaggleError(
            f"Kernel finished but produced no {paths.final_file.name}. Check "
            f"{paths.root / '_kaggle_output'} and the kernel log.{details}"
        )

    # Invariant: verify that the output belongs to this chapter and is not a stale prior run
    render_log = _locate(download_dir, "render_log.txt")
    if render_log and render_log.exists():
        log_text = render_log.read_text(encoding="utf-8", errors="ignore")
        if f"render job for {paths.chapter_id}:" not in log_text:
            raise KaggleError(
                f"Stale output detected! Downloaded log does not belong to {paths.chapter_id}."
            )

    shutil.copy2(video, paths.final_file)"""

if old_s5 in s5_content:
    s5_content = s5_content.replace(old_s5, new_s5, 1)
    s5_path.write_text(s5_content, encoding="utf-8")
    print("Updated s5_render/__init__.py with anti-stale invariant")
else:
    print("s5_render/__init__.py target not found")
