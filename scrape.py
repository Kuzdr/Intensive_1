# -*- coding: utf-8 -*-
"""Скрейпер предстоящих событий с elementy.ru/events -> data/events.json"""
import re, os, sys, json, time, unicodedata
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, 'data')
IMG_DIR = os.path.join(ROOT, 'site', 'assets', 'img')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36'}
S = requests.Session()
S.headers.update(HEADERS)

MONTHS = {'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6,
          'июля': 7, 'августа': 8, 'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}

def clean(s):
    return s.replace('&nbsp;', ' ').replace('&mdash;', '—').replace('&ndash;', '–') \
            .replace('&laquo;', '«').replace('&raquo;', '»').replace('&quot;', '"') \
            .replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')

def tag_text(html):
    t = re.sub(r'<script.*?</script>', ' ', html, flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = clean(t)
    t = re.sub(r'[ \t]+', ' ', t)
    return t.strip()

def strip_punct(s):
    return unicodedata.normalize('NFKC', s)

def parse_list_page():
    html = S.get('https://elementy.ru/events', timeout=30).text
    events = []
    parts = html.split("<div class='edate'>")[1:]
    for p in parts:
        urld = re.search(r'href="(/events/([0-9]+)/([^"?]+))', p)
        if not urld:
            continue
        href, eid, slug = urld.group(1), urld.group(2), urld.group(3)
        city = re.search(r'''<div class="sublink">([^<]+)</div>''', p)
        place = re.search(r"<div class='sublink'>([^<]+)</div>", p)
        pret = re.search(r"<div class='pretitle'>(.*?)</div>", p, re.S)
        title = re.search(r"<div class='title'>(.*?)</div>", p, re.S)
        pret_txt = re.sub(r'<[^>]+>', '', pret.group(1)) if pret else ''
        sub2 = re.search(r"<div class='sublink2'>(.*?)</div>", p, re.S)
        suplink = re.search(r"<div class='suplink'>(.*?)</div>", p, re.S)
        dates = re.search(r"<div class='hdates short_date'>([0-9.]+)</div>", p)
        times = re.findall(r"<div class='htimes subhead'>([^<]+)</div>", p)
        # types and topics from suplink: <a href="...xtypid=...">Лекция</a>, <a href="...prjid=...">Тема</a>
        types, topics = [], []
        if suplink:
            for m in re.finditer(r'<a href="[^"]*?xtypid=(\d+)">([^<]+)</a>', suplink.group(1)):
                types.append(clean(m.group(2)).strip())
            for m in re.finditer(r'<a href="[^"]*?prjid=(\d+)">([^<]+)</a>', suplink.group(1)):
                topics.append(clean(m.group(2)).strip())
        dot = None
        if dates:
            d, mo = dates.group(1).split('.')
            dot = d + '.' + mo
        events.append({
            'id': eid,
            'slug': slug,
            'href': href,
            'url': 'https://elementy.ru' + href,
            'date_dot': dot,
            'weekday': clean(times[0]).strip() if times else None,
            'time': clean(times[1]).strip() if len(times) > 1 else None,
            'city': clean(city.group(1)).strip() if city else None,
            'place': clean(place.group(1)).strip() if place else None,
            'lecturer': clean(pret_txt).strip() if pret_txt else None,
            'title': clean(title.group(1)).strip() if title else None,
            'lectory': clean(sub2.group(1)).strip() if sub2 else None,
            'types': types,
            'topics': topics,
        })
    return events

def pick_year(day_month, weekday):
    # day_month like '16.09' -> 2026 by matching weekday
    day, mon = map(int, day_month.split('.'))
    wd_rus = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    import datetime
    for year in (2026, 2027):
        try:
            dt = datetime.date(year, mon, day)
        except ValueError:
            continue
        if wd_rus[dt.weekday()] == weekday:
            return dt
    return datetime.date(2026, mon, day)

def fix_local_html(html):
    # strip html comments (some are unbalanced, e.g. stray '-->')
    html = re.sub(r'<!--.*?-->', '', html, flags=re.S)
    html = re.sub(r'(?m)^\s*-->\s*$', '', html)
    html = html.replace('&nbsp;', '\u00a0')
    # absolve relative urls (двойные и одинарные кавычки)
    for q in ('"', "'"):
        img_paths = re.findall(r'src=' + q + r'([^' + q + r']+)' + q, html)
        for src in img_paths:
            if src.startswith(('http', 'data:')):
                continue
            full = 'https://elementy.ru/' + src if not src.startswith('/') else 'https://elementy.ru' + src
            html = html.replace('src=%s%s%s' % (q, src, q), 'src=%s%s%s' % (q, full, q))
        a_paths = re.findall(r'href=' + q + r'([^' + q + r']+)' + q, html)
        for h in a_paths:
            if h.startswith(('http', 'mailto:', '#', 'javascript:')):
                continue
            full = 'https://elementy.ru/' + h if not h.startswith('/') else 'https://elementy.ru' + h
            html = html.replace('href=%s%s%s' % (q, h, q), 'href=%s%s%s' % (q, full, q))
    return html

def parse_detail(event):
    html = S.get(event['url'], timeout=30).text
    i0 = html.find("<div class='itemblock memo'>")
    if i0 == -1:
        return {'detail_html': None, 'detail_text': None, 'annot': None,
                'date_iso': None, 'time_start': event.get('time'), 'time_end': None,
                'price_raw': None, 'price_short': None, 'reg_links': []}
    i1 = html.find("<div class='toggle'>", i0)
    if i1 == -1:
        i1 = html.find("<div class='forum", i0)
    trial = html.find("<div class='cl'></div>\n<hr>", i0)
    if i1 == -1 and trial != -1:
        i1 = trial
    if i1 == -1:
        i1 = i0 + 30000
    memo = html[i0:i1]
    memo_clean = fix_local_html(memo)

    t = re.sub(r'<[^>]+>', '', re.sub(r'<script.*?</script>', ' ', memo_clean, flags=re.S))
    text = re.sub(r'\n\s*\n+', '\n', re.sub(r'[ \t]+', ' ', clean(t).replace('\u00a0', ' '))).strip()

    # --- дата/время/место из первой строки ---
    date_iso, time_start, time_end = None, event.get('time'), None
    m = re.search(r'(Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье),\s*(\d{1,2})\s+(январ\S*|феврал\S*|март\S*|апрел\S*|ма[йя]\S*|июн\S*|июл\S*|август\S*|сентябр\S*|октябр\S*|ноябр\S*|декабр\S*)\s+(\d{4})\s+года,\s*([0-9]{1,2}:[0-9]{2})(?:\s*[–—\-]\s*([0-9]{1,2}:[0-9]{2}))?', text)
    if m:
        day, monname, year = int(m.group(2)), m.group(3), int(m.group(4))
        mon = None
        for k, v in MONTHS.items():
            if monname.lower().startswith(k[:5]):
                mon = v
                break
        if mon:
            date_iso = '%04d-%02d-%02d' % (year, mon, day)
        time_start = m.group(5)
        time_end = m.group(6)

    paras_text = []
    for p in re.findall(r'<(?:p|blockquote)[^>]*>(.*?)</(?:p|blockquote)>', memo_clean, re.S):
        pt = tag_text(p)
        if pt:
            paras_text.append(pt)

    # --- цена ---
    price_kws = re.compile(r'(стоимость|цена|вход свободн|бесплатн|билет|рубл| руб\.|₽|оплат)', re.I)
    price_sentences = []
    for para in paras_text:
        sents = re.split(r'(?<=[.!?])\s+|\n', para)
        for s in sents:
            s = s.strip()
            if s and price_kws.search(s):
                price_sentences.append(s)
    price_raw = ' '.join(price_sentences)
    price_short = short_price(' '.join(paras_text))

    # --- аннотация (blockquote) ---
    bq = re.search(r'<blockquote[^>]*>(.*?)</blockquote>', memo_clean, re.S)
    annot = tag_text(bq.group(1)) if bq else None
    if not annot:
        # fallback: самый крупный фрагмент до блока цены
        chunks = [p for p in paras_text if len(p) > 40 and not price_kws.search(p)]
        if chunks:
            annot = max(chunks, key=len)

    # --- ссылки на регистрацию ---
    reg_links = []
    for m in re.finditer(r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', memo, re.S):
        href, txt = m.group(1), tag_text(m.group(2))
        if not txt or txt == href:
            continue
        if re.search(r'(купить билет|регистрация|билет[ыа]?|записаться|регистрация и оплата)', txt, re.I):
            reg_links.append({'text': txt, 'href': href})

    # --- биография лектора (блок about authors) ---
    speakers = []
    for bm in re.finditer(r"<div class='pretitle'>(.*?)</div>\s*<div class='text'>(.*?)</div>", memo_clean, re.S):
        speakers.append({'name': tag_text(bm.group(1)), 'bio': tag_text(bm.group(2))})

    # download images
    imgs = re.findall(r'src="(https://elementy\.ru[^"]+)"', memo_clean)
    imgs += re.findall(r"src='(https://elementy\.ru[^']+)'", memo_clean)
    img_map = {}
    for iu in imgs:
        fn = re.sub(r'[^a-zA-Z0-9._-]+', '_', iu.split('//')[1].replace('/', '_'))
        local = os.path.join('assets/img', fn)
        fp = os.path.join(ROOT, 'site', local)
        if not os.path.exists(fp):
            try:
                r = S.get(iu, timeout=30)
                if r.status_code == 200:
                    with open(fp, 'wb') as f:
                        f.write(r.content)
            except Exception:
                pass
        img_map[iu] = local
    for orig, loc in img_map.items():
        memo_clean = memo_clean.replace(orig, loc)

    return {
        'detail_html': memo_clean,
        'detail_text': text,
        'annot': annot,
        'date_iso': date_iso,
        'time_start': time_start,
        'time_end': time_end,
        'price_raw': price_raw,
        'price_short': price_short,
        'reg_links': reg_links,
        'speakers': speakers,
    }

def clean_amt(a):
    return re.sub(r'\s+', ' ', a).strip()

def short_price(text):
    low = text.lower()
    # убедиться, что «бесплатно/вход свободный» — без денежной суммы
    # главная цена — фраза «Стоимость билета/участия/билетов: ...»
    m_off = re.search(r'стоимость\s+(?:билета|участия|билетов)\s*:?\s*(от\s*)?(\d[\d\s\u00a0.,]*?)\s*(?:до\s*(\d[\d\s\u00a0.,]*?)\s*)?руб', text, re.I)
    if m_off:
        off_pref, off_amt, off_to = m_off.group(1), m_off.group(2), m_off.group(3)
    else:
        moneys = re.findall(r'(от\s*)?(\d[\d\s\u00a0.,]*?)\s*руб', text, re.I)
        if not moneys:
            if re.search(r'вход свободн|бесплатн', low):
                return 'Бесплатно'
            return None
        off_pref, off_amt, off_to = moneys[0][0], moneys[0][1], None

    parts = []
    base = ('От ' if off_pref else '') + clean_amt(off_amt)
    if off_to:
        base += ' до ' + clean_amt(off_to)
    parts.append(base + ' ₽')

    # скидка студентам/школьникам
    if re.search(r'студент\S*|школьник\S*', low):
        m_st = re.search(r'(?:студентам|школьникам)\s*:?\s*(от\s*)?(\d[\d\s\u00a0.,]*?)\s*руб', text, re.I)
        if m_st:
            parts.append('студентам/школьникам ' + ('От ' if m_st.group(1) else '') + clean_amt(m_st.group(2)) + ' ₽')

    # дороже на входе
    m_door = re.search(r'(?:(?:билеты|билет)\s+)?(?:на\xa0входе|на входе|при входе)(.{0,90}?)(\d[\d\s\u00a0.,]*?)\s*руб', text, re.I)
    if m_door and m_door.group(2) and not any('на входе' in p for p in parts):
        parts = [parts[0] + ' (на входе ' + clean_amt(m_door.group(2)) + ' ₽)']

    # онлайн
    loc = low.find('трансляц')
    if loc != -1:
        window = text[max(0, loc - 150):loc + 240]
        m_on = re.search(r'(?:трансляци\S*|стоимость)\s*:?\s*(от\s*)?(\d[\d\s\u00a0.,]*?)\s*руб', window, re.I)
        if not m_on:
            nxt = re.search(r'трансляция\.?\s*(?:Стоимость|стоимость)\s*:?\s*(от\s*)?(\d[\d\s\u00a0.,]*?)\s*руб', text, re.I)
            if nxt:
                m_on = nxt
        if m_on:
            parts.append('онлайн ' + ('От ' if m_on.group(1) else '') + clean_amt(m_on.group(2)) + ' ₽')

    return ', '.join(parts)

def main():
    print('Parsing list page...')
    events = parse_list_page()
    print('Events:', len(events))
    for i, ev in enumerate(events):
        print('Fetching', ev['id'], ev['title'])
        try:
            det = parse_detail(ev)
        except Exception as e:
            print('  ERROR', e)
            det = {}
        ev.update(det)
        # год по дню недели
        if ev['date_iso']:
            y, m, d = map(int, ev['date_iso'].split('-'))
        else:
            dt = pick_year(ev['date_dot'], ev['weekday'])
            y, m, d = dt.year, dt.month, dt.day
        ev['date_iso'] = '%04d-%02d-%02d' % (y, m, d)
        time.sleep(0.4)
    events.sort(key=lambda e: (e['date_iso'], e['time_start'] or '99:99'))
    with open(os.path.join(DATA_DIR, 'events.json'), 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=1)
    print('Saved to', os.path.join(DATA_DIR, 'events.json'))

if __name__ == '__main__':
    main()