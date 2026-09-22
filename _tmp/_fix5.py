# -*- coding: utf-8 -*-
# Последняя правка. Убирает &nbsp; после слов из 2+ букв ВО ВСЁМ файле
# (и в читаемых блоках, и в HTML). Пишет результат и лог на диск (UTF-8).
import io, re, os

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
NEW = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\description_fixed_NEW.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\_audit_NEW.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(x)

log("=== ДО ПРАВКИ (факт с диска) ===")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("на&nbsp;: %d" % s.count("на&nbsp;"))
log("об&nbsp;: %d" % s.count("об&nbsp;"))
log("Что&nbsp;: %d" % s.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s.count("Павел&nbsp;"))
log("Денис&nbsp;: %d" % s.count("Денис&nbsp;"))
log("Владислав&nbsp;: %d" % s.count("Владислав&nbsp;"))
log("Родион&nbsp;: %d" % s.count("Родион&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s)))
log("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
from collections import Counter
for w, c in sorted(Counter(m).items()):
    log("   %d x %s" % (c, w))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s.count("KLBLOCK"))

# ---------------- ПРАВКА ----------------
s2 = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)

log("")
log("=== ПОСЛЕ ПРАВКИ ===")
log("&nbsp; ВСЕГО: %d" % s2.count("&nbsp;"))
log("на&nbsp;: %d" % s2.count("на&nbsp;"))
log("об&nbsp;: %d" % s2.count("об&nbsp;"))
log("Что&nbsp;: %d" % s2.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s2.count("Павел&nbsp;"))
log("Денис&nbsp;: %d" % s2.count("Денис&nbsp;"))
log("Владислав&nbsp;: %d" % s2.count("Владислав&nbsp;"))
log("Родион&nbsp;: %d" % s2.count("Родион&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s2)))
log("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("   %d x %s" % (c, w))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s2.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s2.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s2.count("KLBLOCK"))

# ---------------- ЗАПИСЬ ----------------
with io.open(NEW, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print("OK. written:", NEW)
print("log:", LOG)
