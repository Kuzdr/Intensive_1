# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
start = html.find("Когда-то астрономы разглядели")
end = html.find("Рекомендуемый возраст", start)
seg = html[start:end]
for m in re.finditer(r"<(p|blockquote)[^>]*>(.*?)</\1>", seg, re.S):
    tag = m.group(1)
    t = re.sub(r"<[^>]+>", " ", m.group(2))
    t = re.sub(r"\s+", " ", t).strip()
    if t:
        print("[%s] %s" % (tag, t))
        print()
