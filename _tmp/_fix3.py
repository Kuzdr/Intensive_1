# -*- coding: utf-8 -*-
# Читает description.md (TP-4201530), применяет корректорские правки и
# записывает исправленную версию в НОВЫЙ файл _tmp/description_fixed.md.
# Лог — отдельный UTF-8 файл _tmp/_fix3.log (консоль не используется).

import io, re

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\description_fixed.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\_fix3.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(x)

log("=== ИСХОДНЫЙ ФАЙЛ: %d символов ===" % len(s))
log("")

# Правки:
# 1) &nbsp; после слов из 2+ букв (кроме чисел и сокращений с точкой) -> обычный пробел
s = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)

# 2) Буквенные сокращения: «к. ф. н.», «н. с.», «к.ф.н.», «н.с.» -> через nbsp
s = s.replace(u"к.&nbsp;ф.&nbsp;н.", u"к.&nbsp;ф.&nbsp;н.")
s = s.replace(u"н.&nbsp;с.", u"н.&nbsp;с.")
s = s.replace(u"к.ф.н.", u"к.&nbsp;ф.&nbsp;н.")
s = s.replace(u"н.с.", u"н.&nbsp;с.")

# 3) ё -> е (в файле смыслоразличительных нет)
s = re.sub(u"[ёЁ]", u"е", s)

# 4) Тире и кавычки — на месте, не трогаем.

# Проверка KLBLOCK: должен стоять после шапки, до blockquote. Если нет — вставить.
if "KLBLOCK" not in s:
    m = re.search(u"(<p class=\"small\">.*?</p>)", s, re.S)
    if m:
        s = s[:m.end()] + u"\n\n<KLBLOCK eltclub_authors_about/>" + s[m.end():]
        log("KLBLOCK: добавлен после шапки")
else:
    log("KLBLOCK: уже есть")

log("")
log("=== АУДИТ ПОСЛЕ ПРАВКИ ===")
log("")
log("&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log("нарушения (nbsp после слов из 2+ букв): %d" % len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)))
log("ё: %d" % len(re.findall(u"[ёЁ]", s)))
log("к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log("KLBLOCK: %d" % s.count("KLBLOCK"))

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print("OK", OUT)
