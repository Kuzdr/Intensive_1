# -*- coding: utf-8 -*-
import re, io
OBJ = r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html"
OUT = r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\surdin_visible.txt"
raw = io.open(OBJ, encoding="utf-8").read()
body = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
body = re.sub(r"<[^>]+>", " ", body)
body = re.sub(r"&nbsp;|&#160;|\xa0", " ", body)
body = re.sub(r"&\w+;", " ", body)
body = re.sub(r"\s+", " ", body)
out = []
for pat in [r"руб", r"ОНЛАЙН", r"онлайн", r"онлайн-трансл", r"Ермолаев", r"Ермолаевский", r"Прямая речь", r"Москва", r"Красная планета", r"14 октября"]:
    for m in re.finditer(pat, body, re.I):
        f = body[max(0, m.start()-120): m.end()+160].strip()
        out.append("[%s] …%s…" % (pat, f))
        if len(out) > 30:
            break
    if len(out) > 30:
        break
io.open(OUT, "w", encoding="utf-8").writelines(s + "\n" for s in out)
print("ok", len(out))
