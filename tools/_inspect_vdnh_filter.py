# -*- coding: utf-8 -*-
"""Разовый осмотр DOM страницы vdnh.ru/events/: фильтры и кнопка подгрузки."""
import io
import re
import sys

sys.path.insert(0, "tools")
from cdp_read import visible_text

path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/cdp/vdnh_events_initial.html"
s = io.open(path, encoding="utf-8", errors="replace").read()

print("=== видимый текст (первые 120 строк) ===")
for line in visible_text(s).splitlines()[:120]:
    print(line)

print("\n=== теги с class, содержащим filter (первые 40) ===")
for m in list(re.finditer(r'<[^>]+class="[^"]*filter[^"]*"[^>]*>', s, re.I))[:40]:
    print(re.sub(r"\s+", " ", m.group(0))[:300])

print("\n=== Карточки событий ===")
cards = re.findall(
    r'<div[^>]+class="[^"]*events_items__card[^"]*"[\s\S]{0,4000}?'
    r'<a[^>]+href="(/events/\d+[^"]*)"', s)
print(len(cards), cards[:30])

print("\n=== фрагменты с «Фильтры» в разметке ===")
for m in list(re.finditer(r"Фильтры", s))[:10]:
    print(re.sub(r"\s+", " ", s[max(0, m.start() - 150):m.end() + 150])[:320])
