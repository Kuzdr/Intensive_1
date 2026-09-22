import io, re

PATH = r"C:\_PROJ\Zerocoder\Intensiv_1\data\prototypes\TP-4201530\description.md"

with io.open(PATH, "r", encoding="utf-8") as f:
    s = f.read()

# Названия площадки: nbsp после двухбуквенного прдл. «на» не ставим
# (правило скилла: nbsp только после однобуквенных предлогов/союзов).
# «Библиотека&nbsp;на&nbsp;Газетном» -> «Библиотека&nbsp;на Газетном» (nbsp сохраняется
# только там, где нужен: после «Библиотека»?? — НЕТ: «на&nbsp;Газетном» — в названии
# площадки nbsp НЕ используем вообще, обычные пробелы, кроме стандартных случаев
# (однобуквенные предлоги и числа).
# Правка: убираем ВСЕ nbsp, стоящие после двухбуквенного «на» в этом названии.

pairs = [
    ("Библиотека&nbsp;на&nbsp;Газетном", "Библиотека на&nbsp;Газетном"),
    ("Библиотекiе&nbsp;на&nbsp;Газетном", "Библиотеке на&nbsp;Газетном"),
    ("Библиотеке&nbsp;на&nbsp;Газетном", "Библиотеке на&nbsp;Газетном"),
]

for old, new in pairs:
    cnt = s.count(old)
    s = s.replace(old, new)
    print("REPLACE {!r} -> {!r}: {}".format(old, new, cnt))

with io.open(PATH, "w", encoding="utf-8", newline="\n") as f:
    f.write(s)

print("DONE, len={}".format(len(s)))
