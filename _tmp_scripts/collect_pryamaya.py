# -*- coding: utf-8 -*-
"""Одноразовый сборщик полей «Прямой речи» (лекция Шрайбер). Временный —
живёт в `_tmp_scripts\`, стирается после подтверждения прототипа."""

import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

SRC = r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_shraiber.html"
raw = open(SRC, encoding="utf-8").read()


def meta(name):
    m = re.search(r'name="' + name + r'" content="(.*?)"', raw, re.S)
    return m.group(1) if m else "?"


def prop(name):
    m = re.search(r'property="' + name + r'" content="(.*?)"', raw, re.S)
    return m.group(1) if m else "?"


print("og:title        =", prop("og:title"))
print("og:url          =", prop("og:url"))
print("datePublished   =", meta("datePublished"))
print("priceAmount     =", meta("priceAmount"))
print("address_visible =", meta("address"))
m = re.search(r'"eventPlace":"(.*?)"', raw)
print("eventPlace      =", m.group(1) if m else "?")
m = re.search(r'"address":\s*"([^"]*)"', raw)
print("address_field   =", m.group(1) if m else "?")

# цены, которые глазом видны на странице
for mm in re.finditer(r"(\d{3,4})\s?(?:руб|₽)", raw):
    print("visible_price   =", mm.group(1))
# цена в JSON-LD / microdata
for pat in [r'itemprop="price" content="(\d+)"', r'priceAmount[^>]*content="(\d+)"']:
    mm = re.search(pat, raw)
    print("priceRate       =", mm.group(1) if mm else "?")

# написание фамилии автора в видимом тексте (ищем варианты)
for variant in ["Шрайбер", "Шрайбер", "Шрайбэр", "Шрейбер", "Ўрайбер"]:
    n = len(re.findall(variant, raw))
    if n:
        print("name_variant    =", variant, "x", n)
