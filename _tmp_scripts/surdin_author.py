# -*- coding: utf-8 -*-
import io, re
vis = io.open(r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\surdin_visible.txt", encoding="utf-8").read()
ln = []
# 1) полная аннотация: от «Когда-то астрономы» до «…проверенная информация.»
i = vis.find("Когда-то астрономы")
if i >= 0:
    ln.append("=== АННОТАЦИЯ (полный абзац) ===")
    ln.append(vis[i:i+4200].strip())
# 2) абзац об авторе: ищем «Владимир Сурдин — » и т.п.
j = vis.find("астроном и популяризатор")
ln.append("")
ln.append("=== АБЗАЦ ОБ АВТОРЕ (фрагменты) ===")
for k in ["Владимир Сурдин —", "Сурдин —", "астроном,"]:
    q = vis.find(k)
    if q >= 0:
        ln.append("[%s] ...%s..." % (k, vis[max(0,q-120):q+900].strip()))
io.open(r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\surdin_author_abu.txt", "w", encoding="utf-8").writelines(s + "\n" for s in ln)
print("ok")
