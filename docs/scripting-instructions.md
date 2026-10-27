# Official Scripting Instructions & Golden Standards

> 📌 **Trigger:** When the user says **"look for scripting instruction"** or asks to write/improve a script, any AI agent or developer MUST strictly follow this document. The quality must never degrade.

---

## 1. The Core Philosophy: "A Human Telling an Exciting Story"

The script must **never** sound like a dry textbook summary, an audiobook reading, or a school report. It must sound like an enthusiastic, witty, charismatic YouTube recap creator (like *Mamoru* or top-tier manhwa recap channels) telling an awesome story to a friend.

### Key Rules of Tone:
* **Conversational & Charismatic:** Use natural spoken English (*"Deep inside an ancient cursed dungeon..."*, *"Staring death in the eyes..."*, *"Naturally, swarms of hopeful tomb raiders geared up to strike it rich overnight"*).
* **Situational Humor & Personality:** Add relatable humor, sarcasm towards greedy villains, and hyping up the main character (*"Fearing Joo-Heon's unmatched skills, the paranoid old chairman deliberately set him up to die"*, *"The officer groans in exhaustion, complaining about working overtime on a miserable New Year night"*).
* **Transformative Commentary:** Do **not** read speech bubbles verbatim. Rephrase character dialogue into energetic narration with insight into their true feelings and motivations.
* **Tight Pacing:** Keep total chapter length between **850 and 1,200 words** (~5 to 8 minutes of video). Never write bloated 3,000+ word essays.

---

## 2. Strict Vocabulary Bans (Zero Tolerance)

The script must **NEVER** mention the physical medium or break the fourth wall. Viewers are watching a story, not an art review.

| BANNED WORD | WHY IT IS BANNED | WHAT TO SAY INSTEAD |
| :--- | :--- | :--- |
| `panel` / `panels` | Breaks immersion | Describe the character, action, or environment directly. |
| `chapter` / `chapters` | Meta medium reference | Refer to the story beat, quest, battle, or moment. |
| `page` / `pages` | Meta medium reference | Refer to the scene, corridor, or location. |
| `manga` / `manhwa` / `comic` | Fourth-wall break | Refer to the world, the story, or the game. |
| `author` / `artist` / `creator`| Meta reference | Focus on the character's fate or choices. |
| `drawing` / `drawn` / `art` | Medium mechanics | Describe what the character is experiencing. |
| `illustration` / `frame` | Medium mechanics | Describe the event or visual reality. |
| `reader` / `viewers` / `audience` | Fourth-wall break | Speak directly to the listener as a friend. |
| `tapestry` / `delve` / `testament` | AI cliché filler | Use natural, modern storytelling words. |

---

## 3. Mandatory Step 1: Inception Labs Mercury-3 Summary

**NEVER skip this step.**
Before writing the storyboard script:
1. Run the Inception Labs Mercury-3 summary script (`scripts/generate_mercury_summary_tomb_ch01.py` or equivalent for the active chapter) using `model: mercury-3`.
2. Save the output to `03_summary_mercury.txt`.
3. Read the summary to internalize the emotional high points, character dynamics, betrayals, and plot twists.

---

## 4. Mandatory Step 2: Clean Panel Pruning (No Text-Only Cards)

**NEVER show text-only slides or speech bubbles on solid void backgrounds in the video.**
1. Inspect `03_descriptions.json`:
   * Real story art scenes: `is_credits_or_ad: false` (active visual panels).
   * Floating dialogue bubbles on black/white void backgrounds, margin slivers, and credit cards: `is_credits_or_ad: true` (pruned from video).
2. Attach all dialogue and text from floating speech bubbles into the `speech_bubbles` array of the adjacent scene panel so the narrator knows all the dialogue without displaying floating bubble cards on screen.
3. The video storyboard must reference **ONLY** the active story art scenes.

---

## 5. Mandatory Step 3: Exact Clause-to-Panel Synchronization

In this pipeline, the script (`04_script.json`) is the **Storyboard** controlling video cuts.

### Synchronization Rules:
1. **One Clause, One Panel:**
   * Each beat must be **8 to 14 words** long.
   * Lower than 6 words flashes past too fast; over 14 words causes viewer fatigue.
2. **Explicit `beats` Binding in Every Block:**
   * Always write explicit `beats` with `beat_id`, `text`, and `panel_id`.
   * Group 1 to 2 beats per block (`max_words_per_block: 45`, `max_panels_per_block: 4`).
3. **Sequential Monotonic Order:**
   * Panels in the script must advance in strictly ascending reading order (`panel_0001`, `panel_0002`, `panel_0004`, ...).
   * 100% of required story panels must be covered.

---

## 6. The Golden Standard Template (`04_script.json`)

Here is the exact schema and structure proven in Chapter 1:

```json
{
  "chapter_id": "ch01",
  "title": "Tomb Raider King Chapter 1 - The Betrayal and the Regression",
  "series": "tomb-raider-king",
  "created_at": "2026-10-27T13:15:00",
  "model": "human_director",
  "total_words": 884,
  "blocks": [
    {
      "block_id": "b001",
      "panel_ids": ["panel_0001", "panel_0002"],
      "narration": "Deep inside an ancient cursed dungeon, shadows stretch across freezing stone corridors. Monstrous horned beasts roar in the gloom, hunting whatever unfortunate soul wandered in.",
      "beats": [
        {
          "beat_id": "b001_b00",
          "text": "Deep inside an ancient cursed dungeon, shadows stretch across freezing stone corridors.",
          "panel_id": "panel_0001"
        },
        {
          "beat_id": "b001_b01",
          "text": "Monstrous horned beasts roar in the gloom, hunting whatever unfortunate soul wandered in.",
          "panel_id": "panel_0002"
        }
      ]
    },
    {
      "block_id": "b002",
      "panel_ids": ["panel_0003", "panel_0004"],
      "narration": "Fresh crimson blood stains the cracked cobblestones, telling a grim story of survival. Seo Joo-Heon slams his bloody fist down, cursing the bastard who sent him here.",
      "beats": [
        {
          "beat_id": "b002_b00",
          "text": "Fresh crimson blood stains the cracked cobblestones, telling a grim story of survival.",
          "panel_id": "panel_0003"
        },
        {
          "beat_id": "b002_b01",
          "text": "Seo Joo-Heon slams his bloody fist down, cursing the bastard who sent him here.",
          "panel_id": "panel_0004"
        }
      ]
    }
  ]
}
```

---

## 7. Pre-Flight Verification Checklist Before Audio or Render

Before moving to `manga speak` or `manga render`, run this validation:

```python
from pathlib import Path
from manga_recap.core.config import load_config
from manga_recap.core.schema import DescriptionFile, ScriptFile, load_model
from manga_recap.stages.s3_script.validate import validate

config = load_config()
desc = load_model(Path("data/chapters/<ch>/03_descriptions.json"), DescriptionFile)
script = load_model(Path("data/chapters/<ch>/04_script.json"), ScriptFile)

report = validate(script, desc, config)
assert report.ok, f"Script validation failed: {report.problems}"
print("Script is 100% compliant and ready for audio & render!")
```
