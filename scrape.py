# -*- coding: utf-8 -*-
"""Скрейпер предстоящих событий с elementy.ru/events -> data/events.json"""
import re, os, sys, json, time, unicodedata, datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
import requests

import orderlib as ORD

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

WEEKDAY_RU = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница',
              'Суббота', 'Воскресенье']

def short_date_span(raw):
    """Дата из афиши → (начало «ДД.ММ», конец «ДД.ММ» или None).

    Афиша «Элементов» показывает и одиночную дату («08.12»), и ДИАПАЗОН
    многодневного события — «11&ndash;<wbr/>13.12» или «28.10—05.11».
    Раньше разбиралась только одиночная дата: у диапазона date_dot оставался
    пустым, и scrape.py падал на pick_year (28.10.2026, событие 450818
    «Научная дача «Архэ»»). Теперь диапазон разбирается здесь.
    """
    t = clean(re.sub(r'<[^>]+>', '', raw or ''))
    t = re.sub(r'\s+', '', t.replace('\u00a0', ' '))
    for dash in ('\u2013', '\u2014', '\u2212'):
        t = t.replace(dash, '-')
    m = re.match(r'^(\d{1,2})(?:\.(\d{1,2}))?(?:-(\d{1,2})(?:\.(\d{1,2}))?)?$', t)
    if not m:
        return None, None
    d1, m1, d2, m2 = m.groups()
    if m1:
        mon = int(m1)
        start = '%02d.%02d' % (int(d1), mon)
    elif m2:
        # «11-13.12»: месяц стоит только в конце диапазона
        mon = int(m2)
        start = '%02d.%02d' % (int(d1), mon)
    else:
        return None, None
    end = '%02d.%02d' % (int(d2), int(m2) if m2 else mon) if d2 else None
    return start, end

def range_end_iso(start_iso, end_dot):
    """Дата конца многодневного события в ISO — по «ДД.ММ» и дате начала."""
    if not start_iso or not end_dot:
        return None
    try:
        day, mon = map(int, end_dot.split('.'))
        year = int(start_iso[:4])
        start_mon = int(start_iso[5:7])
    except (ValueError, IndexError):
        return None
    if mon < start_mon:      # диапазон через Новый год
        year += 1
    try:
        return '%04d-%02d-%02d' % (year, mon, day)
    except (ValueError, TypeError):
        return None


