# -*- coding: utf-8 -*-
import io, json, os, re

BASE = 'data/prototypes'
PIDS = ['TP-4207864', 'TP-4213846', 'TP-4213914', 'TP-4215931']
AUD = 'АУДИТ (proofreading п.0, 28.09.2026): «ё» в тексте прототипа нет. Обратная проверка yo_words: «Все спикеры» — мн.ч., без ё; «ее знаниями» — инвариант «ее»; имена собственные (Ельцин, Ломоносов, Сколтех, Коротин, Миркес, Самофалов, Зайцев, Долгоруковых-Бобринских) — «ё» не требуется. nbsp-места:'

def x(ctx):
    s = ctx.replace('&nbsp;', ' | ')
    s = re.sub(r'<[^>]+>', ' ', s)
    s = s.replace('&laquo;','').replace('&raquo;','')
    return ' '.join(s.split())[:42]

for pid in PIDS:
    f = os.path.join(BASE, pid, 'prototype.json')
    p = json.load(io.open(f, encoding='utf-8'))
    # cut old audit
    notes = p.get('notes','')
    if '\n\n\nАУДИТ' in notes:
        notes = notes.split('\n\n\nАУДИТ')[0]
    texts = []
    for fl in p.get('fields', []):
        texts.append(fl.get('value', ''))
    texts.append(p.get('title',''))
    texts.append(p.get('annot',''))
    texts.append(p.get('lecturer',''))
    texts.append(p.get('desc_html',''))
    texts += list(p.get('extra_html', []))
    raw = '\n'.join(texts)
    lines = []
    seen = set()
    for pos in [m.start() for m in re.finditer('&nbsp;', raw)]:
        seg = x(raw[max(0,pos-24):pos+28])
        if seg in seen: continue
        seen.add(seg)
        lines.append('  * ' + seg)
    audit = AUD + '\n' + '\n'.join(lines)
    p['notes'] = (notes + '\n\n\n' + audit).strip()
    json.dump(p, io.open(f,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print(pid, 'nbsp:', len(lines))
