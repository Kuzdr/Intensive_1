import io, os, re

f = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
audit_log = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\audit_final.txt"

with io.open(f, "r", encoding="utf-8") as fh:
    s = fh.read()

L = []
def log(x):
    L.append(x)

log("АУДИТ ПЕРЕД ПРАВКОЙ")
log("")

# ————— корректирующие замены (по разделу 2 скилла) —————
RULE1_NA = [
    # nbsp после двухбуквенного предлога «на» в названии площадки — убрать
    ("Библиотека&nbsp;на&nbsp;Газетном", "Библиотека на&nbsp;Газетном"),
    ("Библиотеке&nbsp;на&nbsp;Газетном", "Библиотеке на&nbsp;Газетном"),
    ("Библиотеки&nbsp;на&nbsp;Газетном", "Библиотеки на&nbsp;Газетном"),
]
done = []
for old, new in RULE1_NA:
    c = s.count(old)
    if c:
        s = s.replace(old, new)
        done.append("%d x %s" % (c, old))

# ————— буквенные сокращения: nbsp между буквами —————
RULE_ABBR = [
    ("к.ф.н.", "к.&nbsp;ф.&nbsp;н."),
    ("н.с.", "н.&nbsp;с."),
]
for old, new in RULE_ABBR:
    c = s.count(old)
    if c:
        s = s.replace(old, new)
        done.append("%d x %s" % (c, old))

log("сделано замен: %s" % ("; ".join(done) if done else "ничего"))
log("")

# запись исправленного файла
with io.open(f, "w", encoding="utf-8", newline="\n") as fh:
    fh.write(s)

# ————— повторный полный аудит ПО ИСПРАВЛЕННОМУ —————
log("АУДИТ ПОСЛЕ ПРАВКИ (повторный проход)")
log("")

# 1) nbsp — весь список с контекстом
m = list(re.finditer(r"&nbsp;", s))
log("nbsp ВСЕГО: %d" % len(m))
for x in m:
    i = x.start()
    ctx = s[max(0, i - 20):i + 20].replace("\r", " ").replace("\n", " ")
    log("  %d ...%s..." % (i, ctx))

# 2) nbsp после подозрительных двухбуквенных
log("")
log("nbsp после «на»: %d" % len(re.findall(r"на&nbsp;", s)))
log("nbsp после «об»: %d" % len(re.findall(r"об&nbsp;", s)))
log("nbsp после «от»: %d" % len(re.findall(r"от&nbsp;", s)))
log("nbsp после «до»: %d" % len(re.findall(r"до&nbsp;", s)))
log("nbsp после «по»: %d" % len(re.findall(r"по&nbsp;", s)))
log("nbsp после «из»: %d" % len(re.findall(r"из&nbsp;", s)))
log("nbsp после «за»: %d" % len(re.findall(r"за&nbsp;", s)))
log("nbsp после «но»: %d" % len(re.findall(r"но&nbsp;", s)))
log("nbsp после «не»: %d" % len(re.findall(r"не&nbsp;", s)))
log("")

# 3) ё
log("ё ВСЕГО: %d" % len(re.findall(r"[ёЁ]", s)))
for x in re.finditer(r"[ёЁ]", s):
    i = x.start()
    log("  %d ...%s..." % (i, s[max(0, i - 12):i + 12]))

# 4) тире
log("")
log("— (U+2014) ВСЕГО: %d" % s.count("\u2014"))
log("– (U+2013) ВСЕГО: %d" % s.count("\u2013"))
log("- (ASCII) ВСЕГО: %d" % s.count("-"))

# 5) кавычки
log("")
log("« ВСЕГО: %d" % s.count("\u00ab"))
log("» ВСЕГО: %d" % s.count("\u00bb"))
log("„ ВСЕГО: %d" % s.count("\u201e"))
log('" ASCII ВСЕГО: %d' % s.count('"'))

# 6) KLBLOCK
log("")
log("KLBLOCK ВСЕГО: %d" % len(re.findall(r"KLBLOCK", s)))
for x in re.finditer(r"KLBLOCK", s):
    i = x.start()
    log("  %s" % s[max(0, i - 20):i + 50].replace("\r", " ").replace("\n", " "))

# 7) буквенные сокращения — итог
log("")
log("к.&nbsp;ф.&nbsp;н. (с nbsp): %d" % s.count("к.&nbsp;ф.&nbsp;н."))
log("н.&nbsp;с. (с nbsp): %d" % s.count("н.&nbsp;с."))
log("к.ф.н. (БЕЗ nbsp, битый): %d" % s.count("к.ф.н."))
log("н.с. (БЕЗ nbsp, битый): %d" % s.count("н.с."))
log("")
log("ДЛИНА файла: %d" % len(s))

with io.open(audit_log, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L))
print("OK done, log ->", audit_log)
