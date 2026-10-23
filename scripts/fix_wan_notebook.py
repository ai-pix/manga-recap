"""Patch and fix wan2gp-12.ipynb for Kaggle."""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK_PATH = Path(r"C:\Users\ravih\Downloads\wan2gp-12.ipynb")

COMMON_HEADER = """import os
import shutil
import subprocess
from pathlib import Path

# Ensure standard Kaggle paths are defined even if running cells out of order
KAGGLE_WORKING = Path('/kaggle/working')
WAN2GP_ROOT = (KAGGLE_WORKING / 'Wan2GP').resolve()

# Auto-detect highest capacity scratch storage (/kaggle/tmp, /tmp, or /kaggle/working)
best_storage = Path('/kaggle/tmp') if Path('/kaggle/tmp').exists() else (Path('/tmp') if Path('/tmp').exists() else KAGGLE_WORKING)
LARGE_DATA_ROOT = (best_storage / 'Wan2GP-data').resolve()
WAN_CKPTS_DIR = (LARGE_DATA_ROOT / 'ckpts').resolve()
WAN_LORAS_DIR = (LARGE_DATA_ROOT / 'loras').resolve()
WAN_CACHE_DIR = (best_storage / 'cache').resolve()
WAN_TEMP_DIR = (best_storage / 'temp').resolve()
WAN_OUTPUTS_DIR = (KAGGLE_WORKING / 'outputs').resolve()
"""


def fix_notebook():
    nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))

    # Convert character arrays into proper line arrays for all cells
    for cell in nb.get("cells", []):
        raw_source = "".join(cell.get("source", []))
        lines = [line + "\n" for line in raw_source.splitlines()]
        if raw_source and not raw_source.endswith("\n") and lines:
            lines[-1] = lines[-1].rstrip("\n")
        cell["source"] = lines

    # Update Cell 8 (Git Clone & Symlinks)
    c8_text = "".join(nb["cells"][8]["source"])
    if "Ensure standard Kaggle paths are defined" not in c8_text:
        c8_text = COMMON_HEADER + "\n" + c8_text
    nb["cells"][8]["source"] = [l + "\n" for l in c8_text.splitlines()]

    # Update Cell 10 (System dependencies)
    c10_text = "".join(nb["cells"][10]["source"])
    # Add aria2 for ultra-fast multi-connection model downloads
    if "aria2" not in c10_text:
        c10_text = c10_text.replace(
            "'ffmpeg', 'libglib2.0-0', 'libgl1', 'libportaudio2'",
            "'ffmpeg', 'libglib2.0-0', 'libgl1', 'libportaudio2', 'aria2'",
        )
    nb["cells"][10]["source"] = [l + "\n" for l in c10_text.splitlines()]

    # Update Cell 12 (PyTorch & Dependencies)
    c12_text = "".join(nb["cells"][12]["source"])
    if "Ensure standard Kaggle paths are defined" not in c12_text:
        c12_text = COMMON_HEADER + "\n" + c12_text

    # Make sure pyngrok, gradio, and huggingface_hub are installed along with requirements
    if "pyngrok" not in c12_text:
        c12_text = c12_text.replace(
            "str(WAN2GP_ROOT / 'requirements.txt')",
            "str(WAN2GP_ROOT / 'requirements.txt'),\n    'pyngrok',\n    'gradio>=4.44.0',\n    'huggingface_hub'",
        )
    nb["cells"][12]["source"] = [l + "\n" for l in c12_text.splitlines()]

    # Update Cell 14 (Compatibility Patches)
    c14_text = "".join(nb["cells"][14]["source"])
    if "Ensure standard Kaggle paths are defined" not in c14_text:
        c14_text = COMMON_HEADER + "\n" + c14_text
    nb["cells"][14]["source"] = [l + "\n" for l in c14_text.splitlines()]

    # Update Cell 16 (Execution & Launch)
    c16_text = "".join(nb["cells"][16]["source"])
    if "Ensure standard Kaggle paths are defined" not in c16_text:
        c16_text = COMMON_HEADER + "\n" + c16_text

    ngrok_snippet = """
# Optional: Use Ngrok tunnel if Gradio's standard --share link fails to connect
NGROK_TOKEN = os.environ.get('NGROK_TOKEN', '')  # Paste your token here if needed
if NGROK_TOKEN:
    try:
        from pyngrok import ngrok
        ngrok.set_auth_token(NGROK_TOKEN)
        tunnel = ngrok.connect(7860)
        print(f'🌐 Ngrok Public Tunnel: {tunnel.public_url}')
    except Exception as e:
        print(f'⚠️ Ngrok tunnel notice: {e}')
"""
    if "NGROK_TOKEN" not in c16_text:
        c16_text = c16_text.replace("cmd = [", ngrok_snippet.strip() + "\n\ncmd = [")

    # Add --server_name 0.0.0.0 and --server_port 7860 for Kaggle network exposure
    if "'--server_name'" not in c16_text:
        c16_text = c16_text.replace(
            "'--share'",
            "'--share',\n    '--server_name',\n    '0.0.0.0',\n    '--server_port',\n    '7860'",
        )
    nb["cells"][16]["source"] = [l + "\n" for l in c16_text.splitlines()]

    NOTEBOOK_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[SUCCESS] Patched and updated {NOTEBOOK_PATH} successfully!")


if __name__ == "__main__":
    fix_notebook()
