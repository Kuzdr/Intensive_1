# -*- coding: utf-8 -*-
# Корректор description.md (TP-4201530): берёт HTML-блоки и убирает
# &nbsp; после слов из 2+ букв («на&nbsp;», «об&nbsp;», «Что&nbsp;» и т.п.),
# оставляя nbsp только после однобуквенных и в сокращениях
# к.&nbsp;ф.&nbsp;н. / н.&nbsp;с. Результат пишет в НОВЫЙ файл.
import io, re, os
from collections import Counter

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\description_fixed.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\fix_audit.txt"

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
log("Денис&nbsp;: %d" % s.count("Денис&nbsp;"))
log("Владислав&nbsp;: %d" % s.count("Владислав&nbsp;"))
log("Родион&nbsp;: %d" % s.count("Родион&nbsp;"))
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
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print("OK. written:", OUT)
print("Итог: nbsp после слов из 2+ букв = %d" % len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)))
