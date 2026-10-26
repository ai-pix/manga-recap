from pathlib import Path

p = Path("src/manga_recap/render/pynv_renderer.py")
text = p.read_text(encoding="utf-8")

old_code = """    clips: list[Clip] = []
    for shot in shots:
        path = panels_dir / f"{shot.panel_id}.png"
        if not path.exists():
            path = panels_dir / f"{shot.panel_id}.jpg"
        if path.exists():"""

new_code = """    clips: list[Clip] = []
    for shot in shots:
        path = panels_dir / f"{shot.panel_id}.webp"
        if not path.exists():
            path = panels_dir / f"{shot.panel_id}.png"
        if not path.exists():
            path = panels_dir / f"{shot.panel_id}.jpg"
        if path.exists():"""

assert old_code in text, "old_code not found in pynv_renderer.py"
text = text.replace(old_code, new_code)
p.write_text(text, encoding="utf-8")
print("SUCCESS: Updated pynv_renderer.py to check for .webp panels first!")
