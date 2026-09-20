# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
start = html.find("Когда-то астрономы")
end = html.find("Рекомендуемый возраст", start)
seg = html[start:end]
print("RAW SEG (first 3500):")
print(seg[:3500])
