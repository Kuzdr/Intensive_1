from pathlib import Path
import re, html

p = Path('data/raw/cdp/vdnh_tp_page2.html')
s = p.read_text(encoding='utf-8', errors='ignore')
for m in re.finditer(r'href="(https://lektorij-vdnh\.timepad\.ru/event/\d+/)[^"]*"[^>]*>([^<]{5,200})</a>', s):
    url = m.group(1).rstrip('/')
    title = html.unescape(m.group(2).strip())
    print(url + ' ||| ' + title)