def parse_list_page():
    html = S.get('https://elementy.ru/events', timeout=40).text
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
        dates = re.search(r"<div class='hdates short_date'>(.*?)</div>", p, re.S)
        times = re.findall(r"<div class='htimes subhead'>([^<]+)</div>", p)
        # types and topics from suplink: <a href="...xtypid=...">Лекция</a>, <a href="...prjid=...">Тема</a>
        types, topics = [], []
        if suplink:
            for m in re.finditer(r'<a href="[^"]*?xtypid=(\d+)">([^<]+)</a>', suplink.group(1)):
                types.append(clean(m.group(2)).strip())
            for m in re.finditer(r'<a href="[^"]*?prjid=(\d+)">([^<]+)</a>', suplink.group(1)):
                topics.append(clean(m.group(2)).strip())
        dot, dot_end = short_date_span(dates.group(1)) if dates else (None, None)
        events.append({
            'id': eid,
            'pos': len(events),
            'slug': slug,
            'href': href,
            'url': 'https://elementy.ru' + href,
            'date_dot': dot,
            'date_dot_end': dot_end,
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
    """«ДД.ММ» (+ день недели из афиши) → дата события.

    Год подбираем по дню недели: афиша показывает только дни недели
    предстоящих событий. У МНОГОДНЕВНЫХ событий дня недели в афише нет
    (там только дата-диапазон), поэтому запасной вариант — ближайшая дата
    не раньше сегодняшней. Пустая/битая дата больше не роняет scrape.py:
    возвращаем None, а вызывающий код событие пропускает.
    """
    if not day_month:
        return None
    try:
        day, mon = map(int, str(day_month).split('.'))
    except (ValueError, AttributeError):
        return None
    today = datetime.date.today()
    years = (today.year, today.year + 1)
    if weekday:
        for year in years:
            try:
                dt = datetime.date(year, mon, day)
            except ValueError:
                continue
            if WEEKDAY_RU[dt.weekday()] == weekday:
                return dt
    for year in years:
        try:
            dt = datetime.date(year, mon, day)
        except ValueError:
            continue
        if dt >= today - datetime.timedelta(days=7):
            return dt
    return None


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
    # Страницы событий «Элементов» иногда отвечают по 35–40 с (29.10.2026:
    # 38 с при живом сайте), поэтому таймаут не 30, а 45 с — иначе scrape
    # рвёт соединение на нормально работающем сайте.
    html = S.get(event['url'], timeout=45).text
    i0 = html.find("<div class='itemblock memo'>")
    if i0 == -1:
        return {'detail_html': None, 'detail_text': None, 'annot': None,
                'date_iso': None, 'date_iso_end': None, 'time_start': event.get('time'),
                'time_end': None, 'price_raw': None, 'price_short': None,
                'reg_links': [], 'speakers': []}
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
    # Обычное событие: «Пятница, 11 декабря 2026 года, 19:00–21:00».
    # Многодневное: «Пятница—воскресенье, 11–13 декабря 2026 года, …» — без
    # времени; дата окончания нужна, чтобы событие не исчезало после первого дня.
    date_iso, date_iso_end, time_start, time_end = None, None, event.get('time'), None
    m = re.search(
        r'(?:Понедельник|Вторник|Среда|Четверг|Пятница|Суббота|Воскресенье)'
        r'(?:\s*[\u2013\u2014-]\s*[А-Яа-яЁё]+)?,\s*'
        r'(\d{1,2})(?:\s*[\u2013\u2014-]\s*(\d{1,2}))?\s+'
        r'(январ\S*|феврал\S*|март\S*|апрел\S*|ма[йя]\S*|июн\S*|июл\S*|август\S*|'
        r'сентябр\S*|октябр\S*|ноябр\S*|декабр\S*)\s+(\d{4})\s+года'
        r'(?:,\s*([0-9]{1,2}:[0-9]{2})(?:\s*[\u2013\u2014-]\s*([0-9]{1,2}:[0-9]{2}))?)?',
        text)
    if m:
        day, day_end, monname, year = int(m.group(1)), m.group(2), m.group(3), int(m.group(4))
        mon = None
        for k, v in MONTHS.items():
            if monname.lower().startswith(k[:5]):
                mon = v
                break
        if mon:
            date_iso = '%04d-%02d-%02d' % (year, mon, day)
            if day_end:
                date_iso_end = '%04d-%02d-%02d' % (year, mon, int(day_end))
        if m.group(5):
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
    price_short = short_price(' '.join(paras_text), event.get('city'), event.get('place'))

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
        'date_iso_end': date_iso_end,
        'time_start': time_start,
        'time_end': time_end,
        'price_raw': price_raw,
        'price_short': price_short,
        'reg_links': reg_links,
        'speakers': speakers,
    }

def clean_amt(a):
    return re.sub(r'\s+', ' ', a).strip()

def clean_num(a):
    """Сумма без хвостовой пунктуации: «60.» → «60», «1 200» → «1 200»."""
    return re.sub(r'\s+', ' ', a).strip().rstrip('.,').strip()

# Иностранные валюты (кроме российского рубля): (обозначение в тексте, код).
# Российский рубль обрабатывается ниже как «руб.». Иностранную валюту пишем
# КОДОМ (NIS, BYN, KZT, EUR, …) — так просил пользователь 15.10.2026: на сайте
# и в Телеграме знак валюты (₪, € и т.п.) непонятен, а код однозначен.
# Флаг word=True — «словесное» обозначение (евро, тенге, шекель): его находим,
# только если рядом стоит ценовое слово, чтобы не спутать с прозой
# (например, «до евро и современных проблем»).
FOREIGN_CURRENCIES = [
    (r'₪|\bNIS\b|\bILS\b', 'NIS'),
    (r'шекел\w*', 'NIS', True),
    (r'₸|\bKZT\b', 'KZT'),
    (r'тенге|тенг[аеи]\b', 'KZT', True),
    (r'€|\bEUR\b', 'EUR'),
    (r'евро\b', 'EUR', True),
    (r'\bUSD\b|\$', 'USD'),
    (r'доллар\w*', 'USD', True),
    (r'£|\bGBP\b', 'GBP'),
    (r'фунт\w*', 'GBP', True),
    (r'₴|\bUAH\b', 'UAH'),
    (r'гривн\w*', 'UAH', True),
    (r'\bBYN\b|\bBr\b', 'BYN'),
    (r'бел\.?\s*руб\w*|белорусск\w*\s+руб\w*', 'BYN', True),
    (r'\bPLN\b', 'PLN'),
    (r'злот\w*', 'PLN', True),
    (r'₺|\bTRY\b', 'TRY'),
    (r'лир\w*', 'TRY', True),
    (r'\bCHF\b', 'CHF'),
    (r'франк\w*', 'CHF', True),
    (r'\bHUF\b', 'HUF'),
    (r'форинт\w*', 'HUF', True),
    (r'\bRON\b', 'RON'),
    (r'леев|лея|лей\b', 'RON', True),
    (r'\bBGN\b', 'BGN'),
    (r'лев[аоы]?\b', 'BGN', True),
    (r'\bRSD\b', 'RSD'),
    (r'динар\w*', 'RSD', True),
]

# Страна/город события → ожидаемая валюта цены (правило пользователя
# 15.10.2026: цена, если она не в руб., должна соответствовать валюте страны,
# где проходит событие). У «Элементов» иностранные события указывают страну
# прямо в поле города («Израиль»), а российские — город («Москва»). Незнакомое
# место считаем Россией (валюта — рубль).
LOCATION_CURRENCY = {
    'россия': 'RUB',
    'израиль': 'NIS', 'хайфа': 'NIS', 'тель-авив': 'NIS', 'иерусалим': 'NIS',
    'казахстан': 'KZT', 'алматы': 'KZT', 'астана': 'KZT',
    'беларусь': 'BYN', 'белоруссия': 'BYN', 'минск': 'BYN',
    'украина': 'UAH', 'киев': 'UAH',
    'сша': 'USD', 'америка': 'USD',
    'великобритания': 'GBP', 'англия': 'GBP', 'лондон': 'GBP',
    'турция': 'TRY', 'стамбул': 'TRY',
    'польша': 'PLN', 'варшава': 'PLN',
    'швейцария': 'CHF', 'цюрих': 'CHF',
    'венгрия': 'HUF', 'будапешт': 'HUF',
    'румыния': 'RON', 'бухарест': 'RON',
    'болгария': 'BGN', 'софия': 'BGN',
    'сербия': 'RSD', 'белград': 'RSD',
    'германия': 'EUR', 'франция': 'EUR', 'италия': 'EUR', 'испания': 'EUR',
    'португалия': 'EUR', 'нидерланды': 'EUR', 'бельгия': 'EUR', 'австрия': 'EUR',
    'ирландия': 'EUR', 'греция': 'EUR', 'финляндия': 'EUR', 'эстония': 'EUR',
    'латвия': 'EUR', 'литва': 'EUR', 'словакия': 'EUR', 'словения': 'EUR',
    'хорватия': 'EUR', 'мальта': 'EUR', 'кипр': 'EUR', 'люксембург': 'EUR',
}

# Площадки-университеты: если цена не указана — событие считаем бесплатным
# (правило пользователя 15.10.2026, пример — Европейский университет, 450726).
UNIVERSITY_MARKERS = ('университет', 'мгу', 'спбгу', 'нгу', 'вшэ', 'мгимо',
                      'рудн', 'мфти', 'мгту', 'мгюа', 'мгпу')

# «множитель» после суммы — это не цена, а оборот прозы: «бюджет $ 2 млрд».
_MAGNITUDE = re.compile(
    r'\s*(?:млрд|млн|тыс|трлн|миллиард\w*|миллион\w*|тысяч\w*'
    r'|billion|million|trillion|bln|bn|mln)\b', re.I)

# коды валют, которые встречаются в итоговой цене («60 NIS», «от 30 EUR»)
_CUR_CODE = re.compile(r'\b(NIS|KZT|EUR|USD|GBP|UAH|BYN|PLN|TRY|CHF|HUF|RON|BGN|RSD)\b')

# ценовое слово рядом со «словесной» валютой («стоимость 30 евро»)
_PRICE_CONTEXT = re.compile(r'стоимост|цен|билет|вход|оплат|участи|стоят|руб|[:—–-]', re.I)

def event_currency(city, place):
    """Ожидаемая валюта цены по стране события (правило пользователя 15.10.2026)."""
    blob = ('%s %s' % (city or '', place or '')).lower().replace('ё', 'е')
    blob = re.sub(r'онлайн', ' ', blob)
    for name, cur in LOCATION_CURRENCY.items():
        if name in blob:
            return cur
    return 'RUB'

def is_university(city, place):
    """True, если событие проходит в вузе (тогда отсутствие цены = бесплатно)."""
    blob = ('%s %s' % (city or '', place or '')).lower().replace('ё', 'е')
    return any(m in blob for m in UNIVERSITY_MARKERS)

def foreign_price(text, country_cur=None):
    """Цена в иностранной валюте → «N КОД» (правило пользователя 15.10.2026).

    Понимает «60 ₪», «₪ 60», «60 NIS», «от 80 шекелей», «30 €», «50 тенге»,
    «25 бел. руб.», «20 фунтов» и т.п. Возвращает сумму с кодом валюты
    (NIS, BYN, KZT, EUR …), а не со знаком.

    country_cur — ожидаемая валюта страны события (см. event_currency): цена
    принимается ТОЛЬКО в этой валюте, иначе это оборот прозы («бюджет $ 2 млрд»).
    """
    if not text:
        return None
    for row in FOREIGN_CURRENCIES:
        token, code = row[0], row[1]
        if country_cur and code != country_cur:
            continue
        if len(row) > 2:  # словесное обозначение — нужен ценовой контекст
            for m in re.finditer(r'(от\s*)?(\d[\d\s\u00a0.,]*?)\s*(?:%s)' % token, text, re.I):
                if _MAGNITUDE.match(text, m.end()):
                    continue
                before = text[max(0, m.start(2) - 45):m.start(2)]
                if _PRICE_CONTEXT.search(before):
                    return ('От ' if m.group(1) else '') + clean_num(m.group(2)) + ' ' + code
            continue
        # сумма перед обозначением валюты: «60 ₪», «от 80 €»
        m = re.search(r'(от\s*)?(\d[\d\s\u00a0.,]*?)\s*(?:%s)' % token, text)
        if m and not _MAGNITUDE.match(text, m.end()):
            return ('От ' if m.group(1) else '') + clean_num(m.group(2)) + ' ' + code
        # обозначение валюты перед суммой: «₪ 60», «€ 30»
        m = re.search(r'(?:%s)\s*(\d[\d\s\u00a0.,]*)' % token, text)
        if m and not _MAGNITUDE.match(text, m.end()):
            return clean_num(m.group(1)) + ' ' + code
    return None

def price_currency(ps):
    """Код валюты итоговой цены: «руб.» → RUB, «60 NIS» → NIS, иначе None."""
    if not ps:
        return None
    if re.search(r'рубл|руб\b|₽', ps, re.I):
        return 'RUB'
    m = _CUR_CODE.search(ps)
    return m.group(1) if m else None

def check_price_country(events):
    """Проверка: не-рублёвая цена должна соответствовать стране события.

    Правило пользователя 15.10.2026. Возвращает список проблем (пусто — всё ок):
    1) итоговая цена в валюте, не совпадающей со страной события;
    2) в тексте есть цена в иностранной валюте, но страна её не подтверждает —
       возможно, цену отбросили зря (пора уточнить таблицу `LOCATION_CURRENCY`).
    """
    probs = []
    for e in events:
        city, place = e.get('city'), e.get('place')
        want = event_currency(city, place)
        ps = (e.get('price_short') or '').strip()
        if ps and not re.search(r'бесплатн|по билетам', ps, re.I):
            pc = price_currency(ps)
            if pc and pc != want:
                probs.append('%s «%s»: цена «%s» (%s), а по стране «%s» ожидается %s'
                             % (e.get('id'), (e.get('title') or '')[:50], ps, pc,
                                city or '?', want))
                continue
        txt = e.get('detail_text') or ''
        fp_any = foreign_price(txt, None)
        if fp_any and not foreign_price(txt, want):
            probs.append('%s «%s»: в тексте цена «%s», а по стране «%s» ожидается '
                         '%s — проверьте страну' % (e.get('id'),
                                                    (e.get('title') or '')[:50],
                                                    fp_any, city or '?', want))
    return probs

def amount_value(a):
    """Числовое значение суммы для сравнения цен (900, 2 900, 1.5 тыс → 1500)."""
    s = clean_amt(a).replace('\u00a0', ' ').replace(' ', '')
    s = s.replace(',', '.').replace('\u00a0', '')
    m = re.match(r'^(\d+(?:\.\d+)?)', s)
    if not m:
        return None
    v = float(m.group(1))
    if re.search(r'тыс', clean_amt(a), re.I):
        v *= 1000
    return int(round(v))

def short_price(text, city=None, place=None):
    low = text.lower()
    # цена в иностранной валюте (шекель, тенге, евро …) — до разбора «руб.»;
    # принимаем ТОЛЬКО валюту страны события (правило пользователя 15.10.2026)
    fp = foreign_price(text, event_currency(city, place))
    if fp:
        return fp
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
            # «Вход по билетам в музей» — не бесплатно: цену берём из самой фразы,
            # но без служебного слова «Вход» (его добавляет шаблон сайта)
            m_ticket = re.search(r'вход\s+по\s+билетам\s+([^.;\n]{2,40})', low)
            if m_ticket:
                return 'По билетам ' + m_ticket.group(1).strip()
            # вуз без указанной цены — считаем бесплатным (правило 15.10.2026)
            if is_university(city, place):
                return 'Бесплатно'
            return None
        off_pref, off_amt, off_to = moneys[0][0], moneys[0][1], None

    parts = []
    base = ('От ' if off_pref else '') + clean_amt(off_amt)
    if off_to:
        base += ' до ' + clean_amt(off_to)
    parts.append(base + ' руб.')
    # числовое значение главной цены — чтобы не повторять её же в других вариантах
    base_num = amount_value(off_amt)

    # скидка студентам/школьникам
    if re.search(r'студент\S*|школьник\S*', low):
        m_st = re.search(r'(?:студентам|школьникам)\s*:?\s*(от\s*)?(\d[\d\s .,]*?)\s*руб', text, re.I)
        if m_st:
            parts.append('студентам/школьникам ' + ('От ' if m_st.group(1) else '') + clean_amt(m_st.group(2)) + ' руб.')

    # дороже на входе
    m_door = re.search(r'(?:(?:билеты|билет)\s+)?(?:на входе|на входе|при входе)(.{0,90}?)(\d[\d\s .,]*?)\s*руб', text, re.I)
    if m_door and m_door.group(2) and not any('на входе' in p for p in parts) \
            and amount_value(m_door.group(2)) != base_num:
        parts = [parts[0] + ' (на входе ' + clean_amt(m_door.group(2)) + ' руб.)']

    # онлайн: ищем цену рядом со словом «трансляция» (там она обычно и стоит),
    # иначе — рядом со словом «онлайн»
    m_on = None
    loc = low.find('трансляц')
    if loc != -1:
        window = text[max(0, loc - 150):loc + 240]
        m_on = re.search(r'(?:трансляци\S*|стоимость)\s*:?\s*(от\s*)?(\d[\d\s .,]*?)\s*руб', window, re.I)
    if not m_on:
        m_on = re.search(r'трансляция\.?\s*(?:Стоимость|стоимость)\s*:?\s*(от\s*)?(\d[\d\s .,]*?)\s*руб', text, re.I)
    if not m_on:
        m_on = re.search(r'(?:онлайн|online)\s*:?\s*(от\s*)?(\d[\d\s .,]*?)\s*руб', text, re.I)
    # отдельная цена «онлайн» нужна, только если она действительно другая:
    # у событий «только онлайн» цена трансляции и есть основная цена,
    # и повторять её вторым числом нельзя («900 руб., онлайн 900 руб.»)
    if m_on and amount_value(m_on.group(2)) != base_num:
        parts.append('онлайн ' + ('От ' if m_on.group(1) else '') + clean_amt(m_on.group(2)) + ' руб.')

    return ', '.join(parts)

def norm_key(s):
    if not s:
        return ''
    s = unicodedata.normalize('NFKC', str(s)).lower().replace('ё', 'е')
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^\w\s]', ' ', s, flags=re.UNICODE)
    return re.sub(r'\s+', ' ', s).strip()

