"""Pydantic data contracts for every artifact that crosses a stage boundary.

Each stage validates its input and its output against these models. That turns
a malformed handoff into a loud failure at the stage boundary instead of a
silently broken video three stages later.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PanelSource = Literal["yolo", "opencv", "manual"]

_WORDS_RE = re.compile(r"[a-z0-9']+")


def _words_of(text: str) -> list[str]:
    """Lowercase word forms, for comparing narration against its beats."""
    return _WORDS_RE.findall(text.lower())


# ---------------------------------------------------------------------------
# Stage 1 -> stage 2 : the panel inventory
# ---------------------------------------------------------------------------


class BBox(BaseModel):
    """Pixel bounding box, origin at the top-left of the page."""

    x1: int = Field(ge=0)
    y1: int = Field(ge=0)
    x2: int
    y2: int

    @model_validator(mode="after")
    def _check_extent(self) -> BBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError(
                f"Bounding box has non-positive extent: "
                f"({self.x1}, {self.y1}) -> ({self.x2}, {self.y2})"
            )
        return self

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    def to_xywh(self) -> list[int]:
        return [self.x1, self.y1, self.width, self.height]

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2.0, (self.y1 + self.y2) / 2.0)

    def intersection_area(self, other: BBox) -> int:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        return max(0, ix2 - ix1) * max(0, iy2 - iy1)

    def iou(self, other: BBox) -> float:
        """Intersection over union, used to collapse duplicate detections."""
        inter = self.intersection_area(other)
        if inter == 0:
            return 0.0
        union = self.area + other.area - inter
        return inter / union if union else 0.0

    def contains_ratio(self, other: BBox) -> float:
        """Fraction of `other` that falls inside this box, 0..1.

        This is the test that decides whether a speech bubble survived the
        crop. A bubble clipped by the panel border scores below 1.0, and a
        bubble that belongs to a different panel entirely scores near 0.
        """
        if other.area == 0:
            return 0.0
        return self.intersection_area(other) / other.area

    def center_inside(self, other: BBox, *, slack: float = 0.0) -> bool:
        """True when this box's centre lies within `other`, optionally grown."""
        cx, cy = self.center
        return (
            other.x1 - slack <= cx <= other.x2 + slack
            and other.y1 - slack <= cy <= other.y2 + slack
        )

    def union(self, other: BBox) -> BBox:
        return BBox(
            x1=min(self.x1, other.x1),
            y1=min(self.y1, other.y1),
            x2=max(self.x2, other.x2),
            y2=max(self.y2, other.y2),
        )

    @classmethod
    def union_all(cls, boxes: list[BBox]) -> BBox | None:
        """Smallest box containing every box in `boxes`, or None if empty."""
        if not boxes:
            return None
        result = boxes[0]
        for box in boxes[1:]:
            result = result.union(box)
        return result


class PanelIndex(BaseModel):
    """A cropped panel's location and reading-order position.

    `text_boxes` are the speech and text regions the detector found inside this
    panel. They are kept rather than discarded because they are the only proof
    that a bubble was not cut by the crop, and because the transcription stage
    needs a tight box to re-read the text at native resolution.
    """

    panel_id: str
    page_number: int = Field(ge=1)
    index_on_page: int = Field(ge=1)
    reading_order: int = Field(ge=1)
    bbox: BBox
    image_path: str
    source: PanelSource = "yolo"
    page_width: int = Field(ge=1)
    page_height: int = Field(ge=1)
    # Detector-found text regions unioned into this panel, in page coordinates.
    text_boxes: list[BBox] = Field(default_factory=list)
    # Native-resolution crop of just those regions, relative to the chapter
    # root. Empty when the panel has no text.
    text_image_path: str = ""
    # panel_id of the panel this one sits inside, when the layout nests panels.
    nested_in: str = ""

    @property
    def area_ratio(self) -> float:
        return self.bbox.area / float(self.page_width * self.page_height)

    @property
    def has_text(self) -> bool:
        return bool(self.text_boxes)


