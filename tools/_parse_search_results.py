# -*- coding: utf-8 -*-
"""Временный разбор сохранённой HTML-страницы поиска «Элементов»."""
import html
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8", errors="replace")
pattern = re.compile(
    r"href=['\"]/events/(\d+)/[^'\"]*['\"]>\s*<div class=['\"]title['\"]>(.*?)</div>\s*"
    r"<div class=['\"]brief['\"]>(.*?)</div>.*?<div class=['\"]sublink['\"]>(.*?)</div>",
    re.S | re.I,
)


def plain(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


for m in pattern.finditer(text):
    print(m.group(1), "|", plain(m.group(2)), "|", plain(m.group(4)))
