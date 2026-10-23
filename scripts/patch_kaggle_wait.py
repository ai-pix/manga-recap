from pathlib import Path

fpath = Path("src/manga_recap/core/kaggle_io.py")
content = fpath.read_text(encoding="utf-8")

old_code = """        run = KernelRun(slug=kernel_id.rsplit("/", 1)[-1], kernel_id=kernel_id)
        self._log.info("Waiting for %s (poll every %ds)", kernel_id, poll_interval)

        deadline = time.time() + max_wait
        reported_queue = False

        while time.time() < deadline:
            status = self.kernel_status(kernel_id)
            run.status = status

            if status in STATUS_DONE:"""

new_code = """        run = KernelRun(slug=kernel_id.rsplit("/", 1)[-1], kernel_id=kernel_id)
        self._log.info("Waiting for %s (poll every %ds)", kernel_id, poll_interval)

        # Give Kaggle API a moment to process the push and transition status
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

if old_code in content:
    content = content.replace(old_code, new_code, 1)
    fpath.write_text(content, encoding="utf-8")
    print("Patched wait_for_kernel in kaggle_io.py successfully")
else:
    print("Target block not found in kaggle_io.py")
