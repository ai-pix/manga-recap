"""Generate structured storyboards and scripts for the 4 video hooks."""

import json

from manga_recap.core.paths import repo_path

HOOKS_DIR = repo_path("data/hooks")
HOOKS_DIR.mkdir(parents=True, exist_ok=True)

HOOKS = {
    "hook_part1": {
        "part": 1,
        "title": "The Trash Skill God (Part 1 Hook)",
        "target_duration_sec": 36,
        "blocks": [
            {
                "block_id": "h1_b01",
                "panel_ids": ["data/chapters/ch01/02_panels/panel_0001.png"],
                "narration": "While everyone chose flashy swords and overpowered magic, one boy made the biggest mistake in gaming history.",
                "beats": [
                    {"beat_id": "h1_b01_b00", "text": "While everyone chose flashy swords and overpowered magic,", "panel_id": "data/chapters/ch01/02_panels/panel_0001.png"},
                    {"beat_id": "h1_b01_b01", "text": "one boy made the biggest mistake in gaming history.", "panel_id": "data/chapters/ch01/02_panels/panel_0001.png"},
                ],
            },
            {
                "block_id": "h1_b02",
                "panel_ids": ["data/chapters/ch01/02_panels/panel_0085.png", "data/chapters/ch01/02_panels/panel_0097.png"],
                "narration": "He accidentally registered with a typo and picked the worst garbage skills on the server.",
                "beats": [
                    {"beat_id": "h1_b02_b00", "text": "He accidentally registered with a typo", "panel_id": "data/chapters/ch01/02_panels/panel_0085.png"},
                    {"beat_id": "h1_b02_b01", "text": "and picked the worst garbage skills on the server.", "panel_id": "data/chapters/ch01/02_panels/panel_0097.png"},
                ],
            },
            {
                "block_id": "h1_b03",
                "panel_ids": ["data/chapters/ch02/02_panels/panel_0008.png", "data/chapters/ch02/02_panels/panel_0045.png"],
                "narration": "They laughed at his wooden bow, but those trash senses held game-breaking hidden synergies.",
                "beats": [
                    {"beat_id": "h1_b03_b00", "text": "They laughed at his wooden bow,", "panel_id": "data/chapters/ch02/02_panels/panel_0008.png"},
                    {"beat_id": "h1_b03_b01", "text": "but those trash senses held game-breaking hidden synergies.", "panel_id": "data/chapters/ch02/02_panels/panel_0045.png"},
                ],
            },
            {
                "block_id": "h1_b04",
                "panel_ids": ["data/chapters/ch027/02_panels/panel_0008.png"],
                "narration": "Grab your snacks. You are about to witness the ultimate rise of an untouchable crafting god.",
                "beats": [
                    {"beat_id": "h1_b04_b00", "text": "Grab your snacks.", "panel_id": "data/chapters/ch027/02_panels/panel_0008.png"},
                    {"beat_id": "h1_b04_b01", "text": "You are about to witness the ultimate rise of an untouchable crafting god.", "panel_id": "data/chapters/ch027/02_panels/panel_0008.png"},
                ],
            },
        ],
    },
    "hook_part2": {
        "part": 2,
        "title": "The Atelier & The Server War (Part 2 Hook)",
        "target_duration_sec": 35,
        "blocks": [
            {
                "block_id": "h2_b01",
                "panel_ids": ["data/chapters/ch028/02_panels/panel_0024.png", "data/chapters/ch028/02_panels/panel_0027.png"],
                "narration": "Yun only wanted a quiet shop, but his potions are now causing bidding wars across the server.",
                "beats": [
                    {"beat_id": "h2_b01_b00", "text": "Yun only wanted a quiet shop,", "panel_id": "data/chapters/ch028/02_panels/panel_0024.png"},
                    {"beat_id": "h2_b01_b01", "text": "but his potions are now causing bidding wars across the server.", "panel_id": "data/chapters/ch028/02_panels/panel_0027.png"},
                ],
            },
            {
                "block_id": "h2_b02",
                "panel_ids": ["data/chapters/ch035/02_panels/panel_0005.png", "data/chapters/ch045/02_panels/panel_0010.png"],
                "narration": "Now top guilds and dangerous player killers are circling his atelier to seize his custom enchantments.",
                "beats": [
                    {"beat_id": "h2_b02_b00", "text": "Now top guilds and dangerous player killers", "panel_id": "data/chapters/ch035/02_panels/panel_0005.png"},
                    {"beat_id": "h2_b02_b01", "text": "are circling his atelier to seize his custom enchantments.", "panel_id": "data/chapters/ch045/02_panels/panel_0010.png"},
                ],
            },
            {
                "block_id": "h2_b03",
                "panel_ids": ["data/chapters/ch052/02_panels/panel_0005.png", "data/chapters/ch055/02_panels/panel_0008.png"],
                "narration": "When the raid catastrophe hits, the crafter they once dismissed becomes the kingmaker of the entire world.",
                "beats": [
                    {"beat_id": "h2_b03_b00", "text": "When the raid catastrophe hits,", "panel_id": "data/chapters/ch052/02_panels/panel_0005.png"},
                    {"beat_id": "h2_b03_b01", "text": "the crafter they once dismissed becomes the kingmaker of the entire world.", "panel_id": "data/chapters/ch055/02_panels/panel_0008.png"},
                ],
            },
        ],
    },
    "hook_part3": {
        "part": 3,
        "title": "Forbidden Alchemy & Uncharted Realm (Part 3 Hook)",
        "target_duration_sec": 34,
        "blocks": [
            {
                "block_id": "h3_b01",
                "panel_ids": ["data/chapters/ch056/02_panels/panel_0002.png", "data/chapters/ch070/02_panels/panel_0001.png"],
                "narration": "What happens when a crafter pushes game mechanics past what the developers ever programmed?",
                "beats": [
                    {"beat_id": "h3_b01_b00", "text": "What happens when a crafter pushes game mechanics", "panel_id": "data/chapters/ch056/02_panels/panel_0002.png"},
                    {"beat_id": "h3_b01_b01", "text": "past what the developers ever programmed?", "panel_id": "data/chapters/ch070/02_panels/panel_0001.png"},
                ],
            },
            {
                "block_id": "h3_b02",
                "panel_ids": ["data/chapters/ch070/02_panels/panel_0004.png", "data/chapters/ch075/02_panels/panel_0005.png"],
                "narration": "Entering the uncharted frontier, Yun unlocks taboo companion evolutions and illegal item combinations.",
                "beats": [
                    {"beat_id": "h3_b02_b00", "text": "Entering the uncharted frontier,", "panel_id": "data/chapters/ch070/02_panels/panel_0004.png"},
                    {"beat_id": "h3_b02_b01", "text": "Yun unlocks taboo companion evolutions and illegal item combinations.", "panel_id": "data/chapters/ch075/02_panels/panel_0005.png"},
                ],
            },
            {
                "block_id": "h3_b03",
                "panel_ids": ["data/chapters/ch080/02_panels/panel_0005.png", "data/chapters/ch084/02_panels/panel_0008.png"],
                "narration": "Get ready for Part 3, where the stakes get deadlier and the game balance shatters completely.",
                "beats": [
                    {"beat_id": "h3_b03_b00", "text": "Get ready for Part 3,", "panel_id": "data/chapters/ch080/02_panels/panel_0005.png"},
                    {"beat_id": "h3_b03_b01", "text": "where the stakes get deadlier and the game balance shatters completely.", "panel_id": "data/chapters/ch084/02_panels/panel_0008.png"},
                ],
            },
        ],
    },
    "hook_part4": {
        "part": 4,
        "title": "The Pinnacle & Grand Finale (Part 4 Hook)",
        "target_duration_sec": 40,
        "blocks": [
            {
                "block_id": "h4_b01",
                "panel_ids": ["data/chapters/ch01/02_panels/panel_0084.png", "data/chapters/ch02/02_panels/panel_0005.png"],
                "narration": "One hundred and twelve chapters and seventeen hours of story come down to this final battlefield.",
                "beats": [
                    {"beat_id": "h4_b01_b00", "text": "One hundred and twelve chapters and seventeen hours of story", "panel_id": "data/chapters/ch01/02_panels/panel_0084.png"},
                    {"beat_id": "h4_b01_b01", "text": "come down to this final battlefield.", "panel_id": "data/chapters/ch02/02_panels/panel_0005.png"},
                ],
            },
            {
                "block_id": "h4_b02",
                "panel_ids": ["data/chapters/ch095/02_panels/panel_0005.png", "data/chapters/ch105/02_panels/panel_0005.png"],
                "narration": "Ancient titan raid bosses descend as entire server alliances fall into chaos.",
                "beats": [
                    {"beat_id": "h4_b02_b00", "text": "Ancient titan raid bosses descend", "panel_id": "data/chapters/ch095/02_panels/panel_0005.png"},
                    {"beat_id": "h4_b02_b01", "text": "as entire server alliances fall into chaos.", "panel_id": "data/chapters/ch105/02_panels/panel_0005.png"},
                ],
            },
            {
                "block_id": "h4_b03",
                "panel_ids": ["data/chapters/ch110/02_panels/panel_0005.png", "data/chapters/ch112/02_panels/panel_0001.png"],
                "narration": "Only the boy who started with a wooden bow can stand between total wipeout and legendary victory.",
                "beats": [
                    {"beat_id": "h4_b03_b00", "text": "Only the boy who started with a wooden bow", "panel_id": "data/chapters/ch110/02_panels/panel_0005.png"},
                    {"beat_id": "h4_b03_b01", "text": "can stand between total wipeout and legendary victory.", "panel_id": "data/chapters/ch112/02_panels/panel_0001.png"},
                ],
            },
            {
                "block_id": "h4_b04",
                "panel_ids": ["data/chapters/ch112/02_panels/panel_0002.png", "data/chapters/ch112/02_panels/panel_0004.png"],
                "narration": "This is the definitive grand finale. Settle in for the last four and a half hours.",
                "beats": [
                    {"beat_id": "h4_b04_b00", "text": "This is the definitive grand finale.", "panel_id": "data/chapters/ch112/02_panels/panel_0002.png"},
                    {"beat_id": "h4_b04_b01", "text": "Settle in for the last four and a half hours.", "panel_id": "data/chapters/ch112/02_panels/panel_0004.png"},
                ],
            },
        ],
    },
}


def main():
    for name, data in HOOKS.items():
        out_path = HOOKS_DIR / f"{name}.json"
        out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        words = sum(len(b["narration"].split()) for b in data["blocks"])
        print(f"Generated {out_path.name}: {len(data['blocks'])} blocks, {words} words (~{data['target_duration_sec']}s)")


if __name__ == "__main__":
    main()
