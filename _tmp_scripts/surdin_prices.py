# -*- coding: utf-8 -*-
import re, io
SRC = r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\surdin_prices.txt"
raw = io.open(SRC, encoding="utf-8").read()
ln = []
# видимый текст
body = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
body = re.sub(r"<[^>]+>", " ", body)
body = re.sub(r"&nbsp;|&#160;|\xa0", " ", body)
body = re.sub(r"&\w+;", " ", body)
body = re.sub(r"\s+", " ", body)
for pat in [r"руб", r"ОНЛАЙН", r"онлайн", r"Ермолаев", r"Прямая речь", r"Москва"]:
    for m in re.finditer(re.escape(pat), body):
        s = max(0, m.start()-160)
        frag = body[s:m.end()+160].strip()
        ln.append("[" + pat + "] ..." + frag + "...")
        if len(ln) > 24:
            break
    if len(ln) > 24:
        break
io.open(OUT, "w", encoding="utf-8").writelines(l + "\n" for l in ln)
print("ok")
