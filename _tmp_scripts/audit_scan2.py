# -*- coding: utf-8 -*-
"""Второй скан: ВСЕ строки с маркерами пробелов + полный HTML."""
import io
import json

P = r"data/prototypes/PR-261214-Shustov-Kulturnyj-kod-Yaponii/prototype.json"
d = json.load(io.open(P, encoding="utf-8"))

def mark(s):
    return s.replace("\u00a0", "҂").replace("&nbsp;", "⍽").replace(" ", "␣")

print("=== ВСЕ ПОЛЯ (пробелы ␣/⍽) ===")
for f in d.get("fields", []):
    print(" [%s] %s" % (f["n"], mark(f.get("value") or "")))
print(" title :", mark(d.get("title") or ""))
print(" annot :", mark(d.get("annot") or ""))
print(" price :", mark(d.get("price_short") or ""))
print()
print("=== DESC_HTML (пробелы ␣/⍽) ===")
for i, line in enumerate(d.get("desc_html", "").split("\n"), 1):
    print("%3d| %s" % (i, mark(line)))
print()
print("=== EXTRA_HTML (пробелы ␣/⍽) ===")
for j, x in enumerate(d.get("extra_html") or []):
    print(" -- extra[%d] --" % j)
    for i, line in enumerate(x.split("\n"), 1):
        print("%3d| %s" % (i, mark(line)))
