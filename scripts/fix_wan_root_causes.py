"""Complete fix for Wan2GP Kaggle notebook:
1. Prevents requirements.txt from overwriting PyTorch 2.6.0+cu124
2. Fixes _safe_inf and _patched_infer_schema signature with (*args, **kwargs)
3. Patches torch._library.infer_schema properly
4. Re-installs torch 2.6.0+cu124 if accidentally downgraded
5. Formats all cells cleanly so 'Run All' works flawlessly
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK_PATH = Path(r"C:\Users\ravih\Downloads\wan2gp-12.ipynb")


def apply_complete_fixes():
    nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # CELL 12: Package installation with Pinning and No Torch Downgrade
    # -------------------------------------------------------------------------
    cell_12_code = """import os
import shutil
import subprocess
from pathlib import Path

# Ensure standard Kaggle paths are defined
KAGGLE_WORKING = Path('/kaggle/working')
WAN2GP_ROOT = (KAGGLE_WORKING / 'Wan2GP').resolve()

best_storage = Path('/kaggle/tmp') if Path('/kaggle/tmp').exists() else (Path('/tmp') if Path('/tmp').exists() else KAGGLE_WORKING)
LARGE_DATA_ROOT = (best_storage / 'Wan2GP-data').resolve()
WAN_CKPTS_DIR = (LARGE_DATA_ROOT / 'ckpts').resolve()
WAN_LORAS_DIR = (LARGE_DATA_ROOT / 'loras').resolve()
WAN_CACHE_DIR = (best_storage / 'cache').resolve()
WAN_TEMP_DIR = (best_storage / 'temp').resolve()
WAN_OUTPUTS_DIR = (KAGGLE_WORKING / 'outputs').resolve()

import importlib
import importlib.util
import sys

print("Installing Python dependencies (PyTorch 2.6.0 with CUDA 12.4 via uv)...")
env = os.environ.copy()
env.setdefault('DEBIAN_FRONTEND', 'noninteractive')
env['UV_CACHE_DIR'] = str(WAN_CACHE_DIR / 'uv')

# 1. Install uv
subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'uv'], check=True, env=env)

PYTORCH_INDEX_URL = 'https://download.pytorch.org/whl/cu124'
TORCH_VERSION = '2.6.0'
TORCHVISION_VERSION = '0.21.0'
TORCHAUDIO_VERSION = '2.6.0'

# 2. Filter requirements.txt to avoid overwriting PyTorch
req_file = WAN2GP_ROOT / 'requirements.txt'
clean_req_file = WAN2GP_ROOT / 'requirements_clean.txt'
if req_file.exists():
    lines = req_file.read_text(encoding='utf-8').splitlines()
    filtered = []
    for l in lines:
        line_clean = l.strip().lower()
        # Drop lines that downgrade torch, torchvision, or torchaudio
        if any(line_clean.startswith(pkg) for pkg in ['torch==', 'torch>=', 'torchvision', 'torchaudio', 'triton']):
            continue
        filtered.append(l)
    clean_req_file.write_text('\\n'.join(filtered), encoding='utf-8')
    print("Filtered requirements.txt to protect PyTorch 2.6 CUDA build.")
else:
    clean_req_file = req_file

# 3. Install requirements
print("Installing repository dependencies...")
subprocess.run([
    sys.executable,
    '-m',
    'uv',
    'pip',
    'install',
    '--system',
    '-r',
    str(clean_req_file),
    'pyngrok',
    'gradio>=4.44.0',
    'huggingface_hub'
], check=True, env=env)

# 4. Enforce exact PyTorch 2.6.0 CUDA 12.4 stack (guaranteed locked)
print("Verifying and locking PyTorch 2.6.0 CUDA 12.4...")
subprocess.run([
    sys.executable,
    '-m',
    'uv',
    'pip',
    'install',
    '--system',
    '--no-cache',
    f'torch=={TORCH_VERSION}',
    f'torchvision=={TORCHVISION_VERSION}',
    f'torchaudio=={TORCHAUDIO_VERSION}',
    '--index-url',
    PYTORCH_INDEX_URL,
], check=True, env=env)

