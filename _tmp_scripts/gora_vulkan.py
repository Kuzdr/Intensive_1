# -*- coding: utf-8 -*-
import re, io
html = io.open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
# 1) полный og:description = content
m = re.search(r'property="og:description"\s+content="([^"]*)"', html)
print("og:description =", m.group(1) if m else "?")
print()
# 2) где "гора" (в каком поле), где "вулкан"
for w in ["гора","вулкан","Гору","гору","высочайш"]:
    print(w, "->", html.count(w))
print()
# 3) контекст вокруг каждого "вулкан"
for mm in re.finditer(r"вулкан", html):
    s=max(0,mm.start()-150); e=mm.end()+120
    ctx=re.sub(r"<[^>]+>"," ",html[s:e]); ctx=re.sub(r"\s+"," ",ctx).strip()
    print("…",ctx)
print()
# 4) og:description JSON-LD (второе поле "description" — полное)
descs = re.findall(r'"description":"((?:[^"\\]|\\.)*?)"', html)
for i,d in enumerate(descs):
    if "Марсе" in d or "вулкан" in d or "гор" in d:
        print(f"--- desc#{i}:", d[:800])
