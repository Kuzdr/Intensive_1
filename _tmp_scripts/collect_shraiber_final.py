
# -*- coding: utf-8 -*-
"""Одноразовый сборщик полей страницы «Почему время идёт только вперёд»
(«Прямая речь»). Временный: живёт в _tmp_scripts, стирается после прототипа."""
import re, sys, datetime
sys.stdout.reconfigure(encoding="utf-8")

raw = open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_shraiber.html", encoding="utf-8").read()

def prop(k):
    m = re.search(r'property="' + k + r'" content="(.*?)"', raw, re.S)
    return m.group(1) if m else "?"

def meta(k):
    m = re.search(r'name="' + k + r'" content="(.*?)"', raw, re.S)
    return m.group(1) if m else "?"

print("og:title        =", prop("og:title"))
print("og:url          =", prop("og:url"))
print("priceAmount     =", meta("priceAmount"))

# подзаголовок-шапка: поищем сценарий в jQuery "прогнозируемое время"/"ревью"
for kw in ["идёт только вперёд", "Шрайбер", "руб", "ОНЛАЙН", "Москва"]:
    hits = re.findall(kw, raw)
    print("kw:", kw, "=>", len(hits))

# день недели по дате из источника
m = re.search(r'itemprop="startDate" content="([^"]+)"', raw)
if m:
    d = datetime.date.fromisoformat(m.group(1)[:10])
    print("startDate =", m.group(1), "день_нед =", d.strftime("%A"))
else:
    # иначе в og: или событие
    m = re.search(r'\b(2026[-/.]09[-/.]21)\b', raw)
    print("rawdate =", m.group(1) if m else "?")

