# -*- coding: utf-8 -*-
"""Показывает заголовок страницы источника (title/og:title/h1) из кэша HTML.

Запуск: python -X utf8 tools\\mm_title.py <slug> [<slug> ...]
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "mediomodo")

PATS = [r"<title>(.*?)</title>",
        r'property="og:title" content="(.*?)"',
        r"<h1[^>]*>(.*?)</h1>"]


def main():
    for slug in sys.argv[1:]:
        path = os.path.join(RAW, slug + ".html")
        if not os.path.exists(path):
            print("== %s: НЕТ КЭША" % slug)
            continue
        t = io.open(path, encoding="utf-8").read()
        print("== %s" % slug)
        for p in PATS:
            for x in re.findall(p, t, re.S)[:2]:
                print("   %-10s %s" % (p[1:9], re.sub(r"<[^>]+>", "", x).strip()[:140]))


if __name__ == "__main__":
    main()
