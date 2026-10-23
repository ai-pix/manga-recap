# YouTube Publishing & Google Drive Upload Guide

This guide covers everything you need to publish your **Only Sense Online (Chapters 1–30)** manga recap series to Google Drive and YouTube.

---

## 1. Export Package Overview

All materials are organized in:
`data/youtube_ready/`

```
data/youtube_ready/
├── 00_FULL_SERIES_COMPILATION/
│   ├── Only_Sense_Online_Full_Story_Recap_Ch01-30.mp4  (1.28 GB, 5 hours 05 min 08s)
│   ├── thumbnail.jpg                                  (1280x720 16:9 blurred backdrop)
│   └── metadata.txt                                   (Master Title, Description w/ Timestamps, Tags)
│
├── Chapter_01_Enter_the_World_of_OSO/
│   ├── Only_Sense_Online_Chapter_1.mp4                (40.5 MB, 10.54 min)
│   ├── thumbnail.jpg                                  (1280x720)
│   └── metadata.txt                                   (Title, Description, Tags)
│
├── Chapter_02_Forest_of_the_Beginning_Potion_Crafting/
│   ├── Only_Sense_Online_Chapter_2.mp4                (39.9 MB, 10.31 min)
│   ├── thumbnail.jpg
│   └── metadata.txt
│
... (31 Chapter Folders in total)
│
└── CHAPTER_TIMESTAMPS.txt                             (Full master timestamp list)
```

> **Note on Storage:** The videos in the `Chapter_XX` folders are NTFS hardlinks to the original renders. They occupy **0 MB** of duplicate disk space on your computer, while appearing as complete, standalone files ready for drag-and-drop or upload.

---

## 2. Step 1: Uploading to Google Drive

You can upload the entire package to Google Drive using either of the following methods:

