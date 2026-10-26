from pathlib import Path

p = Path("kaggle/kernel_render/main.py")
text = p.read_text(encoding="utf-8")

old_code = """        p_path = panels_dir / f"{pid}.jpg"
        if not p_path.exists():
            p_path = panels_dir / f"{pid}.png"
        if not p_path.exists():"""

new_code = """        p_path = panels_dir / f"{pid}.webp"
        if not p_path.exists():
            p_path = panels_dir / f"{pid}.jpg"
        if not p_path.exists():
            p_path = panels_dir / f"{pid}.png"
        if not p_path.exists():"""

assert old_code in text
text = text.replace(old_code, new_code)
p.write_text(text, encoding="utf-8")
print("SUCCESS: Updated sample variants p_path!")
