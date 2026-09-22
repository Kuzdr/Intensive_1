# -*- coding: utf-8 -*-
# v8: точечная коррекция _tmp/description_fixed.md (TP-4201530) по чек-листу.
# Правки:
#   1) формальные поля (текст): убрать <br> в конце каждой строки;
#   2) nbsp перед «—», после «—» обычный пробел;
#   3) в описаниях АВТОРОВ (раздел 5) расшифровать к.&nbsp;ф.&nbsp;н. ->
#      кандидат филологических наук, н.&nbsp;с. -> научный сотрудник
#      (и в читаемом тексте, и в HTML); в описании СОБЫТИЯ (раздел 1/описание)
#      сокращения ОСТАВИТЬ.
# Выход: _tmp/_v8.md ; лог: _tmp/_v8.log (оба UTF-8).
import io, re, os
from collections import Counter

ROOT = u"C:/_PROJ/Zerocoder/Intensiv_1"
SRC  = ROOT + u"/_tmp/description_fixed.md"
OUT  = ROOT + u"/_tmp/_v8.md"
LOG  = ROOT + u"/_tmp/_v8.log"

with io.open(SRC, "r", encoding="utf-8") as f:
    s = f.read()

L = []
def log(x): L.append(x)

log(u"=== ИСХОДНИК (файл на диске) ===")
log(u"&nbsp; ВСЕГО: %d" % s.count(u"&nbsp;"))
log(u"на&nbsp;: %d" % s.count(u"на&nbsp;"))
log(u"об&nbsp;: %d" % s.count(u"об&nbsp;"))
log(u"Что&nbsp;: %d" % s.count(u"Что&nbsp;"))
log(u"Павел&nbsp;: %d" % s.count(u"Павел&nbsp;"))
log(u"Денис&nbsp;: %d" % s.count(u"Денис&nbsp;"))
log(u"Владислав&nbsp;: %d" % s.count(u"Владислав&nbsp;"))
log(u"Родион&nbsp;: %d" % s.count(u"Родион&nbsp;"))
log(u"ё: %d" % len(re.findall(u"[ёЁ]", s)))
log(u"nbsp после слов из 2+ букв (нарушения): %d" %
    len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)))
log(u"")
log(u"к.&nbsp;ф.&nbsp;н.: %d" % s.count(u"к.&nbsp;ф.&nbsp;н."))
log(u"н.&nbsp;с.: %d" % s.count(u"н.&nbsp;с."))
log(u"KLBLOCK: %d" % s.count(u"KLBLOCK"))
log(u"")

# ============ ПРАВКА 1: убрать <br> в конце строк формальных полей ============
s1 = re.sub(u"<br>\\r?\\n", u"\\n", s)
log(u"ПРАВКА 1: убраны <br> в конце строк; <br> осталось: %d" %
    len(re.findall(u"<br>\\r?\\n", s1)))
log(u"")
log(u"  ПРОВЕРКА nbsp после слов из 2+ букв ПОСЛЕ правки 1: %d" %
    len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s1)))
log(u"")

# ============ ПРАВКА 2: nbsp перед «—» (не после) ============
s2 = re.sub(u"(\\s)—", u"\\1&nbsp;—", s1)
log(u"ПРАВКА 2: nbsp перед «—». Проверка:")
log(u"  &nbsp;— (правильно): %d" % s2.count(u"&nbsp;—"))
log(u"  —&nbsp; (нарушение, после тире nbsp): %d" % s2.count(u"—&nbsp;"))
log(u"  обычный пробел перед — (должно быть 0): %d" %
    len(re.findall(u"[\\s]—", s2)))
log(u"")

# ============ ПРАВКА 3: расшифровка сокращений в описаниях АВТОРОВ ============
# Это НЕ пересоздание: строки разделов 5.x остаются, правим только 5.x.4-поля.
# Найдём раздел 5 (авторы). Формат из описания выше:
#   "5.1.4. К.ф.н., доцент ...". В HTML тоже ("- 5.2.4 ...").

i5 = s2.find(u"## 5.")
if i5 >= 0:
    j5 = s2.find(u"\n", i5)
    head = s2[:j5]
    tail = s2[j5:]
    log(u"ПРАВКА 3: раздел 5 найден (с %d)" % i5)
    c_k = tail.count(u"К.ф.н.")
    c_n = tail.count(u"н.&nbsp;с.")
    # в HTML-формах сокращения с nbsp:
    a_k_html = tail.count(u"к.&nbsp;ф.&nbsp;н.")
    a_n_html = tail.count(u"н.&nbsp;с.")
    tail2 = tail.replace(u"К.ф.н.", u"кандидат филологических наук")
    tail2 = tail2.replace(u"к.&nbsp;ф.&nbsp;н.", u"кандидат филологических наук")
    tail2 = tail2.replace(u"н.&nbsp;с.", u"научный сотрудник")
    s3 = head + tail2
    log(u"  К.ф.н. в разделе 5 до: %d" % c_k)
    log(u"  к.&nbsp;ф.&nbsp;н. в разделе 5 до: %d" % a_k_html)
    log(u"  н.&nbsp;с. в разделе 5 до: %d" % a_n_html)
    log(u"  После: кандидат филологических наук: %d" %
        s3.count(u"кандидат филологических наук"))
    log(u"  После: научный сотрудник: %d" % s3.count(u"научный сотрудник"))
    log(u"  Осталось к.&nbsp;ф.&nbsp;н. в разделе 5: %d" %
        tail2.count(u"к.&nbsp;ф.&nbsp;н."))
    log(u"  Осталось н.&nbsp;с. в разделе 5: %d" % tail2.count(u"н.&nbsp;с."))
    log(u"  (в описании СОБЫТИЯ сокращения НЕ трогаем — они в разделе 1/опис.)")
else:
    s3 = s2
    log(u"ПРАВКА 3: раздел 5 НЕ найден — пропущено")

log(u"")

# ============ ПРАВКА 4: убрать ё (после правки выше, вторично) ============
# Первичная правка ё была в ранних версиях; здесь контроль:
s4 = s3
if u"ё" in s4 or u"Ё" in s4:
    s4 = re.sub(u"[ёЁ]", u"е", s4)
    log(u"ПРАВКА 4: ё->е; осталось ё: %d" % len(re.findall(u"[ёЁ]", s4)))
else:
    log(u"ПРАВКА 4: ё нет (0) — ок")

log(u"")

# ============ ПРАВКА 5: контроль кавычек и KLBLOCK ============
log(u"ПРАВКА 6 (контроль):")
log(u"  «ёлочек» нач/кон: %d/%d" % (s4.count(u"«"), s4.count(u"»")))
log(u"  „лапок“: %d" % s4.count(u"„"))
log(u"  KLBLOCK: %d" % s4.count(u"KLBLOCK"))
log(u"  ё: %d" % len(re.findall(u"[ёЁ]", s4)))
log(u"  nbsp после слов из 2+ букв (нарушения, финал): %d" %
    len(re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s4)))
log(u"")

# ============ Запись ============
with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
    f.write(s4)
with io.open(LOG, "w", encoding="utf-8") as f:
    f.write(u"\n".join(L) + u"\n")

print(u"OK OUT=%s" % OUT)
print(u"OK LOG=%s" % LOG)
