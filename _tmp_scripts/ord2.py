# -*- coding: utf-8 -*-
import re
html = open(r'C:\\Users\\mv\\AppData\\Local\\Temp\\opencode\\pryamaya_surdin.html', encoding='utf-8').read()
start = html.find('Когда-то астрономы разглядели')
end = html.find('Рекомендуемый возраст', start)
seg = html[start:end]
blocks = re.findall(r'<(p|blockquote)[^>]*>(.*?)</\1>', seg, re.S)
for i,(tag,inner) in enumerate(blocks,1):
    t = re.sub(r'<[^>]+>',' ',inner)
    t = re.sub(r'\s+',' ',t).strip()
    if t:
        print(f'--- [{tag}] #{i}:')
        print(t[:2000])
        print()
