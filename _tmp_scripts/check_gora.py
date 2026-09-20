# -*- coding: utf-8 -*-
import re
html = open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
for m in re.finditer(r"высочайш\w+(?:\s+\w+){0,3}?", html):
    s = max(0, m.start()-120)
    print("...", re.sub(r"\s+"," ", html[s:m.end()+60]))
    print()
