# -*- coding: utf-8 -*-
import io, re, os

SRC = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
LOG = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\audit_fix.md"

with io.open(SRC, "r", encoding="utf-8") as fh:
    s = fh.read()

lines = []
def log(x):
    lines.append(x)

# ---------- правки (орфография/пунктуация по разделу 2 скилла) ----------
fixes = []

# 1) nbsp после двухбуквенного предлога «на» в названии площадки убираем
#    («на&nbsp;Газетном» -> «на Газетном»; обычный пробел после «на»,
#     nbsp оставляем только перед «Газетном»: «на&nbsp;Газетном»!)
#    НЕТ — правильная форма: «Библиотека на&nbsp;Газетном»
for pat in ["на&nbsp;Газетном", "на&nbsp;Газетном"]:
    c = s.count(pat)
    if c:
        fixes.append("%d x [%s] -> [на с обычным пробелом]" % (c, pat))
        s = s.replace(pat, "на Газетном")

# 2) буквенные сокращения — nbsp между буквами (правило пользователя)
for pat, repl in [("к.ф.н.", "к.&nbsp;ф.&nbsp;н."), ("н.с.", "н.&nbsp;с.")]:
    c = s.count(pat)
    if c:
        fixes.append("%d x [%s] -> [%s]" % (c, pat, repl))
        s = s.replace(pat, repl)

# ---------- запись ----------
with io.open(SRC, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s)

# ---------- аудит ПО ИСПРАВЛЕННОМУ ----------
log("### АУДИТ ПО ИСПРАВЛЕННОМУ")
log("")
log("СДЕЛАННЫЕ ПРАВКИ:")
log("\n".join(" - " + x for x in fixes) if fixes else " - (нет)")
log("")

# 1) все nbsp с контекстом
m = list(re.finditer(r"&nbsp;", s))
log("nbsp ВСЕГО: %d" % len(m))
for x in m:
    i = x.start()
    ctx = s[max(0, i - 25):i + 25].replace("\n", " ").replace("\r", " ")
    log("   [%d] ...%s..." % (i, ctx))
log("")

# 2) подозрительные: nbsp после двухбуквенных предлогов/союзов
for w in ["на", "от", "до", "по", "из", "за", "об", "но", "не", "как", "если",
          "что", "это", "вот", "лишь", "или", "уже", "все", "еще", "при"]:
    c = len(re.findall(re.escape(w) + r"&nbsp;", s))
    if c:
        log("НАРУШЕНИЕ? nbsp после «%s»: %d" % (w, c))
if not any(x.startswith("НАРУШЕНИЕ") for x in lines):
    log("nbsp после двухбуквенных предлогов/союзов: 0 (все корректно)")
log("")

# 3) ё
log("ё ВСЕГО: %d" % len(re.findall(r"[ёЁ]", s)))
for x in re.finditer(r"[ёЁ]", s):
    i = x.start()
    log("   [%d] ...%s..." % (i, s[max(0, i - 15):i + 15]))
log("")

# 4) тире/дефис
log("— (U+2014) ВСЕГО: %d" % s.count("\u2014"))
log("– (U+2013) ВСЕГО: %d" % s.count("\u2013"))
log("- (ASCII) ВСЕГО: %d" % s.count("-"))
log("")

# 5) кавычки
log("« (U+00AB) ВСЕГО: %d" % s.count("\u00ab"))
log("» (U+00BB) ВСЕГО: %d" % s.count("\u00bb"))
log("„ (U+201E) ВСЕГО: %d" % s.count("\u201e"))
log('" ASCII ВСЕГО: %d' % s.count('"'))
log("")

# 6) KLBLOCK
log("KLBLOCK ВСЕГО: %d" % len(re.findall(r"KLBLOCK", s)))
for x in re.finditer(r"KLBLOCK", s):
    i = x.start()
    log("   [%d] ...%s..." % (i, s[max(0, i - 30):i + 40]))
log("")

# 7) буквенные сокращения ИТОГ
log("к.&nbsp;ф.&nbsp;н. (НОРМА): %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с. (НОРМА): %d" % s.count("н.&nbsp;с."))
log("к.ф.н. (старое, без nbsp) В ИТОГЕ: %d" % s.count("к.ф.н."))
log("н.с. (старое, без nbsp) В ИТОГЕ: %d" % s.count("н.с."))
log("КАВЫЧКИ «Библиотека на&nbsp;Газетном» осталось: %d" % s.count("Библиотека на&nbsp;Газетном"))
log("КАВЫЧКИ «Библиотека&nbsp;на&nbsp;Газетном» осталось: %d" % s.count("Библиотека&nbsp;на&nbsp;Газетном"))
log("")

with io.open(LOG, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines) + "\n")
print("OK")
