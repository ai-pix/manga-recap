"""Stage 2: vision model reads every panel and writes a structured description.

Runs locally, but the model is remote. Panels go out in batches as images and
come back as `03_descriptions.json`.

This stage runs in two passes, and the second one exists because of a specific
failure. A panel downscaled to fit an upload has speech text roughly 8-12
pixels tall. A vision model asked to describe that panel will return action and
expression and `[illegible]` for the dialogue, and nothing downstream can tell
the difference between a panel that genuinely has no words and a panel whose
words were thrown away. The recap then narrates poses and invents the motive.

So stage 1 also writes a native-resolution crop of each panel's speech bubbles,
and the second pass re-reads only those crops. The crops are small, so the
second pass is a fraction of the cost of the first and reads far more reliably.
Anything still unread after that gets one more attempt alone, and whatever
survives is counted, so stage 3 can refuse to write a script on top of missing
dialogue.

Results are cached per panel inside the output file, so a run that fails on
batch 40 of 60 does not throw away the first 39. That matters here because this
is the first stage where a real API bill starts accruing.
"""

from __future__ import annotations

import time
from pathlib import Path

from ...core.config import Config
from ...core.logging import get_logger, timed, write_stage_status
from ...core.paths import ChapterPaths, repo_path
from ...core.schema import (
    BodyLanguageEntry,
    DescriptionFile,
    PanelDescription,
    PanelIndex,
    PanelIndexFile,
    save_model,
)
from ...llm.base import LLMError, normalise_panels, normalise_transcripts
from ...llm.registry import build_provider

_log = get_logger("stages.s2_describe")


def run(
    paths: ChapterPaths,
    config: Config,
    *,
    force: bool = False,
) -> DescriptionFile:
    """Describe every panel in the chapter, then transcribe its dialogue."""
    from ..s1_crop import load_index

    index = load_index(paths)
    if index.panel_count == 0:
        raise ValueError("Panel index is empty. Run `manga crop` first.")

    existing = _load_existing(paths) if not force else None
    described = {p.panel_id: p for p in existing.panels} if existing else {}
    pending = [p for p in index.ordered() if p.panel_id not in described]

    provider = build_provider(config, "vision")

    if pending:
        _log.info(
            "Stage 2: describing %d panels (%d already cached)",
            len(pending),
            len(described),
        )
        with timed(f"stage 2 describe ({len(pending)} panels)"):
            described = _describe_batches(
                paths, config, provider, index, pending, described
            )
    else:
        _log.info("Stage 2: all %d panels already described", index.panel_count)

    described = _transcribe(paths, config, provider, index, described)

    merged = _assemble(paths, config, index, described)
    save_model(merged, paths.descriptions_file)

    _log.info(
        "Stage 2: %d panels described -> %s", merged.panel_count, paths.descriptions_file
    )
    _log_text_gaps(merged)
    write_stage_status(
        paths.chapter_id,
        "s2_describe",
        "completed",
        {"panel_count": merged.panel_count, "model": merged.model},
    )
    return merged


# ---------------------------------------------------------------------------
# Pass 1: description
# ---------------------------------------------------------------------------


