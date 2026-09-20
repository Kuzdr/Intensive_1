# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# слово в видимом тексте
for w in ["высочайший вулкан", "высочайшая гора", "гора Солнечной", "вулкан Солнечной"]:
    print(w, "->", w in html)
print()
# og:description полный
m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
if m: print("og-desc:", m.group(1))
print()
# og:title/og:url
for k in ["og:title","og:url"]:
    m = re.search(k+r'\s+content="([^"]*)"', html)
    print(k, "=", m.group(1) if m else "?")
