import time
from pathlib import Path
from package_series_and_upload import package_and_upload

TARGETS = [
    ("The Beginning After the End", "The_Beginning_After_the_End_Clean_WebP_Panels.zip"),
    ("Murim Login", "Murim_Login_Clean_WebP_Panels.zip"),
    ("Myst, Might, Mayhem", "Myst_Might_Mayhem_Clean_WebP_Panels.zip"),
    ("Return of the Mad Demon", "Return_of_the_Mad_Demon_Clean_WebP_Panels.zip"),
    ("Villain to Kill", "Villain_to_Kill_Clean_WebP_Panels.zip"),
]

if __name__ == "__main__":
    results = []
    for name, zip_name in TARGETS:
        print(f"\nProcessing {name}...")
        res = package_and_upload(name, zip_name)
        if res:
            results.append(res)
            
    print("\n" + "="*60)
    print("ALL 5 SERIES PACKAGED AND UPLOADED:")
    for r in results:
        print(f"- {r['name']}: {r['panels']} panels | {r['size']:,} bytes | {r['url']}")
    print("="*60)