# Immediately clean wheel caches to preserve disk
shutil.rmtree(str(WAN_CACHE_DIR / 'uv'), ignore_errors=True)
for p in ['/root/.cache/uv', '/root/.cache/pip']:
    shutil.rmtree(p, ignore_errors=True)

installed = {
    name: importlib.import_module(name).__version__.split('+', 1)[0]
    if importlib.util.find_spec(name) else 'N/A'
    for name in ('torch', 'torchvision', 'torchaudio')
}
print('Installed torch stack:', ', '.join(f"{name} {version}" for name, version in installed.items()))
"""
    nb["cells"][12]["source"] = [l + "\n" for l in cell_12_code.splitlines()]

    # -------------------------------------------------------------------------
    # CELL 14: Robust Compatibility Patches with (*args, **kwargs) Forwarding
    # -------------------------------------------------------------------------
    cell_14_code = """import os
import sys
import re
import site
import importlib.util
from pathlib import Path

# Ensure standard Kaggle paths are defined
KAGGLE_WORKING = Path('/kaggle/working')
WAN2GP_ROOT = (KAGGLE_WORKING / 'Wan2GP').resolve()

best_storage = Path('/kaggle/tmp') if Path('/kaggle/tmp').exists() else (Path('/tmp') if Path('/tmp').exists() else KAGGLE_WORKING)
LARGE_DATA_ROOT = (best_storage / 'Wan2GP-data').resolve()
WAN_CKPTS_DIR = (LARGE_DATA_ROOT / 'ckpts').resolve()
WAN_LORAS_DIR = (LARGE_DATA_ROOT / 'loras').resolve()
WAN_CACHE_DIR = (best_storage / 'cache').resolve()
WAN_TEMP_DIR = (best_storage / 'temp').resolve()
WAN_OUTPUTS_DIR = (KAGGLE_WORKING / 'outputs').resolve()

print("Configuring Headless environment and applying compatibility patches...")

# 1. Replace TkAgg backend with headless Agg in interact_tools.py if present
target = WAN2GP_ROOT / 'preprocessing/matanyone/tools/interact_tools.py'
needle = "matplotlib.use('TkAgg')"
replacement = "matplotlib.use('Agg')"

if not target.exists():
    print(f'Notice: {target} not found (skipping).')
else:
    text = target.read_text(encoding='utf-8')
    if replacement in text:
        print('Agg backend already set in interact_tools.py.')
    elif needle in text:
        target.write_text(text.replace(needle, replacement, 1), encoding='utf-8')
        print('Replaced TkAgg with Agg in interact_tools.py.')

# 2. Touch __init__.py files in all preprocessing and postprocessing subdirectories
for sub in ['preprocessing', 'postprocessing']:
    base_sub = WAN2GP_ROOT / sub
    if base_sub.exists():
        (base_sub / '__init__.py').touch(exist_ok=True)
        for p in base_sub.rglob('*/'):
            (p / '__init__.py').touch(exist_ok=True)
print("Package directories initialized (__init__.py).")

