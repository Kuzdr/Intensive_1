# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# 1) точный текст после заголовка лекции (подзаголовок)
m = re.search(r"Марс:\s*зона\s*возможной\s*жизни(.{0,300}?)14\s*октября", html, re.S)
print("=== ПОСЛЕ НАЗВАНИЯ (подзаголовок+дата) ===")
if m:
    seg = re.sub(r"<[^>]+>", " ", m.group(1))
    seg = re.sub(r"\s+", " ", seg).strip()
    print(repr(seg))
print()
# 2) найти большой блок: описание от "Когда-то астрономы" до, скажем, "ЭЛЕМЕНТЫ" — собрать все абзацы
print("=== АБЗАЦЫ ОПИСАНИЯ (как на странице) ===")
m = re.search(r"Когда-то астрономы разглядели(.{0,2000}?)Рекомендуемый возраст", html, re.S)
if m:
    text = m.group(1)
    # абзацы
    for para in re.split(r"</p>", text):
        p = re.sub(r"<[^>]+>", " ", para)
        p = re.sub(r"\s+", " ", p).strip()
        if p:
            print("-", p)
print()
print("=== ЦЕНЫ (visible) ===")
for m in re.finditer(r"(\d[0-9\s]{2,4}₽)", html):
    pass
# цены отдельно из JSON-LD
m = re.search(r'"price"\s*:\s*"([0-9.]+)"', html)
print("JSON-LD price:", m.group(1) if m else "?")
m = re.search(r'"name"\s*:\s*"([^"]*)"', html)
print("JSON-LD name:", m.group(1) if m else "?")
