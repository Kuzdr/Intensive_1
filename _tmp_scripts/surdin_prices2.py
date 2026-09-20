# -*- coding: utf-8 -*-
import re, io
SRC = r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html"
raw = io.open(SRC, encoding="utf-8").read()
rpt = []
# цены в видимом тексте (без скриптов)
body = re.sub(r"<script.*?</script>", "", raw, flags=re.S)
body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
ts = re.sub(r"<[^>]+>", " ", body)
ts = re.sub(r"&nbsp;|&#160;|\xa0", " ", ts)
ts = re.sub(r"&\w+;", " ", ts)
ts = re.sub(r"\s+", " ", ts)
for m in re.finditer(r"([\d\s]{2,6})\s*руб", ts):
    frag = ts[max(0, m.start()-120): m.start()+10]
    rpt.append("ЦЕНА> " + re.sub(r"\s+", " ", frag).strip())
# og:url
for p in [r'property="og:url"\s+content="(.*?)"', r'content="(.*?)"\s+property="og:url"']:
    m = re.search(p, raw, re.S)
    if m:
        rpt.append("og:url = " + m.group(1).strip()); break
else:
    # возможно og:url через отдельный тег <link rel="canonical">
    m = re.search(r'rel="canonical"\s+href="(.*?)"', raw)
    rpt.append("canonical = " + (m.group(1) if m else "?"))
# онлайн-цена: JSON-LD offers
for m in re.finditer(r'"offers".*?price":\s*"([\d.]+)"', raw, re.S):
    rpt.append("JSON-LD offer price = " + m.group(1))
io.open(r"C:\_PROJ\Zerocoder\Intensiv_1\_tmp_scripts\surdin_prices.txt", "w", encoding="utf-8").writelines(l+"\n" for l in rpt)
print("done")
