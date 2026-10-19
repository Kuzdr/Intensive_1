# -*- coding: utf-8 -*-
import json, re, sys, urllib.request

opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)

ev = json.load(open('data/events.json', encoding='utf-8'))
urls = [e.get('url') for e in ev if str(e.get('url', '')).startswith('https://elementy.ru/events/')][:8]
sel_re = re.compile(r'<select[^>]*name=["\']?\s*lctid["\']?[^>]*>(.*?)</select>', re.S)
opt_re = re.compile(r'<option[^>]*?value=["\']?([^\'">\s]*)["\']?[^>]*>(.*?)</option>', re.S)
for u in urls:
    try:
        raw = urllib.request.urlopen(u, timeout=30).read().decode('utf-8', 'replace')
    except Exception as ex:
        print('ERR', u, ex)
        continue
    m = sel_re.search(raw)
    if not m:
        print('no select', u)
        continue
    opts = [(v, re.sub(r'<[^>]+>', '', t)) for v, t in opt_re.findall(m.group(1))]
    hit = [(v, t) for v, t in opts if 'технологий' in t.lower()]
    print(u.split('/')[-1][:45], 'opts=', len(opts), '| hit:', hit)
