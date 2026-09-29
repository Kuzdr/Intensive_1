# -*- coding: utf-8 -*-
"""Компактная сводка по разобранным событиям mediomodo.ru (из events.json)."""
import io, json, sys, re

P = r'C:\_PROJ\Zerocoder\Intensiv_1\data\raw\mediomodo\events.json'
evs = json.loads(io.open(P, encoding='utf-8').read())
evs.sort(key=lambda e: (e['date_iso'], e['time']))

for e in evs:
    how = ''
    if e.get('howto'):
        how = re.sub(r'\s+', ' ', e['howto']['text'])[:110]
    lect = '; '.join(p['name'] for p in e['lecturers'])
    print('%-42s %s %s  %-11s %-38s' % (
        e['slug'][:42], e['date_iso'], e['time'],
        e['price_human'][:11], (e['venue'] or '-')[:38]))
    print('    возраст: %-5s | лекторы: %s' % (e['contacts']['age'] or '-', lect[:100]))
    print('    как добраться: %s' % (how or '-'))
