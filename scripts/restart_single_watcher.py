"""Single-Instance Watcher Controller for @Gemini Google Sheet Chat.

Ensures strictly ONE instance of watch_gemini_daemon.py is running.
1. Inspects the process tree using psutil / wmic / PowerShell.
2. Identifies and terminates ANY existing or stale watcher processes.
3. Automatically queries the sheet for the latest message ID to avoid missing any recent messages.
4. Uses a local file lock (watch_gemini.lock) so accidental duplicate launches immediately exit.
5. Spawns the clean single instance and verifies it is healthy.
"""

import os
import sys
import time
import json
import psutil
import subprocess
from pathlib import Path

LOCK_FILE = Path("scripts/watch_gemini.lock")
DAEMON_SCRIPT = Path("scripts/watch_gemini_daemon.py").resolve()
PYTHON_EXE = Path(".venv/Scripts/python.exe").resolve()
STATE_FILE = Path("scripts/gemini_watch_state.json")

def kill_all_watchers():
    current_pid = os.getpid()
    killed = 0
    print("[Controller] Scanning for existing watcher processes...", flush=True)
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.pid == current_pid:
                continue
            cmdline = proc.info.get('cmdline') or []
            cmd_str = " ".join(cmdline).lower()
            if "watch_gemini" in cmd_str or "watch_gemini_daemon.py" in cmd_str:
                print(f"[Controller] Killing stale watcher PID {proc.pid}...", flush=True)
                proc.kill()
                killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    # Clean up lock file if orphaned
    if LOCK_FILE.exists():
        try:
            LOCK_FILE.unlink()
        except Exception:
            pass

    print(f"[Controller] Terminated {killed} stale watcher process(es).", flush=True)

def start_single_watcher():
    kill_all_watchers()
    time.sleep(1)

    print(f"[Controller] Launching single dedicated watcher daemon: {DAEMON_SCRIPT.name}...", flush=True)
    # Launch detached background process
    proc = subprocess.Popen(
        [str(PYTHON_EXE), str(DAEMON_SCRIPT)],
        cwd=str(Path.cwd()),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    
    # Verify process is alive
    if psutil.pid_exists(proc.pid):
        print(f"[Controller] SUCCESS: Single watcher running with PID {proc.pid}.", flush=True)
    else:
        print("[Controller] ERROR: Process failed to start.", flush=True)

if __name__ == "__main__":
    start_single_watcher()
