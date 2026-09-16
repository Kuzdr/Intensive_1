# -*- coding: utf-8 -*-
"""Создаёт собственную фавиконку на основе фавиконки «Элементов» (серую вместо чёрной).

Результат: assets/favicon.ico (16/32/48) и assets/favicon.png.
Запуск:  python make_favicon.py
"""
import os, io, sys
import requests
from PIL import Image

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(ROOT, 'assets')
os.makedirs(ASSETS, exist_ok=True)

SRC = 'https://elementy.ru/favicon.ico'
GRAY = (170, 170, 170)  # целевой серый цвет

def main():
    r = requests.get(SRC, timeout=30)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert('RGBA')
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            rr, gg, bb, aa = px[x, y]
            if aa == 0:
                continue
            lum = 0.299 * rr + 0.587 * gg + 0.114 * bb
            if lum < 128:  # тёмные пиксели (в т.ч. чёрные) — в серый
                px[x, y] = (GRAY[0], GRAY[1], GRAY[2], aa)
    im.save(os.path.join(ASSETS, 'favicon.png'))
    im.save(os.path.join(ASSETS, 'favicon.ico'), sizes=[(16, 16), (32, 32), (48, 48)])
    print('Создано:', os.path.join(ASSETS, 'favicon.ico'), '(16/32/48) и favicon.png')

if __name__ == '__main__':
    main()