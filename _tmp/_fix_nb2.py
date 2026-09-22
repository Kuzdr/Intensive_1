# -*- coding: utf-8 -*-
# Корректор description.md (TP-4201530, TimePad https://iep2.timepad.ru/event/4201530/)
# Правила (раздел 2 скилла proofreading):
#   - убрать &nbsp; после слов из 2+ букв — «на&nbsp;Газетном», «на&nbsp;», «об&nbsp;»,
#     «Что&nbsp;говорит», «Павел&nbsp;», «Денис&nbsp;» и т.п. — по ВСЕМУ файлу
#     (текст + HTML + формальные поля);
#   - НЕ трогать &nbsp; после однобуквенных (в, с, о, к, и, у, а) и внутри
#     буквенных сокращений к.&nbsp;ф.&nbsp;н. / н.&nbsp;с. (по решению пользователя);
#   - «ё» при отсутствии смыслоразличения заменяем на «е»;
#   - KLBLOCK: после шапки (после формальных полей), до <blockquote>.
# Вход: C:/_PROJ/Zerocoder/Intensiv_1/data/prototypes/TP-4201530/description.md
# Выход: C:/_PROJ/Zerocoder/Intensiv_1/_tmp/description_fixed.md
# Лог:   C:/_PROJ/Zerocoder/Intensiv_1/_tmp/_fix_nb2.log
# Всё в UTF-8. Лог читается ДОПОЛНИТЕЛЬНО tool'ом Read (не из консоли).

import io, re, os
from collections import Counter

SRC = u"C:/_PROJ/Zerocoder/Intensiv_1/data/prototypes/TP-4201530/description.md"
OUT = u"C:/_PROJ/Zerocoder/Intensiv_1/_tmp/description_fixed.md"
LOG = u"C:/_PROJ/Zerocoder/Intensiv_1/_tmp/_fix_nb2.log"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(x)

log(u"=== АУДИТ ДО (по факту файла) ===")
log(u"")
log(u"&nbsp; ВСЕГО: %d" % s.count("&nbsp;"))
log(u"на&nbsp;: %d" % s.count("на&nbsp;"))
log(u"об&nbsp;: %d" % s.count("об&nbsp;"))
log(u"от&nbsp;: %d" % s.count("от&nbsp;"))
log(u"до&nbsp;: %d" % s.count("до&nbsp;"))
log(u"по&nbsp;: %d" % s.count("по&nbsp;"))
log(u"из&nbsp;: %d" % s.count("из&nbsp;"))
log(u"за&nbsp;: %d" % s.count("за&nbsp;"))
log(u"но&nbsp;: %d" % s.count("но&nbsp;"))
log(u"не&nbsp;: %d" % s.count("не&nbsp;"))
log(u"как&nbsp;: %d" % s.count("как&nbsp;"))
log(u"при&nbsp;: %d" % s.count("при&nbsp;"))
log(u"Что&nbsp;: %d" % s.count("Что&nbsp;"))
log(u"Павел&nbsp;: %d" % s.count("Павел&nbsp;"))
log(u"Денис&nbsp;: %d" % s.count("Денис&nbsp;"))
log(u"Владислав&nbsp;: %d" % s.count("Владислав&nbsp;"))
log(u"Родион&nbsp;: %d" % s.count("Родион&nbsp;"))
log(u"ё: %d" % len(re.findall(u"[ёЁ]", s)))
log(u"")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s)
log(u"nbsp после слов из 2+ букв (нарушения): %d" % len(m))
for w, c in sorted(Counter(m).items()):
    log(u"   %d x %s" % (c, w))
log(u"")
log(u"к.&nbsp;ф.&nbsp;н.: %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log(u"н.&nbsp;с.: %d" % s.count("н.&nbsp;с."))
log(u"KLBLOCK: %d" % s.count("KLBLOCK"))
log(u"")

# ---------------- ПРАВКА ----------------
s2 = re.sub(u"([а-яА-ЯёЁ]{2,})&nbsp;", u"\\1 ", s)
s2 = re.sub(u"[ёЁ]", u"е", s2)

# KLBLOCK — если нет, вставить после шапки (после формальных полей, до описания)
if "KLBLOCK" not in s2:
    m2 = re.search(u"(<p class=\"small\">.*?</p>)", s2, re.S)
    if m2:
        s2 = s2[:m2.end()] + u"\n\n<KLBLOCK eltclub_authors_about/>" + s2[m2.end():]
        log(u"KLBLOCK: добавлен после шапки")
    else:
        log(u"KLBLOCK: НЕ добавлен (шапка не найдена)")
else:
    log(u"KLBLOCK: уже есть (%d)" % s2.count("KLBLOCK"))

log(u"")
log(u"=== АУДИТ ПОСЛЕ ===")
log(u"")
log(u"&nbsp; ВСЕГО: %d" % s2.count("&nbsp;"))
log(u"на&nbsp;: %d" % s2.count("на&nbsp;"))
log(u"об&nbsp;: %d" % s2.count("об&nbsp;"))
log(u"Что&nbsp;: %d" % s2.count("Что&nbsp;"))
log(u"Павел&nbsp;: %d" % s2.count("Павел&nbsp;"))
log(u"Денис&nbsp;: %d" % s2.count("Денис&nbsp;"))
log(u"Владислав&nbsp;: %d" % s2.count("Владислав&nbsp;"))
log(u"Родион&nbsp;: %d" % s2.count("Родион&nbsp;"))
log(u"ё: %d" % len(re.findall(u"[ёЁ]", s2)))
log(u"")
m = re.findall(u"[а-яА-ЯёЁ]{2,}&nbsp;", s2)
log(u"nbsp после слов из 2+ букв (нарушения после): %d" % len(m))
log(u"")
log(u"к.&nbsp;ф.&nbsp;н.: %d" % s2.count("к.&nbsp;ф.&nbsp;н."))
log(u"н.&nbsp;с.: %d" % s2.count("н.&nbsp;с."))
log(u"KLBLOCK: %d" % s2.count("KLBLOCK"))

# ---------------- ЗАПИСЬ ----------------
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with io.open(OUT, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s2)
with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write(u"\n".join(L) + u"\n")

print(u"OK. written:", OUT)
print(u"log:", LOG)
