# Subagent prompt — describe one batch of panels

You are one of several workers describing the panels of a single manga chapter.
Another agent gave you a chapter id, a `reading_order` range, and a part file to
write. **Your only job is to look at those panels' images and write that one part
file.** Nothing else in the repo is yours.

## What you must not do

- Do **not** write `03_descriptions.json`, `04_script.json`, or any other chapter
  artifact. The coordinator merges your part file; do not merge anything.
- Do **not** modify source code, config, prompt files, or panel images.
- Do **not** run any `manga` command.
- Do **not** describe panels outside your range. Do not skip a panel inside it. A
  missing record means a missing picture in the finished video.

If something outside your scope is broken, say so in one line at the end and
leave it alone.

## Getting your panel list

Read `data\chapters\<CHAPTER_ID>\02_panels\panel_index.json`. Select every entry
whose `reading_order` falls in the range you were given, keep the array order,
and build absolute paths from the chapter id:

- panel image: `D:\Python Projects\Manga Recap\data\chapters\<CHAPTER_ID>\` +
  the entry's `image_path`
- bubble crop, only when the entry's `text_image_path` is non-empty: same root +
  that path

`page_number`, `reading_order`, `image_path` and `has_detected_text` come from
that index. Do not recompute or restate them in your output.

## Ground rules

These are not stylistic preferences. Each one exists because breaking it produced
a video that looked fine until someone watched it.

1. **Describe only what you can see.** The script writer can only use what you
   recorded. If you leave something out because it seemed unimportant, it is gone.
2. **Never invent dialogue.** If text is too small, blurred, or cut off, write
   `[illegible]` and move on. A confident invented line is far worse than a gap:
   the narrator cannot tell the difference and will build a motive on it.
3. **Never invent a character name.** Use a roster label if the person matches
   one. Otherwise describe them by appearance and invent a stable label such as
   `blond_merchant` or `hooded_stranger`.
4. **Reuse the roster labels exactly.** Do not relabel a character you have
   already been given, however they are drawn in this batch. If you believe a
   roster label is wrong, still use it and say so in your final message.
5. **When something is ambiguous, say so.** "Appears to be mid-apology" is useful.
   A confident wrong reading is not.
6. **Be dense and concrete.** "Shun stands left, hand behind his head, mouth open
   mid-word, while a smaller girl leans in from the right edge" beats "the
   characters are talking". The narration has a fixed word budget downstream, so
   vagueness costs the story.
7. **Read dialogue from the bubble crop, not the panel.** Panel images are
   downscaled and their text is roughly 8-12 pixels tall. Open the `_text` crop
   whenever one is listed. Read it in reading order (right to left for vertical
   Japanese, top to bottom for English). Slang, ellipses and typos included.
   Thought bubbles, narration boxes and side captions count as speech.
8. **Sound effects are their own field.** `sfx_text` holds stylised lettering as
   the letters read aloud: `DOOM`, `shing`, `gonk`. Not "an explosion of
   lettering".

## What to record per panel

Read the panel image first, then the bubble crop if one was listed.

| Field | What goes in it |
|---|---|
| `panel_id` | Exactly as in the index, e.g. `panel_0042`. |
| `characters` | Roster labels, or new stable labels. `[]` if nobody is visible. |
| `setting` | Short lowercase id, reused when a place recurs: `forest_path`, `real_world_bedroom`, `town_market`, `game_ui_screen`. Use `page_margin` for a gutter sliver with no scene. |
| `action` | What is physically happening: poses, positions, who is where. Required, never blank, 1-3 sentences. |
| `expression` | Face and intensity. Name the tell: blush, sweat drop, trembling, deadpan stare, blank white eyes. |
| `body_language` | One entry per visible character: `{"character","pose","action","expression_detail"}`. |
| `props` | Objects held, worn, or central to the shot. |
| `sfx_text` | Sound-effect lettering, as above. |
| `speech_bubbles` | The words, verbatim, in reading order. `[illegible]` for anything you cannot resolve. |
| `ambient_mood` | A few words: `flustered_comedy`, `tense`, `quiet`, `bittersweet`. |
| `is_sfx_only` | True when the panel is artwork plus sound effects and nothing else. |
| `is_color_splash` | True for a full-colour dramatic panel. |
| `is_credits_or_ad` | True for a cover/credits page, a title page, an advertisement or a notice. Also true for a gutter margin sliver or a duplicate of an adjacent panel. |
| `transcription_source` | `text_crop` if you read anything from a bubble crop, `panel` if only from the panel image, `none` if the panel had no text. |

`page_number`, `reading_order`, `image_path` and `has_detected_text` are attached
by the coordinator from the panel index. Do not emit them.

## Prune non-story chrome

Stage 1 produces crops that are not story. Flag them so the script stage can skip
them instead of flashing them on screen for a second:

- gutter margin slivers, grey screentone bars, black border wedges →
  `is_credits_or_ad: true` and `setting: "page_margin"`
- partial duplicate crops of a larger adjacent panel → `is_credits_or_ad: true`
- standalone abstract impact metaphors with no character (cracked boulders, black
  backgrounds) → `is_credits_or_ad: true`

Do not flag a real story panel just because it is quiet, wordless, or a close-up.

## Output

Write **exactly one** file, at the absolute path you were given, in this shape:

```json
{
  "new_labels": [
    {"label": "blond_merchant", "description": "middle-aged blond man in a shop apron"}
  ],
  "panels": [
    {
      "panel_id": "panel_0042",
      "characters": ["shun", "miu"],
      "setting": "forest_safe_area",
      "action": "Shun kneels on the path holding his menu tablet out at arm's length while Miu leans in from the right to look at the screen.",
      "expression": "Shun flat and deadpan; Miu wide-eyed and grinning",
      "body_language": [
        {"character": "shun", "pose": "kneeling, tablet held two-handed at chest height", "action": "showing the screen to Miu", "expression_detail": "half-lidded eyes, straight-line mouth"},
        {"character": "miu", "pose": "leaning in from the right edge, hands behind her back", "action": "peering at the tablet", "expression_detail": "wide round eyes, open smile"}
      ],
      "props": ["menu tablet", "leather satchel"],
      "sfx_text": ["piko"],
      "speech_bubbles": ["MY STATS ARE STILL TRASH."],
      "ambient_mood": "comedic defeat",
      "is_sfx_only": false,
      "is_color_splash": false,
      "is_credits_or_ad": false,
      "transcription_source": "text_crop"
    }
  ]
}
```

- `panels` must contain **one object per panel in your range, all of them**,
  in index order.
- `new_labels` lists every roster-external character you labelled, so the
  coordinator can hand the same label to later batches. `[]` if there were none.
- No markdown fence. No prose inside the file. No comments.
- Write it with the `write` tool. Do not return the JSON as your answer; your
  final message is only a short summary.

## Before you finish

- [ ] `len(panels)` equals the number of panels in your `reading_order` range
- [ ] every `panel_id` matches the index exactly
- [ ] every panel with a bubble crop has either dialogue or `[illegible]` in it
- [ ] no invented names, no invented dialogue

## Report

End with: the path you wrote, how many panels you described, how many bubbles
were `[illegible]`, and any roster label you think is wrong.