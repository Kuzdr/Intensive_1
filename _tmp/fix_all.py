# -*- coding: utf-8 -*-
# Правка description.md (TP-4201530) по корректорскому скиллу:
#  - убрать &nbsp; после слов из 2+ букв (двухбуквенные предлоги/союзы и длиннее);
#  - оставить &nbsp; только после однобуквенных («в», «с», «к», «о», «у», «и», «а»);
#  - буквенные сокращения «к.ф.н.», «н.с.» -> «к.&nbsp;ф.&nbsp;н.», «н.&nbsp;с.»;
#  - «ё» -> «е» (кроме смыслоразличительных — в файле их нет);
#  - KLBLOCK: <KLBLOCK eltclub_authors_about/> после шапки.
# Лог и статистика пишутся в UTF-8 файл.

import io, re, sys, os

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\fix_result.txt"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(x)

# ---------------- 0) АУДИТ ДО ----------------
log("=== АУДИТ ДО ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("Ё ВСЕГО: %d" % len(re.findall(u"[ёЁ]", s)))
log("на&nbsp;: %d" % s.count("на&nbsp;"))
log("об&nbsp;: %d" % s.count("об&nbsp;"))
log("от&nbsp;: %d" % s.count("от&nbsp;"))
log("до&nbsp;: %d" % s.count("до&nbsp;"))
log("по&nbsp;: %d" % s.count("по&nbsp;"))
log("из&nbsp;: %d" % s.count("из&nbsp;"))
log("за&nbsp;: %d" % s.count("за&nbsp;"))
log("но&nbsp;: %d" % s.count("но&nbsp;"))
log("не&nbsp;: %d" % s.count("не&nbsp;"))
log("как&nbsp;: %d" % s.count("как&nbsp;"))
log("при&nbsp;: %d" % s.count("при&nbsp;"))
log("Что&nbsp;: %d" % s.count("Что&nbsp;"))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log("")
log("KLBLOCK: %d" % s.count("KLBLOCK"))
log("")
log("все nbsp после слов из 2+ букв (нарушения):")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("  ВСЕГО: %d" % len(m))
from collections import Counter
for w, c in sorted(Counter(m).items()):
    log("    %d x %s" % (c, w))
log("")
log("все nbsp после ЧИСЕЛ (правильно):")
m = re.findall(u"[0-9]+&nbsp;", s)
log("  ВСЕГО: %d" % len(m))
log("")
log("все nbsp после ДВУХБУКВЕННЫХ ПРЕДЛОГОВ (нарушения):")
m = re.findall(u"(?:на|об|от|до|по|из|за|но|не|как|при)&nbsp;", s)
log("  ВСЕГО: %d" % len(m))
log("")
log("=== КОНЕЦ АУДИТА ДО ===")
log("")

# ---------------- 1) ПРАВКА ----------------
log("=== ПРАВКА ===")
log("")

before = s

# 1.1 убрать nbsp после слов из 2+ букв (кроме чисел и буквенных сокращений)
#     (регулярно: слово из >=2 кириллических букв + &nbsp; -> слово + пробел)
s = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)

# 1.2 «ё» -> «е» (у нас нет смыслоразличительных)
s = re.sub(u"[ёЁ]", u"е", s)

# 1.3 буквенные сокращения: «к.ф.н.» / «н.с.» -> через nbsp (кроме поста в ТГ —
#     в этом файле поста нет)
s = s.replace(u"к.ф.н.", u"к.&nbsp;ф.&nbsp;н.")
s = s.replace(u"н.с.", u"н.&nbsp;с.")

# 1.4 KLBLOCK — проверяем, что стоит после шапки (поле 7-8) и до blockquote.
#     Если KLBLOCK отсутствует в HTML-коде — добавляем после <p class="small">…</p>.
if "KLBLOCK" not in s:
    # вставляем после строки с «Суббота, 26&nbsp;…» или первой <p class=small>
    m = re.search(r"(<p class=\"small\">.*?</p>)", s, re.S)
    if m:
        s = s[:m.end()] + u"\n\n<KLBLOCK eltclub_authors_about/>" + s[m.end():]
        log("KLBLOCK добавлен после шапки")
    else:
        log("KLBLOCK НЕ добавлен (шапка не найдена)")
else:
    log("KLBLOCK уже есть: %d" % s.count("KLBLOCK"))

after = s
log("")
log("=== КОНЕЦ ПРАВКИ ===")
log("")

# ---------------- 2) АУДИТ ПОСЛЕ ----------------
log("=== АУДИТ ПОСЛЕ ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("Ё ВСЕГО: %d" % len(re.findall(u"[ёЁ]", s)))
log("на&nbsp;: %d" % s.count("на&nbsp;"))
log("об&nbsp;: %d" % s.count("об&nbsp;"))
log("от&nbsp;: %d" % s.count("от&nbsp;"))
log("до&nbsp;: %d" % s.count("до&nbsp;"))
log("по&nbsp;: %d" % s.count("по&nbsp;"))
log("из&nbsp;: %d" % s.count("из&nbsp;"))
log("за&nbsp;: %d" % s.count("за&nbsp;"))
log("но&nbsp;: %d" % s.count("но&nbsp;"))
log("не&nbsp;: %d" % s.count("не&nbsp;"))
log("как&nbsp;: %d" % s.count("как&nbsp;"))
log("при&nbsp;: %d" % s.count("при&nbsp;"))
log("Что&nbsp;: %d" % s.count("Что&nbsp;"))
log("")
log("все nbsp после слов из 2+ букв (нарушения после правки):")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log("  ВСЕГО: %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log("    %d x %s" % (c, w))
log("")
log("все nbsp после ДВУХБУКВЕННЫХ ПРЕДЛОГОВ (нарушения после правки):")
m = re.findall(u"(?:на|об|от|до|по|из|за|но|не|как|при)&nbsp;", s)
log("  ВСЕГО: %d" % len(m))
log("")
log("к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log("")
log("KLBLOCK: %d" % s.count("KLBLOCK"))
log("")

# ---------------- 3) ЗАПИСЬ ----------------
with io.open(SRC, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")

print("OK. written:", SRC)
print("log:", LOG)
