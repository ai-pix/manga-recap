"""Audit Chapters 31 to 40 for SSS-Class Revival Hunter."""

from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate


def audit():
    cfg = load_config()
    print(f"{'CHAPTER':<10} | {'PANELS':<8} | {'BLOCKS':<8} | {'WORDS':<8} | {'MINUTES':<8} | {'VALID':<6} | {'PROBLEMS'}")
    print("-" * 75)

    total_words = 0
    total_blocks = 0
    all_valid = True

    for i in range(31, 41):
        ch_id = f"ch{i:02d}"
        ch_dir = Path(f"data/chapters/sss-class-revival-hunter/{ch_id}")
        desc_p = ch_dir / "03_descriptions.json"
        script_p = ch_dir / "04_script.json"

        if not desc_p.exists() or not script_p.exists():
            print(f"{ch_id:<10} | MISSING FILES")
            all_valid = False
            continue

        desc = load_model(desc_p, DescriptionFile)
        script = load_model(script_p, ScriptFile)
        rep = validate(script, desc, cfg)

        mins = script.total_words / 150.0
        total_words += script.total_words
        total_blocks += len(script.blocks)

        if not rep.ok:
            all_valid = False
            prob_str = f"{len(rep.problems)} errors: {rep.problems[0][:30]}"
        else:
            prob_str = "0 errors"

        print(f"{ch_id:<10} | {len(desc.panels):<8} | {len(script.blocks):<8} | {script.total_words:<8} | {mins:<8.1f} | {str(rep.ok):<6} | {prob_str}")

    print("-" * 75)
    print(f"TOTALS     | 10 Chs   | {total_blocks:<8} | {total_words:<8} | {total_words / 150:<8.1f} | {all_valid}")
    return all_valid


if __name__ == "__main__":
    audit()
