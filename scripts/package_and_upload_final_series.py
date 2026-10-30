import re
import sys
import time
import json
import zipfile
import subprocess
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels")
ZIPS_DIR = Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips")
ZIPS_DIR.mkdir(parents=True, exist_ok=True)

RESULTS_FILE = Path(r"scripts\final_upload_results.json")

def upload_zip(zip_path: Path) -> str:
    print(f"Uploading {zip_path.name} ({zip_path.stat().st_size:,} bytes) to sendit.sh...", flush=True)
    for attempt in range(1, 4):
        try:
            res = subprocess.run(
                ["curl.exe", "--retry", "2", "--max-time", "120", "-T", str(zip_path), "https://sendit.sh/"],
                capture_output=True,
                text=True
            )
            match = re.search(r"https://sendit\.sh/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\.]+", res.stdout)
            if match:
                link = match.group(0)
                print(f"Success ({zip_path.name}): {link}", flush=True)
                return link
            print(f"Attempt {attempt} output did not match URL: {res.stdout[:100]}", flush=True)
        except Exception as e:
            print(f"Attempt {attempt} failed: {e}", flush=True)
        time.sleep(2)
    return ""

def package_and_upload_item(series_name: str, zip_filename: str):
    series_dir = PANELS_ROOT / series_name
    zip_path = ZIPS_DIR / zip_filename
    
    # If zip doesn't exist or is empty, create it
    if not zip_path.exists() or zip_path.stat().st_size == 0:
        print(f"Zipping {series_name} -> {zip_filename}...", flush=True)
        t0 = time.time()
        count = 0
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for file in series_dir.rglob("*"):
                if file.is_file():
                    rel = file.relative_to(series_dir.parent)
                    zf.write(file, arcname=str(rel))
                    if file.suffix.lower() == ".webp":
                        count += 1
        print(f"Zipped {count} panels in {time.time()-t0:.1f}s ({zip_path.stat().st_size:,} bytes)", flush=True)
    else:
        # count panels
        count = len(list(series_dir.rglob("*.webp")))
        print(f"Zip already exists: {zip_path.name} ({zip_path.stat().st_size:,} bytes, {count} panels)", flush=True)
        
    url = upload_zip(zip_path)
    return {
        "name": series_name,
        "zip": zip_filename,
        "size": zip_path.stat().st_size,
        "panels": count,
        "url": url
    }

ITEMS = [
    ("Murim Login", "Murim_Login_Clean_WebP_Panels.zip"),
    ("Myst, Might, Mayhem", "Myst_Might_Mayhem_Clean_WebP_Panels.zip"),
    ("Return of the Mad Demon", "Return_of_the_Mad_Demon_Clean_WebP_Panels.zip"),
    ("Villain to Kill", "Villain_to_Kill_Clean_WebP_Panels.zip"),
    ("Damn Reincarnation", "Damn_Reincarnation_Clean_WebP_Panels.zip"),
]

if __name__ == "__main__":
    results = [
        {
            "name": "The Beginning After the End",
            "zip": "The_Beginning_After_the_End_Clean_WebP_Panels.zip",
            "size": 190821842,
            "panels": 2325,
            "url": "https://sendit.sh/qYmne/s2w1L.zip"
        }
    ]
    
    for name, zip_file in ITEMS:
        r = package_and_upload_item(name, zip_file)
        results.append(r)
        
    RESULTS_FILE.write_text(json.dumps(results, indent=2))
    print("\nALL FINAL 6 SERIES PROCESSED:")
    for r in results:
        print(f"• {r['name']}: {r['panels']} panels -> {r['url']}")