def describe_change(old, fresh):
    """Короткая сверка по основным полям. Возвращает список изменившихся полей."""
    keys = []
    for k in ('title', 'lecturer', 'date_iso', 'date_iso_end', 'lectory', 'city', 'place'):
        if norm_key(old.get(k)) != norm_key(fresh.get(k)):
            keys.append(k)
    # цена: сверяем итоговую цену (её показывает сайт). Смена только формулировки
    # в исходном тексте без смены самой цены перепорождать анонс не должна —
    # для этого сравниваем price_short, а не price_raw.
    if norm_key(old.get('price_short')) != norm_key(fresh.get('price_short')):
        keys.append('price')
    return keys

def progress(pct, msg):
    print('PROGRESS:%d:%s' % (pct, msg), flush=True)

def load_old_events():
    fp = os.path.join(DATA_DIR, 'events.json')
    if os.path.exists(fp):
        try:
            return json.load(open(fp, encoding='utf-8'))
        except Exception:
            return []
    return []

def write_report(report):
    with open(os.path.join(DATA_DIR, 'update_report.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)

def enrich(ev, sleep=0.4):
    """Скачать страницу события и разобрать её (общие поля + год по дню недели).

    Один сетевой сбой не должен рушить всё обновление и не должен выглядеть
    как «событие исчезло с «Элементов» (28.10.2026: три события пропали из
    файла после одиночного таймаута) — пробуем дважды.
    """
    print('Fetching', ev.get('id'), (ev.get('title') or '')[:60], flush=True)
    det = None
    for attempt in (1, 2):
        try:
            det = parse_detail(ev)
            break
        except Exception as e:
            print('  ERROR (попытка %d): %s' % (attempt, e), flush=True)
            if attempt == 1:
                time.sleep(3)
    if det is None:
        return None
    ev.update(det)
    # год по дню недели
    if ev.get('date_iso'):
        y, m, d = map(int, ev['date_iso'].split('-'))
    else:
        dt = pick_year(ev.get('date_dot'), ev.get('weekday'))
        if dt is None:
            print('  ERROR: не удалось определить дату (date_dot=%r)'
                  % (ev.get('date_dot'),), flush=True)
            return None
        y, m, d = dt.year, dt.month, dt.day

    ev['date_iso'] = '%04d-%02d-%02d' % (y, m, d)
    # дата окончания многодневного события: из строки дня на странице события,
    # иначе — из диапазона в афише («11–13.12»)
    if not ev.get('date_iso_end'):
        ev['date_iso_end'] = range_end_iso(ev['date_iso'], ev.get('date_dot_end'))
    if sleep:
        time.sleep(sleep)
    return ev


def reload_ids(ids):
    """Перезагрузить со страницы «Элементов» только перечисленные события.

    Используется кнопкой «Перезагрузить» на странице события: остальные
    события не трогаем, обновляем лишь те, что перечислены в ids.
    """
    today = datetime.date.today().isoformat()
    old = load_old_events()
    by_id = {e['id']: e for e in old}
    changed, missing = [], []
    n = len(ids)
    for i, eid in enumerate(ids):
        eid = str(eid).strip()
        o = by_id.get(eid)
        if o is None:
            missing.append(eid)
            continue
        progress(10 + int(70 * (i + 1) / max(n, 1)),
                 'Событие %d из %d: %s' % (i + 1, n, (o.get('title') or '')[:40]))
        f = enrich(dict(o), sleep=0.2)
        if f is None or not f.get('detail_html'):
            continue
        keys = describe_change(o, f)
        if not keys:
            progress(85, 'Без изменений: %s' % (o.get('title') or '')[:40])
            continue
        f['updated'] = True
        f['updated_at'] = today
        by_id[eid] = f
        changed.append({'id': eid, 'title': f.get('title'), 'fields': keys})
        progress(85, 'Обновлено: %s' % (f.get('title') or '')[:40])

    new_events = [by_id[e['id']] for e in old if e['id'] in by_id]
    # список афиши здесь не перечитываем, поэтому ord остаётся прежним —
    # перечитываем только ради порядка сортировки в файле
    new_events.sort(key=ORD.ord_key)
    # Самый большой номер события на «Элементах» в последнем обновлении
    max_el_id = 0
    for e in new_events:
        eid = e.get('id')
        try:
            if eid is not None and str(eid).isdigit():
                vid = int(eid)
                if vid > max_el_id:
                    max_el_id = vid
        except Exception:
            pass
    with open(os.path.join(DATA_DIR, 'events.json'), 'w', encoding='utf-8') as f:
        json.dump(new_events, f, ensure_ascii=False, indent=1)
    report = {'date': today, 'added': [], 'changed': changed, 'removed': [],
              'missing': missing, 'max_el_id': max_el_id, 'total': len(new_events)}
    write_report(report)
    print('REPORT: перезагружено %d, без изменений %d, всего событий %d'
          % (len(changed), n - len(changed) - len(missing), len(new_events)))
    progress(100, 'Данные обновлены.')
    return report

def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--ids':
        ids = [x for x in re.split(r'[,\s]+', ' '.join(sys.argv[2:])) if x]
        reload_ids(ids)
        return
    progress(2, 'Загрузка списка событий с elementy.ru…')
    events = parse_list_page()
    progress(10, 'Найдено %d событий, скачиваю страницы…' % len(events))
    n = len(events)
    fresh_list, failed = [], []
    for i, ev in enumerate(events):
        if enrich(ev) is None:
            # Страница не скачалась / дата не разобрана. Событие не выбрасываем:
            # для старой записи останутся прежние данные (см. ниже).
            failed.append({'id': ev.get('id'), 'title': ev.get('title')})
            progress(10 + int(60 * (i + 1) / max(n, 1)),
                     'Событие %d из %d: не удалось прочитать, остаются прежние данные — %s'
                     % (i + 1, n, (ev.get('title') or '')[:34]))
            continue
        fresh_list.append(ev)
        progress(10 + int(60 * (i + 1) / max(n, 1)), 'Событие %d из %d: %s' % (i + 1, n, (ev.get('title') or '')[:40]))
        time.sleep(0.4)
    events = fresh_list
    failed_ids = {f['id'] for f in failed if f.get('id')}


    today = datetime.date.today().isoformat()
    fresh = events
    # порядок на «Элементах»: ord по позиции в афише, внутри каждой пары
    # дата+время. Считаем ДО слияния, чтобы старые записи получили свежий
    # порядок, даже если описание события не менялось.
    ORD.assign_order(fresh)
    fresh_by_id = {e['id']: e for e in fresh}
    fresh_ord = {e['id']: e['ord'] for e in fresh}
    old_by_id = {e['id']: e for e in load_old_events()}

    new_events, added, changed, removed = [], [], [], []

    # события, уже бывшие на сайте
    for oid, o in old_by_id.items():
        # многодневное событие живёт до последнего дня (date_iso_end)
        o_end = o.get('date_iso_end') or o.get('date_iso')
        if (o_end or '9999-99-99') < today:
            removed.append({'id': oid, 'title': o.get('title'), 'reason': 'событие уже прошло'})
            continue
        f = fresh_by_id.get(oid)
        if f is None:
            if oid in failed_ids:
                # страница не скачалась — не считаем, что событие исчезло:
                # оставляем прежнюю запись как есть
                new_events.append(o)
                continue
            removed.append({'id': oid, 'title': o.get('title'), 'reason': 'больше нет на elementy.ru'})
            continue
        keys = describe_change(o, f)
        if keys:
            ev = dict(f)
            ev['updated'] = True
            ev['updated_at'] = today
            changed.append({'id': oid, 'title': ev.get('title'), 'fields': keys})
            progress(75, 'Обновлено: %s' % (ev.get('title') or '')[:40])
            new_events.append(ev)
        else:
            new_events.append(o)  # описания не трогаем, если основное не изменилось
            progress(75, 'Без изменений: %s' % (o.get('title') or '')[:40])

    # новые события
    for f in fresh:
        if f['id'] not in old_by_id:
            added.append({'id': f['id'], 'title': f.get('title')})
            new_events.append(f)

    # Свежий порядок «Элементов» применяем ко ВСЕМ событиям, включая те,
    # чьи описания не изменились: иначе у них остался бы старый ord и после
    # перестановки на «Элементах» появились бы дубли (одно место — дважды).
    for ev in new_events:
        oid = ev.get('id')
        if oid in fresh_ord:
            ev['ord'] = fresh_ord[oid]

    new_events.sort(key=ORD.ord_key)
    # «Элементы» могли переставить события внутри одной даты-времени — сообщаем
    order_changed = ORD.diff_order(old_by_id, fresh_by_id, fresh_ord)
    # Самый большой номер события на «Элементах» в последнем обновлении
    max_el_id = 0
    for e in new_events:
        eid = e.get('id')
        try:
            if eid is not None and str(eid).isdigit():
                vid = int(eid)
                if vid > max_el_id:
                    max_el_id = vid
        except Exception:
            pass
    for ev in new_events:
        ev.pop('pos', None)  # позиция в афише — только для расчёта ord
    with open(os.path.join(DATA_DIR, 'events.json'), 'w', encoding='utf-8') as f:
        json.dump(new_events, f, ensure_ascii=False, indent=1)

    report = {
        'date': today,
        'added': added,
        'changed': changed,
        'removed': removed,
        'order_changed': order_changed,
        'max_el_id': max_el_id,
        'total': len(new_events),
        'failed': failed,
    }
    write_report(report)

    print('REPORT: добавлено %d, изменено %d, удалено %d, всего событий %d'
          % (len(added), len(changed), len(removed), len(new_events)))
    if failed:
        print('REPORT: не удалось прочитать %d событий (оставлены прежние данные):'
              % len(failed))
        for f in failed:
            print('  %s %s' % (f.get('id'), (f.get('title') or '')[:60]))
    if order_changed:
        print('REPORT: «Элементы» переставили %d событий внутри одной даты-времени:'
              % len(order_changed))
        for c in order_changed:
            print('  %s %s: %s было %d, стало %d — %s'
                  % (c['date'], c['time'], c['id'], c['was'], c['now'],
                     (c.get('title') or '')[:50]))
    problems = ORD.check_order(new_events)
    if problems:
        print('REPORT: ОШИБКА ПОРЯДКА (нужна правка):')
        for p in problems:
            print('  ' + p)
    price_problems = check_price_country(new_events)
    if price_problems:
        print('REPORT: ПРОВЕРКА ЦЕН (валюта ≠ стране события):')
        for p in price_problems:
            print('  ' + p)
    progress(100, 'Данные обновлены.')

if __name__ == '__main__':
    main()