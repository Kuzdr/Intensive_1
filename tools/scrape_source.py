#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import json
import re
import urllib.parse
from urllib.request import Request, urlopen
from html import unescape
from bs4 import BeautifulSoup

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

def fetch(url):
    req = Request(url, headers={'User-Agent': USER_AGENT})
    with urlopen(req, timeout=60) as resp:
        data = resp.read()
        enc = resp.headers.get_content_charset() or 'utf-8'
    return data.decode(enc, errors='ignore')

def get_meta(soup, names):
    for n in names:
        m = soup.find('meta', attrs={'property': n}) or soup.find('meta', attrs={'name': n})
        if m and m.get('content'):
            return unescape(m['content'].strip())
    return ''

def extract_og(soup):
    res = {}
    for k, v in [('og:title', 'title'), ('og:description', 'description'), ('og:image', 'image'), ('og:url', 'url')]:
        res[v] = get_meta(soup, [k, k.replace('og:', '')] if k.startswith('og:') else [k])
    return res

def extract_jsonld(soup):
    data = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data.append(json.loads(script.string or script.text))
        except Exception:
            pass
    return data

def find_author_img(soup):
    base = ''
    if soup.base and soup.base.get('href'):
        base = soup.base['href']
    for attr in ['src', 'data-src']:
        for img in soup.find_all('img', alt=re.compile('Безруких|Bezrukih|Марьяна', re.I)):
            src = img.get(attr) or img.get('src')
            if src:
                return urllib.parse.urljoin(base or '', src)
    for img in soup.find_all('img'):
        src = img.get(attr) or ''
        if 'lecturer' in src or '292' in src:
            return urllib.parse.urljoin(base or '', src)
    return ''

def main():
    if len(sys.argv) < 2:
        print('usage: python scrape_source.py <url> [out.json]')
        return
    url = sys.argv[1]
    html = fetch(url)
    soup = BeautifulSoup(html, 'html.parser')
    og = extract_og(soup)
    jld = extract_jsonld(soup)
    img = find_author_img(soup)
    res = {'url': url, 'og': og, 'jsonld': jld, 'author_img_hint': img}
    out = sys.argv[2] if len(sys.argv) > 2 else 'scrape_source.json'
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print('written', out)

if __name__ == '__main__':
    main()
