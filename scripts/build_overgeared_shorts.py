"""Generate 12 Viral YouTube Shorts (9:16 Vertical, 1080x1920) for Overgeared.

Features:
- 12 distinct, high-stakes, comedic & hype story segments across Chapters 01-30.
- Fast-paced editing with visual cuts every 2-3 seconds (12-16 panels per short).
- Fish Audio studio narration with word-level alignment (s2.1-pro-free).
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

from manga_recap.core.config import load_config  # noqa: E402
from manga_recap.core.paths import ChapterPaths, repo_path  # noqa: E402
from manga_recap.core.schema import (  # noqa: E402
    ScriptBlock,
    ScriptFile,
    save_model,
)
from manga_recap.stages.s4_speech.fish_tts_engine import run_fish_tts  # noqa: E402
from manga_recap.stages.s5_render import KaggleClient, payload  # noqa: E402

# -----------------------------------------------------------------------------
# SHORTS DEFINITIONS (12 HIGH-RETENTION STORIES ACROSS CHAPTERS 01 TO 30)
# -----------------------------------------------------------------------------

SHORTS_DATA = [
    # Short 01: The -3 Level Loser Unlocks A God Class (Ch 01-02)
    {
        "id": "overgeared_short01",
        "title": "He Dropped To Level -3 To Steal A God-Tier Class #Shorts",
        "desc": "What happens when an angry, debt-ridden gamer opens an ancient relic and drops to Level -3? Shin Youngwoo unlocked the legendary Pagma's Successor! #overgeared #manhwa #anime #recap #shorts #godgrid #webtoon",
        "blocks": [
            {"src": (1, "panel_0010"), "text": "What would you do if your level suddenly dropped to negative three?"},
            {"src": (1, "panel_0012"), "text": "Shin Youngwoo was drowning in debt and grinding for three months straight."},
            {"src": (1, "panel_0018"), "text": "Trapped in the frozen depths of the Northern End Cave,"},
            {"src": (1, "panel_0025"), "text": "fighting frost monsters with broken beginner gear."},
            {"src": (1, "panel_0030"), "text": "At the lowest chamber, he uncovered an ancient golden chest."},
            {"src": (1, "panel_0035"), "text": "Inside was a mythical relic: Pagma's Rare Book!"},
            {"src": (1, "panel_0045"), "text": "An SS-Rank quest item worth hundreds of thousands of dollars!"},
            {"src": (1, "panel_0055"), "text": "Suddenly, the dungeon boss emerged and cornered him!"},
            {"src": (1, "panel_0060"), "text": "With death only seconds away and his loot on the line,"},
            {"src": (1, "panel_0065"), "text": "Youngwoo made the craziest gamble in gaming history!"},
            {"src": (1, "panel_0068"), "text": "He opened the forbidden book and changed his class on the spot!"},
            {"src": (1, "panel_0070"), "text": "The world announced the awakening of Pagma's Successor!"},
            {"src": (2, "panel_0010"), "text": "He died in the cave, but respawned as the only legendary player!"},
            {"src": (2, "panel_0020"), "text": "Starting at Level negative three, the reign of God Grid begins!"},
            {"src": (2, "panel_0035"), "text": "Watch the full two and a half hour movie on my channel!"},
        ],
    },

    # Short 02: A Level -1 Player 1-Punching The Death Cult (Ch 04)
    {
        "id": "overgeared_short02",
        "title": "A Level -1 Player 1-Punching The Death Cult #Shorts",
        "desc": "They thought a Level -1 player would be free loot. They had no idea legendary blacksmith stats made his fists hit like a freight train! #overgeared #manhwa #anime #recap #shorts #godgrid",
        "blocks": [
            {"src": (4, "panel_0005"), "text": "Never judge a player by his level!"},
            {"src": (4, "panel_0008"), "text": "Youngwoo was currently sitting at Level negative one,"},
            {"src": (4, "panel_0012"), "text": "roaming the dark wilderness with negative stats."},
            {"src": (4, "panel_0015"), "text": "Suddenly, fanatical death cultists of the Yatan Church ambushed him!"},
            {"src": (4, "panel_0020"), "text": "They saw a pathetic beginner and mocked him for easy prey."},
            {"src": (4, "panel_0025"), "text": "They had no idea who they were dealing with!"},
            {"src": (4, "panel_0030"), "text": "Because he had legendary blacksmith attributes,"},
            {"src": (4, "panel_0035"), "text": "every point of his strength scaled into monstrous physical power!"},
            {"src": (4, "panel_0040"), "text": "Youngwoo didn't even bother drawing a weapon."},
            {"src": (4, "panel_0045"), "text": "He stepped forward and threw a bare-knuckle punch!"},
            {"src": (4, "panel_0050"), "text": "The impact shattered the cultist's heavy shield instantly!"},
            {"src": (4, "panel_0055"), "text": "Sending elite dark mages flying across the dirt!"},
            {"src": (4, "panel_0060"), "text": "The cultists screamed in absolute terror:"},
            {"src": (4, "panel_0065"), "text": "How can a negative level player hit like a raid boss?!"},
            {"src": (4, "panel_0070"), "text": "He beat the entire ambush to death with his bare hands!"},
            {"src": (4, "panel_0073"), "text": "Watch the full movie recap on my channel!"},
        ],
    },

    # Short 03: He Accidentally Forged A Masterpiece Dagger (Ch 09-10)
    {
        "id": "overgeared_short03",
        "title": "He Accidentally Forged An S-Rank Masterpiece Dagger #Shorts",
        "desc": "He just wanted to make a simple weapon to sell for rent money, and accidentally forged an S-Rank game-breaking artifact! #overgeared #manhwa #anime #recap #shorts #godgrid",
        "blocks": [
            {"src": (9, "panel_0008"), "text": "He tried to craft a simple dagger... and broke the game!"},
            {"src": (9, "panel_0015"), "text": "Grid arrived in Winston to learn real blacksmithing,"},
            {"src": (9, "panel_0022"), "text": "promising old Khan he would prove his legendary potential."},
            {"src": (9, "panel_0030"), "text": "Gripping the heavy hammer with fierce, stubborn pride,"},
            {"src": (9, "panel_0038"), "text": "he pounded the red-hot steel until his muscles tore!"},
            {"src": (10, "panel_0015"), "text": "Hundreds of rhythmic hammer strikes echoed across the forge."},
            {"src": (10, "panel_0018"), "text": "Then, an explosion of blinding crimson light erupted!"},
            {"src": (10, "panel_0021"), "text": "System notifications started flooding his vision!"},
            {"src": (10, "panel_0025"), "text": "You have created an original masterpiece: The Ideal Dagger!"},
            {"src": (10, "panel_0030"), "text": "Attack power exceeding Level fifty rare weapons,"},
            {"src": (10, "panel_0035"), "text": "with an instant-kill probability on critical strikes!"},
            {"src": (10, "panel_0040"), "text": "Old Khan fell to his knees in tears of reverence,"},
            {"src": (10, "panel_0050"), "text": "realizing he was standing before the reincarnation of Pagma!"},
            {"src": (10, "panel_0060"), "text": "Watch the full two and a half hour movie on my channel!"},
        ],
    },

    # Short 04: The 10-Coin Arrow That Shook The Virtual World (Ch 11-13)
    {
        "id": "overgeared_short04",
        "title": "The 10-Coin Arrow That Broke The Game's Economy #Shorts",
        "desc": "Grid hammered out 20 armor-piercing Jaffa arrows and put them on the global auction house. Top rankers went broke fighting for them! #overgeared #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (11, "panel_0010"), "text": "How one tiny arrow made an angry gamer a millionaire!"},
            {"src": (11, "panel_0018"), "text": "Grid discovered a rare dwarven metal called Jaffa,"},
            {"src": (11, "panel_0025"), "text": "capable of ignoring heavy armor penetration."},
            {"src": (11, "panel_0035"), "text": "He spent the afternoon hammering out special arrowheads."},
            {"src": (12, "panel_0015"), "text": "In testing, a single archer shot one arrow at an armored beast."},
            {"src": (12, "panel_0025"), "text": "It pierced straight through high-tier metal like butter!"},
            {"src": (12, "panel_0035"), "text": "One-shotting monsters five times their level!"},
            {"src": (13, "panel_0010"), "text": "Grid placed just twenty Jaffa arrows on the global auction house."},
            {"src": (13, "panel_0020"), "text": "Within minutes, the world's rank one guilds went to war!"},
            {"src": (13, "panel_0030"), "text": "Bids skyrocketed from thousands to millions of gold!"},
            {"src": (13, "panel_0040"), "text": "Top rankers went broke just to buy a single arrow!"},
            {"src": (13, "panel_0050"), "text": "Grid sat back laughing hysterically as gold poured into his account!"},
            {"src": (13, "panel_0060"), "text": "From broke debtor to the richest crafter alive!"},
            {"src": (13, "panel_0068"), "text": "Watch the full movie recap on my channel!"},
        ],
    },

    # Short 05: Defending The Old Blacksmith From 50 Gangsters (Ch 14-15)
    {
        "id": "overgeared_short05",
        "title": "Defending The Old Blacksmith From 50 Armed Thugs #Shorts",
        "desc": "Fifty corrupt gangsters beat up old Khan to seize his smithy. Then Grid walked in and turned the shop into a slaughterhouse! #overgeared #manhwa #anime #recap #shorts #godgrid",
        "blocks": [
            {"src": (14, "panel_0010"), "text": "Never mess with a legendary blacksmith's friend!"},
            {"src": (14, "panel_0020"), "text": "The corrupt Mero Company wanted Khan's smithy destroyed."},
            {"src": (14, "panel_0030"), "text": "They sent fifty heavily armed gangsters to tear the shop down."},
            {"src": (14, "panel_0040"), "text": "They beat old Khan bloody and threw him to the floor."},
            {"src": (14, "panel_0050"), "text": "Big mistake. Grid walked through the front door."},
            {"src": (15, "panel_0010"), "text": "Seeing the only man who treated him with kindness injured,"},
            {"src": (15, "panel_0020"), "text": "Grid's eyes snapped with pure, unadulterated fury!"},
            {"src": (15, "panel_0028"), "text": "He didn't bother calling for city guards."},
            {"src": (15, "panel_0035"), "text": "Equipping high-rank weapons with zero class restrictions,"},
            {"src": (15, "panel_0045"), "text": "he charged into fifty armed thugs like a hurricane of death!"},
            {"src": (15, "panel_0055"), "text": "Every single swing crushed armor and shattered bones!"},
            {"src": (15, "panel_0065"), "text": "The gangsters dropped their weapons and begged for mercy,"},
            {"src": (15, "panel_0070"), "text": "realizing this blacksmith was an unstoppable monster!"},
            {"src": (15, "panel_0078"), "text": "Experience the full story on my channel now!"},
        ],
    },

    # Short 06: When A Blacksmith Awakens Ancient Swordsmanship (Ch 16-17)
    {
        "id": "overgeared_short06",
        "title": "When A Blacksmith Awakens Ancient Godly Swordsmanship #Shorts",
        "desc": "Who said blacksmiths could only forge weapons? Pagma was also an immortal swordsman! Watch Grid execute Sword Dance: Wave! #overgeared #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (16, "panel_0015"), "text": "You thought blacksmiths could only forge weapons?"},
            {"src": (16, "panel_0025"), "text": "Think again! Pagma was both the greatest smith and swordsman!"},
            {"src": (16, "panel_0035"), "text": "Cornered by elite underground assassins in Winston,"},
            {"src": (16, "panel_0045"), "text": "Grid unlocked the hidden secrets of his legendary class!"},
            {"src": (17, "panel_0010"), "text": "Pagma's Swordsmanship: Sword Dance unleashed!"},
            {"src": (17, "panel_0020"), "text": "His body began executing an ancient divine dance,"},
            {"src": (17, "panel_0030"), "text": "weaving graceful footsteps with lethal combat strikes!"},
            {"src": (17, "panel_0040"), "text": "Sword Dance: Wave!"},
            {"src": (17, "panel_0048"), "text": "A colossal tidal wave of compressed sword aura exploded outwards!"},
            {"src": (17, "panel_0055"), "text": "Slicing high-level assassins in half before they could react!"},
            {"src": (17, "panel_0062"), "text": "Their health bars vaporized in a single blinding instant!"},
            {"src": (17, "panel_0070"), "text": "The town erupted in cheers as Grid stood undefeated!"},
            {"src": (17, "panel_0075"), "text": "Watch the full two and a half hour movie on my channel!"},
        ],
    },

    # Short 07: The 50-Hour Insane Blacksmithing Gauntlet (Ch 19)
    {
        "id": "overgeared_short07",
        "title": "He Crafted For 50 Hours Straight With Zero Sleep #Shorts",
        "desc": "Grid locked himself in the furnace room for 50 straight hours, swinging his hammer until his hands tore apart to forge Dainsleif! #overgeared #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (19, "panel_0010"), "text": "How crazy do you have to be to craft for fifty hours straight?"},
            {"src": (19, "panel_0020"), "text": "To craft the legendary Dainsleif greatsword,"},
            {"src": (19, "panel_0030"), "text": "Grid locked himself inside Khan's furnace room."},
            {"src": (19, "panel_0040"), "text": "Ten hours passed. He didn't take a single sip of water."},
            {"src": (19, "panel_0050"), "text": "Twenty-four hours passed. His hands were blistered and bloody."},
            {"src": (19, "panel_0060"), "text": "Most players would log out from exhaustion or mental strain."},
            {"src": (19, "panel_0068"), "text": "Not Grid! His pure greed and stubborn spite kept him hammering!"},
            {"src": (19, "panel_0075"), "text": "Forty hours! Khan begged him to stop before his avatar collapsed!"},
            {"src": (19, "panel_0080"), "text": "Grid just gave an insane, bloodshot glare and kept swinging!"},
            {"src": (19, "panel_0085"), "text": "On the fiftieth hour, the final hammer strike landed!"},
            {"src": (19, "panel_0088"), "text": "A divine light pierced the heavens above Winston!"},
            {"src": (19, "panel_0090"), "text": "A weapon capable of slaying gods was born!"},
            {"src": (19, "panel_0091"), "text": "Check out the full movie on my channel!"},
        ],
    },

    # Short 08: Game Admins Panicking Over A Broken Player (Ch 20)
    {
        "id": "overgeared_short08",
        "title": "Game Admins Panicking Over A Broken Player #Shorts",
        "desc": "The S.A. Group supercomputer Morpheus went into red alert when Grid broke every game balance rule from his bedroom in pajamas! #overgeared #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (20, "panel_0008"), "text": "What happens when developers realize their game is broken?!"},
            {"src": (20, "panel_0015"), "text": "Inside the high-tech headquarters of the S.A. Group,"},
            {"src": (20, "panel_0025"), "text": "the supercomputer Morpheus triggered a red emergency alert!"},
            {"src": (20, "panel_0035"), "text": "Chairman Lim Cheolho rushed into the server room in a panic."},
            {"src": (20, "panel_0045"), "text": "A player had cleared an impossible quest five years early!"},
            {"src": (20, "panel_0052"), "text": "And created items that violated every balance calculation!"},
            {"src": (20, "panel_0058"), "text": "Who is this gaming prodigy? An esports champion? A genius?"},
            {"src": (20, "panel_0065"), "text": "The screen displayed Shin Youngwoo:"},
            {"src": (20, "panel_0068"), "text": "An angry, debt-ridden high school dropout sitting in pajamas!"},
            {"src": (20, "panel_0072"), "text": "Drinking cheap soju and cackling at his screen!"},
            {"src": (20, "panel_0075"), "text": "The developers held their heads in despair: The game is ruined!"},
            {"src": (20, "panel_0076"), "text": "Watch the full movie recap on my channel!"},
        ],
    },

    # Short 09: Soloing The Frost Orc Tribe In An Ice Cave (Ch 22)
    {
        "id": "overgeared_short09",
        "title": "Soloing A Frost Orc Tribe In An Ice Cave #Shorts",
        "desc": "An entire tribe of Frost Orcs ambushed the party in a freezing blizzard. Then Grid revealed his overgeared armor! #overgeared #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (22, "panel_0010"), "text": "They thought an ice cave raid would be suicide for a blacksmith!"},
            {"src": (22, "panel_0020"), "text": "Deep in the Kesan Plateau, a blizzard trapped a raiding party."},
            {"src": (22, "panel_0030"), "text": "Dozens of elite Frost Orcs encircled them with barbed axes."},
            {"src": (22, "panel_0040"), "text": "Freezing frost debuffs cut their health by half."},
            {"src": (22, "panel_0050"), "text": "Then Grid stepped forward and took off his travel cloak."},
            {"src": (22, "panel_0060"), "text": "Beneath it was full-body custom plate armor radiating warmth!"},
            {"src": (22, "panel_0070"), "text": "Immune to cold! Immune to frostbite!"},
            {"src": (22, "panel_0078"), "text": "When the orc chieftain smashed a heavy mace against Grid's chest,"},
            {"src": (22, "panel_0085"), "text": "the mace shattered into fragments upon impact!"},
            {"src": (22, "panel_0090"), "text": "Damage received: Zero!"},
            {"src": (22, "panel_0092"), "text": "Grid smirked, raised his greatsword, and slaughtered the entire tribe!"},
            {"src": (22, "panel_0094"), "text": "Watch the full two and a half hour movie on my channel!"},
        ],
    },

    # Short 10: Humiliating The Leader Of The Strongest Guild (Ch 23)
    {
        "id": "overgeared_short10",
        "title": "Humiliating The Leader Of The Strongest Guild #Shorts",
        "desc": "Peak Sword, master of the Silver Knights, tried to intimidate a humble blacksmith. One flick of Grid's dagger snapped his prized katana in half! #overgeared #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (23, "panel_0010"), "text": "Don't ever try to bully a player who's overgeared!"},
            {"src": (23, "panel_0020"), "text": "Peak Sword was the legendary leader of the Silver Knights,"},
            {"src": (23, "panel_0030"), "text": "feared by every player in the South Korean server."},
            {"src": (23, "panel_0040"), "text": "He cornered Grid, demanding he hand over his rare items."},
            {"src": (23, "panel_0050"), "text": "Do you know who I am? Peak Sword yelled arrogantly."},
            {"src": (23, "panel_0060"), "text": "Grid barely looked up: I don't care, get lost."},
            {"src": (23, "panel_0070"), "text": "Enraged, Peak Sword drew his top-tier katana and attacked!"},
            {"src": (23, "panel_0078"), "text": "Grid casually unsheathed the Ideal Dagger and parried."},
            {"src": (23, "panel_0085"), "text": "With one effortless flick of his wrist,"},
            {"src": (23, "panel_0090"), "text": "he cleaved Peak Sword's blade clean in two!"},
            {"src": (23, "panel_0091"), "text": "Leaving the number one guild master stunned in utter shock!"},
            {"src": (23, "panel_0092"), "text": "Experience the full epic story on my channel!"},
        ],
    },

    # Short 11: Confronting The Immortal Blood Demon Malacus (Ch 25-26)
    {
        "id": "overgeared_short11",
        "title": "Confronting The Immortal Blood Demon Malacus #Shorts",
        "desc": "Malacus trapped the canyon in a poisonous blood cage, paralyzing every top ranker. Then Grid casually walked through the fog completely immune! #overgeared #manhwa #anime #recap #shorts",
        "blocks": [
            {"src": (25, "panel_0015"), "text": "The most feared raid boss met his worst nightmare!"},
            {"src": (25, "panel_0025"), "text": "Malacus was the eighth servant of the Yatan Church,"},
            {"src": (25, "panel_0035"), "text": "an immortal vampire who sacrificed thousands in blood rituals."},
            {"src": (25, "panel_0050"), "text": "He trapped the entire canyon inside an inescapable blood cage!"},
            {"src": (26, "panel_0015"), "text": "Every top player was paralyzed by toxic blood mist."},
            {"src": (26, "panel_0025"), "text": "Malacus laughed, preparing to harvest their souls."},
            {"src": (26, "panel_0035"), "text": "Until one man casually walked through the poisonous fog!"},
            {"src": (26, "panel_0045"), "text": "Grid's legendary title granted absolute immunity to dark magic!"},
            {"src": (26, "panel_0055"), "text": "Malacus stared in horror: Why aren't you bleeding to death?!"},
            {"src": (26, "panel_0065"), "text": "Grid cracked his knuckles and gripped his greatsword:"},
            {"src": (26, "panel_0075"), "text": "Because you're worth a lot of gold, and I'm here to collect!"},
            {"src": (26, "panel_0085"), "text": "Watch the full movie recap on my channel!"},
        ],
    },

    # Short 12: He Erased The Raid Boss In A Single Strike (Ch 27)
    {
        "id": "overgeared_short12",
        "title": "He Erased The World Boss In A Single Strike #Shorts",
        "desc": "Combining the ultimate forged armor with Pagma's Kill sword dance, Grid dealt game-breaking critical damage and vaporized the boss! #overgeared #manhwa #anime #recap #shorts #godgrid",
        "blocks": [
            {"src": (27, "panel_0010"), "text": "The final strike that crowned him God Grid!"},
            {"src": (27, "panel_0020"), "text": "Malacus unleashed his ultimate blood demon transformation,"},
            {"src": (27, "panel_0030"), "text": "raining torrential spears of crimson death from the clouds."},
            {"src": (27, "panel_0040"), "text": "Grid didn't flinch. He channeled every ounce of mana he had!"},
            {"src": (27, "panel_0050"), "text": "Pagma's Swordsmanship: Kill!"},
            {"src": (27, "panel_0060"), "text": "The sky split apart as a blinding golden sword beam surged forward!"},
            {"src": (27, "panel_0070"), "text": "Slicing through Malacus's demonic blood shield like tissue paper!"},
            {"src": (27, "panel_0078"), "text": "The strike dealt critical damage beyond all game limits!"},
            {"src": (27, "panel_0085"), "text": "The eighth servant of Yatan was vaporized into golden dust!"},
            {"src": (27, "panel_0090"), "text": "Server-wide announcements hailed the new legend of Satisfy!"},
            {"src": (27, "panel_0092"), "text": "The birth of the almighty God Grid!"},
            {"src": (27, "panel_0093"), "text": "Watch the complete two and a half hour movie on my channel right now!"},
        ],
    },
]


def resolve_panel_file(ch_num: int, pid: str) -> Path:
    """Find panel file across available folder layouts."""
    candidates = [
        repo_path(f"data/chapters/overgeared/ch{ch_num:02d}/02_panels/{pid}.webp"),
        repo_path(f"data/chapters/overgeared/ch{ch_num:02d}/02_panels/{pid}.png"),
        repo_path(f"data/chapters/overgeared/ch{ch_num:02d}/02_panels/{pid}.jpg"),
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(f"Cannot find {pid} for chapter {ch_num}")


def stage_all_shorts() -> list[str]:
    """Stage panel crops and build 04_script.json for all 12 shorts."""
    staged_ids = []
    print("=" * 70)
    print("STAGING 12 OVERGEARED YOUTUBE SHORTS (FAST-PACED, 9:16 VERTICAL)")
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
            dest_file = paths.panels_dir / f"{pid}.webp"
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
    """Generate Fish Audio narration and timeline for all shorts."""
    cfg = load_config()
    print("\n" + "=" * 70)
    print("SYNTHESIZING STUDIO NARRATION VIA FISH AUDIO FOR 12 SHORTS")
    print("=" * 70)

    for sid in short_ids:
        paths = ChapterPaths.create(sid)
        if paths.narration_file.exists() and paths.timeline_file.exists():
            print(f"[{sid}] Audio and timeline already exist, skipping speech synthesis.")
            continue

        print(f"\n[{sid}] Generating Fish Audio speech...", flush=True)
        t0 = time.time()
        timeline = run_fish_tts(paths, cfg, force=True)
        dur = timeline.duration
        print(f"[{sid}] [OK] Generated {dur:.1f}s studio audio in {time.time() - t0:.1f}s")


def build_batch_render_payload(short_ids: list[str]) -> Path:
    """Bundle all 12 shorts into a single Kaggle batch render archive (9:16 vertical 1080x1920)."""
    staging = repo_path("data/chapters/_kaggle_overgeared_shorts_input")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    chapters_dir = staging / "chapters"
    chapters_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 70)
    print("PACKAGING 12 SHORTS INTO KAGGLE BATCH RENDER PAYLOAD (9:16 VERTICAL 1080x1920)")
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

    zip_path = repo_path("data/chapters/overgeared_shorts_payload.zip")
    archive = payload.build_archive(staging, zip_path)
    shutil.rmtree(staging, ignore_errors=True)
    size_mb = archive.stat().st_size / 1e6
    print(f"Archive built successfully: {archive} ({size_mb:.1f} MB)")
    return archive


def render_all_shorts_kaggle(archive_path: Path, short_ids: list[str]) -> None:
    """Submit batch job to Kaggle GPU kernel and download all 12 rendered vertical shorts."""
    cfg = load_config()
    kernel_slug = "manga-recap-render"
    client = KaggleClient()

    print("\n" + "=" * 70)
    print(f"UPLOADING PAYLOAD AND LAUNCHING KAGGLE GPU RENDER ({kernel_slug})")
    print("=" * 70)

    payload_url = payload.upload(
        archive_path,
        host=str(cfg.get("render.payload_host", payload.DEFAULT_HOST)),
        filename="overgeared-shorts-batch-render.zip",
    )
    print(f"Uploaded batch archive -> {payload_url}")

    kernel_dir = repo_path("kaggle/kernel_render")
    work_dir = repo_path("data/chapters/_kaggle_kernel_overgeared_shorts")
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

    download_dir = client.download_kernel_output(kernel_id, repo_path("data/chapters/_kaggle_overgeared_shorts_output"))

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
            rendered_vid = download_dir / "07_final.mp4"

        if rendered_vid.exists():
            shutil.copy2(rendered_vid, paths.final_file)
            clean_title = item["title"].replace(" #Shorts", "").replace(" ", "_")
            export_file = export_dir / f"{sid}_{clean_title}.mp4"
            shutil.copy2(rendered_vid, export_file)
            mb = export_file.stat().st_size / 1e6
            print(f"[OK] {sid}: {export_file.name} ({mb:.1f} MB, 1080x1920)")

            meta_path = export_dir / f"{sid}_metadata.txt"
            meta_content = f"TITLE:\n{item['title']}\n\nDESCRIPTION:\n{item['desc']}\n"
            meta_path.write_text(meta_content, encoding="utf-8")
        else:
            print(f"[ERROR] Could not find output video for {sid} in {download_dir}")

    shutil.rmtree(download_dir, ignore_errors=True)
    shutil.rmtree(work_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Build and render 12 Overgeared YouTube Shorts")
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
    print("ALL 12 OVERGEARED YOUTUBE SHORTS COMPLETED SUCCESSFULLY!")
    print(f"Export directory: {repo_path('data/export/shorts')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
