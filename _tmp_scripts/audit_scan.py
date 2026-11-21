# -*- coding: utf-8 -*-
"""Разовый скан: все «ё» и все пробелы (␣ обычный / ⍽ nbsp) в тексте прототипа."""
import io
import json
import re

P = r"data/prototypes/PR-261214-Shustov-Kulturnyj-kod-Yaponii/prototype.json"
d = json.load(io.open(P, encoding="utf-8"))

chunks = []
def add(tag, value):
    if value:
        chunks.append((tag, value))

add("title", d.get("title"))
add("annot", d.get("annot"))
add("price", d.get("price_short"))
for f in d.get("fields", []):
    add("field " + f["n"] + " (" + f["name"] + ")", f.get("value"))
add("desc_html", d.get("desc_html"))
for i, x in enumerate(d.get("extra_html") or []):
    add("extra[%d]" % i, x)
for a in d.get("authors", []):
    add("author " + a.get("name", "") + " block", a.get("block_html"))
    for f in a.get("fields", []):
        add("author field " + f["n"], f.get("value"))
add("notes", d.get("notes"))

# ---- ё ----
yo = []
for tag, text in chunks:
    for m in re.finditer("ё|Ё", text):
        ctx = text[max(0, m.start()-28):m.end()+28].replace("\n", " ")
        yo.append((tag, m.group(), ctx))
print("=== ВСЕ «Ё» (%d) ===" % len(yo))
for tag, ch, ctx in yo:
    print(" [%s] %s : …%s…" % (tag, ch, ctx))

# ---- пробелы с маркерами ----
print()
print("=== СТРОКИ С ПРОБЕЛАМИ (␣=обычный, ⍽=nbsp) ===")
for tag, text in chunks:
    marked = text.replace("&nbsp;", "⍽").replace("\u00a0", "҂").replace(" ", "␣")
    # только строки, где есть ⍽ или подозрительные места
    if "⍽" in marked or "҂" in marked:
        for line in marked.split("\n"):
            if "⍽" in line or "҂" in line:
                print(" [%s] %s" % (tag, line))