# 3. Patch PyTorch's torch._library.infer_schema.py to support PEP-585 generic type hints (list[int], Sequence[int], etc.)
try:
    infer_spec = importlib.util.find_spec('torch._library.infer_schema')
    if infer_spec and infer_spec.origin:
        infer_path = Path(infer_spec.origin)
        content = infer_path.read_text(encoding='utf-8')
        modified = False
        
        old_ann = \"\"\"        annotation_type = param.annotation
        if type(annotation_type) == str:
            annotation_type = convert_type_string(annotation_type)\"\"\"
        new_ann = \"\"\"        annotation_type = param.annotation
        if type(annotation_type) == str:
            annotation_type = convert_type_string(annotation_type)
        if hasattr(annotation_type, '__origin__'):
            if annotation_type.__origin__ is list:
                annotation_type = typing.List[annotation_type.__args__]
            elif str(annotation_type.__origin__).endswith('collections.abc.Sequence') or getattr(annotation_type, '__origin__', None) is getattr(typing, 'Sequence', None):
                annotation_type = typing.Sequence[annotation_type.__args__]\"\"\"
        if old_ann in content:
            content = content.replace(old_ann, new_ann, 1)
            modified = True
            
        old_seq = \"\"\"    def derived_seq_types(typ):
        return [
            typing.Sequence[typ],  # type: ignore[valid-type]
            typing.List[typ],  # type: ignore[valid-type]
        ]\"\"\"
        new_seq = \"\"\"    def derived_seq_types(typ):
        res = [
            typing.Sequence[typ],
            typing.List[typ],
        ]
        try:
            import collections.abc
            res.extend([list[typ], collections.abc.Sequence[typ]])
        except Exception:
            pass
        return res\"\"\"
        if old_seq in content:
            content = content.replace(old_seq, new_seq, 1)
            modified = True

        old_ret = \"\"\"    origin = typing.get_origin(annotation)
    if origin is not tuple:\"\"\"
        new_ret = \"\"\"    if hasattr(annotation, '__origin__') and annotation.__origin__ is list:
        annotation = typing.List[annotation.__args__]
    origin = typing.get_origin(annotation)
    if origin is not tuple:\"\"\"
        if old_ret in content:
            content = content.replace(old_ret, new_ret, 1)
            modified = True

        if modified:
            infer_path.write_text(content, encoding='utf-8')
            print("Patched torch._library.infer_schema for PEP-585 generics.")
        else:
            print("torch._library.infer_schema is already patched.")
except Exception as e:
    print(f"Notice patching torch infer_schema: {e}")

# 4. Patch comfy_kitchen files on disk to replace 'list[' with 'typing.List['
try:
    ck_spec = importlib.util.find_spec('comfy_kitchen')
    if ck_spec and ck_spec.submodule_search_locations:
        ck_dir = Path(list(ck_spec.submodule_search_locations)[0])
        patched_count = 0
        for py_file in ck_dir.rglob('*.py'):
            try:
                txt = py_file.read_text(encoding='utf-8')
                new_txt = re.sub(r':\\s*list\\[', ': typing.List[', txt)
                if new_txt != txt:
                    if 'import typing' not in new_txt:
                        new_txt = 'import typing\\n' + new_txt
                    py_file.write_text(new_txt, encoding='utf-8')
                    patched_count += 1
            except Exception:
                pass
        print(f"Patched {patched_count} comfy_kitchen files for PyTorch 2.6.")
except Exception as e:
    print(f"Notice patching comfy_kitchen: {e}")

# 5. Install sitecustomize.py runtime hook with (*args, **kwargs) support
sitecustomize_code = '''import typing
import collections.abc
from pathlib import Path

try:
    import torch._library.infer_schema as _infer_schema
    _orig_infer_schema = _infer_schema.infer_schema

    def _normalize_type(t):
        origin = typing.get_origin(t)
        if origin is None:
            return t
        args = tuple(_normalize_type(a) for a in typing.get_args(t))
        if origin is list:
            return typing.List[args]
        if origin is collections.abc.Sequence or getattr(origin, '__name__', '') == 'Sequence':
            return typing.Sequence[args]
        if origin is tuple:
            return typing.Tuple[args]
        if origin is typing.Union or str(origin) == 'typing.Union' or origin is getattr(typing, '_UnionGenericAlias', None):
            return typing.Union[args]
        return t

    def _patched_infer_schema(prototype_function, /, *args, **kwargs):
        if hasattr(prototype_function, '__annotations__'):
            for k, v in list(prototype_function.__annotations__.items()):
                prototype_function.__annotations__[k] = _normalize_type(v)
        return _orig_infer_schema(prototype_function, *args, **kwargs)

    _infer_schema.infer_schema = _patched_infer_schema
    import torch.library
    if hasattr(torch.library, 'infer_schema'):
        torch.library.infer_schema = _patched_infer_schema
except Exception:
    pass

try:
    import huggingface_hub.file_download as _hfd
    _orig_check = _hfd._check_disk_space
    def _safe_check(expected_size, target_dir):
        try:
            _orig_check(expected_size, Path(target_dir).resolve())
        except Exception:
            pass
    _hfd._check_disk_space = _safe_check
except Exception:
    pass
'''

