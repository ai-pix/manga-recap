"""Generate 10 Viral YouTube Shorts (9:16 Vertical, 1080x1920) for SSS-Class Revival Hunter.

Features:
- 10 distinct, condensed, high-stakes story segments across Chapters 01-40.
- Fast-paced editing with visual cuts every 2-3 seconds (20-28 panels per short).
- Fish Audio studio narration with Whisper word-level alignment.
- Pure GPU NVENC 9:16 vertical rendering (1080x1920) on Kaggle.
"""

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import sys
import time
from pathlib import Path

# Add project root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from manga_recap.core.config import load_config
from manga_recap.core.paths import ChapterPaths, repo_path
from manga_recap.core.schema import (
    ScriptBlock,
    ScriptFile,
    save_model,
)
from manga_recap.stages.s4_speech import run as run_speech
from manga_recap.stages.s5_render import KaggleClient, payload

# -----------------------------------------------------------------------------
# SHORTS DEFINITIONS (10 CONDENSED STORIES ACROSS CHAPTERS 01 TO 40)
# -----------------------------------------------------------------------------

SHORTS_DATA = [
    # -------------------------------------------------------------------------
    # Short 01: The 4,090 Suicides to Slay a Hero (Ch 01-04)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short01",
        "title": "He Committed Suicide 4,090 Times To Steal A Skill #Shorts",
        "desc": "How far would you go for revenge? Confucius Kim died 4,090 times to steal the Flame Emperor's regression skill and travel back 11 years into the past! #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (3, "panel_0100"), "text": "How insane do you have to be..."},
            {"src": (3, "panel_0084"), "text": "to stab a dagger into your chest..."},
            {"src": (3, "panel_0085"), "text": "four thousand and ninety times?!"},
            {"src": (3, "panel_0095"), "text": "Waking up every morning coughing blood,"},
            {"src": (3, "panel_0090"), "text": "plunging cold steel into your heart,"},
            {"src": (3, "panel_0099"), "text": "and repeating death in pure agony!"},
            {"src": (1, "panel_0043"), "text": "Confucius Kim was a pathetic F-rank trash,"},
            {"src": (2, "panel_0057"), "text": "until the world's rank one hero cornered him."},
            {"src": (2, "panel_0061"), "text": "Choked like a dog in a dark alleyway,"},
            {"src": (2, "panel_0078"), "text": "his skull incinerated by raging flames,"},
            {"src": (2, "panel_0055"), "text": "he bled out and died on the concrete."},
            {"src": (1, "panel_0050"), "text": "But the hero made one fatal mistake."},
            {"src": (2, "panel_0084"), "text": "Upon death, Confucius steals his killer's skill!"},
            {"src": (3, "panel_0014"), "text": "An EX-Rank clock rewinding time twenty-four hours!"},
            {"src": (3, "panel_0080"), "text": "To kill that monster before he ever awakens,"},
            {"src": (3, "panel_0083"), "text": "Confucius had to travel eleven years into the past."},
            {"src": (3, "panel_0088"), "text": "One death only rewinds one day."},
            {"src": (3, "panel_0091"), "text": "So he made a terrifying choice:"},
            {"src": (3, "panel_0094"), "text": "Four thousand and ninety suicides in a row!"},
            {"src": (3, "panel_0097"), "text": "Die. Rewind. Stab. Die again!"},
            {"src": (4, "panel_0055"), "text": "Eleven years of torment conquered by spite!"},
            {"src": (4, "panel_0070"), "text": "Slashing through the arrogant hero before his prime!"},
            {"src": (4, "panel_0078"), "text": "Standing over his corpse with a blood-soaked blade!"},
            {"src": (4, "panel_0081"), "text": "Subscribe for the full four-hour manhwa recap!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 02: Assassinating the Rank 1 Hero in an Alley (Ch 04-05)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short02",
        "title": "He Slew The World's Strongest Hero In An Alleyway #Shorts",
        "desc": "Before the Flame Emperor became an untouchable god, he was just a cocky punk in an alleyway. Confucius traveled back 11 years to finish him! #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (4, "panel_0010"), "text": "Imagine meeting the world's strongest hero,"},
            {"src": (4, "panel_0015"), "text": "eleven years before anyone knows his name!"},
            {"src": (4, "panel_0025"), "text": "Yoo Soo-ha was just a cocky delinquent,"},
            {"src": (4, "panel_0032"), "text": "bragging about fire skills in a cheap tavern."},
            {"src": (4, "panel_0040"), "text": "He thought he was the chosen one,"},
            {"src": (4, "panel_0045"), "text": "destined to rule the Babel Tower."},
            {"src": (4, "panel_0050"), "text": "Until Confucius stepped out from the shadows!"},
            {"src": (4, "panel_0058"), "text": "No grand speeches. No epic duel."},
            {"src": (4, "panel_0062"), "text": "Just pure, premeditated assassination!"},
            {"src": (4, "panel_0066"), "text": "A surprise slash straight across his throat!"},
            {"src": (4, "panel_0072"), "text": "The future Flame Emperor collapsed gasping,"},
            {"src": (4, "panel_0075"), "text": "clutching his neck as his blood poured out!"},
            {"src": (4, "panel_0080"), "text": "He screamed in terror: Who the hell are you?!"},
            {"src": (4, "panel_0085"), "text": "Confucius whispered cold as ice:"},
            {"src": (4, "panel_0090"), "text": "I'm the guy you killed four thousand times!"},
            {"src": (4, "panel_0095"), "text": "One final plunge through his blackened heart,"},
            {"src": (4, "panel_0102"), "text": "and the world's greatest tyrant was erased forever!"},
            {"src": (5, "panel_0012"), "text": "The tower announced the impossible victory,"},
            {"src": (5, "panel_0020"), "text": "awarding Confucius his legendary fire sword!"},
            {"src": (5, "panel_0035"), "text": "The weakest F-rank just stole destiny itself!"},
            {"src": (5, "panel_0045"), "text": "Check the full recap on my channel!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 03: The Tragic Secret Behind The Goblin King (Ch 06-08)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short03",
        "title": "The Tragic Truth Behind The 10th Floor Boss #Shorts",
        "desc": "Every hunter treated the 10th floor Goblin King as mindless EXP. But when Confucius heard his dying thoughts, everything changed. #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (6, "panel_0020"), "text": "Hunters think tower monsters are just mindless EXP,"},
            {"src": (6, "panel_0035"), "text": "until you hear what they scream when they die!"},
            {"src": (7, "panel_0015"), "text": "The 10th Floor Boss was the mighty Goblin King,"},
            {"src": (7, "panel_0028"), "text": "commanding an army of desperate, starving monsters."},
            {"src": (7, "panel_0042"), "text": "The elite guilds slaughtered them with laughs,"},
            {"src": (7, "panel_0055"), "text": "burning their homes and butchering their young!"},
            {"src": (7, "panel_0068"), "text": "When Confucius faced the King in single combat,"},
            {"src": (7, "panel_0075"), "text": "his passive skill activated inside his soul!"},
            {"src": (7, "panel_0082"), "text": "He heard the Goblin King's final telepathic prayer:"},
            {"src": (7, "panel_0090"), "text": "Please, protect my children from the invaders!"},
            {"src": (7, "panel_0098"), "text": "He wasn't a monster fighting for blood."},
            {"src": (7, "panel_0105"), "text": "He was a father standing as the final shield!"},
            {"src": (8, "panel_0015"), "text": "Confucius bowed his head in heavy tears,"},
            {"src": (8, "panel_0025"), "text": "delivering a clean, respectful strike to his chest."},
            {"src": (8, "panel_0038"), "text": "I will carry your people's memory forward!"},
            {"src": (8, "panel_0050"), "text": "In a world of selfish, arrogant hunters,"},
            {"src": (8, "panel_0065"), "text": "Confucius chose to become their salvation!"},
            {"src": (8, "panel_0080"), "text": "Watch the full story on the channel!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 04: A Legendary Ghost Emperor Trapped Inside His Mind (Ch 09-11)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short04",
        "title": "A 99th Floor Ghost Emperor Trapped In His Head #Shorts",
        "desc": "Confucius unlocked the phantom spirit of Bae Hu-ryeong, the 99th floor Sword Emperor! What followed was swordsmanship hell. #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (9, "panel_0012"), "text": "What happens when the greatest swordsman in history..."},
            {"src": (9, "panel_0024"), "text": "gets stuck as a ghost inside your brain?!"},
            {"src": (9, "panel_0038"), "text": "Meet Bae Hu-ryeong, the 99th Floor Sword Emperor!"},
            {"src": (9, "panel_0050"), "text": "Loud, obnoxious, and utterly terrifying!"},
            {"src": (10, "panel_0015"), "text": "He looked at Confucius's pathetic sword stance"},
            {"src": (10, "panel_0028"), "text": "and called him a crippled monkey with a stick!"},
            {"src": (10, "panel_0042"), "text": "Ten thousand sword swings before breakfast!"},
            {"src": (10, "panel_0055"), "text": "Ten thousand thrusts while balancing on rocks!"},
            {"src": (10, "panel_0068"), "text": "Confucius's muscles tore and his palms split,"},
            {"src": (10, "panel_0078"), "text": "blood dripping from his wooden training blade!"},
            {"src": (10, "panel_0085"), "text": "Most men would break and give up,"},
            {"src": (11, "panel_0018"), "text": "but Confucius just grinned like a lunatic!"},
            {"src": (11, "panel_0030"), "text": "I've died four thousand times, old man!"},
            {"src": (11, "panel_0045"), "text": "You think sore muscles can make me quit?!"},
            {"src": (11, "panel_0060"), "text": "The arrogant ghost emperor went dead silent,"},
            {"src": (11, "panel_0072"), "text": "realizing this crazy kid had the heart of a god!"},
            {"src": (11, "panel_0075"), "text": "Full marathon recap live on YouTube now!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 05: The 11th Floor Zombie Plague Apocalypse (Ch 12-15)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short05",
        "title": "The 11th Floor Plague That Wiped Out An Entire Kingdom #Shorts",
        "desc": "The 11th floor was an apocalyptic medieval kingdom consumed by a demonic black plague. Confucius died over and over to find a cure! #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (12, "panel_0020"), "text": "The 11th floor wasn't a dungeon,"},
            {"src": (12, "panel_0035"), "text": "it was a kingdom rotting alive in black rot!"},
            {"src": (13, "panel_0018"), "text": "The Aegis Empire fell to an incurable demonic plague,"},
            {"src": (13, "panel_0032"), "text": "turning millions of citizens into screaming zombies!"},
            {"src": (13, "panel_0048"), "text": "Top hunter guilds retreated in sheer panic,"},
            {"src": (14, "panel_0015"), "text": "as toxic black mist melted their armor to slag!"},
            {"src": (14, "panel_0028"), "text": "Confucius marched directly into the quarantine zone."},
            {"src": (14, "panel_0042"), "text": "Infected. Lungs collapsing. Coughing black bile."},
            {"src": (14, "panel_0055"), "text": "He died in agonizing fever!"},
            {"src": (14, "panel_0068"), "text": "Rewind twenty-four hours!"},
            {"src": (15, "panel_0012"), "text": "He mapped out the disease outbreak step by step,"},
            {"src": (15, "panel_0025"), "text": "tracking patient zero through the royal palace!"},
            {"src": (15, "panel_0038"), "text": "He found the infected princess chained in chains,"},
            {"src": (15, "panel_0050"), "text": "and absorbed the lethal demonic toxin into himself!"},
            {"src": (15, "panel_0062"), "text": "Sacrificing his own life to cleanse the realm!"},
            {"src": (15, "panel_0070"), "text": "Watch the full 4-hour epic recap now!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 06: Teaming Up With The Tower's Smiling Psychopath (Ch 16-19)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short06",
        "title": "Teaming Up With The Tower's Most Smiling Psychopath #Shorts",
        "desc": "Meet the Heretic Inquisitor: a cheerful, smiling fanatic who tortures villains with pure joy. Confucius had to survive beside him! #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (16, "panel_0015"), "text": "Beware the man who smiles while cutting off limbs!"},
            {"src": (16, "panel_0030"), "text": "Meet the Heretic Inquisitor of the Ten Thousand Temple!"},
            {"src": (17, "panel_0018"), "text": "He doesn't torture for money or power."},
            {"src": (17, "panel_0032"), "text": "He genuinely believes torture saves your soul!"},
            {"src": (17, "panel_0045"), "text": "To clear the tower's political corruption trial,"},
            {"src": (18, "panel_0015"), "text": "Confucius had to partner with this smiling demon!"},
            {"src": (18, "panel_0028"), "text": "One wrong sentence in their conversation,"},
            {"src": (18, "panel_0042"), "text": "and the Inquisitor's blade was pressed to his neck!"},
            {"src": (18, "panel_0055"), "text": "Are you a heretic, Confucius?"},
            {"src": (18, "panel_0065"), "text": "Should I purify your flesh with holy fire?!"},
            {"src": (19, "panel_0018"), "text": "Confucius didn't flinch. He looked him dead in the eye:"},
            {"src": (19, "panel_0032"), "text": "I've already died four thousand times in hell,"},
            {"src": (19, "panel_0045"), "text": "your little torture chamber is just recess to me!"},
            {"src": (19, "panel_0058"), "text": "For the first time ever, the psychopath blinked,"},
            {"src": (19, "panel_0062"), "text": "and found his first true equal!"},
            {"src": (19, "panel_0064"), "text": "Full series breakdown live on YouTube!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 07: The Demon King Who Wept Black Rain Over Murim (Ch 21-24)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short07",
        "title": "The Demon King Who Wept Black Rain Over Murim #Shorts",
        "desc": "The 20th floor transported hunters into a martial arts world drowning in cursed black rain. The Demon King wasn't a monster—he was pure sorrow. #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (21, "panel_0012"), "text": "The 20th floor wasn't a game,"},
            {"src": (21, "panel_0025"), "text": "it was the dying tomb of the martial arts world!"},
            {"src": (22, "panel_0015"), "text": "A world drowning under relentless, cursed black rain."},
            {"src": (22, "panel_0028"), "text": "Every drop turned honorable masters into hollow zombies,"},
            {"src": (22, "panel_0042"), "text": "forcing brothers to butcher brothers in the mud!"},
            {"src": (23, "panel_0015"), "text": "At the center of the storm stood the Demon King:"},
            {"src": (23, "panel_0028"), "text": "The Demon King of Autumn Rain!"},
            {"src": (23, "panel_0040"), "text": "He didn't laugh or boast of his dark power."},
            {"src": (23, "panel_0052"), "text": "He wept tears of blood as he slaughtered the righteous!"},
            {"src": (24, "panel_0015"), "text": "Confucius stepped into the freezing storm,"},
            {"src": (24, "panel_0028"), "text": "feeling the crushing weight of their centuries of grief."},
            {"src": (24, "panel_0040"), "text": "This wasn't a raid boss to be killed for loot."},
            {"src": (24, "panel_0052"), "text": "This was an entire civilization crying out for peace!"},
            {"src": (24, "panel_0060"), "text": "And Confucius swore to give it to them!"},
            {"src": (24, "panel_0065"), "text": "Check out the full four-hour marathon recap!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 08: Learning The Darkest Martial Art From A Dying Master (Ch 25-28)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short08",
        "title": "Inheriting The Ultimate Demonic Martial Art #Shorts",
        "desc": "In the ruins of the martial arts world, Confucius found the Heavenly Demon on her deathbed. To learn her art, he had to die again and again. #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (25, "panel_0015"), "text": "In the crumbling temple of the Demonic Cult,"},
            {"src": (25, "panel_0030"), "text": "sat the legendary Heavenly Demon!"},
            {"src": (26, "panel_0012"), "text": "Crippled, starving, and coughing blood,"},
            {"src": (26, "panel_0025"), "text": "yet her eyes burned with the fury of a dying sun!"},
            {"src": (26, "panel_0040"), "text": "You want to learn my martial arts, boy?"},
            {"src": (26, "panel_0050"), "text": "The Demonic Art is learned only through death!"},
            {"src": (27, "panel_0015"), "text": "With a flick of her hand, her qi shattered his chest!"},
            {"src": (27, "panel_0028"), "text": "Dead. Rewound. Back in front of her!"},
            {"src": (27, "panel_0038"), "text": "Again! Her sword sliced through his skull!"},
            {"src": (27, "panel_0048"), "text": "Dead. Rewound. Standing up again!"},
            {"src": (28, "panel_0015"), "text": "Dozens of deaths later, his body absorbed her rhythm!"},
            {"src": (28, "panel_0028"), "text": "The flame of the Demonic Cult ignited in his veins!"},
            {"src": (28, "panel_0042"), "text": "The dying master smiled for the first time in eighty years:"},
            {"src": (28, "panel_0055"), "text": "You are my true disciple. Now go slay the heavens!"},
            {"src": (28, "panel_0065"), "text": "Full four-hour story on the channel!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 09: Uniting Murim With Pure Spite (Ch 29-33)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short09",
        "title": "He Conquered The Martial Arts Apocalypse With One Strike #Shorts",
        "desc": "Armed with the Heavenly Demon's sacred art and the Sword Emperor's legacy, Confucius faced the Demon King of Autumn Rain! #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (29, "panel_0015"), "text": "The final battle for the 20th floor had arrived!"},
            {"src": (30, "panel_0018"), "text": "The Demon King unleashed a catastrophic wave of black rain,"},
            {"src": (30, "panel_0035"), "text": "drowning the entire martial arts world in dark miasma!"},
            {"src": (31, "panel_0015"), "text": "Every hunter panicked and prepared to retreat,"},
            {"src": (31, "panel_0030"), "text": "but Confucius unsheathed his blazing sword!"},
            {"src": (31, "panel_0045"), "text": "Channeling the grief of every slaughtered martial artist,"},
            {"src": (32, "panel_0018"), "text": "combining the Heavenly Demon's dark inferno"},
            {"src": (32, "panel_0032"), "text": "with the ghost emperor's supreme sword form!"},
            {"src": (32, "panel_0048"), "text": "He leapt into the storm and severed the heavens!"},
            {"src": (32, "panel_0060"), "text": "A blinding flash of scarlet and silver light!"},
            {"src": (33, "panel_0015"), "text": "The black rain stopped. The clouds parted."},
            {"src": (33, "panel_0028"), "text": "The souls of Murim thanked him as they dissolved into light!"},
            {"src": (33, "panel_0042"), "text": "He didn't just clear the stage; he saved their souls!"},
            {"src": (33, "panel_0055"), "text": "Watch the full marathon video on YouTube!"},
        ],
    },

    # -------------------------------------------------------------------------
    # Short 10: He Fell In Love With The Villainess Who Remembers Death (Ch 35-40)
    # -------------------------------------------------------------------------
    {
        "id": "revival_hunter_short10",
        "title": "He Fell In Love With The Villainess Who Remembers Death #Shorts",
        "desc": "On the 30th floor Otome Romance stage, Confucius met Lady Raviel Ivansia—the villainess who realized every time time rewound! #sssclassrevivalhunter #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (35, "panel_0015"), "text": "What happens when a hunter who can reset death..."},
            {"src": (35, "panel_0030"), "text": "falls in love with a villainess who remembers it all?!"},
            {"src": (37, "panel_0018"), "text": "The 30th floor trapped Confucius in an Otome romance game!"},
            {"src": (37, "panel_0032"), "text": "Enter Lady Raviel Ivansia: cold, brilliant, and untouchable!"},
            {"src": (38, "panel_0015"), "text": "Condemned by the foolish prince, she was marked for ruin."},
            {"src": (38, "panel_0030"), "text": "Confucius killed himself to rewind time and defend her."},
            {"src": (39, "panel_0018"), "text": "When he woke up in the past and stepped before her throne,"},
            {"src": (39, "panel_0032"), "text": "she looked straight into his eyes and whispered:"},
            {"src": (39, "panel_0045"), "text": "You rewound time just for me, didn't you?"},
            {"src": (39, "panel_0060"), "text": "For the first time in thousands of regressions,"},
            {"src": (40, "panel_0015"), "text": "Confucius was no longer alone in his curse!"},
            {"src": (40, "panel_0030"), "text": "They forged a pact written in blood and royalty,"},
            {"src": (40, "panel_0045"), "text": "to overturn the kingdom and conquer the tower together!"},
            {"src": (40, "panel_0060"), "text": "The greatest romance in manhwa history!"},
            {"src": (40, "panel_0070"), "text": "Experience the full 4-hour epic on my channel now!"},
        ],
    },
]


def resolve_panel_file(ch_num: int, pid: str) -> Path:
    """Find panel file across available folder layouts."""
    candidates = [
        repo_path(f"data/chapters/revival_hunter_ch{ch_num:02d}/02_panels/{pid}.jpg"),
        repo_path(f"data/chapters/revival_hunter_ch{ch_num:02d}/02_panels/{pid}.png"),
        repo_path(f"data/chapters/sss-class-revival-hunter/ch{ch_num:02d}/02_panels/{pid}.jpg"),
        repo_path(f"data/chapters/sss-class-revival-hunter/ch{ch_num:02d}/02_panels/{pid}.png"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"Cannot find {pid} for chapter {ch_num}")


def stage_all_shorts() -> list[str]:
    """Stage panel crops, build 04_script.json for all 10 shorts."""
    staged_ids = []
    print("=" * 70)
    print("STAGING 10 YOUTUBE SHORTS (FAST-PACED, NEW PANELS EVERY 2s)")
    print("=" * 70)

    for item in SHORTS_DATA:
        sid = item["id"]
        paths = ChapterPaths.create(sid)
        paths.root.mkdir(parents=True, exist_ok=True)
        paths.panels_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n[{sid}] Staging {len(item['blocks'])} panels for: {item['title']}...")
        script_blocks = []
        for idx, block in enumerate(item["blocks"], start=1):
            pid = f"panel_{idx:04d}"
            ch, src_pid = block["src"]
            src_file = resolve_panel_file(ch, src_pid)
            dest_file = paths.panels_dir / f"{pid}.jpg"
            shutil.copy2(src_file, dest_file)

            narration = block["text"]
            script_blocks.append(
                ScriptBlock(
                    block_id=f"b{idx:03d}",
                    panel_ids=[pid],
                    narration=narration,
                    word_count=len(narration.split()),
                    panel_indices=[idx],
                )
            )

        script_file = ScriptFile(
            chapter_id=sid,
            created_at=datetime.datetime.now().isoformat(),
            total_blocks=len(script_blocks),
            total_words=sum(b.word_count for b in script_blocks),
            blocks=script_blocks,
        )
        save_model(script_file, paths.script_file)
        print(f"[{sid}] Created script: {len(script_blocks)} blocks ({script_file.total_words} words)")
        staged_ids.append(sid)

    return staged_ids


def speak_all_shorts(short_ids: list[str]) -> None:
    """Generate Fish Audio narration and Whisper word alignment for all shorts."""
    cfg = load_config()
    print("\n" + "=" * 70)
    print("SYNTHESIZING STUDIO NARRATION VIA FISH AUDIO FOR 10 SHORTS")
    print("=" * 70)

    for sid in short_ids:
        paths = ChapterPaths.create(sid)
        if paths.narration_file.exists() and paths.timeline_file.exists():
            print(f"[{sid}] Audio and timeline already exist, skipping speech synthesis.")
            continue

        print(f"\n[{sid}] Generating Fish Audio speech and Whisper alignment...", flush=True)
        t0 = time.time()
        timeline = run_speech(paths, cfg, force=True)
        dur = timeline.duration
        print(f"[{sid}] [OK] Generated {dur:.1f}s studio audio in {time.time() - t0:.1f}s")


def build_batch_render_payload(short_ids: list[str]) -> Path:
    """Bundle all 10 shorts into a single Kaggle batch render archive (9:16 vertical)."""
    cfg = load_config()
    staging = repo_path("data/chapters/_kaggle_shorts_batch_input")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    chapters_dir = staging / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("PACKAGING 10 SHORTS INTO KAGGLE BATCH RENDER PAYLOAD (9:16 VERTICAL 1080x1920)")
    print("=" * 70)

    for sid in short_ids:
        paths = ChapterPaths.create(sid)
        ch_stage = chapters_dir / sid
        ch_stage.mkdir(parents=True, exist_ok=True)
        (ch_stage / "panels").mkdir(parents=True, exist_ok=True)

        for p in paths.panel_images():
            shutil.copy2(p, ch_stage / "panels" / p.name)
        shutil.copy2(paths.script_file, ch_stage / "script.json")
        shutil.copy2(paths.narration_file, ch_stage / "narration.wav")
        shutil.copy2(paths.timeline_file, ch_stage / "timeline.json")

    # Build 9:16 vertical batch job.json
    job_spec = {
        "mode": "batch",
        "chapters": short_ids,
        "render": {
            "width": 1080,
            "height": 1920,
            "fps": 30,
            "crf": 20,
            "preset": "p4",
            "encoder": "h264_nvenc",
            "engine": "pynv",
            "audio_bitrate": "192k",
            "video_bitrate": 4500000,
            "background_mode": "blurred",
            "blur_width": 512,
            "blur_radius": 16,
            "blur_darken": 0.12,
            "pan_tall": False,
            "subtle_motion": True,
            "min_shot_seconds": 0.7,
            "max_clip_seconds": 60.0,
            "max_words_per_beat": 14,
            "kenburns": {"enabled": False},
        },
        "bgm": {"enabled": False},
    }
    (staging / "job.json").write_text(json.dumps(job_spec, indent=2), encoding="utf-8")

    # Bundle src
    src_dir = repo_path("src")
    if src_dir.is_dir():
        shutil.copytree(
            src_dir,
            staging / "src",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            dirs_exist_ok=True,
        )

    # Bundle kernel helper modules
    kernel_dir = repo_path("kaggle/kernel_render")
    lib_dir = staging / "lib"
    lib_dir.mkdir(exist_ok=True)
    for module in sorted(kernel_dir.glob("*.py")):
        if module.name != "main.py":
            shutil.copy2(module, lib_dir / module.name)

    zip_path = repo_path("data/chapters/shorts_batch_payload.zip")
    archive = payload.build_archive(staging, zip_path)
    shutil.rmtree(staging, ignore_errors=True)
    size_mb = archive.stat().st_size / 1e6
    print(f"Archive built successfully: {archive} ({size_mb:.1f} MB)")
    return archive


def render_all_shorts_kaggle(archive_path: Path, short_ids: list[str]) -> None:
    """Submit batch job to Kaggle GPU kernel and download all 10 rendered vertical shorts."""
    cfg = load_config()
    kernel_slug = "manga-recap-render"
    client = KaggleClient()

    print("\n" + "=" * 70)
    print(f"UPLOADING PAYLOAD AND LAUNCHING KAGGLE GPU RENDER ({kernel_slug})")
    print("=" * 70)

    payload_url = payload.upload(
        archive_path,
        host=str(cfg.get("render.payload_host", payload.DEFAULT_HOST)),
        filename="shorts-batch-render.zip",
    )
    print(f"Uploaded batch archive -> {payload_url}")

    kernel_dir = repo_path("kaggle/kernel_render")
    work_dir = repo_path("data/chapters/_kaggle_kernel_shorts")
    payload.stage_from_url(
        kernel_dir=kernel_dir,
        url=payload_url,
        work_dir=work_dir,
        metadata={
            "id": f"{client.username}/{kernel_slug}",
            "title": kernel_slug,
            "enable_gpu": True,
            "dataset_sources": ["wampireai/manga-recap-render-bin"],
        },
    )
    client.push_kernel(work_dir)
    kernel_id = f"{client.username}/{kernel_slug}"
    print(f"Kernel pushed: {kernel_id}. Waiting for completion on Tesla T4 pure GPU...")

    run_info = client.wait_for_kernel(
        kernel_id,
        poll_interval=15,
        max_wait=7200,
    )
    print(f"Kernel completed in {run_info.total_seconds:.1f}s! Downloading outputs...")

    download_dir = client.download_kernel_output(kernel_id, repo_path("data/chapters/_kaggle_shorts_output"))

    # Move outputs to respective short directories and data/export/shorts/
    export_dir = repo_path("data/export/shorts")
    export_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("RETRIEVING RENDERED 9:16 VERTICAL SHORTS")
    print("=" * 70)

    for item in SHORTS_DATA:
        sid = item["id"]
        paths = ChapterPaths.create(sid)
        rendered_vid = download_dir / f"{sid}_final.mp4"
        if not rendered_vid.exists():
            # Check fallback name
            rendered_vid = download_dir / "07_final.mp4"

        if rendered_vid.exists():
            # Copy to chapter dir
            shutil.copy2(rendered_vid, paths.final_file)
            # Copy to export dir with nice title
            clean_title = item["title"].replace(" #Shorts", "").replace(" ", "_")
            export_file = export_dir / f"{sid}_{clean_title}.mp4"
            shutil.copy2(rendered_vid, export_file)
            mb = export_file.stat().st_size / 1e6
            print(f"[OK] {sid}: {export_file.name} ({mb:.1f} MB, 1080x1920)")

            # Save metadata
            meta_path = export_dir / f"{sid}_metadata.txt"
            meta_content = f"TITLE:\n{item['title']}\n\nDESCRIPTION:\n{item['desc']}\n"
            meta_path.write_text(meta_content, encoding="utf-8")
        else:
            print(f"[ERROR] Could not find output video for {sid} in {download_dir}")

    shutil.rmtree(download_dir, ignore_errors=True)
    shutil.rmtree(work_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Build and render 10 YouTube Shorts")
    parser.add_argument("--skip-speech", action="store_true", help="Skip speech synthesis")
    parser.add_argument("--skip-render", action="store_true", help="Skip Kaggle render")
    args = parser.parse_args()

    short_ids = stage_all_shorts()

    if not args.skip_speech:
        speak_all_shorts(short_ids)

    if not args.skip_render:
        archive_path = build_batch_render_payload(short_ids)
        render_all_shorts_kaggle(archive_path, short_ids)

    print("\n" + "=" * 70)
    print("ALL 10 YOUTUBE SHORTS COMPLETED SUCCESSFULLY!")
    print(f"Export directory: {repo_path('data/export/shorts')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
