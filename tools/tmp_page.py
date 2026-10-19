# -*- coding: utf-8 -*-
import urllib.request, re, sys

u = sys.argv[1]
raw = urllib.request.urlopen(u, timeout=30).read().decode('utf-8', 'replace')
i = raw.find("eltclub_authors_about")
if i < 0:
    i = raw.find('itemblock memo')
seg = raw[max(0, i - 6000): i + 14000]
seg = re.sub(r'(?is)<(script|style).*?</\1>', ' ', seg)
# keep important tags as markers
seg = re.sub(r'(?i)<br\s*/?>', '\n[BR]\n', seg)
seg = re.sub(r'(?i)</p>', '\n[/P]\n', seg)
seg = re.sub(r'(?i)<p([^>]*)>', lambda m: '\n[P %s]\n' % m.group(1).strip(), seg)
seg = re.sub(r'(?i)<a href="([^"]*)"[^>]*>(.*?)</a>', lambda m: '[A %s]%s[/A]' % (m.group(1), m.group(2)), seg, flags=re.S)
seg = re.sub(r'(?i)<b>', '**', seg)
seg = re.sub(r'(?i)</b>', '**', seg)
seg = re.sub(r'(?i)<i>', '/*', seg)
seg = re.sub(r'(?i)</i>', '*/', seg)
seg = re.sub(r'<[^>]+>', '', seg)
import html as H
seg = H.unescape(seg)
seg = re.sub(r'[ \t\xa0]+', ' ', seg)
seg = re.sub(r'\n{3,}', '\n\n', seg)
print(seg)
