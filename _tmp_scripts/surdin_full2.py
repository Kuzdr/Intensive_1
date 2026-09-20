# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\pryamaya_surdin.html", encoding="utf-8").read()
# найдём структуру события: подзаголовок и описание
# видимые подзаголовки
for pat in [r"Марс: зона возможной жизни(.*?)14 октября, 19:30", r"ступить на Красную планету", r"Когда-то астрономы"]:
    m = re.search(pat, html, re.S)
    if m:
        seg = m.group(0)[:600]
        seg = re.sub(r"<[^>]+>", " ", seg)
        seg = re.sub(r"\s+", " ", seg)
        print("=== PAT:", pat, "===")
        print(seg[:600])
        print()
