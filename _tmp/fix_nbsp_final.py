# -*- coding: utf-8 -*-
# Корректор description.md (TP-4201530): во ВСЁМ файле убирает
# &nbsp; после слов из 2+ букв («на&nbsp;», «об&nbsp;», «Что&nbsp;», «Павел&nbsp;» и т.п.),
# НЕ трогает: после однобуквенных (в, с, о, и, к, у, а), к.&nbsp;ф.&nbsp;н.,
# н.&nbsp;с., и nbsp после чисел (26&nbsp;сентября). Результат — в НОВЫЙ файл.
import io, os, re
from collections import Counter

SRC = r"C:/_PROJ/Zerocoder/Intensiv_1/data/prototypes/TP-4201530/description.md"
OUT = r"C:/_PROJ/Zerocoder/Intensiv_1/_tmp/description_fixed_final.md"
LOG = r"C:/_PROJ/Zerocoder/Intensiv_1/_tmp/fix_audit_final.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def lg(x): L.append(x)

lg("АУДИТ ДО ПРАВКИ (по файлу с диска)")
lg("")
lg("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
lg("на&nbsp;: %d" % s.count("на&nbsp;"))
lg("об&nbsp;: %d" % s.count("об&nbsp;"))
lg("Что&nbsp;: %d" % s.count("Что&nbsp;"))
lg("Павел&nbsp;: %d" % s.count("Павел&nbsp;"))
lg("Денис&nbsp;: %d" % s.count("Денис&nbsp;"))
lg("ё: %d" % len(re.findall(u"[ёЁ]", s)))
lg("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
lg("nbsp после слов из 2+ букв (НАРУШЕНИЯ): %d" % len(m))
for w, c in sorted(Counter(m).items()):
    lg("   %d x %s" % (c, w))
lg("")
lg("из них:")
lg("   на&nbsp;: %d" % len(re.findall(u"на&nbsp;", s)))
lg("   об&nbsp;: %d" % len(re.findall(u"об&nbsp;", s)))
lg("   Что&nbsp;: %d" % len(re.findall(u"Что&nbsp;", s)))
lg("   Павел&nbsp;: %d" % len(re.findall(u"Павел&nbsp;", s)))
lg("   Денис&nbsp;: %d" % len(re.findall(u"Денис&nbsp;", s)))
lg("   Владислав&nbsp;: %d" % len(re.findall(u"Владислав&nbsp;", s)))
lg("   Родион&nbsp;: %d" % len(re.findall(u"Родион&nbsp;", s)))
lg("")
lg("к.&nbsp;ф.&nbsp;н.: %d (правильно)" % s.count("к.&nbsp;ф.&nbsp;н."))
lg("н.&nbsp;с.: %d (правильно)" % s.count("н.&nbsp;с."))
lg("KLBLOCK: %d" % s.count("KLBLOCK"))

# ---------------- ПРАВКА ----------------
s2 = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)
s2 = re.sub(u"[ёЁ]", u"е", s2)

lg("")
lg("АУДИТ ПОСЛЕ ПРАВКИ")
lg("")
lg("&nbsp; ВСЕГО: %d" % s2.count("&nbsp;"))
lg("на&nbsp;: %d" % s2.count("на&nbsp;"))
lg("об&nbsp;: %d" % s2.count("об&nbsp;"))
lg("Что&nbsp;: %d" % s2.count("Что&nbsp;"))
lg("Павел&nbsp;: %d" % s2.count("Павел&nbsp;"))
lg("Денис&nbsp;: %d" % s2.count("Денис&nbsp;"))
lg("ё: %d" % len(re.findall(u"[ёЁ]", s2)))
lg("")
m2 = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)
lg("nbsp после слов из 2+ букв (НАРУШЕНИЯ после правки): %d" % len(m2))
lg("")
lg("к.&nbsp;ф.&nbsp;н.: %d" % s2.count("к.&nbsp;ф.&nbsp;н."))
lg("н.&nbsp;с.: %d" % s2.count("н.&nbsp;с."))
lg("KLBLOCK: %d" % s2.count("KLBLOCK"))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print("OK. OUT:", OUT)
print("LOG:", LOG)
print("VIOL_AFTER:", len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)))
