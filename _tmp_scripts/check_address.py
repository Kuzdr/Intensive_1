# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding="utf-8")
raw = open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_shraiber.html", encoding="utf-8").read()
for k in ["Ермолаев", "переул", "Прямая речь", "ПРЯМАЯ РЕЧЬ", "ул"]:
    hits = re.findall(r'.{60}' + k + r'.{60}', raw, re.S)
    print("==", k, "=>", len(hits))
    for h in hits[:4]:
        print("   ", re.sub(r"\s+"," ",h).strip())
m = re.search(r'og:description" content="(.*?)"', raw, re.S)
print("\nog:description:", (re.sub(r"\s+"," ",m.group(1)).strip() if m else "?"))
