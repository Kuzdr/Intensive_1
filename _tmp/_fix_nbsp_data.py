# -*- coding: utf-8 -*-
import io, os, re

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\_fix_nbsp_data.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()
orig = s

L = []
def log(x):
    L.append(x)

log("СЧЁТ ПО ФАЙЛУ ДО ПРАВКИ")
log("")
log("nbsp ВСЕГО: %d" % s.count("&nbsp;"))
log("вхождений «Что&nbsp;»: %d" % s.count("Что&nbsp;"))
log("вхождений «об&nbsp;»: %d" % s.count("об&nbsp;"))
log("вхождений «на&nbsp;»: %d" % s.count("на&nbsp;"))
a = re.findall(r"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("nbsp после слова из 2+ букв (ВСЕГО): %d" % len(a))
from collections import Counter
for w, c in sorted(Counter(a).items()):
    log("   %d x [%s]" % (c, w))
log("")
log("ё ВСЕГО: %d" % len(re.findall(r"[ёЁ]", s)))
log("« ВСЕГО: %d" % s.count("\u00ab"))
log("» ВСЕГО: %d" % s.count("\u00bb"))
log("— ВСЕГО: %d" % s.count("\u2014"))
log("– ВСЕГО: %d" % s.count("\u2013"))
log("- ASCII ВСЕГО: %d" % s.count("-"))
log("KLBLOCK ВСЕГО: %d" % len(re.findall(r"KLBLOCK", s)))
log("")

# ---- ПРАВКА: после слов из 2+ букв nbsp -> обычный пробел ----
s2 = re.sub(r"([а-яА-ЯёЁ]{2,})&nbsp;", r"\1 ", s)
fixed = 0
for w, c in Counter(re.findall(r"[а-яА-ЯёЁ]{2,}&nbsp;", s)).items():
    fixed += c
log("ПРАВКА: nbsp после слов из 2+ букв заменено на обычный пробел: %d" % fixed)
log("")

with io.open(SRC, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)

# ---- повторный счёт ПО ИСПРАВЛЕННОМУ ----
log("СЧЁТ ПО ИСПРАВЛЕННОМУ")
log("")
log("nbsp ВСЕГО: %d" % s2.count("&nbsp;"))
a2 = re.findall(r"[а-яА-ЯёЁ]{2,}&nbsp;", s2)
log("nbsp после слова из 2+ букв: %d (должно быть 0)" % len(a2))
for w, c in sorted(Counter(a2).items()):
    log("   %d x [%s]" % (c, w))
log("вхождений «Что&nbsp;»: %d" % s2.count("Что&nbsp;"))
log("вхождений «об&nbsp;»: %d" % s2.count("об&nbsp;"))
log("вхождений «на&nbsp;»: %d" % s2.count("на&nbsp;"))
log("ё ВСЕГО: %d" % len(re.findall(r"[ёЁ]", s2)))
log("« ВСЕГО: %d" % s2.count("\u00ab"))
log("» ВСЕГО: %d" % s2.count("\u00bb"))
log("— ВСЕГО: %d" % s2.count("\u2014"))
log("– ВСЕГО: %d" % s2.count("\u2013"))
log("- ASCII ВСЕГО: %d" % s2.count("-"))
log("KLBLOCK ВСЕГО: %d" % len(re.findall(r"KLBLOCK", s2)))
log("")

with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("OK -> %s" % LOG)