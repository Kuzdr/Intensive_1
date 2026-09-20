# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# найти большие цитаты-кавычки целиком с тегами
for m in re.finditer(r"<div[^>]*class=\"[^\"]*quote[^\"]*\"[^>]*>(.*?)</div>", html, re.S):
    seg = m.group(1)
    txt = re.sub(r"<[^>]+>", " ", seg); txt = re.sub(r"\s+", " ", txt).strip()
    if txt and len(txt) > 2:
        print("QUOTE-CLASS:", m.group(0)[:0])
        # покажем имена классов
        cls = re.search(r'class="([^"]*)"', m.group(0))
        print("  class =", cls.group(1) if cls else "?")
        print("  TEXT:", txt[:400])
        print()