### Method A: Web Drag-and-Drop (Fastest & Simplest)
1. Open [Google Drive](https://drive.google.com).
2. Click **+ New** > **New Folder** and name it `Manga Recap - Only Sense Online`.
3. Open `data/youtube_ready` in File Explorer:
   - Path: `D:\Python Projects\Manga Recap\data\youtube_ready`
4. Drag and drop the folders (or the entire `youtube_ready` folder) directly into your Google Drive browser window.
5. Google Drive will upload the files with all subfolders intact.

### Method B: Google Drive for Desktop
If you have the Google Drive app installed on Windows (mapped to `G:\` or a local sync folder):
1. Copy or move `data/youtube_ready` directly into `G:\My Drive\Manga Recap - Only Sense Online\`.
2. Windows and Google Drive will sync the files in the background automatically.

### Method C: Automated Python API Script
If you prefer automated command-line upload:
1. Enable Google Drive API in Google Cloud Console and download `credentials.json` into the project root.
2. Run:
   ```powershell
   .venv\Scripts\python.exe scripts/upload_to_gdrive.py
   ```
3. A browser tab will open for authentication, and the script will upload all videos, thumbnails, and metadata with progress indicators.

---

## 3. Step 2: Automated YouTube Upload Pipeline

You can upload directly to YouTube via the new automated CLI uploader [`scripts/upload_to_youtube.py`](file:///D:/Python%20Projects/Manga%20Recap/scripts/upload_to_youtube.py), which handles:
- Video upload with resumable 10MB chunking and live progress bar
- Custom 16:9 thumbnail upload & binding
- Title, Description (with chapter timestamps), Tags, Category (`24` Entertainment), and Kids status
- Privacy settings (`unlisted`, `private`, `public`) and scheduled release (`--publish-at`)
- Upload history & state tracking in `data/youtube_uploads.json`

### One-Time YouTube API Setup (Takes 2 Minutes)
1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project (e.g., `Manga Recap Uploader`).
2. In **APIs & Services** > **Library**, search for and enable **YouTube Data API v3**.
3. Go to **Credentials** > **Create Credentials** > **OAuth client ID**:
   - Application type: **Desktop App**
   - Name: `Manga Recap Uploader`
4. Click **Download JSON**, rename the file to `client_secrets.json`, and place it in the project root (`D:\Python Projects\Manga Recap\client_secrets.json`).
5. (First run only): A browser tab will open asking you to sign in with your YouTube channel account. Once approved, the access token is cached at `config/youtube_token.json` and refreshes automatically!

### CLI Commands:

```powershell
# 1. Preview what will be uploaded (Dry Run - no network calls needed):
.venv\Scripts\python.exe scripts/upload_to_youtube.py --dry-run ch01 --compilation

# 2. Upload the 5.1-Hour Master Marathon Compilation Video:
.venv\Scripts\python.exe scripts/upload_to_youtube.py --compilation

# 3. Upload a single chapter (defaults to unlisted for review):
.venv\Scripts\python.exe scripts/upload_to_youtube.py ch01

# 4. Upload immediately as public:
.venv\Scripts\python.exe scripts/upload_to_youtube.py ch01 --privacy public

# 5. Schedule video release:
.venv\Scripts\python.exe scripts/upload_to_youtube.py ch01 --publish-at 2026-10-06T12:00:00Z

# 6. Upload all 31 chapters in sequence:
.venv\Scripts\python.exe scripts/upload_to_youtube.py --all
```

---

## 4. Manual Web Upload via YouTube Studio (Alternative)

If you prefer uploading manually via YouTube Studio:

1. In Google Drive, download the desired video and `thumbnail.jpg` to your device (or upload directly if using Google Drive YouTube integration).
2. Go to [YouTube Studio](https://studio.youtube.com) and click **Create** > **Upload videos**.
3. Select the `.mp4` video file.
4. Open the accompanying `metadata.txt` from the chapter folder:
   - **Title:** Copy the `TITLE` line.
   - **Description:** Copy the `DESCRIPTION` block (includes the synopsis, episode hook, fair-use disclaimer, and hashtags).
   - **Thumbnail:** Click **Upload thumbnail** and choose `thumbnail.jpg`.
   - **Tags:** In "Show More" > "Tags", paste the comma-separated keywords from the `TAGS` section.
5. Set audience ("No, it's not made for kids"), category to **Entertainment** or **Gaming**, and publish or schedule as desired!

---

## 4. Full Story Marathon Video (Master Compilation)

For the **5.1-hour complete compilation video**:
- **Video:** `data/youtube_ready/00_FULL_SERIES_COMPILATION/Only_Sense_Online_Full_Story_Recap_Ch01-30.mp4`
- **Thumbnail:** `data/youtube_ready/00_FULL_SERIES_COMPILATION/thumbnail.jpg`
- **Metadata:** `data/youtube_ready/00_FULL_SERIES_COMPILATION/metadata.txt`

### Master Timestamps (Included in Master Description):
```text
00:00:00 - Chapter 1: Enter the World of OSO
00:10:32 - Chapter 2: Forest of the Beginning & Potion Crafting
00:20:50 - Chapter 3: Crafting Discoveries & The Target Lock Secret
00:32:03 - Chapter 4: The Crystal Tree and Myuu
00:42:39 - Chapter 5: The Golem and the Third Town
00:54:02 - Chapter 5.5: Bonus Strips & The Trash Tier List
00:57:52 - Chapter 6: The Blacksmith Trial & Wholesale Mystery
01:04:54 - Chapter 7: Trion Ring & The Value of Information
01:16:56 - Chapter 8: The Value of Information Part 2 & Magic Gems
01:28:56 - Chapter 9: Black Maiden's Longbow & The Trainman
01:40:42 - Chapter 10: The Monster Horde & The Great Stampede
01:50:43 - Chapter 11: The Grand Server Update & Atelier Yun Opens
02:01:43 - Chapter 12: The Radiant Woodland Camp & Forest Festival
02:13:53 - Chapter 13: The Cursed Woodland & The Fallen Adventurer
02:25:01 - Chapter 14: The Berserk Curse & The White Fox Cub
02:33:52 - Chapter 15: The Lake Monster & Base Camp Annihilation
02:44:35 - Chapter 16: Inferno at the Camp & United Counterattack
02:53:38 - Chapter 17: Healing the Black Kitsune & Atelier Mascot
03:03:09 - Chapter 18: The Older Sister Arrives
03:12:30 - Chapter 19: Sei's Authority & The Atelier Banquet
03:22:26 - Chapter 20: Taming the Twin Foxes & Leveling Up
03:30:17 - Chapter 21: The Massive World Boss Raid Begins
03:40:03 - Chapter 22: High Altitude Strike & Victory Celebration
03:50:35 - Chapter 23: The Atelier Economy & Server Balance
03:59:31 - Chapter 24: Cloude's Labyrinth Trap & Boss Room Scheme
04:08:20 - Chapter 25: Atelier Renovations & The Ancient Library
04:16:17 - Chapter 26: Master Chef Yun & The Secret Recipe
04:24:11 - Chapter 27: The Phantom Dungeon & The Forbidden Grimoire
04:35:20 - Chapter 28: Deciphering The Grimoire & Composite Alchemy
04:44:40 - Chapter 29: Northern Woodlands & Mass Potion Synthesis
04:55:10 - Chapter 30: The Ancient Boss Doors & The Ultimate Dungeon
```
When pasted into YouTube's description box, YouTube automatically turns these timestamps into clickable chapter markers on the video playback bar.