class PanelIndexFile(BaseModel):
    """Stage 1 output: every panel in the chapter, in reading order."""

    chapter_id: str
    page_count: int = Field(ge=0)
    panel_count: int = Field(ge=0)
    created_at: str
    panels: list[PanelIndex]
    # Every text region the detector found on each page, keyed by page number,
    # including any that no panel claimed. Without this list a bubble that
    # falls in a gutter belongs to nothing and is invisible to the coverage
    # check, which is precisely the case the check exists to catch.
    page_text_boxes: dict[int, list[BBox]] = Field(default_factory=dict)
    # Drawn extent of each page, margins excluded. Page area is the wrong
    # denominator for "did we detect enough panels", because a page with wide
    # margins can be almost entirely gutter and still be fully detected.
    page_content_bbox: dict[int, BBox] = Field(default_factory=dict)
    # Ink that no detected panel accounts for, offered as a second opinion.
    # Reported, never applied: a panel bleeding off the page and artwork
    # spilling between two bordered panels look identical in ink.
    page_missing_candidates: dict[int, list[BBox]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_orders(self) -> PanelIndexFile:
        if self.panels and len(self.panels) != self.panel_count:
            raise ValueError(
                f"panel_count {self.panel_count} does not match "
                f"{len(self.panels)} indexed panels"
            )
        orders = [p.reading_order for p in self.panels]
        if len(set(orders)) != len(orders):
            raise ValueError("Duplicate reading_order values in panel index")
        return self

    def ordered(self) -> list[PanelIndex]:
        return sorted(self.panels, key=lambda p: p.reading_order)

    def by_id(self) -> dict[str, PanelIndex]:
        return {p.panel_id: p for p in self.panels}

    def by_page(self) -> dict[int, list[PanelIndex]]:
        """Panels grouped by page, each group in reading order."""
        grouped: dict[int, list[PanelIndex]] = {}
        for panel in self.ordered():
            grouped.setdefault(panel.page_number, []).append(panel)
        return grouped


# ---------------------------------------------------------------------------
# Stage 2 output : the vision model's reading of each panel
# ---------------------------------------------------------------------------


class BodyLanguageEntry(BaseModel):
    character: str
    pose: str
    action: str
    expression_detail: str


class PanelDescription(BaseModel):
    """What a vision model sees in one panel.

    Kept descriptive and free of interpretation. The script stage is what turns
    this into a story, so this stage must not pre-judge what is funny.
    """

    panel_id: str
    page_number: int = Field(ge=1)
    reading_order: int = Field(ge=1)
    image_path: str
    characters: list[str] = Field(default_factory=list)
    setting: str = ""
    action: str
    expression: str = ""
    body_language: list[BodyLanguageEntry] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    sfx_text: list[str] = Field(default_factory=list)
    speech_bubbles: list[str] = Field(default_factory=list)
    ambient_mood: str = ""
    is_sfx_only: bool = False
    is_color_splash: bool = False
    is_credits_or_ad: bool = False
    # True when stage 1 found text regions on this panel. Carried here so the
    # script gate can tell a genuinely wordless panel from a failed read.
    has_detected_text: bool = False
    # Which image the dialogue actually came from. `text_crop` is the reliable
    # one; `panel` means only the downscaled panel was legible.
    transcription_source: Literal["none", "panel", "text_crop"] = "none"

    @field_validator("action")
    @classmethod
    def _action_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("action must not be empty")
        return value.strip()

    def is_untranscribed(self) -> bool:
        """True when text was detected but nothing readable came back.

        This is the signal that a beat's dialogue was lost, and it is the one
        failure mode that silently guts a recap: the description still has
        poses and expressions, so nothing crashes, the narrator just invents
        the motivation.
        """
        return self.has_detected_text and not self.speech_bubbles and not self.sfx_text

    def is_skippable(self, skippable_labels: set[str]) -> bool:
        """True when a panel is chrome (credits, an ad) rather than story."""
        if self.is_credits_or_ad:
            return True
        return self.setting.strip().lower() in skippable_labels

    def to_context_line(self) -> str:
        """Compact single-line rendering for the script prompt.

        Keeping the payload dense matters: the script stage reads the whole
        chapter in one call, so every wasted token is multiplied.
        """
        who = ", ".join(self.characters) if self.characters else "nobody"
        bits = [f"[{self.panel_id}] {who} in {self.setting or 'unknown setting'}: {self.action}"]
        if self.expression:
            bits.append(f"Expression: {self.expression}.")
        if self.speech_bubbles:
            # Dialogue is the ground truth for what a character wants. Labelling
            # it explicitly stops the writer from reinterpreting the beat.
            bits.append(f"They say: {' | '.join(self.speech_bubbles)}")
        elif self.has_detected_text:
            bits.append("(Dialogue present in the art but unreadable.)")
        if self.sfx_text:
            bits.append(f"SFX: {', '.join(self.sfx_text)}")
        if self.is_sfx_only:
            bits.append("(sound-effect only panel)")
        return " ".join(bits)


class DescriptionFile(BaseModel):
    """Stage 2 output: descriptions for every panel, in reading order."""

    chapter_id: str
    title: str = ""
    series: str = ""
    created_at: str
    model: str = ""
    panel_count: int = Field(ge=0)
    panels: list[PanelDescription]

    @model_validator(mode="after")
    def _check_ids(self) -> DescriptionFile:
        ids = [p.panel_id for p in self.panels]
        if len(set(ids)) != len(ids):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            raise ValueError(f"Duplicate panel_id values: {duplicates}")
        return self

    def ordered(self) -> list[PanelDescription]:
        return sorted(self.panels, key=lambda p: p.reading_order)

    def by_id(self) -> dict[str, PanelDescription]:
        return {p.panel_id: p for p in self.panels}


# ---------------------------------------------------------------------------
# Stage 3 output : the storyboard script
# ---------------------------------------------------------------------------


class ScriptBeat(BaseModel):
    """One clause of a block's narration, bound to the single panel showing it.

    A block is what TTS speaks. A beat is what the viewer sees *while* it is
    being spoken. Splitting the two is what makes the video trackable: a
    sentence that describes three actions gets three panels, each held for the
    words that talk about it, rather than one panel for the whole sentence.

    The renderer derives beats automatically when a block does not declare them,
    so `beats` is optional. Declaring them is how a writer overrides that guess.
    """

    beat_id: str
    text: str = Field(min_length=1)
    panel_id: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class ScriptBlock(BaseModel):
    """One narration beat, bound to the panels it plays over.

    This is the central contract of the whole system. A block is the atom that
    TTS speaks and the renderer shows, so `panel_ids` and `narration` must
    always agree.
    """

    block_id: str
    panel_ids: list[str] = Field(min_length=1)
    narration: str = Field(min_length=1)
    # Free-text note for the renderer, e.g. "punchline", "establishing".
    direction: str = ""
    # Optional explicit clause-to-panel mapping, in narration order. When empty
    # the renderer splits `narration` itself and distributes `panel_ids` across
    # the clauses. See `render.sync.derive_beats`.
    beats: list[ScriptBeat] = Field(default_factory=list)

    @field_validator("panel_ids")
    @classmethod
    def _no_duplicate_panels(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            duplicates = sorted({p for p in value if value.count(p) > 1})
            raise ValueError(f"Duplicate panel_ids in block: {duplicates}")
        return value

    @model_validator(mode="after")
    def _beats_belong_to_the_block(self) -> ScriptBlock:
        if not self.beats:
            return self
        unknown = sorted({b.panel_id for b in self.beats} - set(self.panel_ids))
        if unknown:
            raise ValueError(
                f"Block {self.block_id} binds beats to panels that are not in "
                f"panel_ids: {unknown}"
            )
        if len({b.beat_id for b in self.beats}) != len(self.beats):
            raise ValueError(f"Duplicate beat_id values in block {self.block_id}")

        # Every clause of the narration must be spoken by some beat, or the
        # words in the gap have no picture and the panel on screen will not be
        # the one being described. Compared on words rather than on the exact
        # string, so punctuation and casing differences do not trip it.
        said = [w for b in self.beats for w in _words_of(b.text)]
        narrated = _words_of(self.narration)
        missing = [w for w in narrated if w not in said]
        if missing and len(missing) <= max(3, len(narrated) // 10):
            raise ValueError(
                f"Block {self.block_id} has beats that do not cover its whole "
                f"narration; these words are spoken with no panel bound to them: "
                f"{missing[:10]}"
            )
        return self

    @property
    def word_count(self) -> int:
        return len(self.narration.split())


class ScriptFile(BaseModel):
    """Stage 3 output: the full storyboard."""

    chapter_id: str
    title: str = ""
    series: str = ""
    created_at: str
    model: str = ""
    target_words: int = 0
    blocks: list[ScriptBlock] = Field(min_length=1)

    @property
    def total_words(self) -> int:
        return sum(b.word_count for b in self.blocks)

    def referenced_panels(self) -> list[str]:
        seen: set[str] = set()
        for block in self.blocks:
            seen.update(block.panel_ids)
        return sorted(seen)

    def full_text(self, block_gap: str = "\n\n") -> str:
        """Concatenated narration, in block order.

        TTS speaks this as one continuous stream; the aligner maps word timings
        back onto block boundaries using these exact sentences.
        """
        return block_gap.join(b.narration.strip() for b in self.blocks)

    def block_char_spans(self) -> list[tuple[int, int]]:
        """Character offsets of each block inside `full_text`."""
        spans: list[tuple[int, int]] = []
        cursor = 0
        for block in self.blocks:
            text = block.narration.strip()
            start = cursor
            spans.append((start, start + len(text)))
            cursor = start + len(text) + 2
        return spans


# ---------------------------------------------------------------------------
# Stage 4 output : the audio timeline
# ---------------------------------------------------------------------------


class WordTiming(BaseModel):
    word: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)

    @model_validator(mode="after")
    def _check_order(self) -> WordTiming:
        if self.end < self.start:
            raise ValueError(
                f"Word {self.word!r} ends at {self.end}s, before it starts at {self.start}s"
            )
        return self


class BlockTiming(BaseModel):
    """When a block's narration plays, in seconds from audio start."""

    block_id: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    # `aligned` means Whisper word timings pinned it. `fallback_proportional`
    # means the character-ratio estimate was used because alignment failed.
    method: Literal["aligned", "fallback_proportional"] = "aligned"
    # Fraction of this block's tokens that matched a recognised word, 0..1.
    match_ratio: float = Field(default=1.0, ge=0.0, le=1.0)

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


class TimelineFile(BaseModel):
    """Stage 4 output: the audio and the block timing derived from it."""

    chapter_id: str
    audio_file: str
    sample_rate: int = Field(ge=1)
    duration: float = Field(ge=0)
    tts_backend: str = ""
    whisper_model: str = ""
    created_at: str
    words: list[WordTiming] = Field(default_factory=list)
    blocks: list[BlockTiming] = Field(min_length=1)

    @model_validator(mode="after")
    def _check_monotonic(self) -> TimelineFile:
        previous_end = -1.0
        for block in self.blocks:
            if block.start < previous_end - 0.001:
                raise ValueError(
                    f"Block {block.block_id} starts at {block.start:.3f}s, "
                    f"before the previous block ended at {previous_end:.3f}s"
                )
            previous_end = block.end
        return self

    def degraded_blocks(self) -> list[BlockTiming]:
        return [b for b in self.blocks if b.method != "aligned" or b.match_ratio < 0.75]


# ---------------------------------------------------------------------------
# Stage 5 output : the render report
# ---------------------------------------------------------------------------


class RenderClip(BaseModel):
    panel_id: str
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    zoom_start: float = 1.0
    zoom_end: float = 1.0


class RenderManifest(BaseModel):
    chapter_id: str
    created_at: str
    width: int
    height: int
    fps: int
    duration: float = Field(ge=0)
    clip_count: int = Field(ge=0)
    bgm_track: str | None = None
    output_file: str
    clips: list[RenderClip] = Field(default_factory=list)

    @property
    def panels_shown(self) -> set[str]:
        return {c.panel_id for c in self.clips}


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_model(path: Path, model_cls: type[BaseModel]) -> BaseModel:
    """Read JSON from disk and validate it against its schema."""
    if not path.exists():
        raise FileNotFoundError(f"Expected artifact is missing: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return model_cls.model_validate(raw)


def save_model(model: BaseModel, path: Path, *, indent: int = 2) -> Path:
    """Validate then write JSON. Never writes an invalid artifact to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump(mode="json")
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8"
    )
    return path


def validate_or_raise(model_cls: type[BaseModel], payload: Any, context: str) -> BaseModel:
    """Validate raw provider output, with an error message a human can act on."""
    try:
        return model_cls.model_validate(payload)
    except Exception as exc:  # pydantic ValidationError and anything else
        raise ValueError(
            f"{context} failed validation against {model_cls.__name__}: {exc}"
        ) from exc
