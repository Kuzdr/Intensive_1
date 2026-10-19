# -*- coding: utf-8 -*-
"""Временный скрипт: показать текст school.spbstu.ru из локального HTML."""
import re
import html as H

raw = open(r"C:\Users\mv\AppData\Local\Temp\opencode\school.html", encoding="utf-8").read()
raw = re.sub(r"(?is)<script.*?</script>", " ", raw)
raw = re.sub(r"(?is)<style.*?</style>", " ", raw)
raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
raw = re.sub(r"(?is)</(p|div|li|h[1-6]|tr)>", "\n", raw)
txt = re.sub(r"(?s)<[^>]+>", " ", raw)
txt = H.unescape(txt)
lines = [re.sub(r"[ \t ]+", " ", l).strip() for l in txt.split("\n")]
lines = [l for l in lines if l]
print("\n".join(lines))
