# -*- coding: utf-8 -*-
import re, json, datetime
raw = open(r"C:\Users\mv\AppData\Local\Temp\opencode\pryamaya_surdin.html", encoding="utf-8").read()
rpt = []
def prop(k):
    m = re.search(r'property="'+k+r'"[^>]*?content="(.*?)"', raw, re.S) or re.search(r'content="(.*?)"[^>]*?property="'+k+r'"', raw, re.S)
    return m.group(1).strip() if m else "?"
def meta(k):
    m = re.search(r'name="'+k+r'"[^>]*?content="(.*?)"', raw, re.S) or re.search(r'content="(.*?)"[^>]*?name="'+k+r'"', raw, re.S)
    return m.group(1).strip() if m else "?"
rpt.append("og:title   = " + prop("og:title"))
rpt.append("og:url     = " + prop("og:url"))
# день недели
for pat in [r'"datePublished":"([^"]+)"', r'itemprop="startDate" content="([^"]+)"', r'"startDate":"([^"]+)"', r'\b(2026-10-14)\b']:
    m = re.search(pat, raw)
    if m:
        try:
            d = datetime.date.fromisoformat(m.group(1)[:10])
            rpt.append("data:"+m.group(1)+" => день недели: "+d.strftime("%A"))
        except Exception:
            rpt.append("data(не дата):"+m.group(1))
        break
# видимое время начала
for pat in [r'(19:\d\d)</', r'(18:\d\d)</']:
    m = re.search(pat, raw)
    if m: rpt.append("видимое время: "+m.group(1)); break
# JSON-LD
m = re.search(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S)
if m:
    rpt.append("--- JSON-LD (полный) ---")
    rpt.append(m.group(1))
# адрес/площадка
for kw in ["Ермолаев","переулок","ОНЛАЙН","онлайн","Прямая речь","ПРЯМАЯ РЕЧЬ"]:
    cnt = raw.count(kw)
    rpt.append("kw[%s] => %d" % (kw, cnt))
# видимые цены
for pat in [r'(\d[\d ]{2,5})\s*руб', r'руб\.\s*</'], re:
    m = re.search(pat, raw)
    if m: rpt.append("цена-строка: "+re.sub(r'\s+',' ',m.group(0))); 
rpt.append("--- видимый текст страницы (начало) ---")
body_txt = re.sub(r'<script.*?</script>','',raw,flags=re.S)
body_txt = re.sub(r'<style.*?</style>','',body_txt,flags=re.S)
body_txt = re.sub(r'<[^>]+>',' ',body_txt)
body_txt = re.sub(r'&nbsp;|&#160;|\xa0',' ',body_txt)
body_txt = re.sub(r'&[a-z#0-9]+;',' ',body_txt)
body_txt = re.sub(r'\s+',' ',body_txt)
i = body_txt.find("Марс")
rpt.append(body_txt[max(0,i-200):i+2500])
open(r"C:\Users\mv\AppData\Local\Temp\opencode\surdin_pasport.txt","w",encoding="utf-8").write("\n".join(rpt))
print("ok")