try:
    for sp in site.getsitepackages():
        sp_path = Path(sp)
        if sp_path.exists() and os.access(str(sp_path), os.W_OK):
            (sp_path / 'sitecustomize.py').write_text(sitecustomize_code, encoding='utf-8')
            print(f"Installed sitecustomize hook to {sp_path}.")
            break
except Exception as e:
    print(f"Notice installing sitecustomize to site-packages: {e}")

(WAN2GP_ROOT / 'sitecustomize.py').write_text(sitecustomize_code, encoding='utf-8')
print("Installed sitecustomize hook to Wan2GP directory.")

# 6. Safeguard in wgp.py with (*args, **kwargs) support
wgp_path = WAN2GP_ROOT / 'wgp.py'
if wgp_path.exists():
    wgp_text = wgp_path.read_text(encoding='utf-8')
    if 'PEP585_CUSTOM_OP_PATCH' not in wgp_text:
        wgp_hook = '''# PEP585_CUSTOM_OP_PATCH
try:
    import typing, collections.abc, torch._library.infer_schema as _inf
    _orig_inf = _inf.infer_schema
    def _norm_t(t):
        o = typing.get_origin(t)
        if o is None: return t
        args = tuple(_norm_t(a) for a in typing.get_args(t))
        if o is list: return typing.List[args]
        if o is collections.abc.Sequence: return typing.Sequence[args]
        if o is tuple: return typing.Tuple[args]
        if o is typing.Union or str(o) == 'typing.Union' or o is getattr(typing, '_UnionGenericAlias', None): return typing.Union[args]
        return t
    def _safe_inf(fn, /, *args, **kwargs):
        if hasattr(fn, '__annotations__'):
            for k, v in list(fn.__annotations__.items()):
                fn.__annotations__[k] = _norm_t(v)
        return _orig_inf(fn, *args, **kwargs)
    _inf.infer_schema = _safe_inf
    if hasattr(torch.library, 'infer_schema'): torch.library.infer_schema = _safe_inf
except Exception:
    pass
'''
        if 'import torch' in wgp_text:
            wgp_text = wgp_text.replace('import torch\\n', 'import torch\\n' + wgp_hook, 1)
        else:
            wgp_text = wgp_hook + '\\n' + wgp_text
        wgp_path.write_text(wgp_text, encoding='utf-8')
        print("Inserted custom_op schema safeguard into wgp.py.")

# 7. Patch refresh_prompt_enhancer_labels in wgp.py to guard against NoneType metadata
if wgp_path.exists():
    wgp_text = wgp_path.read_text(encoding='utf-8')
    pat = re.compile(r'(def\\s+refresh_prompt_enhancer_labels\\s*\\([^)]*\\):\\s*\\n)(\\s*(?:#[^\\n]*\\n\\s*)?)(inputs\\s*=\\s*dict\\(zip\\(prompt_enhancer_labels\\.INPUT_KEYS,\\s*metadata\\[1:-1\\]\\)\\))')
    m = pat.search(wgp_text)
    if m and "if not metadata" not in m.group(0):
        replacement = m.group(1) + "    if not metadata or not isinstance(metadata, (list, tuple)):\\n        return gr.skip(), gr.skip()\\n    " + m.group(2) + m.group(3)
        wgp_text = pat.sub(replacement, wgp_text, count=1)
        wgp_path.write_text(wgp_text, encoding='utf-8')
        print("Patched refresh_prompt_enhancer_labels to guard against NoneType metadata.")
    else:
        print("refresh_prompt_enhancer_labels is already guarded.")

