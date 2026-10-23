# Stage 2 reference — describe one chapter

`03_descriptions.json` is written by many small vision workers, each covering a
contiguous `reading_order` range and writing one part file. This file is the
chapter-level reference every one of them shares: the roster that keeps labels
stable, the settings vocabulary, the pruning rules, and the two commands that
turn part files into the artifact stage 3 reads.

Repo root: `D:\Python Projects\Manga Recap`
Chapter root: `data\chapters\<CHAPTER_ID>\`
Python: `.venv\Scripts\python.exe`, run from the repo root

## Pipeline

1. Read `02_panels\panel_index.json`. It is the source of truth for which panels
   exist, in what order, and where their bubble crops are. Never reorder it.
2. Split the ordered panels into consecutive batches of 15. Batch *k* covers
   reading orders `15k+1 .. 15k+15`, and writes `_describe_parts\part_<NN>.json`.
   A worker is given only the chapter id, its range, and its output path; it
   derives the rest from the index.
3. Merge: `python scripts\merge_descriptions.py <CHAPTER_ID>`
4. Repair any panel whose dialogue came back unreadable, one panel per worker,
   rewriting that panel's part file.
5. Check: `python scripts\check_chapter.py <CHAPTER_ID> --stage describe`

## Why the merge script exists

A vision worker has no way to know `page_number`, `reading_order`, `image_path`
or `has_detected_text`, and a mis-keyed value silently corrupts reading order
three stages later. `merge_descriptions.py` re-attaches all four from the index
and drops unknown fields, so a stray comment key in a part file cannot take the
chapter down. It exits non-zero and names the missing panels when a batch is
absent. Do not pass `--allow-missing`; a chapter with missing panels has holes
in the finished video.

## Series character roster

Reuse these labels exactly. Chapters 01 and 02 established them; a different
label for the same person makes the recap call one character two names.

| Label | Who |
|---|---|
| `shun` | Kyousuke Izumi, the protagonist — **a young man**, never a girl. **Dark hair**, short and spiky, with a fringe that often falls across his eyes. In greyscale art his hair reads mid-grey, not black. Dark green vest/capelet over a black top, high-collared light jacket in some scenes, often drawn simplified/chibi. **Both the real-world Kyousuke (short dark hair) and his in-game avatar (the long fringe over the eyes) are `shun`.** Never give them two labels. |
| `miu` | Myu, his younger sister, **female**. **Light** hair, drawn variously as a high ponytail, a short violet bob, or a light bob with a small top tuft. Cheerful. Confirm her by dialogue — she calls him `onii-chan` — not by hairstyle. |
| `magi` | A cheerful **girl**, light-brown bob with a small top tuft, frequently drawn with floating hearts. She calls Shun `Yuno-kun`. |
| `onee_chan` | Sei, his elder sister, **female**. Long silver-lavender hair, magic user, carries a wooden wand. She may be drawn with shorter dark hair; address, not hair colour, settles it. |
| `takumi` | A cheerful young **man**, light hair, light jacket. |
| `shop_clerk` | A weapon-shop attendant. |
| `stall_merchant` | A market vendor. |

### "Yuno" is the game, not a person

The game this story takes place in is called **Yuno**. When a character says
`YUN.`, `YUN,` or `YUNO-KUN`, they are addressing **the player** — Kyousuke's
in-game avatar, who registered under the name "Yun". It is an in-joke about his
name typo, not the name of somebody standing in the scene.

`YUNO-KUN` therefore identifies whoever is being talked to as Shun. So does
`add to my party` when Shun is the one recruiting.

### The two rules that matter most

**Shun's hair is dark.** If a figure is described as light-haired, blond or
fair-haired, that figure is not Shun. Several workers have taken a *light*
spiky-haired boy for him because the fringe is the memorable feature; the fringe
is not the discriminator, the colour is. Short spiky hair with the fringe
falling over the eyes is normal for him, and so is short spiky hair with the
eyes visible.

**When two people are in a panel and only one is being addressed, the address
decides which is which.** Long dark hair belongs to Shun; light hair with a top
tuft belongs to Miu. `-san` and `-kun` say nothing about gender — one worker read
`Magi-san` as a boy, and `Magi` is a girl.

New characters get new stable descriptive labels (`blond_merchant`,
`hooded_stranger`, `armored_guard`). Whatever is invented is recorded in the
`new_labels` array of the part file that uses it and reused in every later part.
Two labels for one person is the failure this roster exists to stop.

## Series settings vocabulary

Reuse these ids where they apply, and add new ones freely:

`real_world_bedroom`, `real_world_dining_room`, `real_world_home`,
`real_world_street`, `real_world_stairwell`, `game_start_town`, `game_forest`,
`forest_safe_area`, `forest_entrance`, `deep_forest`, `game_field`,
`game_ui_screen`, `game_infographic`, `town_market`, `game_weapon_shop`,
`abstract_reaction`, `page_margin`

## Prune non-story chrome

Stage 1 produces crops that are not story. Flag them so the script stage skips
them instead of flashing them on screen for a second:

- gutter margin slivers, grey screentone bars, black border wedges →
  `is_credits_or_ad: true` and `setting: "page_margin"`
- partial duplicate crops of a larger adjacent panel → `is_credits_or_ad: true`
- standalone abstract impact metaphors with no character (cracked boulders, black
  backgrounds) → `is_credits_or_ad: true`

Never flag a real story panel for being quiet, wordless, or a close-up.

## The unreadable-dialogue gate

`describe.max_untranscribed_ratio` is **0.1**. A panel with detected text and no
readable words is a panel whose dialogue was lost, and past 10% of them stage 3
refuses to run at all. That gate is the reason the bubble crops exist: a panel
image is downscaled, so its text is 8-12 pixels tall and reads as noise.

A panel alone in a worker reads far better than one of fifteen. Give the
leftovers their own single-panel run, twice, then accept `[illegible]`. An honest
gap is visible and fixable; an invented line is not.