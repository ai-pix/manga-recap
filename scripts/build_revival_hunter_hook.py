"""Generate studio audio, timeline, and render the ultra-rapid, high-retention hook video for SSS-Class Revival Hunter."""

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
    # Act 1: The Suicide Shock
    {
        "block_id": "h001",
        "panel_src": ("ch03", "panel_0100"),  # kneeling gripping dagger with determination
        "narration": "How insane do you have to be..."
    },
    {
        "block_id": "h002",
        "panel_src": ("ch03", "panel_0084"),  # two hands driving blade down glowing impact
        "narration": "to stab a blade into your own heart..."
    },
    {
        "block_id": "h003",
        "panel_src": ("ch03", "panel_0085"),  # clutching dagger to chest suicide
        "narration": "four thousand and ninety times?!"
    },
    {
        "block_id": "h004",
        "panel_src": ("ch03", "panel_0095"),  # extreme close-up coughing blood
        "narration": "Waking up every morning coughing blood,"
    },
    {
        "block_id": "h005",
        "panel_src": ("ch03", "panel_0090"),  # driving sword down forcefully
        "narration": "plunging a dagger through your chest,"
    },
    {
        "block_id": "h006",
        "panel_src": ("ch03", "panel_0099"),  # montage repeatedly dying
        "narration": "and repeating death in pure agony!"
    },

    # Act 2: The Villain & The Alley Murder
    {
        "block_id": "h007",
        "panel_src": ("ch01", "panel_0043"),  # crying facing wall of envy
        "narration": "Confucius Kim was a pathetic F-rank nobody,"
    },
    {
        "block_id": "h008",
        "panel_src": ("ch02", "panel_0057"),  # flame emperor smug smile
        "narration": "until the world's greatest hero cornered him."
    },
    {
        "block_id": "h009",
        "panel_src": ("ch02", "panel_0061"),  # choking gongja by throat
        "narration": "Choked like a dog in a dirty alleyway,"
    },
    {
        "block_id": "h010",
        "panel_src": ("ch02", "panel_0078"),  # flaming hand incinerating head
        "narration": "his skull incinerated by blazing flames,"
    },
    {
        "block_id": "h011",
        "panel_src": ("ch02", "panel_0055"),  # bloody face gasping on ground dying
        "narration": "he bled out and took his final breath."
    },

    # Act 3: The Cheat Card
    {
        "block_id": "h012",
        "panel_src": ("ch01", "panel_0050"),  # blue system shock window
        "narration": "But the hero made one fatal mistake."
    },
    {
        "block_id": "h013",
        "panel_src": ("ch02", "panel_0084"),  # FLASH glowing gold card
        "narration": "Upon death, Confucius steals his murderer's greatest skill!"
    },
    {
        "block_id": "h014",
        "panel_src": ("ch03", "panel_0014"),  # Time Traveler's Clock EX-rank
        "narration": "An EX-Rank clock, rewinding time twenty-four hours!"
    },

    # Act 4: The 11-Year Suicide Grind
    {
        "block_id": "h015",
        "panel_src": ("ch03", "panel_0080"),  # Flame emperor interview 11 years ago
        "narration": "To kill that monster before he ever got strong,"
    },
    {
        "block_id": "h016",
        "panel_src": ("ch03", "panel_0083"),  # touching blade near chest
        "narration": "Confucius had to travel eleven years into the past."
    },
    {
        "block_id": "h017",
        "panel_src": ("ch03", "panel_0088"),  # gasping on back shocked
        "narration": "One death only rewinds one day."
    },
    {
        "block_id": "h018",
        "panel_src": ("ch03", "panel_0091"),  # Player Death notification
        "narration": "So he made a terrifying choice:"
    },
    {
        "block_id": "h019",
        "panel_src": ("ch03", "panel_0094"),  # submerged grimacing
        "narration": "Four thousand and ninety suicides in a row!"
    },
    {
        "block_id": "h020",
        "panel_src": ("ch03", "panel_0097"),  # kneeling in pain and despair
        "narration": "Die. Rewind. Stab. Die again!"
    },

    # Act 5: The Bloody Revenge Payoff
    {
        "block_id": "h021",
        "panel_src": ("ch04", "panel_0055"),  # sword impact flash with blood
        "narration": "Eleven years of torment conquered by pure spite!"
    },
    {
        "block_id": "h022",
        "panel_src": ("ch04", "panel_0070"),  # red/green slash cutting flame emperor
        "narration": "Slicing through the arrogant idol before he gains power!"
    },
    {
        "block_id": "h023",
        "panel_src": ("ch04", "panel_0078"),  # standing over corpse with bloody knife
        "narration": "Standing over his corpse with a blood-soaked knife."
    },
    {
        "block_id": "h024",
        "panel_src": ("ch04", "panel_0081"),  # close up bloodied resolved face
        "narration": "Witness the complete four-hour story of SSS-Class Revival Hunter!"
    }
]


def build_hook():
    cfg = load_config()
    paths = ChapterPaths.create("revival_hunter_hook")
    paths.root.mkdir(parents=True, exist_ok=True)
    paths.panels_dir.mkdir(parents=True, exist_ok=True)

    print("[hook] Staging 24 rapid-fire panels and punchy script...", flush=True)

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
    print(f"[hook] Staged {len(script_blocks)} rapid blocks ({script_file.total_words} words)")

    print("[hook] Synthesizing narration audio via Fish Audio...", flush=True)
    timeline = run_speech(paths, cfg, force=True)
    print(f"[hook] Audio generated: {timeline.duration:.1f}s ({len(timeline.blocks)} blocks)")

    print("\n[hook] Launching Kaggle GPU render for ultra-fast hook...", flush=True)
    run_render(paths, cfg, force=True, kernel_slug="manga-recap-render")
    print(f"[hook] Hook video successfully rendered -> {paths.final_file}")


if __name__ == "__main__":
    build_hook()
