# -*- coding: utf-8 -*-
# Доводка description.md: убрать &nbsp; после слов из 2+ букв (на, об, Что,
# Павел, Денис и т.п.) в ТЕКСТЕ и в HTML-коде. Оставить nbsp только после
# однобуквенных (в, с, к, о, у, и, а) и в сокращениях к.ф.н./н.с.
import io, re, os

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\_fix_audit.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(x)

log("=== ДО ПРАВКИ (по факту файла с диска) ===")
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
for w, c in sorted(set((x, m.count(x)) for x in m)):
    log("   %d x %s" % (c, w))

# ---------------- ПРАВКА ----------------
s2 = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)
s2 = re.sub(u"[ёЁ]", u"е", s2)

log("")
log("=== ПОСЛЕ ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s2.count("&nbsp;"))
log("на&nbsp;: %d" % s2.count("на&nbsp;"))
log("об&nbsp;: %d" % s2.count("об&nbsp;"))
log("Что&nbsp;: %d" % s2.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s2.count("Павел&nbsp;"))
log("Денис&nbsp;: %d" % s2.count("Денис&nbsp;"))
log("ё: %d" % len(re.findall(u"[ёЁ]", s2)))
log("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)
log("nbsp после слов из 2+ букв (нарушения): %d" % len(m))
for w, c in sorted(set((x, m.count(x)) for x in m)):
    log("   %d x %s" % (c, w))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s2.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s2.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s2.count("KLBLOCK"))

with io.open(SRC, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print("OK violations_after=%d" % len(m))
