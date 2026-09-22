# -*- coding: utf-8 -*-
# Правит description.md по протоколу proofreading (раздел 2, nbsp):
#   - убираем &nbsp; после двухбуквенных предлогов/союзов:
#     на, об, от, до, по, но, не, как, при (и др.)
#   - «ё» в мета-комментариях -> «е»
# Пишет исправленный файл и полный лог-файл (UTF-8).

import io, re, os, sys

def main():
    src = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"
    logp = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp\fix_log.md"

    with io.open(src, "r", encoding="utf-8") as fh:
        s = fh.read()
    orig = s

    lines = []
    def log(x):
        lines.append(x)

    # ---------- 1) nbsp после двухбуквенных ----------
    two = ["на", "об", "от", "до", "по", "но", "не", "как", "при",
           "из", "за", "во", "со", "без", "под", "над", "через",
           "чтобы", "если", "что", "когда"]
    log("=== 1) nbsp после двухбуквенных предлогов/союзов ===")
    total = 0
    changed = []
    for w in sorted(two, key=len, reverse=True):
        pat = re.escape(w) + r"&nbsp;"
        n = len(re.findall(pat, s))
        if n:
            total += n
            changed.append("%d x «%s&nbsp;»" % (n, w))
            s = re.sub(pat, w + " ", s)
    log("  ВСЕГО заменено nbsp-после-двухбуквенных: %d" % total)
    for c in changed:
        log("    - %s" % c)

    # ---------- 2) «ё» в тексте/мета -> «е» ----------
    log("")
    log("=== 2) «ё» -> «е» ===")
    # меняем только там, где «ё» не смыслоразличительна (в мета-комментариях)
    for old, new in [("пересоздаётся", "пересоздается"),
                     ("замечан", "замечан"),
                     ("включён", "включен"),
                     ("учётом", "учетом")]:
        n = s.count(old)
        if n:
            s = s.replace(old, new)
            log("  - %d x «%s» -> «%s»" % (n, old, new))

    # ---------- запись ----------
    with io.open(src, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(s)

    # ---------- финальный аудит по исправленному ----------
    log("")
    log("=== ФИНАЛЬНЫЙ АУДИТ (по исправленному тексту) ===")
    m = list(re.finditer(r"&nbsp;", s))
    log("nbsp ВСЕГО: %d" % len(m))
    log("ё ВСЕГО: %d" % len(re.findall(r"[ёЁ]", s)))
    log("— ВСЕГО: %d" % s.count("\u2014"))
    log("– ВСЕГО: %d" % s.count("\u2013"))
    log("- ASCII ВСЕГО: %d" % s.count("-"))
    log("« ВСЕГО: %d" % s.count("\u00ab"))
    log("» ВСЕГО: %d" % s.count("\u00bb"))
    log("к.&nbsp;ф.&nbsp;н. : %d" % s.count("к.&nbsp;ф.&nbsp;н."))
    log("н.&nbsp;с. : %d" % s.count("н.&nbsp;с."))
    log("")

    # остались ли nbsp после двухбуквенных?
    bad = 0
    for w in two:
        n = len(re.findall(re.escape(w) + r"&nbsp;", s))
        if n:
            bad += n
            log("  ОСТАЛОСЬ: %d x «%s&nbsp;»" % (n, w))
    log("  Осталось нарушений nbsp-после-двухбуквенных: %d" % bad)
    if bad == 0:
        log("  ✔ ЧИСТО (0 нарушений)")

    with io.open(logp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("DONE -> %s" % logp)

if __name__ == "__main__":
    main()
