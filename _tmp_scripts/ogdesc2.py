# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
print("OG-DESC:", m.group(1) if m else "?")
print()
m = re.search(r'"description":"((?:[^"\\]|\\.)*)"', html)
if m:
    d = m.group(1).encode().decode("unicode_escape")
    print("JSONLD-DESC-1st:", d[:3000])
