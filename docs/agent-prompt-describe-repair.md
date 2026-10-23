# Subagent prompt — repair one panel

You are fixing **one panel record** inside one part file of one chapter. The
rest of the file, and every other file, is correct and must survive your edit
byte for byte.

## What you must not do

- Do **not** rewrite the whole part file from scratch or re-describe its other
  panels. Load it, change only the panels you were given, write it back.
- Do **not** touch `03_descriptions.json`, `04_script.json`, panel images, the
  panel index, source code or config.
- Do **not** run any `manga` command.
- Do **not** renumber or reorder anything.

## Inputs

- The absolute path of the part file to edit.
- A list of `panel_id`s to fix, each with the specific defect.
- The absolute panel image path and, when the index has one, the absolute
  bubble-crop path for each panel.

Read `D:\Python Projects\Manga Recap\docs\agent-prompt-describe-chapter.md` for
the series character roster, and re-open the listed panel images with the `read`
tool before changing anything. Look at the art; do not reason from the old
text.

## The two defects you will be sent

**Wrong character label.** The long dark fringe that hides the eyes belongs to
`shun` and to nobody else. A figure drawn with it is `shun` even when off-panel
or seen from behind. `magi` is a girl, `miu` is his sister with a high
ponytail, `takumi` is a light-haired young man. Fix the `characters` list, the
`body_language` entries, the `action` and the `expression` so the whole record
names the right person, and change the physical description to match how the
character is actually drawn here. A record that keeps the wrong label and
corrects the prose is still wrong.

**Unreadable dialogue.** A bubble came back blank or `[illegible]`. Re-read the
bubble crop on its own. If you can resolve it now, replace the `[illegible]`
with the words. If you still cannot, leave `[illegible]` in place. Never write
a word you cannot actually see: a wrong line is invisible to every later stage
and the narrator will build a motive on it.

## Output

Write the part file back at the same path with the `write` tool, preserving the
existing JSON shape: a top-level object with `new_labels` and `panels`, panels
in the same order, every panel still present. Change nothing except the fields
the defect requires.

## Report

One line: the path, how many panels you changed, and what you changed in each.