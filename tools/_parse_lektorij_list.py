from pathlib import Path
import re

p = Path('data/raw/cdp/vdnh_lektorij_tp_list.html')
s = p.read_text(encoding='utf-8', errors='ignore')
events = []
for m in re.finditer(r'href="(https?://lektorij-vdnh\.timepad\.ru/event/\d+/[^"]*)"', s):
    url = m.group(1).split('?')[0].rstrip('/')
    events.append(url)
seen = set()
uniq = []
for u in events:
    if u not in seen:
        seen.add(u)
        uniq.append(u)
for u in uniq:
    print(u)
