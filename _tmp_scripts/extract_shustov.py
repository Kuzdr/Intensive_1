# -*- coding: utf-8 -*-
"""Одноразовый извлекатель данных лекции Шустова (временный)."""
import re
import sys
import urllib.request
import html as html_mod

sys.stdout.reconfigure(encoding="utf-8")

URL = "https://www.pryamaya.ru/vsevolod_sustov_kak_vzlomat_kul_turnyj_kod_aponii_14_12_2026"
UA = "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"
req = urllib.request.Request(URL, headers={"User-Agent": UA})
raw = urllib.request.urlopen(req, timeout=45).read().decode("utf-8", errors="replace")
open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_shustov.html", "w", encoding="utf-8").write(raw)
print("LEN=", len(raw))


def prop(k):
    m = re.search(r'property="' + k + r'" content="(.*?)"', raw, re.S)
    return html_mod.unescape(m.group(1)) if m else "?"


def meta(k):
    m = re.search(r'name="' + k + r'" content="(.*?)"', raw, re.S)
    return html_mod.unescape(m.group(1)) if m else "?"


for k in ("og:title", "og:description", "og:url"):
    print(k, "=", prop(k))
for k in ("datePublished", "priceAmount", "address"):
    print(k, "=", meta(k))

# JSON-LD
for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', raw, re.S):
    print("--- JSON-LD ---")
    print(m.group(1).strip()[:4000])

# lectureDetails: ищем各种 вхождений
for pat in (r'lectureDetails\s*=\s*(\{.*?\});', r'"lectureDetails"\s*:\s*(\{.*?\})\s*[,}]',
            r'lectureDetails[^=]*=\s*(\{.*\})'):
    m = re.search(pat, raw, re.S)
    if m:
        print("--- lectureDetails (pat %s) ---" % pat[:20])
        print(m.group(1)[:8000])
        break
else:
    idx = raw.find("lectureDetails")
    print("lectureDetails idx =", idx)
    if idx >= 0:
        print(raw[idx:idx + 6000])