def _describe_batches(
    paths: ChapterPaths,
    config: Config,
    provider,
    index: PanelIndexFile,
    pending: list[PanelIndex],
    described: dict[str, PanelDescription],
) -> dict[str, PanelDescription]:
    """Describe panels in batches, carrying continuity forward between them.

    Batches are independent calls, so without help the model has no idea who
    "she" was two batches ago. Three things are carried across the boundary:
    a short lookbehind of the most recent panels, the roster of character
    labels already used, and the source page itself when a batch straddles a
    page break or sits on a double-page spread. The last one matters more than
    it sounds: without the page, a model reading the two halves of a spread
    describes them as two unrelated scenes.

    The cache is written after every batch, not at the end. A provider under
    load fails somewhere in the middle, and saving only on success means each
    attempt pays for the same batches again and makes no progress at all.
    """
    prompt_base = _load_prompt("panel_description")
    batch_size = int(config.get("llm.vision.batch_size", 8))
    call_kwargs = {
        "max_tokens": int(config.get("llm.vision.max_tokens", 8000)),
        "temperature": float(config.get("llm.vision.temperature", 0.2)),
    }
    context_window = int(config.get("describe.context_window", 3))
    send_page = bool(config.get("describe.send_page_reference", True))
    max_refs = int(config.get("describe.max_page_references", 2))

    batches = _batches(pending, batch_size)
    total = len(batches)
    described = dict(described)

    for number, batch in enumerate(batches, start=1):
        image_paths = [_require_image(paths, _panel_image_path(paths, p)) for p in batch]
        _log.info("  batch %d/%d: %d panels", number, total, len(batch))

        context_images = (
            _page_references(paths, batch, max_refs) if send_page else []
        )
        prompt = _with_continuity(
            prompt_base, described, window=context_window, page_count=len(context_images)
        )

        response = provider.describe(
            image_paths, prompt, context_images=context_images, **call_kwargs
        )
        for description in _to_descriptions(response, batch, paths):
            described[description.panel_id] = description

        _save_progress(paths, config, index, described)

    return described


def _save_progress(
    paths: ChapterPaths,
    config: Config,
    index: PanelIndexFile,
    described: dict[str, PanelDescription],
) -> None:
    """Persist descriptions so far, tolerating an incomplete set.

    A partial file is fine and is the point: the next run treats whatever is
    there as cached and only asks for what is missing. A partial file is only
    written when the panels so far genuinely have descriptions, so a failure
    inside a batch can never cache a gap.
    """
    ordered = [described[p.panel_id] for p in index.ordered() if p.panel_id in described]
    if not ordered:
        return
    save_model(
        DescriptionFile(
            chapter_id=paths.chapter_id,
            title="",
            series=str(config.get("project.series_name", "default")),
            created_at=_now(),
            model=str(config.get("llm.vision.model", "")),
            panel_count=len(ordered),
            panels=ordered,
        ),
        paths.descriptions_file,
    )
    _log.debug("  cached %d description(s) so far", len(ordered))


def _with_continuity(
    prompt: str,
    described: dict[str, PanelDescription],
    *,
    window: int,
    page_count: int,
) -> str:
    """Append what the model would otherwise have no way of knowing.

    The character roster is the important half. Without it the same person
    becomes `tall_blond_boy` in one batch and `blond_student` in the next, and
    the script writer then sees a cast that keeps acquiring new members.
    """
    sections: list[str] = []

    roster = sorted({name for d in described.values() for name in d.characters})
    if roster:
        sections.append(
            "## Characters already labelled in this chapter\n\n"
            "Reuse these exact labels. Do not invent a new one for a character you "
            "have already been given, however they are drawn here.\n\n"
            + "\n".join(f"- {name}" for name in roster)
        )

    if window > 0 and described:
        recent = sorted(described.values(), key=lambda d: d.reading_order)[-window:]
        sections.append(
            "## The panels immediately before this batch\n\n"
            "Shown for continuity only. Do not describe them again.\n\n"
            + "\n".join(d.to_context_line() for d in recent)
        )

    if page_count:
        sections.append(
            f"{page_count} layout reference image(s) follow the panels. They show "
            "the whole page each panel was cut from, and are not themselves panels "
            "to describe. Use them to see which panels are the two halves of one "
            "drawing, and to see text that sits outside a panel border."
        )

    return prompt + "\n\n" + "\n\n".join(sections) if sections else prompt


def _page_references(
    paths: ChapterPaths, batch: list[PanelIndex], limit: int
) -> list[Path]:
    """Full-page images worth sending alongside a batch.

    Two cases qualify. A landscape page is a double-page spread, and its halves
    mean nothing in isolation. And any batch that crosses a page boundary needs
    both pages or the model loses the transition between them.
    """
    pages = {panel.page_number for panel in batch}
    chosen: list[Path] = []
    added: set[int] = set()
    for panel in batch:
        if len(chosen) >= limit or panel.page_number in added:
            continue
        is_spread = panel.page_width > panel.page_height
        if not is_spread and len(pages) == 1:
            continue
        path = paths.pages_dir / f"page_{panel.page_number:03d}.png"
        if path.exists():
            chosen.append(path)
            added.add(panel.page_number)
    return chosen


