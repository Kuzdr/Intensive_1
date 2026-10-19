# -*- coding: utf-8 -*-
"""Временный скрипт: показать текст события elementy 450732 (образец СПбПУ)."""
import sys
import re
import html as H
import urllib.request

url = sys.argv[1]
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
raw = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
open(r"C:\Users\mv\AppData\Local\Temp\opencode\elem_tmp.html", "w", encoding="utf-8").write(raw)
raw = re.sub(r"(?is)<script.*?</script>", " ", raw)
raw = re.sub(r"(?is)<style.*?</style>", " ", raw)
raw = re.sub(r"(?is)<br\s*/?>", "\n", raw)
raw = re.sub(r"(?is)</(p|div|li|h[1-6]|tr|section)>", "\n", raw)
txt = re.sub(r"(?s)<[^>]+>", " ", raw)
txt = H.unescape(txt)
lines = [re.sub(r"[ \t ]+", " ", l).strip() for l in txt.split("\n")]
lines = [l for l in lines if l]
sys.stdout.reconfigure(encoding="utf-8")
print("\n".join(lines[:200]))
