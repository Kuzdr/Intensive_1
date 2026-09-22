# -*- coding: utf-8 -*-
import io, os, re, sys

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\description_audit.txt"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x): L.append(x)
def short(x, n=45):
    x = x.replace("\r", " ").replace("\n", " ")
    return x if len(x) <= n else x[:n] + "…"

log("=== АУДИТ description.md (проход по фактическому содержимому) ===")
log("путь: %s" % SRC)
log("длина: %d" % len(s))
log("")

# 1) «ё»
log("--- Ё ---")
yo = re.findall(r"[ёЁ]", s)
log("ё ВСЕГО: %d" % len(yo))
for i, ch in enumerate(yo):
    log("  [%d] %s" % (i, ch))
log("")

# 2) все &nbsp; с контекстом
log("--- NBSP (каждый, с контекстом) ---")
m = list(re.finditer(r"&nbsp;", s))
log("nbsp ВСЕГО: %d" % len(m))
for x in m:
    i = x.start()
    log("  [%d] ...%s..." % (i, short(s[max(0,i-28):i+28])))
log("")

# 3) nbsp после двухбуквенных предлогов/союзов — отдельно
log("--- NBSP ПОСЛЕ ДВУХБУКВЕННЫХ (нарушение по п.2) ---")
badpat = [r"(?:на|об|от|по|до|из|за|но|не|как|при|то|чем|что)&nbsp;"]
cnt = 0
for pat in badpat:
    mm = re.findall(pat, s)
    if mm:
        cnt += len(mm)
        log("  ПАТТЕРН «%s»: %d" % (pat.replace("&nbsp;","&nbsp;"), len(mm)))
if cnt == 0:
    log("  НАРУШЕНИЙ 0 — ЧИСТО")
else:
    log("  ВСЕГО НАРУШЕНИЙ: %d" % cnt)
log("")

# 4) отдельные двухбуквенные + nbsp — полный перечень
log("--- ПОИСК «{[а-яёА-ЯЁ]{2}}&nbsp;» (полный) ---")
mm = re.findall(r"[а-яёА-ЯЁ]{2}&nbsp;", s)
log("найдено: %d" % len(mm))
for w in sorted(set(mm)):
    log("  %s x %d" % (w, mm.count(w)))
log("")

# 5) тире/дефис
log("--- ТИРЕ/ДЕФИС ---")
log("— (U+2014) ВСЕГО: %d" % s.count("\u2014"))
log("– (U+2013) ВСЕГО: %d" % s.count("\u2013"))
log("''- ASCII ВСЕГО: %d" % s.count("-"))
log("")

# 6) кавычки
log("--- КАВЫЧКИ ---")
log("« ВСЕГО: %d" % s.count("\u00ab"))
log("» ВСЕГО: %d" % s.count("\u00bb"))
log("„ ВСЕГО: %d" % s.count("\u201e"))
log("“ ВСЕГО: %d" % s.count("\u201c"))
log('" ASCII ВСЕГО: %d' % s.count('"'))
log("")

# 7) KLBLOCK
log("--- KLBLOCK ---")
log("KLBLOCK ВСЕГО: %d" % s.count("KLBLOCK"))
for x in re.finditer(r"KLBLOCK", s):
    i = x.start()
    log("  [%d] ...%s..." % (i, short(s[max(0,i-15):i+30])))
log("")

# 8) KLBLOCK-компонент
log("--- KLBLOCK-компонент ---")
for c in ["eltclub_authors_about", "eltclub_authors_about", "KLBLOCK"]:
    log("  «%s»: %d" % (c, s.count(c)))
log("")

# 9) результирующая статистика
log("--- ИТОГ ---")
log("nbsp ВСЕГО: %d (из них нарушений после двухбуквенных: %d)" % (len(m), cnt))
log("ё: %d | —: %d | –: %d | «: %d | »: %d | „: %d | \"ascii: %d" % (
    len(yo), s.count("\u2014"), s.count("\u2013"), s.count("\u00ab"),
    s.count("\u00bb"), s.count("\u201e"), s.count('"')))
log("KLBLOCK: %d (компонент eltclub_authors_about: %d)" % (
    s.count("KLBLOCK"), s.count("eltclub_authors_about")))

with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("AUDIT -> %s" % LOG)