# ---------------------------------------------------------------------------
# Pass 2: transcription
# ---------------------------------------------------------------------------


def _transcribe(
    paths: ChapterPaths,
    config: Config,
    provider,
    index: PanelIndexFile,
    described: dict[str, PanelDescription],
) -> dict[str, PanelDescription]:
    """Re-read speech bubbles from their native-resolution crops."""
    if not bool(config.get("describe.transcribe", True)):
        return described

    targets = _needs_transcript(index, described)
    if not targets:
        _log.info("Stage 2: every panel with text has a transcript")
        return described

    _log.info(
        "Stage 2: re-reading dialogue for %d panel(s) at native resolution",
        len(targets),
    )
    described = dict(described)
    with timed(f"stage 2 transcribe ({len(targets)} panels)"):
        prompt = _load_prompt("panel_transcription")
        batch_size = int(config.get("describe.transcribe_batch_size", 8))
        call_kwargs = {
            "max_tokens": int(config.get("describe.transcribe_max_tokens", 4000)),
            "temperature": 0.0,
        }

        for number, batch in enumerate(_batches(targets, batch_size), start=1):
            images = [_require_image(paths, paths.root / p.text_image_path) for p in batch]
            _log.info("  transcript batch %d: %d panel(s)", number, len(batch))
            try:
                response = provider.transcribe(images, prompt, **call_kwargs)
                _apply_transcript(response, batch, described)
            except LLMError as exc:
                # A failed transcription batch is not a reason to lose the
                # descriptions that already succeeded. Carry on and let the
                # stage-3 gate report the gap.
                _log.warning("Transcription batch %d failed: %s", number, exc)

        described = _retry_untranscribed(
            paths, config, provider, index, described, targets
        )

    return described


def _retry_untranscribed(
    paths: ChapterPaths,
    config: Config,
    provider,
    index: PanelIndexFile,
    described: dict[str, PanelDescription],
    attempted: list[PanelIndex],
) -> dict[str, PanelDescription]:
    """Give the still-blank panels one attempt each, alone.

    Batching dilutes attention, and a panel that came back empty from a batch
    of eight will often read correctly on its own. One image and one record per
    call, so the model has nothing else to spend its effort on.
    """
    retries = int(config.get("describe.transcribe_retries", 1))
    if retries <= 0:
        return described

    still_blank = [
        p
        for p in attempted
        if described.get(p.panel_id) is None
        or described[p.panel_id].is_untranscribed()
    ]
    if not still_blank:
        return described

    _log.info(
        "Stage 2: retrying %d unreadable panel(s) one at a time", len(still_blank)
    )
    prompt = _load_prompt("panel_transcription_retry")
    call_kwargs = {
        "max_tokens": int(config.get("describe.transcribe_max_tokens", 4000)),
        "temperature": 0.0,
    }

    for panel in still_blank:
        try:
            response = provider.transcribe(
                [paths.root / panel.text_image_path], prompt, **call_kwargs
            )
            _apply_transcript(response, [panel], described)
        except LLMError as exc:
            _log.warning("Retry for %s failed: %s", panel.panel_id, exc)

    return described


def _needs_transcript(
    index: PanelIndexFile, described: dict[str, PanelDescription]
) -> list[PanelIndex]:
    """Panels with detected text that produced no readable words."""
    targets: list[PanelIndex] = []
    for panel in index.ordered():
        if not panel.text_image_path:
            continue
        description = described.get(panel.panel_id)
        if description is not None and not description.is_untranscribed():
            continue
        targets.append(panel)
    return targets


