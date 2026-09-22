# -*- coding: utf-8 -*-
# Читает description.md (TP-4201530), применяет корректорскую правку
# (nbsp только после однобуквенных слов/цифр и в сокращениях к.ф.н./н.с.),
# результат пишет в НОВЫЙ файл _tmp/description_fixed.md. Лог — в UTF-8 файл.
import io, re, os
from collections import Counter

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\description_fixed.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\_fix_write.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s0 = fh.read()

L = []
def log(x): L.append(x)

log("=== АУДИТ ДО ===")
log("")
log("&nbsp; ВСЕГО: %d" % s0.count("&nbsp;"))
log("на&nbsp;: %d" % s0.count("на&nbsp;"))
log("об&nbsp;: %d" % s0.count("об&nbsp;"))
log("Что&nbsp;: %d" % s0.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s0.count("Павел&nbsp;"))
log("Денис&nbsp;: %d" % s0.count("Денис&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s0)))
log("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s0)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("   %d x %s" % (c, w))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s0.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s0.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s0.count("KLBLOCK"))
log("")

# ---------------- ПРАВКА ----------------
s = s0
# nbsp после слов из 2+ букв -> обычный пробел
s = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)
# ё -> е (смыслоразличительных нет)
s = re.sub(u"[ёЁ]", u"е", s)
# оставить корректные сокращения (уже в нужном виде)
log("=== ПРАВКА ПРИМЕНЕНА ===")
log("")

# ---------------- АУДИТ ПОСЛЕ ----------------
log("=== АУДИТ ПОСЛЕ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("на&nbsp;: %d" % s.count("на&nbsp;"))
log("об&nbsp;: %d" % s.count("об&nbsp;"))
log("Что&nbsp;: %d" % s.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s.count("Павел&nbsp;"))
log("Денис&nbsp;: %d" % s.count("Денис&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s)))
log("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
log("к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s.count("KLBLOCK"))
log("")
log("длинное тире —: %d" % s.count(u"\u2014"))
log("короткое –: %d" % s.count(u"\u2013"))
log("дефис -: %d" % s.count("-"))
log("«: %d" % s.count(u"\u00ab"))
log("»: %d" % s.count(u"\u00bb"))
log("„: %d" % s.count(u"\u201e"))
log("“: %d" % s.count(u"\u201c"))

# ---------------- ЗАПИСЬ НОВОГО ФАЙЛА ----------------
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")
print("OK written:", OUT)
print("log:", LOG)
