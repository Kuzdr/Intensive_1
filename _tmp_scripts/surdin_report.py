# -*- coding: utf-8 -*-
import re
raw = open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
out = []
def meta(p):
    m = re.search(r'property="'+p+r'" content="(.*?)"', raw, re.S)
    return m.group(1).strip() if m else "?"
def mname(p):
    m = re.search(r'name="'+p+r'" content="(.*?)"', raw, re.S)
    return m.group(1).strip() if m else "?"
out.append("og:title        = " + meta("og:title"))
out.append("og:url          = " + meta("og:url"))
out.append("og:description  = " + meta("og:description"))
out.append("priceAmount     = " + mname("priceAmount"))
# начало og:description полностью (первый абзац)
m = re.search(r'property="og:description" content="(.*?)"', raw, re.S)
if m:
    out.append("--- og:description POLNOSTYU ---")
    out.append(m.group(1))
open(r"C:\Users\mv\AppData\Local\Temp\opencode\surdin_report.txt","w",encoding="utf-8").write("\n".join(out))
print("written")
