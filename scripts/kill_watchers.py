import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from restart_single_watcher import kill_all_watchers

if __name__ == "__main__":
    kill_all_watchers()
