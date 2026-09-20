# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# найдём сегмент описания: от "Когда-то астрономы разглядели" до "Рекомендуемый возраст"
start = html.find("Когда-то астрономы разглядели")
end = html.find("Рекомендуемый возраст", start)
seg = html[start:end]
# распознать теги \u003C экранированные внутри JSON: заменю \u003C на < и \u0022 на "
for name in ["blockquote","p"]:
    seg = re.sub(r"\\u003C/"+name+r"\\u003E", "</"+name+">", seg)
    seg = re.sub(r"\\u003C"+name+r"\b[^>]*?\\u003E", lambda m: "<"+name+">", seg)
seg = re.sub(r"\\u003C/?br\s*/?\\u003E", "<br>", seg)
# теперь перечисляем блочные элементы по порядку
plain_blocks = []
for m in re.finditer(r"<(p|blockquote)[^>]*>(.*?)</\1>", seg, re.S):
    t = re.sub(r"<[^>]+>", " ", m.group(2))
    t = re.sub(r"\\u0022", '"', t)
    t = re.sub(r"\s+", " ", t).strip()
    plain_blocks.append((m.group(1), t))
for i,(tag,t) in enumerate(plain_blocks,1):
    print(f"{i}. [{tag}] {t[:1200]}")
    print()
