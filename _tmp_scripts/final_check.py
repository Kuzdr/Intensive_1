# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# 1) все og: и meta description, которые пишут про гору/вулкан
for key in ["og:description"]:
    m = re.search(r'property="%s"\s+content="([^"]*)"' % key, html)
    print(key, "=>", m.group(1) if m else "?")
print()
# JSON-LD summary/description поля
for f in ["description","summary"]:
    m = re.search(r'"%s":"((?:[^"\\]|\\.)*)"' % f, html)
    if m:
        print(f, "=>", m.group(1)[:1200])
        print()
# видимый текст события (первый абзац и цитата)
seg = html[html.find("Когда-то астрономы"):html.find("Рекомендуемый возраст")]
plain = re.sub(r"<[^>]+>", " ", seg)
plain = re.sub(r"\s+", " ", plain).strip()
print("VISIBLE-FULL:", plain)
print()
# абзац об авторе полностью
m = re.search(r"Владимир Сурдин — астроном и популяризатор науки\..*?книг по астрономии и астрофизике\.", plain)
print("AUTHOR-PARA:", m.group(0) if m else "?")
