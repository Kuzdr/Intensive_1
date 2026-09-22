# -*- coding: utf-8 -*-
# Корректор description.md (TP-4201530) по п.2 proofreading-скилла.
# Убирает &nbsp; после слов из 2+ букв (на&nbsp;, об&nbsp;, Что&nbsp;, Павел&nbsp; и т.п.)
# во ВСЁМ файле. Оставляет:
#   - nbsp после однобуквенных (в, с, о, и, к, у, а) — 57 шт;
#   - nbsp в сокращениях: к.&nbsp;ф.&nbsp;н. (10), н.&nbsp;с. (5), к.&nbsp;ф.&nbsp;н.;
#   - nbsp после чисел (26&nbsp;сентября и т.д.).
# ё -> е. Результат: НОВЫЙ файл description_fixed.md + лог (оба UTF-8, на диск).

import io, re, os
from collections import Counter

ROOT = "C:/_PROJ/Zerocoder/Intensiv_1"
SRC  = ROOT + "/data/prototypes/TP-4201530/description.md"
OUT  = ROOT + "/_tmp/description_fixed.md"
LOG  = ROOT + "/_tmp/fix_nbsp3.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(str(x))

log("=== АУДИТ ДО ПРАВКИ ===")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("на&nbsp;: %d" % s.count("на&nbsp;"))
log("об&nbsp;: %d" % s.count("об&nbsp;"))
log("Что&nbsp;: %d" % s.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s.count("Павел&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s)))
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("   %d x %s" % (c, w))
log("")

# ---------------- ПРАВКА ----------------
s2 = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)
s2 = re.sub(u"[ёЁ]", u"е", s2)

log("=== АУДИТ ПОСЛЕ ПРАВКИ ===")
log("&nbsp; ВСЕГО: %d" % s2.count("&nbsp;"))
log("на&nbsp;: %d" % s2.count("на&nbsp;"))
log("об&nbsp;: %d" % s2.count("об&nbsp;"))
log("Что&nbsp;: %d" % s2.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s2.count("Павел&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s2)))
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s2.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s2.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s2.count("KLBLOCK"))

# ---------------- ЗАПИСЬ ----------------
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print("OK")
print("OUT:", OUT)
print("LOG:", LOG)
print("VIOL_AFTER:", len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)))
