import urllib.request, urllib.parse, re

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=15).read().decode('utf-8', errors='replace')

for q in ['Квартальнов', 'Резникова']:
    html = fetch('https://elementy.ru/find?objs=eltevents&words=' + urllib.parse.quote(q))
    links = sorted(set(re.findall(r'href="([^"]*eltevents/(\d{6})[^"]*)"', html)))
    print(q, '-> events:', [m[1] for m in links][:8])
    imgs = sorted(set(re.findall(r'(?:src|data-src)="([^"]+\.(?:jpg|png|webp))"', html)))
    print('  imgs:', imgs[:6])
