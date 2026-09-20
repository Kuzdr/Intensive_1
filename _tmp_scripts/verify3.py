# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()

# og:description полностью
m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
print("OG-DESC:", m.group(1) if m else "?")
print()
# JSON-LD description полностью (последнее вхождение, не огласовка)
descs = re.findall(r'"description":"((?:[^"\\]|\\.)*?)"', html)
for i,d in enumerate(descs):
    if "Марсе" in d or "жизни" in d or "вулкан" in d or "гора" in d:
        print(f"JSONLD[{i}]:", d[:2000])
print()
# есть ли в HTML слова "гора"/"вулкан" и в каком контексте
for w in ["высочайший вулкан","высочайшая гора","высочайший вулкан Солнечной","гора","вулкан","горы"]:
    print(w, "->", html.count(w))
print()
# подзаголовок "Что мешает человеку ступить на Красную планету"
for w in ["Что мешает человеку ступить","Что мешает человеку ступить на Красную планету","Красную планету"]:
    print(w, "->", html.count(w))
print()
# большая цитата в кавычках (блок quote) — собрать все blockquote
for i,m in enumerate(re.finditer(r"<blockquote[^>]*>(.*?)</blockquote>", html, re.S),1):
    t = re.sub(r"<[^>]+>"," ",m.group(1)); t = re.sub(r"\s+"," ",t).strip()
    print(f"BLOCKQUOTE#{i}: {t[:1200]}")
