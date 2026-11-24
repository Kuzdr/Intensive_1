# -*- coding: utf-8 -*-
r"""Разбор сохранённой страницы публичного телеграм-канала (t.me/s/...).

Помогает найти второй источник и точную дату/ссылки на карту: поиск по
подстроке в текстах постов печатает `data-post`, дату,permalink и все ссылки.
DOM сохраняется через `tools\cdp_read.py` (Telegram через webfetch часто
не отдаёт содержимое).

    python -X utf8 tools\cdp_read.py tgfond "https://t.me/s/fondnauk?q=..." t.me
    python -X utf8 tools\telegram_parse.py data\raw\cdp\tgfond.html "Миролюбов"
    python -X utf8 tools\telegram_parse.py data\raw\cdp\tgfond.html --post fondnauk/10397
"""
import argparse
import html as H
import io
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def show(part):
    m = re.search(r'data-post="([^"]+)"', part)
    d = re.search(r'datetime="([^"]+)"', part)
    post = m.group(1) if m else "?"
    print("ПОСТ:", post, "ДАТА:", d.group(1) if d else "?")
    print("ССЫЛКА: https://t.me/%s" % post.replace("/", "/"))
    txt = H.unescape(re.sub(r"<[^>]+>", " ", part))
    txt = re.sub(r"\s+", " ", txt).strip()
    print("ТЕКСТ:", txt[:2500])
    links = []
    for x in re.finditer(r'href="([^"]+)"', part):
        u = H.unescape(x.group(1))
        if u not in links:
            links.append(u)
    print("ССЫЛКИ:")
    for u in links:
        print("  ", u[:220])
    print("---")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dom", help="путь к сохранённому DOM-файлу")
    ap.add_argument("needle", nargs="?", help="подстрока в тексте поста")
    ap.add_argument("--post", help="точно этот data-post, например fondnauk/10397")
    a = ap.parse_args()
    path = a.dom if os.path.isabs(a.dom) else os.path.join(ROOT, a.dom)
    t = io.open(path, encoding="utf-8", errors="replace").read()
    parts = re.split(r'(?=<div class="tgme_widget_message )', t)
    n = 0
    for part in parts:
        m = re.search(r'data-post="([^"]+)"', part)
        if a.post and (not m or m.group(1) != a.post):
            continue
        if a.needle and a.needle not in part:
            continue
        show(part)
        n += 1
    if not n:
        print("Посты не найдены")


if __name__ == "__main__":
    main()
