import re
p = r'C:\_PROJ\Zerocoder\Intensiv_1\_tmp\2_arhe.html'
with open(p, encoding='utf-8', errors='ignore') as f:
    s = f.read()
ps = re.findall(r'<p[^>]*>(.*?)</p>', s, re.S|re.I)
for x in ps:
    t = re.sub(r'<[^>]+>','',x)
    t = t.replace('&nbsp;',' ').replace('&amp;','&').replace('&quot;','"').replace('&#39;','\'').replace('&mdash;','—').replace('&ndash;','–').replace('&#171;','«').replace('&#187;','»').replace('&#8212;','—')
    t = re.sub(r'\s+',' ', t).strip()
    if t and 'надёжных' in t:
        print(t)
        break
