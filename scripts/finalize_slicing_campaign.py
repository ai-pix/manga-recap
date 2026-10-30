import os
import sys
import time
import json
import psutil
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from package_series_and_upload import package_and_upload

PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels")
DAMN_DIR = PANELS_ROOT / "Damn Reincarnation"

def wait_for_damn_reincarnation_and_stop():
    print("[Finalizer] Waiting for Damn Reincarnation to finish all 30 chapters...", flush=True)
    while True:
        completed = list(DAMN_DIR.glob("Chapter */02_panels/panel_index.json"))
        print(f"[Finalizer] Damn Reincarnation chapters done: {len(completed)}/30", flush=True)
        if len(completed) >= 30:
            print("[Finalizer] Damn Reincarnation is 100% COMPLETE!", flush=True)
            break
        time.sleep(5)

    # Terminate the batch slicer process tree
    print("[Finalizer] Terminating batch_smart_slice_all_series process tree...", flush=True)
    for p in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmd = " ".join(p.info.get('cmdline') or []).lower()
            if "batch_smart_slice_all_series" in cmd:
                print(f"[Finalizer] Killing slicer PID {p.pid}...", flush=True)
                p.kill()
        except Exception:
            pass

    print("[Finalizer] Batch slicer stopped. No further series will be sliced.", flush=True)

if __name__ == "__main__":
    wait_for_damn_reincarnation_and_stop()
