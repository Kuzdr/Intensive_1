# -*- coding: utf-8 -*-
import io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
import re
for m in re.finditer(r"высочайш\w+ (гора|горы|вулкан|вулкана)", html):
    s=max(0,m.start()-400); e=min(len(html),m.end()+200)
    seg = re.sub(r"<[^>]+>"," ",html[s:e]); seg=re.sub(r"\s+"," ",seg)
    print("CONTEXT:", seg[:700]); print()
# og:description
m=re.search(r'og:description"\s*content="([^"]*)"', html)
if m: print("og:description:", m.group(1))
