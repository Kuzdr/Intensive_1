# -*- coding: utf-8 -*-
# ТОЧЕЧНАЯ правка description.md по замечаниям:
#   п.2 корректорского скилла: nbsp — ТОЛЬКО после однобуквенных слов (в, с, к, о, у, и, а),
#   после чисел и в сокращениях к.&nbsp;ф.&nbsp;н. / н.&nbsp;с.
#   Убираем nbsp после слов из 2+ букв: на&nbsp;, об&nbsp;, от&nbsp;, до&nbsp;, по&nbsp;, из&nbsp;, за&nbsp;, но&nbsp;, как&nbsp;, при&nbsp;, Что&nbsp;, Павел&nbsp; и т.п. -> обычный пробел.
# Файл НЕ пересоздаётся, правится на месте. Лог — в UTF-8 файл на диск (не в консоль).

import io, re, os
from collections import Counter

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\_fix_nb2.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(x)

log("=== ДО ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("на&nbsp;: %d" % s.count("на&nbsp;"))
log("об&nbsp;: %d" % s.count("об&nbsp;"))
log("от&nbsp;: %d" % s.count("от&nbsp;"))
log("до&nbsp;: %d" % s.count("до&nbsp;"))
log("по&nbsp;: %d" % s.count("по&nbsp;"))
log("из&nbsp;: %d" % s.count("из&nbsp;"))
log("за&nbsp;: %d" % s.count("за&nbsp;"))
log("но&nbsp;: %d" % s.count("но&nbsp;"))
log("при&nbsp;: %d" % s.count("при&nbsp;"))
log("как&nbsp;: %d" % s.count("как&nbsp;"))
log("Что&nbsp;: %d" % s.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s.count("Павел&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s)))
log("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("   %d x %s" % (c, w))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s.count("KLBLOCK"))
log("")

# ---------------- ПРАВКА ----------------
# nbsp после слов из 2+ букв -> обычный пробел (но НЕ трогаем «к.&nbsp;ф.&nbsp;н.»/«н.&nbsp;с.» —
# они начинаются с «к.»/«н.» однобуквенных, и nbsp там оставляем).
# Также не трогаем nbsp после ЦИФР (26&nbsp;сентября) — там число.
s2 = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)
# ё -> е (в файле смыслоразличительных нет)
s2 = re.sub(u"[ёЁ]", u"е", s2)

log("=== ПОСЛЕ ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s2.count("&nbsp;"))
log("на&nbsp;: %d" % s2.count("на&nbsp;"))
log("об&nbsp;: %d" % s2.count("об&nbsp;"))
log("Что&nbsp;: %d" % s2.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s2.count("Павел&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s2)))
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("   %d x %s" % (c, w))
log("к.&nbsp;ф.&nbsp;н.: %d" % s2.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s2.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s2.count("KLBLOCK"))
log("«: %d" % s2.count(u"\u00ab"))
log("»: %d" % s2.count(u"\u00bb"))
log("—: %d" % s2.count(u"\u2014"))
log("–: %d" % s2.count(u"\u2013"))
log("-: %d" % s2.count("-"))
log("")

# ---------------- ЗАПИСЬ ----------------
with io.open(SRC, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print("OK nbsp_2+=" + str(len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2))) + " log=" + LOG)
