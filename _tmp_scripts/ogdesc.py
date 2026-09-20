# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# og:description полностью
m = re.search(r'property="og:description"\s+content="([^"]*)"|<meta[^>]+property="og:description"[^>]+>', html)
if m:
    g = m.group(1) if m.lastindex else m.group(0)
    print("OG-DESC:", g.encode("unicode_escape").decode()[:1500])
    print()
# JSON-LD description полностью (unicode-экраны)
for mm in re.finditer(r'"description":"((?:[^"\\]|\\.)*?)"', html):
    d = mm.group(1)
    print("JSONLD-DESC:", d[:1600])
    print()
