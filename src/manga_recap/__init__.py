"""Manga recap pipeline: pages in, narrated video out.

Stage layout, in execution order:

    s0_ingest    pages in  -> normalised page images
    s1_crop      pages     -> cropped panels + panel index
    s2_describe  panels    -> per-panel visual descriptions
    s3_script    panels    -> storyboard script
    s4_speech    script    -> narration audio + block timeline   (Kaggle)
    s5_render    timeline  -> final video                        (Kaggle)

Each stage owns exactly one numbered artifact and validates both ends of its
handoff, so swapping one stage cannot silently corrupt the next.
"""

__version__ = "0.1.0"

__all__ = ["__version__"]
