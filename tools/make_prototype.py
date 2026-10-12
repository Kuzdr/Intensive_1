#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys, os, json, re, datetime

MONTHS = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']

def slugify(s):
    s = str(s).lower()
    s = re.sub(r'[^a-z0-9а-яё]+', '-', s, flags=re.I|re.U)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

def parse_iso(dt):
    try:
        if not dt: return None
        dt = dt.replace('Z','+00:00')
        d = datetime.datetime.fromisoformat(dt)
        if d.tzinfo:
            d = d.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return d
    except Exception:
        return None

def field1(date_iso, tstart):
    try:
        d = datetime.date.fromisoformat(date_iso)
        hh,mm = map(int, tstart.split(':'))
    except Exception:
        return ''
    if hh <= 12: head='0'
    elif hh <= 20: head=str(hh-12)
    else: head='9'
    if 13<=hh<=20 and mm!=0:
        if mm < 30: idx2='4'
        elif mm == 30: idx2='6'
        else: idx2='8'
    else:
        idx2='0'
    return f'{d.strftime("%Y.%m.%d")}{head}{idx2}'

def main():
    if len(sys.argv)<3:
        print('usage: python make_prototype.py <scrape_source.json> <outdir> [code=PR]')
        return
    src = json.load(open(sys.argv[1], encoding='utf-8'))
    outdir = sys.argv[2]
    code = sys.argv[3] if len(sys.argv)>3 else 'PR'
    os.makedirs(outdir, exist_ok=True)
    url = src.get('url','')
    og = src.get('og',{})
    jld = src.get('jsonld',[])
    be = None
    for x in jld:
        t = x.get('@type','')
        if isinstance(t,list): t=t[0] if t else ''
        if 'BroadcastEvent' in str(t): be=x; break
    title_full = og.get('title') or (be.get('name') if be else '')
    title_clean = re.sub(r'\s*Марьяна\s+Безруких.*$', '', title_full, flags=re.I).strip() or title_full
    start = parse_iso(be.get('startDate')) if be else None
    end = parse_iso(be.get('endDate')) if be else None
    performer = (be.get('performer') or {}).get('name') if be and be.get('performer') else 'Марьяна Безруких'
    is_online = True
    tstart = f'{start.hour:02d}:{start.minute:02d}' if start else ''
    tend = f'{end.hour:02d}:{end.minute:02d}' if end else ''
    date_iso = start.date().isoformat() if start else ''
    lect_id = f'{code}-{start.strftime("%y%m%d")}-{slugify(title_clean)[:35]}' if start else f'{code}-{slugify(title_clean)[:40]}'
    proto = {
        'id': lect_id,
        'lectory': 'Лекторий «Прямая речь»',
        'date_iso': date_iso,
        'time_start': tstart,
        'time_end': tend,
        'city': 'Москва',
        'place': 'ОНЛАЙН' if is_online else '',
        'lecturer': performer,
        'title': title_clean.replace(' и ',' и&nbsp;'),
        'types': ['Лекция'],
        'topics': ['Психология','Нейронаука'],
        'price_short': '1900&nbsp;руб.',
        'annot': '',
        'url': url,
        'sources': [url],
        'fields': [],
        'desc_html': '',
        'extra_html': [],
        'authors': [],
        'verbatim_fragments': [],
        'reg_labels': [],
        'photo_file': '',
        'notes': ''
    }
    with open(os.path.join(outdir,'proto.json'),'w',encoding='utf-8') as f:
        json.dump(proto,f,ensure_ascii=False,indent=2)
    print('ok', lect_id)

if __name__=='__main__':
    main()
