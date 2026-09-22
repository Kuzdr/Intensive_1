# -*- coding: utf-8 -*-
# Читает description.md (TP-4201530), применяет корректорские правки и
# пишет результат в НОВЫЙ файл _tmp/description_fixed.md (UTF-8).
# Правило nbsp: ТОЛЬКО после однобуквенных (в, с, и, о, к, у, а) и в
# сокращениях к.&nbsp;ф.&nbsp;н. / н.&nbsp;с. После слов из 2+ букв
# (на, об, от, до, по, из, за, но, не, как, при, Что и т.д.) — обычный пробел.

import io, re, os

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\description_fixed.md"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

# 1) убираем nbsp после слов из 2+ букв (кроме чисел и цифр)
s = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)

# 2) ё -> е (в тексте смыслоразличительных нет)
s = re.sub(u"[ёЁ]", u"е", s)

# 3) контроль: KLBLOCK и сокращения оставляем как есть (они уже с nbsp)
#    к.ф.н. / н.с. уже в виде к.&nbsp;ф.&nbsp;н. / н.&nbsp;с.

with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s)

m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
print("OK. violations=%d out=%s" % (len(m), OUT))
