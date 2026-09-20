# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# главная секция: от «Когда-то астрономы» до «Рекомендуемый возраст»
start = html.find("Когда-то астрономы")
end = html.find("Рекомендуемый возраст", start)
seg = html[start:end]
# вывести блочные элементы по порядку: p, blockquote
for mm in re.finditer(r"<(p|blockquote|h[1-6])\b[^>]*>(.*?)</\1>", seg, re.S):
    tag = mm.group(1)
    inner = re.sub(r"<br\s*/?>", "\n", mm.group(2))
    inner = re.sub(r"<[^>]+>", "", inner)
    inner = re.sub(r"[ \t]+", " ", inner)
    inner = re.sub(r"\n\s*\n", "\n", inner).strip()
    if not inner: continue
    if tag == "blockquote":
        print(">>> ЦИТАТА:", repr(inner))
    elif tag == "p":
        print("   АБЗАЦ:", repr(inner[:500]))
    else:
        print("   ", tag.upper(), ":", repr(inner[:300]))
    print()
print("=== длина сегмента:", len(seg))
