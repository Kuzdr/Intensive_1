from pathlib import Path
import re, html

p = Path('data/raw/cdp/vdnh_tp_page2.html')
s = p.read_text(encoding='utf-8', errors='ignore')

events = []
for m in re.finditer(r'href="(https://lektorij-vdnh\.timepad\.ru/event/\d+/)[^"]*"[^>]*>([^<]{5,200})</a>', s):
    url = m.group(1).rstrip('/')
    title = html.unescape(m.group(2).strip())
    pos = m.start()
    events.append((url, title, pos))

for url, title, pos in events:
    chunk = s[pos:pos+800]
    rel = None
    m2 = re.search(r'(через\s+[^<]{1,60})', chunk, re.I)
    if m2:
        rel = html.unescape(m2.group(1)).strip()
    else:
        m2 = re.search(r'([^<]{0,40}(?:назад|вчера|позавчера|сегодня|завтра)[^<]{0,40})', chunk, re.I)
        if m2:
            rel = html.unescape(m2.group(1)).strip()
    eid = url.rsplit('/', 1)[-1]
    print(f"{eid} || {rel if rel else 'NO_REL'} || {title[:70]}")
