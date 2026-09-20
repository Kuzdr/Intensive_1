# -*- coding: utf-8 -*-
"""Одноразовый сборщик полного og:description Шрайбер (временный, стрянется)."""
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
raw = open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_shraiber.html", encoding="utf-8").read()

m = re.search(r'property="og:description" content="(.*?)"', raw, re.S)
d = m.group(1) if m else ""
print("LEN=", len(d))
print(d)
