# -*- coding: utf-8 -*-
r"""Разбор сохранённой страницы «Троицкого варианта живьем» (trovant.ru).

DOM берём через `tools\cdp_read.py` — обычный HTTP-запрос отдаёт неполную
страницу (как и у Timepad). Скрипт печатает видимый текст анонса (дата, место,
программа, спикеры, цены, карта); ключ `--links` добавляет контекст ссылок
(билеты, трансляция, Timepad, карта).

    python -X utf8 tools\\cdp_read.py trovant https://trovant.ru/events/
    python -X utf8 tools\\trovant_parse.py data\\raw\\cdp\\trovant_events.html
    python -X utf8 tools\\trovant_parse.py data\\raw\\cdp\\trovant_events.html --links
"""
import argparse
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timepad_parse import visible_text

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LINK_KEYS = ("Купить билет в зал", "Купить на Timepad", "Трансляция",
             "Открыть в Яндекс Картах")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dom", help="путь к сохранённому DOM-файлу")
    ap.add_argument("--links", action="store_true", help="контекст ссылок")
    a = ap.parse_args()
    path = a.dom if os.path.isabs(a.dom) else os.path.join(ROOT, a.dom)
    with io.open(path, encoding="utf-8", errors="replace") as f:
        html = f.read()
    print(visible_text(html))
    if a.links:
        for key in LINK_KEYS:
            print("\n=== " + key)
            for m in list(re.finditer(re.escape(key), html))[:5]:
                ctx = html[max(0, m.start() - 350):m.end() + 200]
                print(re.sub(r"\s+", " ", ctx))


if __name__ == "__main__":
    main()
