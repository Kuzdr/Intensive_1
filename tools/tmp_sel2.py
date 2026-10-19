# -*- coding: utf-8 -*-
import re, urllib.request, sys, html

u = sys.argv[1]
raw = urllib.request.urlopen(u, timeout=30).read().decode('utf-8', 'replace')
for name in ['lctid', 'plcid']:
    m = re.search(r'<select[^>]*name=["\']?\s*%s["\']?[^>]*>(.*?)</select>' % name, raw, re.S)
    print('==== select', name, 'found' if m else 'NOT FOUND')
    if not m:
        continue
    opts = re.findall(r'<option[^>]*?value=["\']?([^\'">\s]*)["\']?[^>]*>(.*?)</option>', m.group(1), re.S)
    for v, t in opts:
        t = html.unescape(re.sub(r'<[^>]+>', '', t))
        print(' ', v, ':', t)
