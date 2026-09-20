# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
print("len:", len(html))
start = html.find("Когда-то астрономы")
end = html.find("Рекомендуемый возраст", start)
seg = html[start:end]
print("segment len:", len(seg))
for mm in re.finditer(r"<(p|blockquote|div|h[1-6])[^>]*>(.*?)</\1>", seg, re.S):
    tag = mm.group(1)
    txt = re.sub(r"<[^>]+>", " ", mm.group(2))
    txt = re.sub(r"\s+", " ", txt).strip()
    if txt:
        print(f"[{tag}] {txt[:800]}")
        print()
