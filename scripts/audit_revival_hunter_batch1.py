"""Audit Chapters 1 to 10 for SSS-Class Revival Hunter."""

from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate

def audit():
    cfg = load_config()
    print(f"{'CHAPTER':<10} | {'PANELS':<8} | {'BLOCKS':<8} | {'WORDS':<8} | {'MINUTES':<8} | {'VALID':<6} | {'SUMMARY'}")
    print("-" * 65)
    
    total_words = 0
    total_blocks = 0
    all_valid = True

    for i in range(1, 11):
        ch_id = f"ch{i:02d}"
        ch_dir = Path(f"data/chapters/sss-class-revival-hunter/{ch_id}")
        desc_p = ch_dir / "03_descriptions.json"
        script_p = ch_dir / "04_script.json"
        summary_p = ch_dir / "03_summary_mercury.txt"

        if not desc_p.exists() or not script_p.exists():
            print(f"{ch_id:<10} | MISSING FILES")
            all_valid = False
            continue

        desc = load_model(desc_p, DescriptionFile)
        script = load_model(script_p, ScriptFile)
        rep = validate(script, desc, cfg)

        has_summary = "Yes" if summary_p.exists() else "No"
        mins = script.total_words / 150.0

        total_words += script.total_words
        total_blocks += len(script.blocks)
        if not rep.ok:
            all_valid = False

        print(f"{ch_id:<10} | {len(desc.panels):<8} | {len(script.blocks):<8} | {script.total_words:<8} | {mins:<8.1f} | {str(rep.ok):<6} | {has_summary}")

    print("-" * 65)
    print(f"TOTALS     | 10 Chs   | {total_blocks:<8} | {total_words:<8} | {total_words / 150:<8.1f} | {all_valid}")

if __name__ == "__main__":
    audit()
