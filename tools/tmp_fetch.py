import urllib.request, re

UA = {'User-Agent': 'Mozilla/5.0'}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=15).read().decode('utf-8', 'ignore')


html = get('https://elementy.ru/events/450362')
print('=== TITLE ===')
t = re.search(r'<title>(.*?)</title>', html, re.S)
print(t.group(1).strip() if t else '?')

# look for place / city / address blocks
for key in ['Место проведения', 'Город', 'Адрес', 'Лекторий', 'Организатор']:
    idx = html.find(key)
    if idx >= 0:
        seg = html[idx:idx + 400]
        txt = re.sub(r'<[^>]+>', ' ', seg)
        txt = re.sub(r'\s+', ' ', txt).strip()
        print(key, '->', txt[:250])

# author bio: search for 'Об авторе' or block after lecturer name
for pat in [r'Об авторе(.*?)</div>', r'lecturerabout(.*?)</div>', r'autorsabout(.*?)</div>',
            r'class="lecturerabout"(.*?)</p>']:
    m = re.search(pat, html, re.S)
    if m:
        txt = re.sub(r'<[^>]+>', ' ', m.group(1))
        txt = re.sub(r'\s+', ' ', txt).strip()
        print('BIO', pat, '->', txt[:700])
        print('---')

# fallback: paragraphs containing 'писатель' or 'Семянников' near bio
ps = re.findall(r'<p[^>]*>(.*?)</p>', html, re.S)
for p in ps:
    tt = re.sub(r'<[^>]+>', ' ', p)
    tt = re.sub(r'\s+', ' ', tt).strip()
    if ('писатель' in tt or 'географ' in tt or 'исследовател' in tt or 'журналист' in tt) and len(tt) > 40:
        print('BIO-P:', tt[:600])
