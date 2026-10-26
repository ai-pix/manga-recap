from pathlib import Path

p = Path("kaggle/kernel_render/main.py")
content = p.read_text(encoding="utf-8")

old_func = """def find_panels_dir() -> Path:
    \"\"\"The directory holding panel_*.png or panel_*.jpg.\"\"\"
    for directory in sorted(INPUT_ROOT.rglob("panels")):
        if directory.is_dir() and (any(directory.glob("panel_*.png")) or any(directory.glob("panel_*.jpg"))):
            return directory
    for candidate in sorted(list(INPUT_ROOT.rglob("panel_*.png")) + list(INPUT_ROOT.rglob("panel_*.jpg"))):
        return candidate.parent
    raise FileNotFoundError(
        f"No panel_* images found under {INPUT_ROOT}. The render payload carries the "
        "chapter's panel crops."
    )"""

new_func = """def find_panels_dir() -> Path:
    \"\"\"The directory holding panel_*.webp, panel_*.png, or panel_*.jpg.\"\"\"
    for directory in sorted(INPUT_ROOT.rglob("panels")) + sorted(INPUT_ROOT.rglob("02_panels")):
        if directory.is_dir() and (
            any(directory.glob("panel_*.webp"))
            or any(directory.glob("panel_*.png"))
            or any(directory.glob("panel_*.jpg"))
        ):
            return directory
    for candidate in sorted(
        list(INPUT_ROOT.rglob("panel_*.webp"))
        + list(INPUT_ROOT.rglob("panel_*.png"))
        + list(INPUT_ROOT.rglob("panel_*.jpg"))
    ):
        return candidate.parent
    raise FileNotFoundError(
        f"No panel_* images found under {INPUT_ROOT}. The render payload carries the "
        "chapter's panel crops."
    )"""

# Also ensure PyNvDecoder / Pillow opens webp
assert old_func in content, "old_func not found in main.py"
content = content.replace(old_func, new_func)
p.write_text(content, encoding="utf-8")
print("SUCCESS: Updated find_panels_dir in kaggle/kernel_render/main.py to support .webp!")
