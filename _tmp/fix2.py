# -*- coding: utf-8 -*-
# Корректорская правка description.md (TP-4201530) по SKILL.md proofreading.
# 1) &nbsp; --- только после ОДНОБУКВЕННЫХ слов (в, с, и, о, у, а) и в сокращениях
#    к.&nbsp;ф.&nbsp;н. / н.&nbsp;с. и в числах (26&nbsp;сентября). После «на», «об», «до»,
#    «от», «по», «из», «за», «но», «не», «как», «при», «Что» и слов из 2+ букв nbsp НЕ ставится.
# 2) ё -> е (в тексте ё нет).
# 3) Тире: смысловое — U+2014; интервал – U+2013; дефис - ASCII.
# 4) Кавычки «ёлочки» «-» (U+00AB U+00BB) и „лапки“ — только ёлочки.
# 5) KLBLOCK на месте.
# Лог пишется в UTF-8 файл (не в консоль).

import io, re, sys, os
from collections import Counter

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\fix2.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x):
    L.append(x)

log("=== АУДИТ ДО ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("на&nbsp;: %d" % s.count("на&nbsp;"))
log("об&nbsp;: %d" % s.count("об&nbsp;"))
log("Что&nbsp;: %d" % s.count("Что&nbsp;"))
log("Павел&nbsp;: %d" % s.count("Павел&nbsp;"))
log("Владислав&nbsp;: %d" % s.count("Владислав&nbsp;"))
log("Родион&nbsp;: %d" % s.count("Родион&nbsp;"))
log("ё ВСЕГО: %d" % len(re.findall(u"[ёЁ]", s)))
log("")
log("все nbsp после слов из 2+ букв (нарушения):")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("  ВСЕГО: %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("    %d x %s" % (c, w))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s.count("KLBLOCK"))
log("")
log("=== ПРАВКИ ===")
log("")

# --- 1) убрать nbsp после слов из 2+ букв (нарушения) ---
s = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)

# --- 2) к.ф.н. / н.с. -> через nbsp (в HTML-коде) ---
#    (в текстовых полях п.1 и тексте описания — обычные пробелы, НО в сокращениях
#     к.ф.н./н.с. nbsp сохраняем; здесь уже есть к.&nbsp;ф.&nbsp;н. — оставляем)
#    после шага 1 регэксп мог разбить к.&nbsp;ф.&nbsp;н. — нет, он действует на слово+&nbsp;, не на "к.".

# --- 3) ё -> е ---
s = re.sub(u"[ёЁ]", u"е", s)

log("применено: убраны nbsp после слов из 2+ букв; ё -> е (если были)")
log("")

after = s
with io.open(SRC, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(after)

# --- аудит после ---
log("=== АУДИТ ПОСЛЕ ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % after.count("&nbsp;"))
log("на&nbsp;: %d" % after.count("на&nbsp;"))
log("об&nbsp;: %d" % after.count("об&nbsp;"))
log("Что&nbsp;: %d" % after.count("Что&nbsp;"))
log("ё ВСЕГО: %d" % len(re.findall(u"[ёЁ]", after)))
log("")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", after)
log("нарушений nbsp после слов из 2+ букв: %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("    %d x %s" % (c, w))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % after.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % after.count("н.&nbsp;с."))
log("— (U+2014): %d" % after.count(u"\u2014"))
log("– (U+2013): %d" % after.count(u"\u2013"))
log("- (ASCII): %d" % after.count("-"))
log("« : %d" % after.count(u"\u00ab"))
log("» : %d" % after.count(u"\u00bb"))
log("„ : %d" % after.count(u"\u201e"))
log("“ : %d" % after.count(u"\u201c"))
log("KLBLOCK: %d" % after.count("KLBLOCK"))
log("")

with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

print("OK len=%d" % len(after))
