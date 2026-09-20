# -*- coding: utf-8 -*-
"""Временный извлекатель полного описания «Прямой речи» (Шрайбер).
Одноразовый, живёт в `_tmp_scripts\`, стираем после подтверждения прототипа.
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

SRC = r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_shraiber.html"
raw = open(SRC, encoding="utf-8").read()


def meta(k):
    m = re.search(r'name="' + k + r'" content="(.*?)"', raw, re.S)
    return m.group(1) if m else "?"


def propg(k):
    m = re.search(r'property="' + k + r'" content="(.*?)"', raw, re.S)
    return m.group(1) if m else "?"


def st_meta(k):
    # schema.org в JSON-LD или микроразметке
    m = re.search(k + r'[^>]*content="(.*?)"', raw, re.S)
    return m.group(1) if m else "?"
    # microdata: <meta itemprop="priceAmount" content="3000">


print("og:title         =", propg("og:title"))
print("og:url           =", propg("og:url"))
m = re.search(r"datePublished[^>]*content=\"(.*?)\"", raw)
print("datePublished    =", m.group(1) if m else "?")
m = re.search(r"itemprop=\"(?:startDate|eventDate)\"[^>]*content=\"(.*?)\"", raw)
print("eventDate        =", m.group(1) if m else "?")
m = re.search(r"itemprop=\"priceAmount\"[^>]*content=\"(.*?)\"", raw)
print("priceAmount      =", m.group(1) if m else "?")
# ищем цены в видимом тексте
for pr in re.finditer(r"(?:(\d{4}|\d{3})\s?руб|(\d{4}|\d{3})\s?₽)", raw):
    print("price_visible    =", (pr.group(1) or pr.group(2)) + " руб.")
# длинный читаемый текст: блок аннотации (blockquote / blurb)
m = re.search(r'(?:class="[^"]*content[^"]*"|class="blurb"[^>]*>)(.*?)</(?:div|section)>',
              raw, re.S)
