# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# Проверка слов «гора»/«вулкан» по всему документу
for w in ["гора", "горы", "вулкан", "вулкана", "вулкана систем"]:
    pass
print("гора встречается как 'высочайшая гора':", "высочайшая гора" in html)
print("вулкан как 'высочайший вулкан':", "высочайший вулкан" in html)
print()
# Ключевой блок: от «Когда-то астрономы» до «Рекомендуемый возраст»
start = html.find("Когда-то астрономы")
end = html.find("Рекомендуемый возраст", start)
seg = html[start:end]
# вывести абзацы и блок quote по порядку
for mm in re.finditer(r"<(p[^>]*|blockquote[^>]*)>(.*?)</\1>", seg, re.S):
    inner = re.sub(r"<[^>]+>", " ", mm.group(2))
    inner = re.sub(r"\s+", " ", inner).strip()
    if inner:
        print(f"[{mm.group(1)}] {inner}")
        print()
