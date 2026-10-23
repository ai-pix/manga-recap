import json
from pathlib import Path

desc_data = json.loads(Path('data/chapters/barbarian_ch01/03_descriptions.json').read_text(encoding='utf-8'))
desc = {p['panel_id']: p for p in desc_data['panels']}
script = json.loads(Path('data/chapters/barbarian_ch01/04_script.json').read_text(encoding='utf-8'))

out = []
for b in script['blocks']:
    bid = b['block_id']
    pids = b.get('panel_ids', [])
    pid = pids[0] if pids else 'none'
    p = desc.get(pid, {})
    speech = ' // '.join(p.get('speech_bubbles', []))
    act = p.get('action', '')
    out.append(f"[{bid}] panel={pid}\n   SCRIPT : {b['narration']}\n   PANEL  : {act}\n   BUBBLES: {speech}\n")

Path('all_blocks_comparison.txt').write_text('\n'.join(out), encoding='utf-8')
print("Wrote all_blocks_comparison.txt")
