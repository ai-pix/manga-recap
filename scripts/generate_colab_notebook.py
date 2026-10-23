import json
from pathlib import Path

nb = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🎬 Manga Recap — GPU Video Renderer (Google Colab)\n",
                "This notebook renders recap videos for all Manga Recap chapters using **Google Colab's free T4 GPU** with hardware-accelerated NVENC encoding.\n",
                "\n",
                "### 🚀 Quick Start Instructions:\n",
                "1. **Enable GPU**: Click **Runtime** > **Change runtime type** > Select **T4 GPU** > Click **Save**.\n",
                "2. **Run All**: Click **Runtime** > **Run all** (or run each cell sequentially).\n",
                "3. At the end, you will receive a direct download link for all rendered `07_final.mp4` recap videos!\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 1. Verify NVIDIA T4 GPU\n",
                "!nvidia-smi\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 2. Install dependencies & verify NVENC hardware acceleration\n",
                "!pip install -q Pillow soundfile torchaudio pyyaml requests tqdm\n",
                "!ffmpeg -y -hide_banner -loglevel error -f lavfi -i testsrc=duration=0.05:size=64x64:rate=1 -c:v h264_nvenc -f null - && echo \"✅ Hardware NVENC is ACTIVE on Colab GPU!\" || echo \"⚠️ Standard ffmpeg check completed.\"\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 3. Setup workspace and define batch payload URLs\n",
                "import os\n",
                "import sys\n",
                "import shutil\n",
                "import urllib.request\n",
                "import zipfile\n",
                "from pathlib import Path\n",
                "\n",
                "WORKSPACE = Path('/content/manga_recap')\n",
                "WORKSPACE.mkdir(parents=True, exist_ok=True)\n",
                "os.chdir(WORKSPACE)\n",
                "\n",
                "BATCH_URLS = {\n",
                "    'batch_1': 'https://sendit.sh/1HWxo/Do5eu.zip',  # ch004 - ch012 (10 chapters)\n",
                "    'batch_2': 'https://sendit.sh/Bpqh8/5UZgH.zip',  # ch013 - ch022 (10 chapters)\n",
                "    'batch_3': 'https://sendit.sh/UNplX/Csd6k.zip',  # ch023 - ch026 (4 chapters)\n",
                "    'batch_4': 'https://sendit.sh/Ik5c9/1Myiz.zip',  # ch027 - ch030 (4 chapters)\n",
                "}\n",
                "\n",
                "print('Available batches on sendit.sh:')\n",
                "for k, v in BATCH_URLS.items():\n",
                "    print(f'  {k}: {v}')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 4. Choose which batch to render:\n",
                "# Set to 'all' to render all 27 chapters, or choose a specific batch (e.g. 'batch_1', 'batch_2', etc.)\n",
                "BATCH_TO_RUN = 'all'\n",
                "\n",
                "batches_to_process = list(BATCH_URLS.keys()) if BATCH_TO_RUN == 'all' else [BATCH_TO_RUN]\n",
                "print(f'Selected batches: {batches_to_process}')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 5. Download, extract, and render recap videos\n",
                "import time\n",
                "import subprocess\n",
                "import json\n",
                "\n",
                "OUTPUT_ROOT = Path('/content/rendered_outputs')\n",
                "OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)\n",
                "\n",
                "for batch_name in batches_to_process:\n",
                "    url = BATCH_URLS[batch_name]\n",
                "    print('\\n' + '=' * 60)\n",
                "    print(f'Processing {batch_name} ({url})...')\n",
                "    print('=' * 60)\n",
                "    \n",
                "    batch_dir = WORKSPACE / batch_name\n",
                "    batch_dir.mkdir(parents=True, exist_ok=True)\n",
                "    zip_path = WORKSPACE / f'{batch_name}.zip'\n",
                "    \n",
                "    print(f'Downloading {batch_name}...')\n",
                "    urllib.request.urlretrieve(url, zip_path)\n",
                "    print(f'Extracting {batch_name}...')\n",
                "    with zipfile.ZipFile(zip_path) as z:\n",
                "        z.extractall(batch_dir)\n",
                "    zip_path.unlink()\n",
                "    \n",
                "    src_dir = batch_dir / 'src'\n",
                "    if str(src_dir) not in sys.path:\n",
                "        sys.path.insert(0, str(src_dir))\n",
                "    \n",
                "    job_file = batch_dir / 'job.json'\n",
                "    chapters_dir = batch_dir / 'chapters'\n",
                "    job = json.loads(job_file.read_text(encoding='utf-8'))\n",
                "    chapters = job.get('chapters', [d.name for d in chapters_dir.iterdir() if d.is_dir()])\n",
                "    print(f'Rendering {len(chapters)} chapters: {chapters}')\n",
                "    \n",
                "    from manga_recap.render.ffmpeg import (\n",
                "        build_clips,\n",
                "        render_panels,\n",
                "        has_nvenc,\n",
                "        join_clips,\n",
                "    )\n",
                "    \n",
                "    use_nvenc = has_nvenc()\n",
                "    print(f'Hardware NVENC enabled: {use_nvenc}')\n",
                "    \n",
                "    for ch_name in chapters:\n",
                "        ch_dir = chapters_dir / ch_name\n",
                "        if not ch_dir.exists():\n",
                "            continue\n",
                "        \n",
                "        t0 = time.time()\n",
                "        print(f'\\n>>> Rendering {ch_name}...')\n",
                "        \n",
                "        script_file = ch_dir / 'script.json'\n",
                "        timeline_file = ch_dir / 'timeline.json'\n",
                "        narration_file = ch_dir / 'narration.wav'\n",
                "        panels_dir = ch_dir / 'panels'\n",
                "        \n",
                "        clips = build_clips(\n",
                "            timeline_file=timeline_file,\n",
                "            script_file=script_file,\n",
                "            audio_file=narration_file,\n",
                "            panels_dir=panels_dir,\n",
                "            min_seconds=job['render'].get('min_panel_duration', 0.5),\n",
                "            max_seconds=job['render'].get('max_panel_duration', 8.0),\n",
                "            fps=job['render'].get('fps', 24),\n",
                "            strategy=job['render'].get('shot_strategy', 'beats'),\n",
                "            max_words_per_beat=job['render'].get('max_words_per_beat', 14),\n",
                "            sync_report_file=ch_dir / '07_sync_report.json',\n",
                "        )\n",
                "        \n",
                "        stills = render_panels(\n",
                "            clips=clips,\n",
                "            job=job['render'],\n",
                "            output_dir=ch_dir / 'stills',\n",
                "        )\n",
                "        \n",
                "        final_mp4 = ch_dir / '07_final.mp4'\n",
                "        join_clips(\n",
                "            clips=clips,\n",
                "            stills=stills,\n",
                "            audio_file=narration_file,\n",
                "            output_file=final_mp4,\n",
                "            job=job['render'],\n",
                "            nvenc=use_nvenc,\n",
                "        )\n",
                "        \n",
                "        dur = time.time() - t0\n",
                "        mb = final_mp4.stat().st_size / 1e6\n",
                "        print(f'✅ {ch_name} rendered in {dur:.1f}s ({mb:.1f} MB)')\n",
                "        \n",
                "        target_ch_dir = OUTPUT_ROOT / ch_name\n",
                "        target_ch_dir.mkdir(parents=True, exist_ok=True)\n",
                "        shutil.copy2(final_mp4, target_ch_dir / '07_final.mp4')\n",
                "        if (ch_dir / '07_sync_report.json').exists():\n",
                "            shutil.copy2(ch_dir / '07_sync_report.json', target_ch_dir / '07_sync_report.json')\n"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# 6. Package and upload rendered recap videos\n",
                "import zipfile\n",
                "import requests\n",
                "\n",
                "archive_name = 'rendered_recap_videos.zip'\n",
                "archive_path = Path(f'/content/{archive_name}')\n",
                "\n",
                "print('Packaging all rendered outputs...')\n",
                "with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as z:\n",
                "    for f in sorted(OUTPUT_ROOT.rglob('*')):\n",
                "        if f.is_file():\n",
                "            z.write(f, arcname=f.relative_to(OUTPUT_ROOT))\n",
                "\n",
                "mb = archive_path.stat().st_size / 1e6\n",
                "print(f'Archive ready ({mb:.1f} MB). Uploading to sendit.sh...')\n",
                "\n",
                "with archive_path.open('rb') as f:\n",
                "    resp = requests.put('https://sendit.sh', data=f, headers={'X-Filename': archive_name}, timeout=600)\n",
                "    download_url = resp.text.strip()\n",
                "\n",
                "print('\\n' + '=' * 60)\n",
                "print('🎉 ALL VIDEOS RENDERED & READY!')\n",
                "print(f'📥 Download Link: {download_url}')\n",
                "print('=' * 60)\n"
            ]
        }
    ],
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "provenance": []
        },
        "kernelspec": {
            "display_name": "Python 3",
            "name": "python3"
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 0
}

target = Path("notebooks/Manga_Recap_Colab_GPU_Render.ipynb")
target.write_text(json.dumps(nb, indent=2), encoding="utf-8")
print("Successfully generated:", target)