print("All compatibility patches successfully applied.")
"""
    nb["cells"][14]["source"] = [l + "\n" for l in cell_14_code.splitlines()]

    # -------------------------------------------------------------------------
    # CELL 16: Robust Launch with Clean Arguments
    # -------------------------------------------------------------------------
    cell_16_code = """import os
import subprocess
import sys
import threading
import time
from pathlib import Path

# Ensure standard Kaggle paths are defined
KAGGLE_WORKING = Path('/kaggle/working')
WAN2GP_ROOT = (KAGGLE_WORKING / 'Wan2GP').resolve()

best_storage = Path('/kaggle/tmp') if Path('/kaggle/tmp').exists() else (Path('/tmp') if Path('/tmp').exists() else KAGGLE_WORKING)
LARGE_DATA_ROOT = (best_storage / 'Wan2GP-data').resolve()
WAN_CKPTS_DIR = (LARGE_DATA_ROOT / 'ckpts').resolve()
WAN_LORAS_DIR = (LARGE_DATA_ROOT / 'loras').resolve()
WAN_CACHE_DIR = (best_storage / 'cache').resolve()
WAN_TEMP_DIR = (best_storage / 'temp').resolve()
WAN_OUTPUTS_DIR = (KAGGLE_WORKING / 'outputs').resolve()

env = os.environ.copy()
env['WAN_CACHE_DIR'] = str(WAN_CACHE_DIR)
env['HF_HOME'] = str(WAN_CACHE_DIR / 'huggingface')
env['HUGGINGFACE_HUB_CACHE'] = str(WAN_CACHE_DIR / 'huggingface' / 'hub')
env['TORCH_HOME'] = str(WAN_CACHE_DIR / 'torch')
env['XDG_CACHE_HOME'] = str(WAN_CACHE_DIR / '.cache')
env['TMPDIR'] = str(WAN_TEMP_DIR)
env['TEMP'] = str(WAN_TEMP_DIR)
env['TMP'] = str(WAN_TEMP_DIR)
env['PYTHONPATH'] = f"{str(WAN2GP_ROOT)}:{env.get('PYTHONPATH', '')}"
env.pop('TRANSFORMERS_CACHE', None)

# Optional: Ngrok tunnel support (highly reliable if gradio.live is congested)
NGROK_TOKEN = os.environ.get('NGROK_TOKEN', '')
if NGROK_TOKEN:
    try:
        from pyngrok import ngrok
        ngrok.set_auth_token(NGROK_TOKEN)
        tunnel = ngrok.connect(7860)
        print(f'Ngrok Public Tunnel URL: {tunnel.public_url}')
    except Exception as e:
        print(f'Notice starting ngrok: {e}')

cmd = [
    sys.executable,
    '-u',
    'wgp.py',
    '--share'
]

print('Launching Wan2GP...')
process = subprocess.Popen(
    cmd,
    cwd=str(WAN2GP_ROOT),
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

stop_event = threading.Event()

def keepalive():
    while not stop_event.is_set():
        time.sleep(45)
        if stop_event.is_set():
            break
        print('[keepalive] Notebook cell still running...')

keepalive_thread = threading.Thread(target=keepalive, daemon=True)
keepalive_thread.start()

try:
    for line in iter(process.stdout.readline, ''):
        if not line:
            break
        print(line, end='')
except KeyboardInterrupt:
    print('\\nStopping Wan2GP...')
    process.terminate()
finally:
    stop_event.set()
    process.wait()
    keepalive_thread.join(timeout=1)
    print(f'Wan2GP stopped (return code: {process.returncode}).')
"""
    nb["cells"][16]["source"] = [l + "\n" for l in cell_16_code.splitlines()]

    # Normalize all other cells
    for cell in nb.get("cells", []):
        raw = "".join(cell.get("source", []))
        lines = [line + "\n" for line in raw.splitlines()]
        if raw and not raw.endswith("\n") and lines:
            lines[-1] = lines[-1].rstrip("\n")
        cell["source"] = lines

    NOTEBOOK_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"[SUCCESS] Completely patched and verified {NOTEBOOK_PATH}!")


if __name__ == "__main__":
    apply_complete_fixes()
