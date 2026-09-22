# -*- coding: utf-8 -*-
import io, re, os

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\audit.log"

with io.open(SRC, "r", encoding="utf-8") as f:
    s = f.read()

lines = []
def log(x):
    lines.append(x)

log("=== АУДИТ description.md (TP-4201530) ===")
log("длина: %d" % len(s))
log("")

# ---- 1. ВСЕ nbsp с контекстом ----
m = list(re.finditer(r"&nbsp;", s))
log("nbsp ВСЕГО: %d" % len(m))
for x in m:
    i = x.start()
    ctx = s[max(0, i - 22):i + 22].replace("\r", " ").replace("\n", " ")
    log("  [%d] ...%s..." % (i, ctx))
log("")

# ---- 2. АВТОМАТ-ПРОВЕРКА: nbsp после двухбуквенных предлогов/союзов ----
log("=== ПРОВЕРКА nbsp ПОСЛЕ ДВУХБУКВЕННЫХ (должно быть 0) ===")
suspects = ["на", "от", "до", "по", "из", "за", "об", "но", "не", "как",
            "что", "это", "при", "вот", "или", "уже", "все", "еще", "там", "тут"]
found = 0
for w in suspects:
    c = s.count(w + "&nbsp;")
    if c:
        found += c
        log("  НАРУШЕНИЕ %d: «%s&nbsp;»" % (c, w))
log("  итог нарушений: %d" % found)
log("")

# ---- 3. «ё» ----
log("=== «ё» ===")
mm = list(re.finditer(r"[ёЁ]", s))
log("ё ВСЕГО: %d" % len(mm))
for x in mm:
    i = x.start()
    log("  [%d] ...%s..." % (i, s[max(0, i - 12):i + 12].replace("\r", " ").replace("\n", " ")))
log("")

# ---- 4. Тире/дефис ----
log("=== ТИРЕ/ДЕФИС ===")
log("— (U+2014 em-dash): %d" % s.count("\u2014"))
log("– (U+2013 en-dash): %d" % s.count("\u2013"))
log("- (ASCII hyphen): %d" % s.count("-"))
log("")

# ---- 5. Кавычки ----
log("=== КАВЫЧКИ ===")
log("« : %d" % s.count("\u00ab"))
log("» : %d" % s.count("\u00bb"))
log("„ (лапки-откр): %d" % s.count("\u201e"))
log('" (ASCII): %d' % s.count('"'))
log("")

# ---- 6. KLBLOCK ----
log("=== KLBLOCK ===")
log("KLBLOCK всего: %d" % s.count("KLBLOCK"))
for x in re.finditer(r"KLBLOCK", s):
    i = x.start()
    log("  [%d] ...%s..." % (i, s[max(0, i - 20):i + 50].replace("\r", " ").replace("\n", " ")))
log("")

# ---- 7. Буквенные сокращения (правило: nbsp между буквами; КРОМЕ поста в ТГ) ----
log("=== БУКВЕННЫЕ СОКРАЩЕНИЯ ===")
def abbr_log(txt):
    log("к.ф.н. (без nbsp): %d ; к.&nbsp;ф.&nbsp;н. (с nbsp): %d" % (
        txt.count("к.ф.н."), txt.count("к.&nbsp;ф.&nbsp;н.")))
    log("н.с. (без nbsp): %d ; н.&nbsp;с. (с nbsp): %d" % (
        txt.count("н.с."), txt.count("н.&nbsp;с.")))
abbr_log(s)
log("")

with io.open(LOG, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print("AUDIT DONE -> %s" % LOG)
