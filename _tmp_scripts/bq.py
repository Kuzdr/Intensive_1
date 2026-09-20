# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()

# ВСЕ blockquote в HTML (там большая цитата в кавычках)
print("=== BLOCKQUOTE (все) ===")
for i, m in enumerate(re.finditer(r"<blockquote[^>]*>(.*?)</blockquote>", html, re.S)):
    seg = re.sub(r"<[^>]+>", " ", m.group(1))
    seg = re.sub(r"\s+", " ", seg).strip()
    if seg:
        print(f"#{i}: {seg}")
        print()

# точный подзаголовок между названием и датой в og:title/видимом
print()
print("=== og:title ===")
m = re.search(r'og:title"\s+content="([^"]*)"', html)
print("og:title:", m.group(1) if m else "?")
