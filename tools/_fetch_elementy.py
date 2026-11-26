# -*- coding: utf-8 -*-
"""Временная загрузка страницы события «Элементов» в data/raw/cdp/."""
import pathlib
import sys
import urllib.request

event_id = sys.argv[1]
url = "https://elementy.ru/events/%s/" % event_id
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=60) as response:
    raw = response.read()
try:
    text = raw.decode("utf-8")
except UnicodeDecodeError:
    text = raw.decode("cp1251", errors="replace")
out = pathlib.Path("data/raw/cdp") / ("elementy_%s.html" % event_id)
out.write_text(text, encoding="utf-8")
print(out, len(text), text[:120].replace("\n", " "))
