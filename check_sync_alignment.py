import json
from pathlib import Path

desc_data = json.loads(Path('data/chapters/barbarian_ch01/03_descriptions.json').read_text(encoding='utf-8'))
desc = {p['panel_id']: p for p in desc_data['panels']}
script = json.loads(Path('data/chapters/barbarian_ch01/04_script.json').read_text(encoding='utf-8'))
report = json.loads(Path('data/chapters/barbarian_ch01/07_sync_report.json').read_text(encoding='utf-8'))

import json
from pathlib import Path

desc_data = json.loads(Path('data/chapters/barbarian_ch01/03_descriptions.json').read_text(encoding='utf-8'))
desc = {p['panel_id']: p for p in desc_data['panels']}
script = json.loads(Path('data/chapters/barbarian_ch01/04_script.json').read_text(encoding='utf-8'))
report = json.loads(Path('data/chapters/barbarian_ch01/07_sync_report.json').read_text(encoding='utf-8'))
timeline = json.loads(Path('data/chapters/barbarian_ch01/06_timeline.json').read_text(encoding='utf-8'))

from PIL import Image

from manga_recap.render.sync import plan_shots
rep = plan_shots(script['blocks'], timeline['words'], audio_duration=float(timeline['duration']), max_words_per_beat=14, min_shot_seconds=0.7)

for pid in ['panel_0034', 'panel_0057', 'panel_0060', 'panel_0062', 'panel_0083', 'panel_0102']:

    beats = [sh for sh in rep.shots if sh.panel_id == pid]
    p_path = Path(f'data/chapters/barbarian_ch01/02_panels/{pid}.jpg')
    with Image.open(p_path) as im:
        ratio = im.height / im.width
    print(f'Panel {pid} (ratio={ratio:.2f}, beats={len(beats)}):')
    for b in beats:
        print(f'   {b.start:.2f}s - {b.end:.2f}s: "{b.text}"')







