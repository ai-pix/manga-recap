import os
import sys
import time
import zipfile
import subprocess
from pathlib import Path

PANELS_ROOT = Path(r"D:\Python Projects\Hakuniku\panels")
ZIPS_DIR = Path(r"D:\Python Projects\Hakuniku\cli\downloads\zips")
ZIPS_DIR.mkdir(parents=True, exist_ok=True)

def package_and_upload(series_name: str, zip_filename: str):
    series_dir = PANELS_ROOT / series_name
    if not series_dir.exists():
        print(f"Error: {series_dir} does not exist!")
        return None
    
    zip_path = ZIPS_DIR / zip_filename
    print(f"Packaging {series_name} into {zip_path} (ZIP_STORED)...")
    t0 = time.time()
    
    count = 0
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for file in series_dir.rglob("*"):
            if file.is_file():
                rel = file.relative_to(series_dir.parent)
                zf.write(file, arcname=str(rel))
                if file.suffix.lower() == ".webp":
                    count += 1
                    
    sz = zip_path.stat().st_size
    print(f"Created {zip_filename}: {sz:,} bytes, {count} panels in {time.time() - t0:.1f}s")
    
    # Upload to sendit.sh
    print(f"Uploading {zip_filename} to sendit.sh...")
    res = subprocess.run(
        ["curl.exe", "-s", "-T", str(zip_path), "https://sendit.sh/"],
        capture_output=True,
        text=True
    )
    import re
    match = re.search(r"https://sendit\.sh/[a-zA-Z0-9_\-]+/[a-zA-Z0-9_\-\.]+", res.stdout)
    link = match.group(0) if match else res.stdout.strip()
    print(f"Sendit URL: {link}")
    return {"name": series_name, "zip": zip_filename, "size": sz, "panels": count, "url": link}

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        package_and_upload(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 2:
        target = sys.argv[1]
        if target == "Eleceed":
            package_and_upload("Eleceed", "Eleceed_Clean_WebP_Panels.zip")
        elif target == "Pick Me Up":
            package_and_upload("Pick Me Up, Infinite Gacha", "Pick_Me_Up_Infinite_Gacha_Clean_WebP_Panels.zip")
        elif target == "Player":
            package_and_upload("Player Who Returned 10,000 Years Later", "Player_Who_Returned_10000_Years_Later_Clean_WebP_Panels.zip")
        elif target == "Returners Magic":
            package_and_upload("A Returner's Magic Should Be Special", "A_Returners_Magic_Should_Be_Special_Clean_WebP_Panels.zip")
        elif target == "Estate":
            package_and_upload("The Greatest Estate Developer", "The_Greatest_Estate_Developer_Clean_WebP_Panels.zip")
        elif target == "Newbie":
            package_and_upload("I'm the Max-Level Newbie", "Im_the_Max_Level_Newbie_Clean_WebP_Panels.zip")
        elif target == "Ragnarok":
            package_and_upload("Solo Leveling - Ragnarok", "Solo_Leveling_Ragnarok_Clean_WebP_Panels.zip")
        elif target == "Mercenary":
            package_and_upload("The Regressed Mercenary Has a Plan", "The_Regressed_Mercenary_Has_a_Plan_Clean_WebP_Panels.zip")
        elif target == "Swordmaster":
            package_and_upload("The Stellar Swordmaster", "The_Stellar_Swordmaster_Clean_WebP_Panels.zip")
        elif target == "TBATE":
            package_and_upload("The Beginning After the End", "The_Beginning_After_the_End_Clean_WebP_Panels.zip")
        elif target == "Murim":
            package_and_upload("Murim Login", "Murim_Login_Clean_WebP_Panels.zip")
        elif target == "MMM":
            package_and_upload("Myst, Might, Mayhem", "Myst_Might_Mayhem_Clean_WebP_Panels.zip")
        elif target == "Mad Demon":
            package_and_upload("Return of the Mad Demon", "Return_of_the_Mad_Demon_Clean_WebP_Panels.zip")
        elif target == "Villain":
            package_and_upload("Villain to Kill", "Villain_to_Kill_Clean_WebP_Panels.zip")
        elif target == "Damn Reincarnation":
            package_and_upload("Damn Reincarnation", "Damn_Reincarnation_Clean_WebP_Panels.zip")
        else:
            print(f"Unknown target: {target}")
    else:
        print("Usage: python package_series_and_upload.py <SeriesName> <ZipFilename>")

