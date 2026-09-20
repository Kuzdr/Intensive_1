# -*- coding: utf-8 -*-
"""Вытащить из pryamaya_surdin.html поля для прототипа «Прямой речи»."""
import re, io, datetime

SRC = r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\surdin_report.txt"

raw = io.open(SRC, encoding="utf-8").read()
rpt = []

def prop(k):
    m = re.search(r'property="' + k + r'"\s+content="(.*?)"', raw, re.S)
    if m:
        return m.group(1).strip()
    m = re.search(r'content="(.*?)"\s+property="' + k + r'"', raw, re.S)
    return m.group(1).strip() if m else "?"

rpt.append("og:title        = " + prop("og:title"))
rpt.append("og:url          = " + prop("og:url"))
rpt.append("og:description  = " + prop("og:description"))
rpt.append("")

# день недели по og:url / startDate
for pat in [r'"startDate":"([^"]+)"', r'itemprop="startDate"\s+content="([^"]+)"',
            r'(\d{2}\.\d{2}\.\d{4})', r'(\d{4}-\d{2}-\d{2})']:
    m = re.search(pat, raw)
    if m:
        s = m.group(1)
        dt = None
        for fmt in ["%d.%m.%Y", "%Y-%m-%d"]:
            try:
                dt = datetime.datetime.strptime(s[:10], fmt)
                break
            except ValueError:
                pass
        if dt:
            rpt.append("ДАТА: " + s + "  день_недели=" + dt.strftime("%A") +
                       " (" + dt.strftime("%d.%m.%Y") + ")")
        break
rpt.append("")

# JSON-LD (цена) — обычно в конце рядом с "price"
for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S):
    txt = m.group(1)
    if "Price" in txt or "price" in txt or "Offer" in txt:
        rpt.append("--- JSON-LD (с ценой) ---")
        rpt.append(txt.strip()[:1200])
        rpt.append("")
        break

# цена в видимом тексте
prices = re.findall(r'([\d\s]{2,6})\s*руб', raw)
seen = set()
rpt.append("цены в тексте:")
for p in prices[:10]:
    p2 = re.sub(r"\s+", " ", p).strip()
    if p2 not in seen:
        seen.add(p2)
        rpt.append("  " + p2 + " руб.")
rpt.append("")

# онлайн/офлайн, адрес
for kw in ["ОНЛАЙН", "онлайн", "Ермолаев", "Москва,", "Прямая речь"]:
    rpt.append("kw [%s] = %d" % (kw, len(re.findall(re.escape(kw), raw))))
rpt.append("")

# видимый текст: вычистить HTML, показать вокруг даты/анонса
body = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
body = re.sub(r"<[^>]+>", " ", body)
body = re.sub(r"&nbsp;|&#160;|\xa0", " ", body)
body = re.sub(r"&\w+;", " ", body)
body = re.sub(r"\s+", " ", body)
i = body.find("Марс")
rpt.append("=== Видимый текст (фрагмент) ===")
rpt.append(body[max(0, i-300): i+2500])

io.open(OUT, "w", encoding="utf-8").writelines(l + "\n" for l in rpt)
print("ok, символов:", sum(len(l) for l in rpt))
