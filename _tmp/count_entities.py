# -*- coding: utf-8 -*-
# Полный построчный подсчёт сущностей в description.md (путь из glob).
# Пишет отчёт в UTF-8 файл (консольная кодировка не важна).
import io, re, os

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\entities_report.txt"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x):
    L.append(x)

log("== ФАЙЛ ==")
log("путь: %s" % SRC)
log("байт в utf-8: %d" % len(s.encode("utf-8")))
log("символов: %d" % len(s))
log("")

log("== 1) БУКВА ё (каждая, с контекстом) ==")
m = list(re.finditer(u"[ёЁ]", s))
log("ё ВСЕГО: %d" % len(m))
for x in m:
    i = x.start()
    log("  [%d] ...%s..." % (i, s[max(0, i - 20):i + 20].replace("\n", " ").replace("\r", " ")))
log("")

log("== 2) НЕРАЗБИВАЕМЫЕ ПРОБЕЛЫ ==")
m = list(re.finditer(u"&nbsp;", s))
log("&nbsp; ВСЕГО: %d" % len(m))
log("-- после двухбуквенных (нарушение по п.2) --")
m24 = list(re.finditer(u"(?:на|об|от|по|до|из|за|но|не|как|при|для|над|под|через|между)&nbsp;", s))
if m24:
    for x in m24:
        i = x.start()
        log("  [%d] ...%s..." % (i, s[max(0, i - 18):i + 22].replace("\n", " ").replace("\r", " ")))
    log("  ИТОГ нарушений: %d" % len(m24))
else:
    log("  ИТОГ нарушений: 0 (чисто)")
# две буквы + nbsp (шире — для контроля)
m2 = list(re.finditer(u"[а-яА-ЯёЁ]{2}&nbsp;", s))
log("-- две-любые-буквы + nbsp (контроль): %d --" % len(m2))
for x in m2[:25]:
    i = x.start()
    log("  [%d] ...%s..." % (i, s[max(0, i - 14):i + 18].replace("\n", " ").replace("\r", " ")))
log("")

log("== 3) БУКВЕННЫЕ СОКРАЩЕНИЯ ==")
for pat, name in [(u"к\\.&nbsp;ф\\.&nbsp;н\\.", "к. ф. н."), (u"н\\.&nbsp;с\\.", "н. с."), (u"н\\.&nbsp;с\\.&nbsp;ИФ", "н. с. ИФ")]:
    log("  «%s» (через nbsp): %d" % (name, len(re.findall(pat, s))))
log("")

log("== 4) ТИРЕ/ДЕФИС ==")
log("— (U+2014, длинное): %d" % s.count(u"\u2014"))
log("– (U+2013, короткое): %d" % s.count(u"\u2013"))
log("- (ASCII): %d" % s.count("-"))
log("")

log("== 5) КАВЫЧКИ ==")
log("« : %d" % s.count(u"\u00ab"))
log("» : %d" % s.count(u"\u00bb"))
log("„ : %d" % s.count(u"\u201e"))
log('" (ASCII): %d' % s.count('"'))
log("")

log("== 6) KLBLOCK ==")
m = list(re.finditer(u"KLBLOCK", s))
log("KLBLOCK ВСЕГО: %d" % len(m))
for x in m:
    i = x.start()
    log("  [%d] ...%s..." % (i, s[max(0, i - 10):i + 45].replace("\n", " ").replace("\r", " ")))
log("")

with io.open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("OK: %s" % OUT)
