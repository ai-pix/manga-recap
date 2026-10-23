"""Generate studio audio, timeline, and render the 1-minute hook video for SSS-Class Revival Hunter."""

from __future__ import annotations

import datetime
import shutil

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths, repo_path
from manga_recap.core.schema import (
    ScriptBlock,
    ScriptFile,
    save_model,
)
from manga_recap.stages.s4_speech import run as run_speech
from manga_recap.stages.s5_render import run as run_render

HOOK_BLOCKS = [
    {
        "block_id": "h001",
        "panel_src": ("ch01", "panel_0043"),
        "narration": "In a deadly tower where death is permanent, one pathetic F-rank hunter unlocked the most useless skill in human history."
    },
    {
        "block_id": "h002",
        "panel_src": ("ch01", "panel_0056"),
        "narration": "He can copy one skill from whoever murders him, meaning to even activate it, he has to die first."
    },
    {
        "block_id": "h003",
        "panel_src": ("ch02", "panel_0061"),
        "narration": "When the world's number one hunter, Flame Emperor, brutally slaughters him in a dark alley,"
    },
    {
        "block_id": "h004",
        "panel_src": ("ch02", "panel_0079"),
        "narration": "The skill triggers, revealing the terrifying secret behind the invincible idol's power."
    },
    {
        "block_id": "h005",
        "panel_src": ("ch02", "panel_0083"),
        "narration": "A golden system prompt flashes: copying the killer's highest rank ability."
    },
    {
        "block_id": "h006",
        "panel_src": ("ch03", "panel_0014"),
        "narration": "EX-Rank Skill: The Time Traveler's Clock, automatically rewinding time twenty-four hours upon death!"
    },
    {
        "block_id": "h007",
        "panel_src": ("ch03", "panel_0077"),
        "narration": "Flame Emperor never had godlike instincts; he simply died repeatedly until he memorized every battle."
    },
    {
        "block_id": "h008",
        "panel_src": ("ch03", "panel_0083"),
        "narration": "Realizing killing him today is impossible because Flame Emperor will just rewind and strike back,"
    },
    {
        "block_id": "h009",
        "panel_src": ("ch03", "panel_0085"),
        "narration": "Gong-ja makes an insane decision: strike eleven full years in the past before Flame Emperor ever awakened."
    },
    {
        "block_id": "h010",
        "panel_src": ("ch03", "panel_0091"),
        "narration": "And to rewind eleven full years with a twenty-four hour clock means one thing:"
    },
    {
        "block_id": "h011",
        "panel_src": ("ch03", "panel_0093"),
        "narration": "Plunging a dagger into his own chest four thousand and ninety times."
    },
    {
        "block_id": "h012",
        "panel_src": ("ch04", "panel_0072"),
        "narration": "Die. Rewind. Stab. Die. Four thousand deaths of pure agonizing torment to conquer destiny!"
    },
    {
        "block_id": "h013",
        "panel_src": ("ch01", "panel_0065"),
        "narration": "Witness the complete four-hour journey of how the universe's greatest lunatic conquered the tower!"
    }
]


def build_hook():
    cfg = load_config()
    paths = ChapterPaths.create("revival_hunter_hook")
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.panels_dir.mkdir(parents=True, exist_ok=True)

    print("[hook] Staging panels and script...", flush=True)

    script_blocks = []
    for idx, item in enumerate(HOOK_BLOCKS, start=1):
        pid = f"panel_{idx:04d}"
        ch, src_pid = item["panel_src"]
        src_path = repo_path(f"data/chapters/revival_hunter_{ch}/02_panels/{src_pid}.jpg")
        if not src_path.exists():
            src_path = repo_path(f"data/chapters/revival_hunter_{ch}/02_panels/{src_pid}.png")
        shutil.copy2(src_path, paths.panels_dir / f"{pid}.jpg")

        bid = item["block_id"]
        narration = item["narration"]
        script_blocks.append(
            ScriptBlock(
                block_id=bid,
                panel_ids=[pid],
                narration=narration,
                word_count=len(narration.split()),
                panel_indices=[idx],
            )
        )

    script_file = ScriptFile(
        chapter_id="revival_hunter_hook",
        created_at=datetime.datetime.now().isoformat(),
        total_blocks=len(script_blocks),
        total_words=sum(b.word_count for b in script_blocks),
        blocks=script_blocks,
    )
    save_model(script_file, paths.script_file)
    print(f"[hook] Staged {len(script_blocks)} blocks ({script_file.total_words} words)")

    print("[hook] Synthesizing narration audio via Fish Audio...", flush=True)
    timeline = run_speech(paths, cfg, force=True)
    print(f"[hook] Audio generated: {timeline.duration:.1f}s ({len(timeline.blocks)} blocks)")

    print("\n[hook] Launching Kaggle GPU render for 1-minute hook...", flush=True)
    run_render(paths, cfg, force=True, kernel_slug="manga-recap-render")
    print(f"[hook] Hook video successfully rendered -> {paths.final_file}")


if __name__ == "__main__":
    build_hook()