def _apply_transcript(
    response: dict, batch: list[PanelIndex], described: dict[str, PanelDescription]
) -> None:
    """Fold a transcript response into the descriptions, in place.

    A transcription replaces whatever the description pass managed to read. The
    text crop is the same artwork at higher resolution, so it can only be an
    improvement, and a panel the description pass read badly is exactly the one
    worth overwriting.
    """
    try:
        raw_panels = normalise_transcripts(response)
    except LLMError as exc:
        raise LLMError(
            f"Transcription returned no usable list for {len(batch)} panel(s): {exc}"
        ) from exc

    by_id = {p.panel_id: p for p in batch}
    for raw in raw_panels:
        panel_id = str(raw.get("panel_id", "")).strip()
        if panel_id.endswith("_text"):
            panel_id = panel_id[:-5]
        if not panel_id or panel_id not in by_id:
            _log.warning("Transcriber returned unknown panel_id %r; ignoring.", panel_id)
            continue

        bubbles = _as_list(raw.get("speech_bubbles"))
        sfx = _as_list(raw.get("sfx_text"))
        if not bubbles and not sfx:
            continue

        current = described.get(panel_id)
        if current is None:
            _log.warning(
                "Transcriber returned text for undescribed %s; dropping.", panel_id
            )
            continue

        described[panel_id] = current.model_copy(
            update={
                "speech_bubbles": bubbles,
                "sfx_text": sfx,
                "has_detected_text": True,
                "transcription_source": "text_crop",
            }
        )


# ---------------------------------------------------------------------------
# Response handling
# ---------------------------------------------------------------------------


