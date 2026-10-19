# -*- coding: utf-8 -*-
import urllib.request, urllib.parse, re, sys

q = sys.argv[1]
url = 'https://elementy.ru/find?objs=eltevents&words=' + urllib.parse.quote(q)
r = urllib.request.urlopen(url, timeout=30).read().decode('utf-8', 'replace')
links = sorted(set(re.findall(r'href="([^"]*/events/[^"]*)"', r)))
for l in links[:30]:
    print(l)
