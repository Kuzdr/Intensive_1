# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()

def clean(x):
    x = re.sub(r"<[^>]+>", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x

print("== og:title ==")
m = re.search(r'og:title"\s+content="([^"]*)"', html)
print(m.group(1) if m else "?")
print()
print("== og:description (полностью) ==")
m = re.search(r'og:description"\s+content="([^"]*)"', html)
print(m.group(1) if m else "?")
print()
print("== og:url ==")
m = re.search(r'og:url"\s+content="([^"]*)"', html)
print(m.group(1) if m else "?")
print()
print("== где 'гора'/'вулкан' в видимом тексте ==")
for mm in re.finditer(r"высочайш\S+", html):
    s = max(0, mm.start()-200); e = mm.end()+120
    print("   ...", clean(html[s:e]), "\n")
