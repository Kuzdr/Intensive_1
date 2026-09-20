# -*- coding: utf-8 -*-
import re, io

html = io.open(r"A:\Users\owen\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()

# 1. полностью og:title / og:description / og:url
print("OG-TITLE:", re.search(r'og:title"\s+content="([^"]*)"', html).group(1))
print("OG-URL:  ", re.search(r'og:url"\s+content="([^"]*)"', html).group(1))
print("OG-DESC: ", re.search(r'og:description"\s+content="([^"]*)"', html).group(1))
print()

# 2. JSON-LD description (полный)
m = re.search(r'"description":"((?:[^"\\]|\\.)*?)"', html)
if m:
    d = m.group(1).encode("utf-8").decode("unicode_escape")
    print("JSONLD-DESC:", d)
    print()

# 3. видимые абзацы описания по порядку (между названием и "Информация о мероприятии")
start = html.find("Когда-то астрономы разглядели")
end = html.find("Информация о мероприятии", start)
seg = html[start:end]
print("SEG-LEN:", len(seg))
for mm in re.finditer(r"<(p|blockquote)[^>]*>(.*?)</\1>", seg, re.S):
    tag = mm.group(1)
    t = re.sub(r"<[^>]+>", " ", mm.group(2))
    t = re.sub(r"\s+", " ", t).strip()
    if t:
        print("--- [%s] порядок: %s" % (tag, t[:600]))
        print()