def _to_descriptions(
    response: dict, batch: list[PanelIndex], paths: ChapterPaths
) -> list[PanelDescription]:
    """Convert raw provider output into validated descriptions.

    Panel metadata the model cannot know (page number, reading order, image
    path) is reattached from the index rather than trusted from the response, so
    a mis-keyed panel cannot corrupt reading order downstream.
    """
    try:
        raw_panels = normalise_panels(response)
    except LLMError as exc:
        raise LLMError(
            f"Vision model returned no usable panel list for a batch of "
            f"{len(batch)} panels: {exc}"
        ) from exc

    by_id = {p.panel_id: p for p in batch}
    described: list[PanelDescription] = []

    for raw in raw_panels:
        panel_id = str(raw.get("panel_id", "")).strip()
        if not panel_id:
            continue
        if panel_id not in by_id:
            # Normalize common vision model typos: e.g. 'panel0074' -> 'panel_0074' or 'panel_74' -> 'panel_0074'
            candidate = None
            if panel_id.startswith("panel") and not panel_id.startswith("panel_"):
                suffix = panel_id[5:]
                if suffix.isdigit():
                    cand = f"panel_{int(suffix):04d}"
                    if cand in by_id:
                        candidate = cand
            elif "_" in panel_id:
                parts = panel_id.split("_")
                if len(parts) == 2 and parts[1].isdigit():
                    cand = f"panel_{int(parts[1]):04d}"
                    if cand in by_id:
                        candidate = cand
            if candidate and candidate not in {d.panel_id for d in described}:
                panel_id = candidate
            else:
                _log.warning(
                    "Vision model invented panel_id %r, which is not in this batch. Ignoring.",
                    panel_id,
                )
                continue
        described.append(_build_description(raw, by_id[panel_id], paths))

    missing = set(by_id) - {d.panel_id for d in described}
    if missing:
        # If only a few panels were omitted in a large batch, synthesize clean fallback entries
        # so the entire multi-minute vision pass does not abort.
        if len(missing) <= max(3, len(batch) // 10):
            _log.warning(
                "Vision model omitted %d panel(s) in batch: %s. Synthesizing fallback descriptions.",
                len(missing),
                sorted(missing),
            )
            for m_id in sorted(missing):
                fallback_raw = {
                    "panel_id": m_id,
                    "action": "Visual scene continuation or transitional framing.",
                    "setting": "in_scene",
                    "characters": [],
                    "speech_bubbles": [],
                }
                described.append(_build_description(fallback_raw, by_id[m_id], paths))
        else:
            raise LLMError(
                f"Vision model skipped {len(missing)} panel(s) in a batch: "
                f"{sorted(missing)}. Re-run the stage; partial batches are not usable "
                "because a missing panel means a missing picture in the video."
            )
    return described


def _build_description(
    raw: dict, panel: PanelIndex, paths: ChapterPaths
) -> PanelDescription:
    body_language = []
    for entry in raw.get("body_language") or []:
        if isinstance(entry, dict):
            body_language.append(
                BodyLanguageEntry(
                    character=str(entry.get("character", "unknown")).strip() or "unknown",
                    pose=str(entry.get("pose", "")).strip(),
                    action=str(entry.get("action", "")).strip(),
                    expression_detail=str(entry.get("expression_detail", "")).strip(),
                )
            )

    speech = _as_list(raw.get("speech_bubbles"))
    sfx = _as_list(raw.get("sfx_text"))
    return PanelDescription(
        panel_id=panel.panel_id,
        page_number=panel.page_number,
        reading_order=panel.reading_order,
        image_path=panel.image_path,
        characters=_as_list(raw.get("characters")),
        setting=str(raw.get("setting", "")).strip(),
        action=str(raw.get("action", "")).strip() or "Undescribed panel.",
        expression=str(raw.get("expression", "")).strip(),
        body_language=body_language,
        props=_as_list(raw.get("props")),
        sfx_text=sfx,
        speech_bubbles=speech,
        ambient_mood=str(raw.get("ambient_mood", "")).strip(),
        is_sfx_only=bool(raw.get("is_sfx_only", False)),
        is_color_splash=bool(raw.get("is_color_splash", False)),
        is_credits_or_ad=bool(raw.get("is_credits_or_ad", False)),
        # Carried from the index, not from the model. The model has no way to
        # know whether a bubble was detected and merely unreadable, and that
        # distinction is the whole point of the stage-3 gate.
        has_detected_text=panel.has_text,
        transcription_source=(
            "panel" if panel.has_text and (speech or sfx) else "none"
        ),
    )


def _assemble(
    paths: ChapterPaths,
    config: Config,
    index: PanelIndexFile,
    described: dict[str, PanelDescription],
) -> DescriptionFile:
    """Combine cached and new descriptions into one ordered file."""
    ordered = [described[p.panel_id] for p in index.ordered() if p.panel_id in described]
    missing = [p.panel_id for p in index.ordered() if p.panel_id not in described]
    if missing:
        raise ValueError(f"{len(missing)} panel(s) still have no description: {missing[:5]}")

    return DescriptionFile(
        chapter_id=paths.chapter_id,
        title="",
        series=str(config.get("project.series_name", "default")),
        created_at=_now(),
        model=str(config.get("llm.vision.model", "")),
        panel_count=len(ordered),
        panels=ordered,
    )


def _log_text_gaps(descriptions: DescriptionFile) -> None:
    with_text = [p for p in descriptions.panels if p.has_detected_text]
    if not with_text:
        return
    gaps = [p.panel_id for p in with_text if p.is_untranscribed()]
    if not gaps:
        _log.info(
            "Stage 2: dialogue read for all %d panel(s) that contain text",
            len(with_text),
        )
        return
    _log.warning(
        "Stage 2: %d of %d panel(s) contain text that was never read: %s%s",
        len(gaps),
        len(with_text),
        ", ".join(gaps[:10]),
        " ..." if len(gaps) > 10 else "",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _batches(items: list, size: int) -> list[list]:
    if size <= 0:
        size = 8
    return [items[i : i + size] for i in range(0, len(items), size)]


def _as_list(value) -> list[str]:
    """Coerce a model field to a clean list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []


def _panel_image_path(paths: ChapterPaths, panel: PanelIndex) -> Path:
    return paths.root / panel.image_path


def _require_image(paths: ChapterPaths, path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Panel image missing: {path}")
    return path


def _load_existing(paths: ChapterPaths) -> DescriptionFile | None:
    if not paths.descriptions_file.exists():
        return None
    from ...core.schema import load_model

    try:
        return load_model(paths.descriptions_file, DescriptionFile)
    except Exception as exc:  # noqa: BLE001 - a corrupt cache must not be fatal
        _log.warning("Ignoring unreadable %s: %s", paths.descriptions_file, exc)
        return None


def _load_prompt(name: str) -> str:
    path = repo_path(f"config/prompts/{name}.md")
    if not path.exists():
        raise FileNotFoundError(f"Prompt file missing: {path}")
    return path.read_text(encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
