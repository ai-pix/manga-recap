"""Objective, pixel-level classification of a panel crop's *visual* content.

Why this exists
---------------
The storyboard binds each spoken clause to one panel image, and whatever it
binds ends up on screen for that whole clause. If a bound panel is really just
a speech bubble floating on a blank void, or a black title card with white
text, the viewer stares at a wall of words instead of art -- the single most
common way these recap videos look cheap.

Nothing downstream can catch that from the *description* alone: a vision model
asked to describe a text-only crop will happily write "two narration boxes on a
white background", but it will also, when its crops are stale or misaligned,
describe a text card as a dramatic close-up (this exact failure shipped in
ORV ch01). Text is unreliable. Pixels are not.

So this module measures the actual image file and answers one question: does
this crop contain drawn artwork worth showing, or is it chrome? It reads the
same ``image_path`` the renderer will open, so a panel can never be judged from
one file and shown from another.

It is deliberately conservative about calling something *art*: only crops that
are overwhelmingly empty space (a void), or a flat field of ink with no local
structure (large lettering / UI bars), are pruned. A real scene always has
mid-tone detail spread across the frame and survives.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Tunables (kept here so they are visible and testable, not buried in config)
# ---------------------------------------------------------------------------

# A pixel within this many grey levels of pure white counts as empty paper.
_NEAR_WHITE = 238
# ...and within this many of pure black counts as empty void.
_NEAR_BLACK = 14
# Mid-tones between these bounds count as "drawn detail" (lineart, colour,
# shading). A real illustration is mostly mid-tones; a text card is mostly
# extremes (background + glyphs).
_DETAIL_LO = 30
_DETAIL_HI = 235

# Smallest dimension below which a crop cannot hold readable story art, only a
# sliver, gutter, or thin UI bar.
_MIN_SIDE = 90
# Below this total area a crop is a fragment, not a shot.
_MIN_AREA = 14_000

# Fraction of the frame that must be near-white/near-black before we call it a
# void. Real scenes rarely exceed ~0.7 because backgrounds carry tone.
_VOID_FRACTION = 0.80
# Even a mostly-empty frame is kept if enough pixels are genuine mid-tone
# detail (a face on a plain backdrop still has structure).
_MIN_DETAIL_FRACTION = 0.06

# Local-structure floor. A blurred/scaled copy of the frame compared against
# itself: high-frequency energy that survives downscaling is lineart/detail.
# A flat lettering field has almost none once averaged.
_STRUCT_FLOOR = 0.02


@dataclass(frozen=True)
class PanelContent:
    """Measured visual content of one panel crop."""

    panel_id: str
    width: int
    height: int
    # Share of pixels that are near-white or near-black (empty space).
    void_fraction: float
    # Share of pixels that are mid-tone "drawn detail".
    detail_fraction: float
    # Normalised high-frequency energy (local structure) in [0, 1].
    structure: float
    # True when the crop is chrome: a void, a text/title card, or a sliver.
    is_text_only: bool
    reason: str = ""


def _load_grey(path: Path):
    """Return (numpy array HxW uint8, width, height) for a WebP/PNG/JPEG crop."""
    import numpy as np
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("L")
        w, h = im.size
        arr = np.asarray(im, dtype=np.uint8)
    return arr, w, h


def analyse_panel(panel_id: str, image_path: Path | str) -> PanelContent:
    """Measure one panel crop and decide whether it is showable art or chrome.

    ``image_path`` must point at the exact file the renderer will open, so the
    verdict and the picture can never disagree.
    """
    path = Path(image_path)
    if not path.exists():
        for ext in (".webp", ".png", ".jpg", ".jpeg"):
            alt = path.with_suffix(ext)
            if alt.exists():
                path = alt
                break
    if not path.exists():
        # Missing file: do not prune on measurement grounds -- let the existing
        # render-time "missing panel" error surface it loudly instead.
        return PanelContent(panel_id, 0, 0, 0.0, 0.0, 0.0, False, "image missing")

    arr, w, h = _load_grey(path)

    void = float(((arr >= _NEAR_WHITE) | (arr <= _NEAR_BLACK)).mean())
    detail = float(((arr >= _DETAIL_LO) & (arr <= _DETAIL_HI)).mean())

    # High-frequency proxy: how much detail survives halving the resolution.
    # Real lineart and faces keep their edges under a 2x downsample; a flat
    # field of large glyphs and UI bars smooths away to almost nothing. Cheap
    # and robust -- no manual convolution needed.
    structure = _downsample_structure(arr)

    reasons: list[str] = []
    if min(w, h) < _MIN_SIDE:
        reasons.append(f"sliver {w}x{h}")
    if w * h < _MIN_AREA:
        reasons.append(f"tiny {w * h}px")
    if void >= _VOID_FRACTION and detail < _MIN_DETAIL_FRACTION:
        reasons.append(f"void/text-card ({void:.0%} empty)")
    elif void >= 0.88 and detail < 0.12:
        reasons.append(f"void/text-card ({void:.0%} empty, detail {detail:.0%})")
    elif detail < _MIN_DETAIL_FRACTION and structure < _STRUCT_FLOOR:
        reasons.append(f"flat lettering (detail {detail:.0%})")

    is_text_only = bool(reasons)
    return PanelContent(
        panel_id=panel_id,
        width=w,
        height=h,
        void_fraction=round(void, 4),
        detail_fraction=round(detail, 4),
        structure=round(structure, 4),
        is_text_only=is_text_only,
        reason="; ".join(reasons),
    )


def _downsample_structure(arr) -> float:
    """Fraction of local contrast that survives a 2x downsample, in [0, 1].

    A real illustration keeps sharp edges after averaging neighbours; a flat
    field of large lettering or a solid UI bar smooths toward uniform grey and
    loses almost all of it. Computed on the halved frame so it is cheap even on
    tall splash panels. Returns 0 for degenerate (sub-2px) crops.
    """
    import numpy as np

    h, w = arr.shape
    if h < 4 or w < 4:
        return 0.0
    a = arr.astype(np.float32)
    # Crop to an even grid, then average each 2x2 block into one value.
    eh, ew = (h // 2) * 2, (w // 2) * 2
    blocks = a[:eh, :ew].reshape(eh // 2, 2, ew // 2, 2).mean(axis=(1, 3))
    # Mean absolute neighbour difference on the smoothed frame, normalised.
    dh = np.abs(np.diff(blocks, axis=0)).mean()
    dv = np.abs(np.diff(blocks, axis=1)).mean()
    return float((dh + dv) / 2.0 / 255.0)


def classify_panels(descriptions, paths_root: Path) -> dict[str, PanelContent]:
    """Analyse every described panel against its real image file.

    Returns ``{panel_id: PanelContent}``. ``descriptions`` may be a
    ``DescriptionFile`` or any iterable of objects/dicts exposing ``panel_id``
    and ``image_path`` (relative to ``paths_root``).
    """
    results: dict[str, PanelContent] = {}
    if isinstance(descriptions, dict) and "panels" in descriptions:
        items = descriptions["panels"]
    else:
        items = getattr(descriptions, "panels", descriptions)
    for p in items:
        if isinstance(p, dict):
            pid = p.get("panel_id", "")
            rel = p.get("image_path", "")
        else:
            pid = getattr(p, "panel_id", "")
            rel = getattr(p, "image_path", "")
        if not pid:
            continue
        img = Path(rel)
        if not img.is_absolute():
            img = Path(paths_root) / rel
        results[pid] = analyse_panel(pid, img)
    return results


def clean_descriptions(
    descriptions: Any,
    chapter_dir: Path | str,
    config: Any = None,
) -> tuple[Any, int]:
    """Prunes text-only panels, voids, ads, and migrates dialogue to adjacent art panels.

    Returns (cleaned_descriptions, pruned_count).
    """
    from .schema import DescriptionFile

    skippable_labels: set[str] = set()
    if config:
        if hasattr(config, "get"):
            skippable_labels = {str(x).lower() for x in config.get("script.skippable_panel_labels", [])}
        elif isinstance(config, dict):
            skippable_labels = {str(x).lower() for x in config.get("script", {}).get("skippable_panel_labels", [])}

    ch_path = Path(chapter_dir)
    panels_dir = ch_path / "02_panels"

    is_dict = isinstance(descriptions, dict)
    if is_dict:
        desc_obj = DescriptionFile(**descriptions)
    else:
        desc_obj = descriptions

    ordered = desc_obj.ordered()
    pruned_count = 0
    pending_dialogue: list[str] = []

    for p in ordered:
        img_file = panels_dir / f"{p.panel_id}.webp"
        if not img_file.exists():
            img_file = panels_dir / f"{p.panel_id}.png"

        content = analyse_panel(p.panel_id, img_file) if img_file.exists() else None
        sem_skip = p.is_skippable(skippable_labels)
        pix_skip = content.is_text_only if content else False

        is_chrome = sem_skip or pix_skip or p.is_credits_or_ad

        if is_chrome:
            p.is_credits_or_ad = True
            p.is_text_only = True
            pruned_count += 1
            if p.speech_bubbles:
                for b in p.speech_bubbles:
                    if b not in pending_dialogue:
                        pending_dialogue.append(b)
        else:
            p.is_credits_or_ad = False
            p.is_text_only = False
            if pending_dialogue:
                # Prepend migrated dialogue
                p.speech_bubbles = pending_dialogue + [b for b in p.speech_bubbles if b not in pending_dialogue]
                pending_dialogue = []

    if pending_dialogue:
        story_panels = [p for p in ordered if not p.is_credits_or_ad]
        if story_panels:
            story_panels[-1].speech_bubbles.extend(
                [b for b in pending_dialogue if b not in story_panels[-1].speech_bubbles]
            )

    if is_dict:
        return desc_obj.model_dump(), pruned_count
    return desc_obj, pruned_count


def rebind_skippable_panels(
    script: Any,
    descriptions: Any,
    config: Any = None,
) -> tuple[Any, int]:
    """Rebind any script block or beat referencing a skippable/text panel to the closest story art panel.

    Returns (rebound_script, rebound_count).
    """
    from .schema import DescriptionFile, ScriptFile

    is_dict_script = isinstance(script, dict)
    script_obj = ScriptFile(**script) if is_dict_script else script

    is_dict_desc = isinstance(descriptions, dict)
    desc_obj = DescriptionFile(**descriptions) if is_dict_desc else descriptions

    skippable_labels: set[str] = set()
    if config:
        if hasattr(config, "get"):
            skippable_labels = {str(x).lower() for x in config.get("script.skippable_panel_labels", [])}
        elif isinstance(config, dict):
            skippable_labels = {str(x).lower() for x in config.get("script", {}).get("skippable_panel_labels", [])}

    panels = desc_obj.ordered()
    story_panels = [p for p in panels if not p.is_skippable(skippable_labels)]
    if not story_panels:
        story_panels = [p for p in panels if not p.is_credits_or_ad] or panels

    story_ids = {p.panel_id for p in story_panels}
    rebind_map: dict[str, str] = {}

    for p in panels:
        pid = p.panel_id
        if pid in story_ids:
            rebind_map[pid] = pid
        else:
            p_order = p.reading_order
            best_story_id = story_panels[0].panel_id
            min_dist = float("inf")
            for sp in story_panels:
                sp_order = sp.reading_order
                dist = abs(sp_order - p_order)
                # Slight bias to prefer preceding story panel
                eff_dist = dist if sp_order <= p_order else dist + 0.5
                if eff_dist < min_dist:
                    min_dist = eff_dist
                    best_story_id = sp.panel_id
            rebind_map[pid] = best_story_id

    def _find_best_rebind(cur_pid: str, local_story_pids: list[str]) -> str:
        if cur_pid in story_ids:
            return cur_pid
        if local_story_pids:
            cur_order = next((p.reading_order for p in panels if p.panel_id == cur_pid), 0)
            return min(
                local_story_pids,
                key=lambda sid: abs(
                    next((p.reading_order for p in story_panels if p.panel_id == sid), 0) - cur_order
                ),
            )
        return rebind_map.get(cur_pid, cur_pid)

    rebound_count = 0
    for block in script_obj.blocks:
        # Check story panels present in this block
        block_story_panels = [
            pid for pid in (block.panel_ids or []) if pid in story_ids
        ]
        if not block_story_panels and block.beats:
            block_story_panels = [
                b.panel_id for b in block.beats if b.panel_id in story_ids
            ]

        if block.beats:
            for beat in block.beats:
                cur_pid = beat.panel_id
                target_pid = _find_best_rebind(cur_pid, block_story_panels)
                if target_pid != cur_pid:
                    beat.panel_id = target_pid
                    rebound_count += 1
            distinct_pids: list[str] = []
            for beat in block.beats:
                if beat.panel_id and beat.panel_id not in distinct_pids:
                    distinct_pids.append(beat.panel_id)
            block.panel_ids = distinct_pids or [story_panels[0].panel_id]
        else:
            new_pids: list[str] = []
            for pid in block.panel_ids:
                target_pid = _find_best_rebind(pid, block_story_panels)
                if target_pid != pid:
                    rebound_count += 1
                if target_pid and target_pid not in new_pids:
                    new_pids.append(target_pid)
            block.panel_ids = new_pids or [story_panels[0].panel_id]

    if is_dict_script:
        return script_obj.model_dump(), rebound_count
    return script_obj, rebound_count

