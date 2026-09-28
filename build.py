# -*- coding: utf-8 -*-
"""Сборка статического сайта из data/events.json -> site/"""
import os, re, json, datetime, html as H, shutil
from urllib.parse import urlparse
import protolib as PL

if hasattr(__import__('sys').stdout, 'reconfigure'):
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data', 'events.json')
SITE = os.path.join(ROOT, 'site')
EVENT_DIR = os.path.join(SITE, 'event')
JS_DIR = os.path.join(SITE, 'js')
CSS_DIR = os.path.join(SITE, 'css')
os.makedirs(EVENT_DIR, exist_ok=True)
os.makedirs(JS_DIR, exist_ok=True)
os.makedirs(CSS_DIR, exist_ok=True)

def progress(pct, msg):
    print('PROGRESS:%d:%s' % (pct, msg), flush=True)

evs = json.load(open(DATA, encoding='utf-8'))
evs.sort(key=lambda e: (e['date_iso'], e['time_start'] or '99:99'))
for e in evs:
    e['kind'] = 'el'
    e['hidden'] = False

MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
MONTHS_NOM = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
WEEKDAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

NBSP_ENTITIES = ('&nbsp;', '&#160;', '&#xa0;', '&#XA0;', '&#xA0;')


def nbsp_to_char(s):
    """Сущности неразбиваемого пробела → настоящий пробел U+00A0.

    В данных проекта (prototype.json) неразбиваемый пробел ВСЕГДА записан
    текстом `&nbsp;` — так его видно глазами и он не теряется при копировании
    (решение пользователя 28.09.2026). А при выводе текста в HTML мы обязаны
    вернуть настоящий U+00A0, иначе на странице появится слово «&nbsp;».
    """
    for e in NBSP_ENTITIES:
        s = s.replace(e, '\u00A0')
    return s


def esc(s):
    return H.escape(nbsp_to_char(s or ''))

def fmt_date_ru(iso):
    y, m, d = map(int, iso.split('-'))
    return '%d %s %d' % (d, MONTHS_GEN[m - 1], y)

def fmt_date_short(iso):
    y, m, d = map(int, iso.split('-'))
    return '%02d.%02d' % (d, m)

def fmt_date_num(iso):
    y, m, d = map(int, iso.split('-'))
    return '%02d.%02d.%d' % (d, m, y)

def fmt_time(e):
    t = e.get('time_start') or ''
    if e.get('time_end'):
        t += '\u2013' + e['time_end']
    return t

def day_midnight_msk(iso):
    """Unix-время 00:00 московского времени для даты iso (YYYY-MM-DD)."""
    dt = datetime.datetime.strptime(iso + ' 00:00', '%Y-%m-%d %H:%M')
    return int(dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=3))).timestamp())

def clean_place(s):
    """Убрать инициалы людей из названий площадок: «им. Н. А. Некрасова» → «им. Некрасова»."""
    return re.sub(r'\b([А-ЯЁ])\.\s*([А-ЯЁ])\.\s*', '', s or '').strip()

def price_txt(p):
    p = (p or '').strip()
    if not p:
        return ''
    if 'бесплатно' in p.lower():
        return '(бесплатно)'
    # убираем пробелы между группами цифр: «10 000» → «10000» (только в посте)
    t = re.sub(r'(?<=\d)\s+(?=\d)', '', p).replace('₽', 'руб.').strip()
    # диапазон «от X до Y руб.» → «от X руб.» (только нижняя граница)
    if re.search(r'\sдо\s', t, flags=re.I):
        t = re.split(r'\sдо\s', t, maxsplit=1, flags=re.I)[0].strip() + ' руб.'
    t = re.sub(r'\s{2,}', ' ', t).strip()
    if t and t[0].isupper():
        t = t[0].lower() + t[1:]
    return '(' + t + ')'

POST_STOP = {'лекторий', 'лектория', 'лектории', 'имени', 'открытый',
             'центральный', 'сообщество', 'сообщества', 'научно', 'популярный'}

def post_keywords(s):
    s = (s or '').lower()
    s = re.sub(r'[«»"“”(),:;.\-–—]', ' ', s)
    return [w for w in s.split() if len(w) > 2 and w not in POST_STOP]

def kw_prefix(a, b):
    n = min(len(a), len(b))
    return (a[:4] == b[:4]) if n >= 4 else (a == b)

def post_subtitle(e):
    """Подзаголовок (поле lectory) — показываем в скобках, если он нетривиален
    по сравнению с площадкой (не повторяет её)."""
    lec = (e.get('lectory') or '').strip()
    if not lec:
        return ''
    place = (e.get('place') or '').strip()
    if not place:
        return ' (' + lec + ')'
    lkeys = post_keywords(lec)
    pkeys = post_keywords(place)
    if not lkeys or not pkeys:
        return ''
    covered = sum(any(kw_prefix(lk, pk) for pk in pkeys) for lk in lkeys)
    if covered == len(lkeys):
        return ''
    return ' (' + lec + ')'

def month_id(date):
    return 'm-%04d-%02d' % (date.year, date.month)

def month_label_ym(y, m):
    return '%s %d' % (MONTHS_NOM[m - 1], y)

def week_start(date):
    return date - datetime.timedelta(days=date.weekday())

def month_bounds(date):
    y, m = date.year, date.month
    first = datetime.date(y, m, 1)
    last = (datetime.date(y + 1, 1, 1) if m == 12 else datetime.date(y, m + 1, 1)) - datetime.timedelta(days=1)
    return first, last

def week_range_label(lo, hi):
    if lo == hi:
        return '%02d.%02d' % (lo.day, lo.month)
    return '%02d\u2013%02d.%02d' % (lo.day, hi.day, lo.month)

def month_weeks(y, m):
    first, last = month_bounds(datetime.date(y, m, 1))
    weeks = {}
    d = first
    while d <= last:
        weeks.setdefault(week_start(d), []).append(d)
        d += datetime.timedelta(days=1)
    out = []
    total = 0
    for ws in sorted(weeks):
        days = weeks[ws]
        label = week_range_label(days[0], days[-1])
        out.append((ws, label, days))
        total += len(days)
    assert total == (last - first).days + 1, 'Недели месяца %d-%02d не покрывают месяц целиком' % (y, m)
    return out

def week_id(y, m, ws):
    return 'w-%04d-%02d-%s' % (y, m, ws.isoformat())

def url_detail(e, prefix=''):
    return prefix + 'event/%s.html' % (e.get('slug') or e['id'])

def annot_snippet(e, limit=260):
    a = re.sub(r'\s+', ' ', (e.get('annot') or '')).strip()
    if not a:
        return ''
    if len(a) > limit:
        a = a[:limit].rstrip(' ,;:') + '…'
    return a

# ------------------------------------------------------------------ прототипы

items = list(evs)          # события «Элементов» + прототипы (для списка и страниц)
PROTO_SUMMARY = {'shown': 0, 'hidden': 0, 'archived': 0, 'dup': 0, 'total': 0}

def proto_item(p, st):
    """Данные прототипа -> то же, что у события «Элементов» (для карточки)."""
    return {
        'id': p['id'],
        'kind': 'proto',
        'slug': PL.slugify(p['id']),
        'date_iso': p['date_iso'],
        'weekday': WEEKDAYS[datetime.date(*map(int, p['date_iso'].split('-'))).weekday()],
        'time_start': p.get('time_start') or '',
        'time_end': p.get('time_end') or '',
        'date_dot': fmt_date_short(p['date_iso']),
        'city': p.get('city') or '',
        'place': p.get('place') or '',
        'lecturer': p.get('lecturer') or '',
        'title': p.get('title') or '',
        'lectory': p.get('lectory') or '',
        'types': p.get('types') or [],
        'topics': p.get('topics') or [],
        'price_short': p.get('price_short') or '',
        'annot': p.get('annot') or '',
        'url': p.get('url') or '',
        'proto': p,
        'st': st,
        'hidden': st['hidden'],
        'dup': st['dup'],
        'dup_of': st['dup_of'],
        'dup_hits': st['dup_hits'],
        'comment': st['comment'],
        'feedback': st['feedback'],
        'rebuild': st['rebuild'],
    }

def load_prototypes():
    """Читает data/prototypes/*/prototype.json, применяет состояние пользователя,
    прячет прошедшие (в архив) и дубли «Элементов»."""
    global items
    items = list(evs)
    state = PL.load_state()
    notes = []
    for pid in PL.list_ids():
        try:
            p = PL.load(pid)
        except Exception as e:
            print('ПРОТОТИП %s: не читается (%s)' % (pid, e))
            continue
        PROTO_SUMMARY['total'] += 1
        if PL.is_past(p.get('date_iso')):
            PL.archive(pid)
            PROTO_SUMMARY['archived'] += 1
            notes.append('%s — событие уже прошло, перенесён в архив' % pid)
            continue
        st = PL.state_of(state, pid)
        hits, dup = PL.find_duplicate(p, evs)
        st['dup'] = bool(hits)
        st['dup_of'] = dup['id'] if dup else ''
        st['dup_hits'] = hits or []
        st['dup_url'] = dup['url'] if dup else ''
        it = proto_item(p, st)
        if hits:
            PROTO_SUMMARY['dup'] += 1
            notes.append('%s — дубль на «Элементах» (ID %s: %s), скрыт автоматически'
                         % (pid, dup['id'], ', '.join(hits)))
        if st['hidden'] or hits:
            PROTO_SUMMARY['hidden'] += 1
            it['hidden'] = True
        else:
            PROTO_SUMMARY['shown'] += 1
        items.append(it)
    items.sort(key=lambda e: (e['date_iso'], e.get('time_start') or '99:99'))
    return notes

def proto_lectorium(p):
    """Название лектория (канала) прототипа: поле 6.3, иначе подзаголовок.

    Если лектория нет (поле 6.3 = «—»), на карточке строка не выводится:
    лектория у события нет, показывать прочерк незачем.

    Это строка карточки. ФИЛЬТР фильтрует не по ней, а по организатору —
    см. proto_organizer().
    """
    v = (PL.field(p, '6.3') or PL.field(p, '6') or p.get('lectory') or '').strip()
    if v in ('', '—', '-', '–'):
        return ''
    return nbsp_to_char(v)


# Организатор = тот, чей это сайт или Timepad (решение пользователя 28.09.2026).
# Свой домен → понятное название; Timepad → имя аккаунта (поддомен).
ORGANIZER_NAMES = {
    'spbu.ru': 'Санкт-Петербургский государственный университет',
    'festivalnauki.ru': 'Фестиваль науки NAUKA 0+',
}
# Эти сайты организатором не считаются: «Элементы» — витрина, а не организатор.
NOT_ORGANIZER = ('elementy.ru', 'elementy.com')


def _host(url):
    u = re.sub(r'^\w+://', '', (url or '').strip())
    return u.split('/')[0].lower().split('@')[-1].split(':')[0]


def proto_organizer(p):
    """Название организатора прототипа — по источникам (сайт или Timepad).

    Порядок выбора источника: сначала сайт организатора (не Timepad), потом
    аккаунт Timepad, потом — если источников нет вовсе — площадка/город.
    Например: spbu.ru → «Санкт-Петербургский государственный университет»,
    filial-eltsin-tsentra-v-m.timepad.ru → «filial-eltsin-tsentra-v-m».
    """
    urls = list(p.get('sources') or [])
    if p.get('url'):
        urls.append(p['url'])
    hosts, seen = [], set()
    for u in urls:
        h = _host(u)
        if h and h not in seen:
            seen.add(h)
            hosts.append(h)
    own = [h for h in hosts if h not in NOT_ORGANIZER and not h.endswith('.timepad.ru')]
    pads = [h for h in hosts if h.endswith('.timepad.ru')]
    for h in own + pads:
        if h in ORGANIZER_NAMES:
            return ORGANIZER_NAMES[h]
        if h.endswith('.timepad.ru'):
            return h[:-len('.timepad.ru')]
        return h
    city = (p.get('city') or '').strip()
    place = (p.get('place') or '').strip()
    if city and place and city.lower() not in place.lower():
        return city + ', ' + place
    return place or city or 'ОНЛАЙН'


def proto_filter_key(p):
    """Идентификатор для фильтра «Организаторы» (см. proto_organizer)."""
    return proto_organizer(p)


def organizers_of_prototypes():
    cnt = {}
    for it in items:
        if it.get('kind') != 'proto':
            continue
        name = proto_filter_key(it['proto'])
        cnt[name] = cnt.get(name, 0) + 1
    return sorted(cnt.items())


def card(e, prefix=''):
    if e.get('kind') == 'proto':
        return proto_card(e, prefix)
    dt = datetime.date(*map(int, e['date_iso'].split('-')))
    wd = WEEKDAYS[dt.weekday()]
    supl = []
    if e.get('types'):
        supl.append(', '.join(e['types']))
    if e.get('topics'):
        supl.append(', '.join(e['topics']))
    sup_txt = ' • '.join(supl)
    upd = ''
    if e.get('updated'):
        upd = f'<div class="badge-upd">обновлено {esc(e.get("updated_at", ""))}</div>'
    return f'''<div class="event" data-kind="el" data-id="{esc(e['id'])}" data-date="{esc(e['date_iso'])}">
  <div class="edate">
    <div class="hday">{esc(fmt_date_short(e['date_iso']))}</div>
    <div class="hmeta">{esc(wd)}</div>
    <div class="hmeta">{esc(fmt_time(e))}</div>
    <div class="hcity">{esc(e['city'] or '')}</div>
    <div class="hlink"><a href="{esc(e['url'])}" target="_blank" rel="noopener">{esc(e['id'])}</a></div>
  </div>
  <div class="edesc">
    <div class="suplink">{esc(sup_txt)}</div>
    <a class="nohover" href="{url_detail(e, prefix)}">
      <div class="pretitle">{esc(e['lecturer'] or '')}</div>
      <div class="title">{esc(e['title'] or '')}</div>
      <div class="lectory">{esc(e['lectory'] or '')}</div>
    </a>
    <div class="sublink">{esc(e['place'] or '')}</div>
    <div class="price">{esc(e['price_short'] or '')}</div>{upd}
    <div class="annot">{esc(annot_snippet(e))}</div>
  </div>
</div>'''

def proto_actions(e, where='card'):
    """Кнопки действий с прототипом. На не-локальном сайте (GitHub Pages) кнопки
    правки скрывает prototypes.js — здесь только разметка и текущие значения."""
    st = e.get('st') or {}
    hid = '1' if e.get('hidden') else '0'
    return ('<div class="pbtns" data-for="%s" data-id="%s" data-hidden="%s"'
            ' data-comment="%s" data-feedback="%s" data-rebuild="%s">'
            '<button type="button" class="pb" data-act="hide" title="%s">%s</button>'
            '<button type="button" class="pb" data-act="comment" title="Комментарий: ваша заметка к прототипу, сохраняется в файле состояния">Комментарий</button>'
            '<button type="button" class="pb" data-act="feedback" title="Обратная связь: задача агенту, что нужно переделать в прототипе">Обратная связь</button>'
            '<button type="button" class="pb del" data-act="delete" title="Удалить прототип: папка переедет в архив, её можно вернуть">Удалить</button>'
            '</div>') % (esc(where), esc(e['id']), hid,
                         esc(e.get('comment') or ''), esc(e.get('feedback') or ''),
                         '1' if st.get('rebuild') else '0',
                         'Показать прототип в списке' if e.get('hidden')
                         else 'Скрыть прототип в списке (файл останется на месте)',
                         'Восстановить' if e.get('hidden') else 'Скрыть')

def note_del_btn(kind):
    """Кнопка-иконка удаления для выведенного комментария или обратной связи."""
    what = 'комментарий' if kind == 'comment' else 'обратную связь'
    return ('<button type="button" class="un-del" data-act="del-%s"'
            ' title="Удалить %s (с подтверждением)"'
            ' aria-label="Удалить %s">✕</button>' % (kind, what, what))


def user_notes_html(e, where, in_card=False):
    """Комментарий и обратная связь. in_card=True — компактно, для карточки списка."""
    out = []
    if e.get('comment'):
        out.append('<div class="usernote comment"><div class="un-h"><span class="un-t">Комментарий</span>'
                   '%s</div>%s</div>' % (note_del_btn('comment'), nl2br(H.escape(e['comment']))))
    if e.get('feedback'):
        out.append('<div class="usernote feedback"><div class="un-h"><span class="un-t">'
                   'Обратная связь (задача агенту)</span>%s</div>%s</div>'
                   % (note_del_btn('feedback'), nl2br(H.escape(e['feedback']))))
    if not out:
        return ''
    return '<div class="usernotes%s" data-where="%s" data-id="%s" data-comment="%s" data-feedback="%s" data-rebuild="%s">%s</div>' % (
        ' in-card' if in_card else '', esc(where), esc(e['id']),
        esc(e.get('comment') or ''), esc(e.get('feedback') or ''),
        '1' if (e.get('st') or {}).get('rebuild') else '0', ''.join(out))


def proto_card(e, prefix=''):
    p = e['proto']
    sup = []
    if e.get('types'):
        sup.append(', '.join(e['types']))
    if e.get('topics'):
        sup.append(', '.join(e['topics']))
    marks = []
    if e.get('dup'):
        marks.append('<span class="pmark dup">дубль на «Элементах»</span>')
    if e.get('st', {}).get('rebuild'):
        marks.append('<span class="pmark rebuild">переделать</span>')
    mark_html = ('<div class="pmarks">' + ''.join(marks) + '</div>') if marks else ''
    hidden_attr = ' hidden' if e.get('hidden') else ''
    lectory = proto_lectorium(p)
    filter_key = proto_filter_key(p)
    eurl = url_detail(e, prefix)
    return f'''<div class="event proto{hidden_attr}" data-kind="proto" data-id="{esc(e['id'])}" data-organizer="{esc(filter_key)}" data-date="{esc(e['date_iso'])}" data-lecturer="{esc(e.get('lecturer') or '')}" data-title="{esc(e.get('title') or '')}" data-where="{esc(fmt_date_ru(e['date_iso']))}">
  <div class="edate">
    <div class="hday">{esc(fmt_date_short(e['date_iso']))}</div>
    <div class="hmeta">{esc(e['weekday'])}</div>
    <div class="hmeta">{esc(fmt_time(e))}</div>
    <div class="hcity">{esc(e['city'] or '')}</div>
    <div class="hlink"><a href="{esc(e['url'])}" target="_blank" rel="noopener">{esc(e['id'])}</a></div>
    {proto_actions(e, 'card')}
  </div>
  <div class="edesc">
    <div class="suplink">{esc(' • '.join(sup))}</div>
    <a class="nohover" href="{eurl}">
      <div class="pretitle">{esc(e['lecturer'] or '')}</div>
      <div class="title">{esc(e['title'] or '')}</div>
    </a>
    <div class="sublink">{esc(e['place'] or '')}</div>
    <div class="price">{esc(e['price_short'] or '')}</div>
    {('<div class="lectory plectory">%s</div>' % esc(lectory)) if lectory else ''}
    {mark_html}
    <div class="annot">{esc(annot_snippet(e))}</div>
  </div>
  {user_notes_html(e, 'card', in_card=True)}
</div>'''


def header(title, active, prefix=''):
    nav = []
    for name, href, key in [('События', prefix + 'index.html', 'events'), ('Календарь', prefix + 'calendar.html', 'calendar')]:
        cls = ' class="active"' if key == active else ''
        nav.append(f'<a href="{href}"{cls}>{name}</a>')
    navs = '\n      '.join(nav)
    return f'''<div class="header">
  <div class="wrap">
    <div class="brand">
      <a class="logo" href="{prefix}index.html">Научный календарь</a>
      <div class="tagline">анонсы научно-популярных лекций</div>
    </div>
    <nav>
      {navs}
    </nav>
  </div>
</div>'''

def snapshot_str():
    ts = os.path.getmtime(DATA) if os.path.exists(DATA) else 0
    return datetime.datetime.fromtimestamp(ts).strftime('%d.%m.%Y %H:%M')

def footer(prefix=''):
    docs = 'https://github.com/Kuzdr/Intensive_1/blob/master/ПАМЯТКА.md'
    skill = 'https://github.com/Kuzdr/Intensive_1/tree/master/.opencode/skills'
    return f'''<div class="footer">
  <div class="wrap">
    <div class="source">Данные: <a href="https://elementy.ru/events" target="_blank">elementy.ru/events</a> — предстоящие события (снимок от {snapshot_str()}).</div>
    <div class="note">Прототип. Не является официальным сайтом «Элементов». Уточняйте условия у организаторов.</div>
    <div class="docs"><a href="{docs}" target="_blank" rel="noopener">Памятка проекта</a> · <a href="{skill}" target="_blank" rel="noopener">Скиллы (правила поста в Телеграм и др.)</a></div>
  </div>
</div>'''

def page(title, body, active, prefix='', extra_js=''):
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — Научный календарь</title>
<link rel="icon" type="image/x-icon" href="{prefix}favicon.ico">
<link rel="stylesheet" href="{prefix}css/style.css">
</head>
<body>
{header(title, active, prefix)}
<div class="wrap content">
{body}
</div>
{footer(prefix)}
{extra_js}
</body>
</html>'''

TOOLBAR = '''<div class="toolbar">
  <button type="button" class="tbtn js-update" data-panel="update-panel-top" title="Пересобрать данные с сайта «Элементов» и опубликовать изменения">Обновить данные</button>
  <button type="button" class="tbtn js-post" title="Составить пост в Телеграм по событиям календаря">Пост в Телеграм</button>
  <div class="toolbar-view" id="view-switch">
    <label><input type="radio" name="vmode" value="all" checked> всё</label>
    <label><input type="radio" name="vmode" value="el"> «Элементы»</label>
    <label><input type="radio" name="vmode" value="proto"> прототипы</label>
    <label class="vhidden"><input type="checkbox" id="v-showhidden"> скрытые</label>
    <button type="button" class="tbtn mini" id="btn-organizers">Организаторы</button>
    <button type="button" class="tbtn mini" id="btn-reset-filters" title="Вернуть режим «всё», снять галочку «скрытые» и отметить всех лекториев">Сбросить фильтры</button>
  </div>
  <div class="filter-note" id="filter-note" hidden><span id="filter-note-text"></span>
    <button type="button" class="tbtn mini" id="btn-reset-filters-2">Сбросить фильтры</button>
  </div>
</div>'''

# Панель кнопок страницы прототипа: та же, что сверху, и её копия снизу.
# У каждой копии своя панель прогресса (data-panel), поэтому работают обе.
TOOLBAR_PAGE = '''<div class="toolbar toolbar-page">
  <button type="button" class="tbtn js-update" data-panel="update-panel-%s" title="Пересобрать данные с сайта «Элементов» и опубликовать изменения">Обновить данные</button>
  <button type="button" class="tbtn js-post" title="Составить пост в Телеграм по событиям календаря">Пост в Телеграм</button>
  <div class="toolbar-more"></div>
</div>
%s'''

PANEL = '''<div class="update-panel" id="update-panel-top" hidden>
  <div class="update-progress" hidden>
    <div class="bar"><div class="bar-fill" id="up-bar"></div></div>
    <div class="bar-msg" id="up-msg"></div>
  </div>
  <div class="update-status"></div>
  <div class="update-actions" hidden>
    <button type="button" class="tbtn sec" id="up-close">Закрыть</button>
  </div>
</div>'''

PANEL_PAGE = '''<div class="update-panel" id="update-panel-%s" hidden>
  <div class="update-progress" hidden>
    <div class="bar"><div class="bar-fill"></div></div>
    <div class="bar-msg"></div>
  </div>
  <div class="update-status"></div>
  <div class="update-actions" hidden>
    <button type="button" class="tbtn sec">Закрыть</button>
  </div>
</div>'''
def toolbar_page(tag):
    """Панель кнопок для страницы прототипа + своя панель прогресса."""
    return TOOLBAR_PAGE % (tag, PANEL_PAGE % tag)


MODAL = '''<div class="modal-overlay" id="modal-update" hidden>
  <div class="modal">
    <div class="modal-title">Обновить данные?</div>
    <div class="modal-body">
      <p class="modal-hint" id="mp-hint">Будут удалены прошедшие события, добавлены новые, а события, у которых изменились название, авторы, дата, лекторий, место или цена, будут обновлены и помечены.</p>
    </div>
    <div class="modal-actions">
      <button type="button" class="tbtn" id="mp-ok">Да</button>
      <button type="button" class="tbtn sec" id="mp-cancel">Нет</button>
    </div>
  </div>
</div>'''

MODAL = '''<div class="modal-overlay" id="modal-update" hidden>
  <div class="modal">
    <div class="modal-title">Обновить данные?</div>
    <div class="modal-body">
      <p class="modal-hint">Будут удалены прошедшие события, добавлены новые, а события, у которых изменились название, авторы, дата, лекторий, место или цена, будут обновлены и помечены.</p>
    </div>
    <div class="modal-actions">
      <button type="button" class="tbtn" data-mp="ok">Да</button>
      <button type="button" class="tbtn sec" data-mp="cancel">Нет</button>
    </div>
  </div>
</div>'''


MODAL_POST = '''<div class="modal-overlay" id="modal-post" hidden>
  <div class="modal modal-post">
    <div class="modal-title">Пост в Телеграм</div>
    <div class="modal-body">
      <div class="post-controls">
        <label>С: <select id="pp-from"></select></label>
        <label>По: <select id="pp-to"></select></label>
        <button type="button" class="tbtn" id="pp-gen">Сформировать</button>
      </div>
      <div class="post-preview" id="pp-preview"></div>
    </div>
    <div class="modal-actions">
      <button type="button" class="tbtn" id="pp-copy">Копировать</button>
      <button type="button" class="tbtn sec" id="pp-close">Закрыть</button>
    </div>
  </div>
</div>'''


MODAL_ORGANIZERS = '''<div class="modal-overlay" id="modal-organizers" hidden>
  <div class="modal modal-org">
    <div class="modal-title">Организаторы (сайты и Timepad) прототипов</div>
    <div class="modal-body">
      <div class="modal-hint">Отметьте организаторов (сайт или Timepad источника), прототипы которых нужно показывать. Настройка действует в режимах «всё» и «только прототипы».</div>
      <div class="org-list" id="org-list"><!--LEC--></div>
    </div>
    <div class="modal-actions">
      <button type="button" class="tbtn sec" id="org-all">Отметить все</button>
      <button type="button" class="tbtn sec" id="org-none">Убрать все</button>
      <button type="button" class="tbtn sec" id="org-inv">Инвертировать</button>
      <button type="button" class="tbtn" id="org-ok">Готово</button>
    </div>
  </div>
</div>'''

def build_toc(sections):
    months = []
    for mid, ml, weeks in sections:
        wlis = ''.join(f'<li><a href="#{wid}">{esc(wl)}</a></li>' for wid, wl, _counts in weeks)
        months.append(f'<li><a href="#{mid}">{esc(ml)}</a><ul>{wlis}</ul></li>')
    return '<aside class="toc"><div class="toc-title">Содержание</div><nav><ul>' + ''.join(months) + '</ul></nav></aside>'

def week_is_done(ws):
    """Неделя «окончилась», если её воскресенье уже прошло (данные обещают
    только предстоящие события, значит такие недели показывать незачем)."""
    return ws + datetime.timedelta(days=6) < datetime.date.today()

def week_counts_line(days):
    """Строка «17.09: 4. 18.09: 2. …» — только по дням недели, на которые есть
    события (прошедшие и пустые дни не выводятся)."""
    counts = {}
    for e in items:
        d = datetime.date(*map(int, e['date_iso'].split('-')))
        if week_start(d) == week_start(days[0]):
            counts[d] = counts.get(d, 0) + 1
    parts = []
    for d in sorted(counts):
        parts.append('%s: %d' % (fmt_date_short(d.isoformat()), counts[d]))
    return '. '.join(parts) + ('.' if parts else '')

def build_index():
    head = ['<h1>Календарь событий</h1>',
            '<p class="intro">Предстоящие научно-популярные лекции, встречи и круглые столы. Открывайте событие, чтобы узнать подробности и стоимость.</p>',
            TOOLBAR,
            PANEL]
    by_month = {}
    for e in items:
        d = datetime.date(*map(int, e['date_iso'].split('-')))
        by_month.setdefault((d.year, d.month), []).append(e)
    sections = []
    main = []
    for (y, m), evlist in sorted(by_month.items()):
        mid = month_id(datetime.date(y, m, 1))
        month_weeks_lst = [w for w in month_weeks(y, m) if not week_is_done(w[0])]
        if not month_weeks_lst:
            continue
        main.append(f'<h2 class="month" id="{mid}">{esc(month_label_ym(y, m))}</h2>')
        weeks = []
        by_week = {}
        for e in evlist:
            d = datetime.date(*map(int, e['date_iso'].split('-')))
            by_week.setdefault(week_start(d), []).append(e)
        for ws, wl, days in month_weeks_lst:
            wid = week_id(y, m, ws)
            weeks.append((wid, wl, ''))
            main.append(f'<h3 class="week" id="{wid}">{esc(wl)}</h3>')
            wc = week_counts_line(days)
            if wc:
                main.append('<div class="weekcount" data-week="%s">%s</div>' % (wid, esc(wc)))
            for e in by_week.get(ws, []):
                main.append(card(e))
        sections.append((mid, month_label_ym(y, m), weeks))
    lec = ''.join(
        '<label class="org-item"><input type="checkbox" value="%s"%s> %s <span class="org-n">(%d)</span></label>'
        % (esc(name), ' checked' if cnt else '', esc(name), cnt)
        for name, cnt in organizers_of_prototypes())
    if not lec:
        lec = '<div class="modal-hint">Прототипов пока нет.</div>'
    body_parts = [*head,
                  '<div class="idxbody">',
                  build_toc(sections),
                  '<div class="idxmain">',
                  '\n'.join(main),
                  '</div>',
                  '<div class="v-empty" id="v-empty" hidden>По этим условиям ничего не нашлось. '
                  'Попробуйте включить «показать скрытые» или выбрать других организаторов.</div>',
                  '</div>',
                  MODAL,
                  MODAL_POST,
                  MODAL_ORGANIZERS.replace('<!--LEC-->', lec),
                  '<script src="js/post.js"></script>',
                  '<script src="js/prototypes.js"></script>',
                  '<script src="js/toolbar.js"></script>']
    body = '\n'.join(body_parts)
    open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8').write(page('Календарь событий', body, 'events'))

def render_memo(e, prefix):
    m = e.get('detail_html') or ''
    m = m.replace('\\', '/')
    m = m.replace('assets/img/', prefix + 'assets/img/')
    return m

EVENT_JS = '<script src="../js/reload.js"></script>'

# Кнопка «Перезагрузить с «Элементов»» на странице события. Отдельный файл:
# страница события почти не имеет скриптов, а prototypes.js на ней не нужен.
RELOAD_JS = r'''/* кнопка «Перезагрузить с «Элементов» на странице события */
(function () {
  var btn = document.querySelector('[data-act=reload]');
  if (!btn) return;
  var row = btn.parentNode;
  var note = row.querySelector('.reload-note');
  var local = /^(localhost|127\.0\.0\.1|\[::1\])$/i.test(location.hostname);
  if (!local) { row.parentNode.removeChild(row); return; }

  function say(text, kind) {
    note.className = 'reload-note ' + kind;
    note.textContent = text;
  }
  btn.addEventListener('click', function () {
    if (!window.confirm('Перезагрузить событие с «Элементов»?\n\n'
      + 'Страница события будет скачана с elementy.ru заново, сайт пересобран. '
      + 'Это займёт несколько секунд.')) return;
    btn.disabled = true;
    btn.textContent = 'Перезагружаю…';
    say('Скачиваю страницу с «Элементов»…', 'work');
    fetch('/api/proto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'reload', id: btn.getAttribute('data-id') })
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok || !j.ok) throw new Error(j.error || ('ошибка ' + r.status));
        return j;
      });
    }).then(function (j) {
      say(j.message || 'Готово', 'ok');
      setTimeout(function () { location.reload(); }, 900);
    }).catch(function (e) {
      btn.disabled = false;
      btn.textContent = 'Перезагрузить с «Элементов»';
      say('Не получилось: ' + e.message, 'err');
    });
  });
})();
'''

def build_reload_js():
    open(os.path.join(JS_DIR, 'reload.js'), 'w', encoding='utf-8').write(RELOAD_JS)

def build_event_pages():
    n = len(items)
    written = set()
    for i, e in enumerate(items):
        if e.get('kind') == 'proto':
            body = proto_page(e, '../')
        else:
            body = event_page(e, i, n, '../')
        name = (e.get('slug') or e['id']) + '.html'
        written.add(name)
        doc = e['title'] or ('Событие ' + e['id'])
        if e.get('lecturer'):
            doc += ' — ' + e['lecturer']
        open(os.path.join(EVENT_DIR, name), 'w', encoding='utf-8').write(
            page(doc, body, 'events', '../', extra_js=EVENT_JS))
    # Убрать страницы, оставшиеся от прошлых сборок (событие удалено,
    # переименовано или прошло): иначе в папке годами лежат копии со
    # старыми данными, на которые ещё можно зайти по старой ссылке.
    stale = [f for f in os.listdir(EVENT_DIR)
             if f.endswith('.html') and f not in written]
    for f in stale:
        try:
            os.remove(os.path.join(EVENT_DIR, f))
        except OSError:
            pass
    if stale:
        print('Удалено устаревших страниц: %d' % len(stale))

def event_page(e, i, n, prefix):
    nav_prev = nav_next = ''
    if i > 0:
        p = items[i - 1]
        nav_prev = f'<a class="pagenav prev" href="{url_detail(p, prefix)}"><span>Предыдущее</span><b>{esc(p["title"])}</b><i>{esc(fmt_date_short(p["date_iso"]))} · {esc(p["lecturer"] or "")}</i></a>'
    if i < n - 1:
        nxt = items[i + 1]
        nav_next = f'<a class="pagenav next" href="{url_detail(nxt, prefix)}"><span>Следующее</span><b>{esc(nxt["title"])}</b><i>{esc(fmt_date_short(nxt["date_iso"]))} · {esc(nxt["lecturer"] or "")}</i></a>'
    reg = ''
    if e.get('reg_links'):
        links = ' · '.join(
            f'<a href="{esc(l["href"])}" target="_blank" rel="noopener">{esc(l["text"])}</a>' for l in e['reg_links'])
        reg = f'<div class="reglinks"><span class="lbl">Регистрация:</span> {links}</div>'
    upd_src = ''
    if e.get('updated'):
        upd_src = f'<div class="upd-src">Обновлено: {esc(e.get("updated_at", ""))}</div>'
    return f'''<div class="crumb"><a href="../index.html">Календарь событий</a> » <span>{esc(e['title'] or '')}</span></div>
  <div class="detailblk">
    {render_memo(e, '../')}
  </div>
  <div class="sourcebox">
    <div class="price-short">Стоимость: <b>{esc(e['price_short'] or 'не указана')}</b></div>
    {upd_src}
    {reg}
    <div class="src">Источник: <a href="{esc(e['url'])}" target="_blank" rel="noopener">страница на elementy.ru</a> (ID {esc(e['id'])})</div>
    <div class="reload-row">
      <button type="button" class="tbtn mini" data-act="reload" data-id="{esc(e['id'])}"
        title="Скачать страницу этого события с elementy.ru заново и пересобрать сайт">Перезагрузить с «Элементов»</button>
      <span class="reload-note">Если на «Элементах» что-то исправили — нажмите, и данные этого события обновятся.</span>
    </div>
  </div>
  <div class="pagenavs">
    {nav_prev}{nav_next}
  </div>'''

# ------------------------------------------------------- страница прототипа

def klblock_to_text(html_txt):
    """Тег блока об авторе показываем как есть, в угловых скобках."""
    def rep(m):
        return '<span class="klblock">' + H.escape(m.group(0)) + '</span>'
    return re.sub(r'</?KLBLOCK[^>]*>', rep, html_txt, flags=re.I)

def proto_authors(p):
    """Список авторов прототипа. У старых прототипов он один и лежит в
    ключе author; у новых (встреча с двумя лекторами) — в authors."""
    lst = p.get('authors')
    if isinstance(lst, list) and lst:
        return [a for a in lst if isinstance(a, dict)]
    a = p.get('author')
    return [a] if isinstance(a, dict) else []


def proto_lecturers(p):
    """Автор(ы) строкой для шапки страницы прототипа."""
    names = [(a.get('name') or '').strip() for a in proto_authors(p)]
    names = [n for n in names if n]
    if not names:
        return (p.get('lecturer') or '').strip()
    if len(names) == 1:
        return names[0]
    return ', '.join(names[:-1]) + ' и ' + names[-1]


def proto_photo(a, p, prefix):
    """Фото автора из источника (пусто, если фото нет).

    Подписи под фото НЕ выводим: пользователь просил убрать её вообще
    (решение от 28.09.2026) — ни на странице прототипа, ни в HTML-фрагменте.
    """
    src = (a.get('photo') or '').strip()
    if not src:
        return ''
    if not re.match(r'^(https?:)?//', src):
        src = prefix + src
    return ('<div class="pphoto"><img src="%s" alt="%s" style="max-width:600px;height:auto">'
            '</div>') % (
                esc(src), esc(a.get('name') or p.get('lecturer') or 'автор'))


def author_block_full(a, p, prefix, show_who=False):
    """Полноценный блок об авторе для автора, который уже есть на «Элементах»:
    фото, имя и описание (исходное ТЗ). Без кнопок правки — копировать нечего,
    автор уже в базе «Элементов»."""
    name = (a.get('name') or p.get('lecturer') or '').strip()
    photo = proto_photo(a, p, prefix)
    desc = (a.get('block_html') or '').strip()
    if not desc:
        # описание берём из поля 7.4, если готовый блок не заполнен
        for f in a.get('fields') or []:
            if str(f.get('n')) == '7.4':
                desc = str(f.get('value') or '').strip()
    parts = ['<div class="fblock"><div class="fb-t">Об авторе</div>']
    if show_who and name:
        parts.append('<div class="fb-who">%s</div>' % esc(name))
    parts.append('<div class="itemblock memo author-full">')
    if photo:
        parts.append(photo)
    if name:
        parts.append('<p class="aname"><b>%s</b></p>' % esc(name))
    if desc:
        parts.append(desc)
    parts.append('</div></div>')
    return ''.join(parts)


def author_blocks(p, prefix):
    """Все блоки «Об авторе» прототипа: по одному на автора.

    Решает флаг author.on_elementy: он ставится ТОЛЬКО если автор реально
    найден на «Элементах». По умолчанию False — новый автор, поля 7.1–7.4.
    (Раньше решение принималось по наличию block_html, из-за чего новые
    авторы показывались как «уже в базе», а стандартные поля были скрыты.)
    Когда авторов несколько, под заголовком блока показываем, о ком он."""
    aus = proto_authors(p)
    many = len(aus) > 1
    out = []
    for i, a in enumerate(aus):
        if a.get('on_elementy'):
            out.append(author_block_full(a, p, prefix, show_who=many))
            continue
        name = (a.get('name') or '').strip()
        rows = []
        for f in a.get('fields') or []:
            nm = f['name']
            rows.append('<tr><td class="fname">%s</td><td class="fval">%s</td>'
                        '<td class="fbtns-cell">%s</td></tr>'
                        % (esc(nm), f.get('value') or '—',
                           cell_btns('author_fields', f, nm, key=str(i) + ':' + str(f['n']))))
        head = '<div class="fb-t">Об авторе</div>'
        if many and name:
            head += '<div class="fb-who">%s</div>' % esc(name)
        out.append('<div class="fblock">%s%s<table class="ftable">%s</table></div>'
                   % (head, proto_photo(a, p, prefix), ''.join(rows)))
    return ''.join(out)

def edit_btns(area, key, name, value=''):
    return ('<span class="fbtns" data-area="%s" data-key="%s" data-name="%s" data-text="%s">'
            '<button type="button" class="fb" data-act="edit" title="Редактировать %s">&#9998;</button>'
            '<button type="button" class="fb" data-act="copy" title="Скопировать %s">&#128203;</button>'
            '</span>') % (esc(area), esc(key), esc(name), esc(value or ''),
                          esc(name.lower()), esc(name.lower()))

# --------------------------------------------------------- источники прототипа

# Числовой ID в адресе источника: Timepad (/event/12345/), Архэ, Timepad-Donational
# и подобные. Возвращаем (id, подпись источника) или (None, имя хоста).
def source_num_id(u):
    m = re.search(r'elementy\.ru/events/(\d+)', u or '')
    if m:
        return m.group(1), 'Элементы'
    m = re.search(r'/event/(\d+)', u or '')
    if m:
        return m.group(1), 'Timepad'
    m = re.search(r'arche\.ru/events/(\d+)', u or '')
    if m:
        return m.group(1), 'Архэ'
    m = re.search(r'timepad\.ru/(\d{5,})', u or '')
    if m:
        return m.group(1), 'Timepad'
    return None, ''


def source_label(u):
    """Короткое имя источника: «Timepad», «Архэ», «Сайт Фестиваля» и т. п."""
    host = re.sub(r'^www\.', '', (urlparse(u).netloc if '//' in (u or '') else u or ''))
    num, kind = source_num_id(u)
    if kind:
        return '%s, ID %s' % (kind, num)
    m = re.match(r'^(.*?)\.timepad\.ru', host)
    if m:
        return 'Timepad, %s' % m.group(1)
    m = re.match(r'^(.*?)\.arche\.ru', host)
    if m:
        return 'Архэ, %s' % m.group(1)
    return host or u


def source_btns(area, key, name, value=''):
    """Свой набор кнопок для источника: правка HTML, копирование HTML и ID."""
    num, kind = source_num_id(value if value.startswith('http') else '')
    out = edit_btns(area, key, name, value)
    if num:
        out = out.replace('</span>',
                          '<button type="button" class="fb" data-act="copyid" data-text="%s"'
                          ' title="Скопировать ID источника: %s (%s)">ID</button></span>'
                          % (esc(num), esc(num), esc(kind)))
    return out


def source_add_row(n):
    """Пустая строка для добавления нового источника (правьте и сохраняйте)."""
    return ('<tr class="src-add"><td class="fname">новый источник</td>'
            '<td class="fval src-url">—</td>'
            '<td class="fbtns-cell">%s</td></tr>'
            % edit_btns('source', str(n), 'ссылку на новый источник', ''))

def cell_btns(area, f, name, no_edit=False, key=None):
    """Ячейка с кнопками правки/копирования для поля в таблице."""
    if no_edit:
        return ''
    return edit_btns(area, key if key is not None else f.get('n'), name, f.get('value') or '')

def source_cell_btns(p, f):
    """Поле 9 «Источники»: свой набор кнопок на КАЖДЫЙ источник
    (правка, копирование и — если у источника есть числовой ID — копирование ID).
    Список источников общий с блоком «Источники» внизу страницы, поэтому
    правка здесь меняет тот же список."""
    srcs = p.get('sources') or ([p['url']] if p.get('url') else [])
    lines = []
    for i, u in enumerate(srcs):
        lines.append('<div class="src-line"><a href="%s" target="_blank" rel="noopener">%s</a>%s</div>'
                     % (esc(u), esc(u), source_btns('source', str(i), 'ссылку на источник', u)))
    if not lines:
        lines.append('<div class="src-line">—</div>')
    return ''.join(lines)

def proto_page(e, prefix):
    p = e['proto']
    st = e.get('st') or {}
    lectory = proto_lectorium(p)
    # --- шапка и кнопки
    flags = []
    if e.get('dup'):
        flags.append('<div class="pflag dup">Такая же лекция уже есть на «Элементах»'
                     ' (ID %s) — прототип скрыт автоматически%s.</div>'
                     % (esc(e.get('dup_of') or ''),
                        ('; совпало: ' + esc(', '.join(e.get('dup_hits') or []))) if e.get('dup_hits') else ''))
    if e.get('hidden') and not e.get('dup'):
        flags.append('<div class="pflag">Прототип скрыт — показывается только в режиме «показать скрытые».</div>')
    if e.get('rebuild'):
        flags.append('<div class="pflag rebuild">По обратной связи: событие нужно пересоздать заново и заменить этот прототип.</div>')
    notes = (p.get('notes') or '').strip()
    # --- описание
    desc = klblock_to_text(p.get('desc_html') or '')
    desc = desc.replace('\\', '/').replace('assets/img/', prefix + 'assets/img/')
    desc_blk = ('<div class="fblock"><div class="fbar">%s</div>'
                '<div class="itemblock memo pdesc">%s</div></div>') % (
                    edit_btns('desc', 'desc', 'Описание лекции', p.get('desc_html') or ''), desc)
    # --- автор(ы): блок с «Элементов» показываем целиком (имя, фото, описание),
    #     без кнопок правки; для нового автора — поля 7.1–7.4. См. author_blocks.
    author = author_blocks(p, prefix)
    # --- дополнительная информация
    extras = p.get('extra_html') or []
    ex_rows = []
    for i, x in enumerate(extras):
        xh = x.replace('\\', '/')
        ex_rows.append('<div class="exrow"><div class="exbar">%s</div><div class="exview">%s</div></div>'
                       % (edit_btns('extra', str(i), 'Дополнительная информация, абзац %d' % (i + 1), x), xh))
    extra_blk = ''
    if extras:
        extra_blk = '<div class="fblock">%s</div>' % ''.join(ex_rows)
    # --- формальные поля: компактная таблица без заголовка, номеров и
    #     пометок «только для справки»; значение показываем как есть (без тегов),
    #     HTML-код остаётся в кнопках.
    #     Поле «0. ID события» не показываем: ID и так виден в шапке страницы
    #     («прототип: <ID>»). В JSON и в памятке паспорта оно остаётся.
    frows = []
    for f in PL.fields(p):
        if f['n'] == '0':
            continue
        no_edit = f['n'] in PL.NO_EDIT
        if f['n'] == '9':
            # у поля «Источники» кнопки свои — по одному набору на источник
            frows.append('<tr class="ftable-src-row"><td class="fname">%s</td>'
                         '<td class="fval" colspan="2">%s</td></tr>'
                         % (esc(f['name']), source_cell_btns(p, f)))
            continue
        frows.append('<tr class="%s"><td class="fname">%s</td><td class="fval">%s</td>'
                    '<td class="fbtns-cell">%s</td></tr>' % (
                        'ro' if no_edit else '',
                        esc(f['name']),
                        f.get('value') or '—',
                        cell_btns('fields', f, f['name'], no_edit)))
    fields_blk = '<table class="ftable ftable-fields">%s</table>' % ''.join(frows)
    # --- замечания при подготовке
    notes_blk = ''
    if notes:
        notes_blk = '<div class="fblock"><div class="pnotes">%s</div></div>' % nl2br(H.escape(notes))
    srcs = p.get('sources') or ([p['url']] if p.get('url') else [])
    src_rows = []
    for i, u in enumerate(srcs):
        src_rows.append('<tr><td class="fname">%s</td><td class="fval src-url">'
                        '<a href="%s" target="_blank" rel="noopener">%s</a></td>'
                        '<td class="fbtns-cell">%s</td></tr>'
                        % (esc(source_label(u)), esc(u), esc(u),
                           source_btns('source', str(i), 'ссылку на источник', u)))
    src_rows.append(source_add_row(len(srcs)))
    src_html = ('<div class="fblock"><table class="ftable ftable-src">%s</table></div>'
                % ''.join(src_rows)) if srcs else ''
    # --- автор(ы) в шапке страницы: без них непонятно, чья это лекция
    who = proto_lecturers(p)
    who_html = ('<div class="pwho">%s: %s</div>'
                % ('Авторы' if len(proto_authors(p)) > 1 else 'Автор', esc(who))) if who else ''
    return f'''<div class="crumb"><a href="../index.html">Календарь событий</a> » <span>прототип: {esc(e['id'])}</span></div>
<div class="ptop" data-id="{esc(e['id'])}">
  <div class="ptitle"><span class="ptag">прототип</span> {esc(e['title'] or '')}<div class="psub">{esc(fmt_date_num(e['date_iso']))} · {esc(e['weekday'])} · {esc(fmt_time(e) or '')} · {esc(e['city'] or '')}</div>{who_html}</div>
  {proto_actions(e, 'page')}
</div>
{''.join(flags)}
{user_notes_html(e, 'top')}
{fields_blk}
{desc_blk}
{author}
{extra_blk + notes_blk}
<div class="psrc">Источники: {src_html}</div>
{user_notes_html(e, 'bottom')}
<div class="pagenavs"><a class="pagenav prev" href="../index.html"><span>К списку</span><b>Календарь событий</b></a></div>
{MODAL}
<script src="{prefix}js/prototypes.js"></script>
<script src="{prefix}js/toolbar.js"></script>'''

def nl2br(s):
    return re.sub(r'\n', '<br>\n', s)


def build_calendar():
    js_events = []
    for e in evs:
        js_events.append({
            'id': e['id'],
            'date': e['date_iso'],
            'time': e.get('time_start'),
            'time_end': e.get('time_end'),
            'city': e.get('city'),
            'title': e['title'],
            'lecturer': e.get('lecturer'),
            'lectory': e.get('lectory'),
            'place': e.get('place'),
            'price': e.get('price_short'),
            'url': 'event/%s.html' % e['id'],
            'source': e.get('url'),
        })
    js = 'window.EVENTS = ' + json.dumps(js_events, ensure_ascii=False) + ';'
    open(os.path.join(JS_DIR, 'events.js'), 'w', encoding='utf-8').write(js)

    body = '''<div class="calwrap">
  <div class="calhead">
    <button id="cal-prev" type="button">‹</button>
    <div id="cal-title" class="cal-title"></div>
    <button id="cal-next" type="button">›</button>
  </div>
  <table class="calgrid" id="cal-grid">
    <thead><tr><th>Пн</th><th>Вт</th><th>Ср</th><th>Чт</th><th>Пт</th><th>Сб</th><th>Вс</th></tr></thead>
    <tbody></tbody>
  </table>
  <div class="calhint">Дни с событиями подсвечены — кликните по дате, чтобы увидеть события дня.</div>
  <div class="calperiod" id="cal-period"></div>
</div>
<script src="js/events.js"></script>
<script src="js/calendar.js"></script>'''
    open(os.path.join(SITE, 'calendar.html'), 'w', encoding='utf-8').write(
        page('Календарь', body, 'calendar'))

CSS = r'''/* base */
[hidden] { display: none !important; }
* { box-sizing: border-box; }
body { margin: 0; background: #f4f1ea; color: #222; font: 14px/1.5 Arial, Helvetica, sans-serif; }
a { color: #005e8a; text-decoration: none; }
a:hover { color: #02334d; }
.wrap { max-width: 1080px; margin: 0 auto; padding: 0 16px; }

/* index: sidebar + main column */
.idxbody { display: flex; gap: 28px; align-items: flex-start; }
.toc { flex: 0 0 200px; position: sticky; top: 14px; }
.toc-title { font-size: 12px; text-transform: uppercase; letter-spacing: .4px; color: #8a7040; margin-bottom: 6px; }
.toc nav { font-size: 13px; max-height: calc(100vh - 60px); overflow: auto; border-left: 2px solid #e3dccb; padding-left: 10px; }
.toc ul { list-style: none; margin: 0; padding: 0; }
.toc ul ul { margin: 2px 0 6px 12px; }
.toc li { margin: 2px 0; }
.toc a { color: #6a643f; }
.toc a:hover { color: #005e8a; }
.toc ul ul a { color: #8a8270; }
.idxmain { flex: 1 1 auto; min-width: 0; }

/* week header */
.week { font: normal 19px/1.2 Georgia, serif; color: #8a7040; margin: 8px 0 2px; }
.month + .week { margin-top: -2px; }
.weekcount { font-size: 13px; color: #8a8270; margin: 0 0 8px; }

/* mobile: hide toc sidebar */
@media (max-width: 860px) {
  .idxbody { display: block; }
  .toc { display: none; }
}

/* header */
.header { background: #fff; border-bottom: 1px solid #d8d2c4; }
.header .wrap { display: flex; align-items: flex-end; flex-wrap: wrap; padding-top: 14px; padding-bottom: 10px; }
.brand { margin-right: auto; }
.logo { font: bold 26px/1 Georgia, 'Times New Roman', serif; color: #4a3b1f; letter-spacing: .5px; }
.tagline { font-size: 12px; color: #77704f; margin-top: 2px; }
.header nav { display: flex; gap: 6px; }
.header nav a { padding: 6px 12px; font-size: 15px; color: #333; border-bottom: 3px solid transparent; }
.header nav a:hover { color: #005e8a; }
.header nav a.active { border-bottom-color: #005e8a; color: #005e8a; }

.content { padding-top: 18px; padding-bottom: 40px; }
h1 { font: normal 30px/1.2 Georgia, serif; color: #3a2f16; margin: 4px 0 6px; }
.intro { color: #555; margin: 0 0 18px; max-width: 720px; }

.month { font: normal 26px/1.2 Georgia, serif; color: #8a7040; border-bottom: 1px solid #ddd5c3; padding-bottom: 6px; margin: 26px 0 14px; }

/* event card (list, as on Elementy) */
.event { display: flex; padding: 12px 0; border-bottom: 1px solid #e3dccb; }
.event .edate { width: 126px; flex: none; padding-right: 14px; }
.event .hday { font: bold 24px/1.1 Georgia, serif; color: #3a2f16; }
.event .hmeta { font-size: 13px; color: #444; }
.event .hcity { font-size: 12px; color: #777; }
.event .edesc { flex: 1 1 auto; min-width: 0; }
.event .suplink { font-size: 12px; color: #6a643f; margin-bottom: 2px; }
.event .pretitle { font-size: 13px; color: #6f6a52; }
.event .title { font: bold 18px/1.25 Georgia, serif; color: #2d2a16; }
.event a.nohover:hover .title { color: #005e8a; }
.event .lectory { font-size: 13px; color: #444; font-weight: bold; }
.event .sublink { font-size: 13px; color: #6f6a52; margin-top: 2px; }
.event .price { margin-top: 5px; display: inline-block; background: #e9e2cf; border: 1px solid #d8cdb0; border-radius: 3px; padding: 1px 8px; font-size: 13px; color: #4a3b1f; }
.event .price + .price { margin-left: 6px; }
.event .annot { margin-top: 6px; color: #555; font-size: 13px; }
.event .hlink { margin-top: 4px; font-size: 12px; }
.event .hlink a { color: #6a84a8; }
.event .hlink a:hover { color: #02334d; }
.badge-upd { margin-top: 5px; display: inline-block; background: #e2eee2; border: 1px solid #c3dcc3; border-radius: 3px; padding: 1px 8px; font-size: 12px; color: #2e5d2e; }
.upd-src { margin-bottom: 4px; color: #2e5d2e; font-size: 12px; }

/* detail page */
.crumb { font-size: 13px; color: #6a643f; margin: 6px 0 14px; }
.crumb a { color: #005e8a; }
/* Оформление текста — как на «Элементах»: три разных размера шрифта.
   Обычный абзац — 16px, строка class="small" (дата, ссылки) — 13.5px,
   аннотация в <blockquote class="small"> — 15px с рамкой слева. */
.itemblock.memo { background: #fff; border: 1px solid #ddd5c3; padding: 18px 22px; }
.itemblock.memo p { margin: 0 0 12px; font: 16px/1.55 Georgia, "PT Serif", "Times New Roman", serif; color: #2b2b2b; }
.itemblock.memo p:last-child { margin-bottom: 0; }
.itemblock.memo p.small,
.itemblock.memo p.Small { margin: 0 0 12px; font: 13.5px/1.5 Arial, Helvetica, sans-serif; color: #4a4438; }
.itemblock.memo blockquote { background: #f3efdc; border-left: 3px solid #c8bb8f; margin: 0 0 12px; padding: 12px 16px; }
.itemblock.memo blockquote.small,
.itemblock.memo blockquote.Small { font: 15px/1.6 Georgia, "PT Serif", "Times New Roman", serif; color: #2b2b2b; }
.itemblock.memo blockquote p { margin: 0 0 10px; font: inherit; line-height: inherit; color: inherit; }
.itemblock.memo blockquote p:last-child { margin-bottom: 0; }
.itemblock.memo b { font-weight: bold; }
.about { display: flex; gap: 12px; margin: 12px 0; padding: 10px; background: #f3efdc; border: 1px solid #e0d6b8; align-items: flex-start; }
.about .img { width: 72px; flex: none; }
.about .img img { width: 72px; height: 72px; object-fit: cover; background: #eee; }
.about .text { flex: 1 1 auto; }
.about .pretitle { font-weight: bold; color: #4a3b1f; margin-bottom: 4px; }
.sourcebox { background: #fff; border: 1px solid #ddd5c3; border-top: none; padding: 12px 22px; font-size: 13px; color: #444; }
.price-short { margin-bottom: 4px; }
.reglinks { margin-bottom: 4px; }
.sourcebox .src { color: #777; font-size: 12px; margin-top: 6px; }
.reload-row { margin-top: 10px; padding-top: 10px; border-top: 1px dashed #e2dccd; }
.reload-note { display: block; margin-top: 5px; font-size: 12px; color: #777; }
.reload-note.work { color: #8a6d1f; }
.reload-note.ok { color: #2e5d2e; font-weight: bold; }
.reload-note.err { color: #a33; font-weight: bold; }

.pagenavs { display: flex; gap: 12px; margin-top: 18px; }
.pagenav { flex: 1 1 50%; display: block; background: #fff; border: 1px solid #ddd5c3; padding: 10px 14px; }
.pagenav span { display: block; font-size: 12px; color: #999; }
.pagenav b { display: block; font: bold 15px/1.25 Georgia, serif; color: #2d2a16; margin-top: 2px; }
.pagenav i { font-size: 12px; color: #777; font-style: normal; }
.pagenav:hover { border-color: #005e8a; }
.pagenav.next { text-align: right; }

/* calendar */
.calwrap { background: #fff; border: 1px solid #ddd5c3; padding: 18px 22px; }
.calhead { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.calhead button { font-size: 22px; width: 40px; height: 40px; border: 1px solid #ccc3aa; background: #f4f1ea; color: #4a3b1f; cursor: pointer; border-radius: 4px; }
.calhead button:hover { background: #e9e2cf; }
.cal-title { font: bold 20px/1 Georgia, serif; color: #3a2f16; }
.calgrid { width: 100%; border-collapse: collapse; }
.calgrid th, .calgrid td { width: 14.28%; text-align: center; border: 1px solid #e8e1d1; padding: 0; }
.calgrid th { background: #f3efdc; color: #6a643f; font-weight: normal; font-size: 13px; padding: 6px 0; }
.calgrid td { height: 52px; vertical-align: top; font-size: 13px; }
.day { display: block; padding: 6px 0 2px; color: #333; }
.day.out { color: #bbb; }
.day.ev { color: #fff; background: #b07a2f; font-weight: bold; cursor: pointer; border-radius: 3px; margin: 3px 8px 0; }
.day.ev:hover { background: #005e8a; }
.day.ev.sel { background: #005e8a; outline: 2px solid #005e8a; }
.daycnt { display: block; font-size: 10.5px; color: #8a7040; }
.day.ev .daycnt { color: #ffe9c2; }
.calhint { font-size: 12px; color: #999; margin-top: 10px; }
.calperiod { margin-top: 16px; border-top: 1px solid #e3dccb; padding-top: 6px; }

/* toolbar + modal */
.toolbar { display: flex; gap: 10px; align-items: stretch; margin: 0 0 18px; flex-wrap: wrap; }
      .tbtn { border: 1px solid #b9a878; background: #fffdf5; color: #4a3b1f; font-size: 14px; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
      .tbtn:hover { background: #e9e2cf; }
      .tbtn.sec { color: #6a643f; }
      .tbtn.mini { padding: 5px 12px; font-size: 13px; }
      .filter-note { flex: 1 0 100%; font-size: 13px; color: #8c2f2f; background: #fdf1ef;
        border: 1px solid #e6c9c4; border-radius: 4px; padding: 7px 12px; }
      .filter-note[hidden] { display: none; }
      .filter-note .tbtn.mini { margin-left: 10px; }

.toolbar-more { flex: 1 1 auto; min-width: 120px; border: 1px dashed #cfc4a6; border-radius: 4px; min-height: 36px; }

/* переключатель показа: режим / скрытые / лектории */
.toolbar-view { display: flex; gap: 12px; align-items: center; flex-wrap: nowrap; margin-left: auto;
  border: 1px solid #ddd5c3; background: #fff; border-radius: 4px; padding: 5px 12px; }
.toolbar-view label { font-size: 13px; color: #333; white-space: nowrap; cursor: pointer; }
.toolbar-view input[type=radio], .toolbar-view input[type=checkbox] { margin-right: 3px; vertical-align: middle; }
.toolbar-view .vhidden { color: #8c2f2f; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-overlay[hidden] { display: none; }
.modal { background: #fff; max-width: 560px; width: 92%; border-radius: 8px; padding: 22px 24px; box-shadow: 0 10px 40px rgba(0,0,0,.3); }
.modal-title { font: bold 20px/1.3 Georgia, serif; color: #3a2f16; margin-bottom: 10px; }
.modal-sub { font-size: 13px; color: #6a643f; margin: -4px 0 10px; line-height: 1.45; }
.modal-hint { font-size: 14px; color: #444; line-height: 1.5; }
.modal-actions { margin-top: 18px; display: flex; gap: 10px; justify-content: flex-end; flex-wrap: wrap; }
/* окна заметок: поле ввода во всю ширину, кнопки прижаты к низу,
   размер окна меняется целиком (у textarea resize отключён) */
.modal-note-win { display: flex; flex-direction: column; min-height: 0; }
.modal-note-win .modal-body { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
.modal-note-win textarea { width: 100%; box-sizing: border-box; resize: none; min-height: 120px;
  font: 14px/1.5 Arial, Helvetica, sans-serif; border: 1px solid #ccc3aa; border-radius: 4px;
  padding: 8px 10px; color: #2d2a16; background: #fffdf5; }
.modal-note-win .pj-cb { margin-top: 10px; font-size: 14px; color: #333; }
.modal-resize { resize: both; overflow: auto; }

/* модальное окно выбора лекториев */
.modal-org { max-width: 460px; }
.org-list { margin-top: 12px; max-height: 50vh; overflow: auto; border: 1px solid #e3dccb; border-radius: 4px; padding: 8px 10px; background: #fffdf5; }
.org-item { display: block; font-size: 14px; color: #333; padding: 3px 0; }
.org-item .org-n { color: #8a7040; }

/* прототипы в списке */
.event.proto .hday, .event.proto .title { color: #a3311f; }
.event.proto a.nohover:hover .title { color: #7d2415; }
.event.proto .plectory { font-weight: bold; color: #4a3b1f; margin-top: 4px; }
.event.proto .pmarks { margin-top: 4px; }
.pmark { display: inline-block; background: #f6e3e0; border: 1px solid #e0bdb7; border-radius: 3px; padding: 0 6px; font-size: 12px; color: #8c2f2f; margin-right: 5px; }
.pmark.rebuild { background: #fdeeda; border-color: #e0c9a2; color: #8a5a12; }
.event.proto.hidden .hday, .event.proto.hidden .title, .event.proto.hidden .pretitle,
.event.proto.hidden .plectory, .event.proto.hidden .sublink, .event.proto.hidden .annot { color: #9a958a; }
.event.proto.hidden { background: #f0eee9; }

/* кнопки действий с прототипом */
.pbtns { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
.pbtns .pb { font: 11px/1.3 Arial, Helvetica, sans-serif; padding: 3px 7px; border: 1px solid #c3b48c; border-radius: 3px; background: #fffdf5; color: #4a3b1f; cursor: pointer; }
.pbtns .pb:hover { background: #e9e2cf; }
.pbtns .pb.del { border-color: #d8b0a8; color: #8c2f2f; }
.pbtns .pb.del:hover { background: #f6e3e0; }
.pbtns[hidden] { display: none; }

/* страница прототипа */
.ptop { display: flex; gap: 16px; align-items: flex-start; flex-wrap: wrap; margin-bottom: 14px; }
.ptitle { font: bold 20px/1.3 Georgia, serif; color: #3a2f16; }
.ptitle .ptag { display: inline-block; background: #a3311f; color: #fff; border-radius: 3px; font: bold 12px/1.4 Arial, sans-serif; padding: 1px 7px; vertical-align: 3px; margin-right: 6px; }
.ptitle .psub { font: 13px/1.4 Arial, sans-serif; color: #6f6a52; margin-top: 3px; }
.ptitle .pwho { font: italic 15px/1.4 Georgia, serif; color: #4a3f28; margin-top: 6px; }
.ftable-src-row .fval { line-height: 2.1; }
.src-line { margin: 0; }
.src-line .fbtns { margin-left: 8px; }
.fb-who { font: italic 15px/1.4 Georgia, serif; color: #4a3f28; margin: 0 0 8px; }
.ptop .pbtns { flex-direction: row; margin-top: 0; }
.pflag { flex: 1 1 100%; background: #fdf3e3; border: 1px solid #e0c9a2; border-radius: 4px; padding: 7px 10px; font-size: 13px; color: #6b4c14; margin-top: 8px; }
.pflag.dup { background: #f6e3e0; border-color: #e0bdb7; color: #8c2f2f; }
.pflag.rebuild { background: #fdeeda; }
.usernotes { margin: 0 0 14px; }
.usernote { border-left: 3px solid #b07a2f; background: #fffdf5; padding: 8px 12px; font-size: 13.5px; color: #333; margin-bottom: 8px; }
.usernote .un-t { font-size: 12px; text-transform: uppercase; letter-spacing: .3px; color: #8a7040; }
.usernote.feedback { border-left-color: #8c2f2f; }
.usernote.feedback .un-t { color: #8c2f2f; }
/* шапка заметки: подпись + иконка удаления справа */
.usernote .un-h { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-bottom: 3px; }
.usernote .un-del { flex: none; width: 20px; height: 20px; padding: 0; border: 1px solid transparent;
  border-radius: 3px; background: transparent; color: #a09684; font: 13px/1 "Segoe UI", Arial, sans-serif;
  cursor: pointer; }
.usernote .un-del:hover { border-color: #d8c9b4; background: #fff; color: #8c2f2f; }
/* в карточке списка заметки компактнее */
.usernotes.in-card { margin: 8px 0 0; }
.usernotes.in-card .usernote { font-size: 13px; padding: 6px 10px; margin-bottom: 6px; }
.fblock { background: #fff; border: 1px solid #ddd5c3; border-radius: 4px; padding: 12px 16px; margin-bottom: 14px; }
.fb-t { font: bold 15px/1.3 Georgia, serif; color: #4a3b1f; margin-bottom: 8px; }
/* полоса кнопок блока: прижата вправо, без заголовка */
.fbar, .exbar { display: flex; justify-content: flex-end; align-items: center; gap: 6px; margin-bottom: 6px; }
.fbar:empty, .exbar:empty { display: none; }
.itemblock.memo.pdesc { border: none; padding: 0; background: transparent; }
/* полный блок об авторе (автор уже есть на «Элементах»): фото, имя, описание */
.author-full .aname { margin: 0 0 10px; font: 700 17px/1.4 Georgia, "Times New Roman", serif; }
.author-full p:last-child { margin-bottom: 0; }
.klblock { font: 12px/1.4 Consolas, "Courier New", monospace; color: #8a7040; background: #f3efdc; border: 1px dashed #c8bb8f; border-radius: 3px; padding: 0 4px; }
.pphoto { margin: 0 0 10px; }
.pphoto img { display: block; border: 1px solid #ddd5c3; }
.pphoto .phint { font-size: 12px; color: #8a8270; margin-top: 3px; }
.exrow { border-top: 1px solid #eee7d8; padding: 8px 0; }
.exrow:first-of-type { border-top: none; }
.exview p { margin: 6px 0; }
.pnotes { font-size: 13.5px; color: #333; }
.psrc { font-size: 12.5px; color: #6a643f; margin: 4px 0 14px; }
.psrc a { overflow-wrap: anywhere; }
.ftable { width: 100%; border-collapse: collapse; }
.ftable td { border-top: 1px solid #eee7d8; padding: 6px 8px 6px 0; vertical-align: top; font-size: 13px; }
.ftable tr:first-child td { border-top: none; }
.ftable .fname { width: 250px; color: #6a643f; }
.ftable .fval code { font: 12.5px/1.5 Consolas, "Courier New", monospace; color: #2d2a16; white-space: pre-wrap; overflow-wrap: anywhere; }
.ftable .fbtns-cell { width: 54px; text-align: right; white-space: nowrap; }
.ftable-src .fname { width: auto; min-width: 190px; color: #4a3b1f; font-weight: bold; }
.ftable-src .src-url a { overflow-wrap: anywhere; }
.ftable-src tr.src-add .fname, .ftable-src tr.src-add .fval { color: #a09a8c; font-weight: normal; font-style: italic; }
.fb[data-act="copyid"] { font: bold 11px/1 Arial, sans-serif; letter-spacing: .3px; }
.ftable tr.ro .fval code { color: #6a643f; }
.ftable .htmlrow td { padding: 0 0 8px; }
.fref { font-size: 11.5px; color: #a09a8c; }
.fbtns { display: inline-flex; gap: 3px; vertical-align: middle; justify-content: flex-end; width: 100%; }
.fb { font-size: 13px; line-height: 1; padding: 3px 5px; border: 1px solid #c3b48c; border-radius: 3px; background: #fffdf5; color: #4a3b1f; cursor: pointer; }
.fb:hover { background: #e9e2cf; }
.fbtns[hidden], .fbtns.off { display: none; }

/* окно правки HTML */
.modal-edit { max-width: 780px; width: 94%; display: flex; flex-direction: column; }
.modal-edit .modal-body { flex: 1 1 auto; display: flex; flex-direction: column; min-height: 0; }
.modal-edit textarea { width: 100%; height: 46vh; box-sizing: border-box; resize: none; min-height: 240px;
  font: 12.5px/1.5 Consolas, "Courier New", monospace;
  border: 1px solid #ccc3aa; border-radius: 4px; padding: 8px 10px; color: #2d2a16; background: #fffdf5; }
.modal-drag .modal-title { cursor: move; user-select: none; }
.modal-note { font-size: 12.5px; color: #6a643f; margin-top: 6px; }
.modal-note.err { color: #8c2f2f; }
.tbtn.del { border-color: #c99a90; color: #8c2f2f; }
.tbtn.del:hover { background: #f6e3e0; }
.pj-cb { display: block; margin-top: 10px; font-size: 14px; color: #333; }
.pj-cb input { margin-right: 6px; vertical-align: middle; }
.v-empty { margin: 24px 0; padding: 14px 16px; border: 1px dashed #cfc4a6; border-radius: 4px;
  background: #fffdf5; color: #6a643f; font-size: 14px; }
.v-empty[hidden] { display: none; }
.pj-toast { position: fixed; left: 50%; bottom: 22px; transform: translateX(-50%); z-index: 200;
  background: #3a2f16; color: #fff; border-radius: 4px; padding: 9px 18px; font-size: 14px;
  box-shadow: 0 4px 18px rgba(0,0,0,.3); }
.pj-toast.err { background: #8c2f2f; }

/* post modal */
.modal-post { max-width: 720px; }
.post-controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
.post-controls label { font-size: 13px; color: #444; }
.post-controls select { font: 13px/1.3 Arial, Helvetica, sans-serif; padding: 4px 8px; border: 1px solid #ccc3aa; border-radius: 3px; color: #4a3b1f; background: #fffdf5; }
.post-controls .tbtn { padding: 5px 12px; }
.post-preview { background: #fffdf5; border: 1px solid #ddd5c3; border-radius: 4px; padding: 14px 16px; font: 14px/1.55 Arial, Helvetica, sans-serif; color: #333; white-space: pre-line; overflow-wrap: anywhere; word-break: break-word; max-height: 56vh; overflow: auto; }

.update-panel { margin: -6px 0 18px; background: #fff; border: 1px solid #ddd5c3; border-radius: 6px; padding: 14px 16px; }
.update-panel[hidden] { display: none; }
.update-status { margin-top: 12px; font-size: 14px; line-height: 1.5; white-space: pre-wrap; }
.update-actions { margin-top: 14px; display: flex; justify-content: flex-end; }

.bar { height: 14px; background: #ece4d0; border-radius: 7px; overflow: hidden; }
.bar-fill { height: 100%; width: 0; background: #b07a2f; transition: width .4s ease; }
.bar-msg { margin-top: 6px; font-size: 13px; color: #6a643f; }

/* footer */
.footer { background: #efe9da; border-top: 1px solid #d8d2c4; margin-top: 30px; padding: 18px 0 26px; font-size: 12.5px; color: #6a643f; }
.footer .source a { color: #4a3b1f; }
.footer .note { margin-top: 4px; color: #999; }
.footer .docs { margin-top: 6px; }
.footer .docs a { color: #005e8a; }
'''

def build_calendar_js():
    js = r'''/* Календарь событий: месяц/день */
(function () {
  var EVENTS = window.EVENTS || [];
  var grid = document.getElementById('cal-grid');
  var title = document.getElementById('cal-title');
  var period = document.getElementById('cal-period');
  var btnPrev = document.getElementById('cal-prev');
  var btnNext = document.getElementById('cal-next');

  var byDate = {};
  EVENTS.forEach(function (ev) {
    (byDate[ev.date] = byDate[ev.date] || []).push(ev);
  });

  var today = new Date();
  var year = today.getFullYear(), month = today.getMonth();
  var selected = null;

  var MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  var WD = ['вс','пн','вт','ср','чт','пт','сб'];
  var MONTHS_GEN = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря'];

  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function iso(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }

  function render() {
    year = Math.abs(year); if (month < 0) { month = 11; year--; } if (month > 11) { month = 0; year++; }
    title.textContent = MONTHS[month] + ' ' + year;

    var first = new Date(year, month, 1);
    var start = new Date(year, month, 1 - first.getDay());
    var tbody = grid.tBodies[0]; tbody.innerHTML = '';
    for (var r = 0; r < 6; r++) {
      var tr = document.createElement('tr');
      for (var c = 0; c < 7; c++) {
        var d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + r * 7 + c);
        var td = document.createElement('td');
        var key = iso(d);
        var hasEv = byDate[key];
        var a = document.createElement('a');
        a.className = 'day' + (d.getMonth() === month ? '' : ' out') + (hasEv ? ' ev' : '') + (selected === key ? ' sel' : '');
        a.href = '#'; a.textContent = d.getDate(); a.dataset.key = key;
        a.addEventListener('click', function (evnt) {
          evnt.preventDefault();
          selected = (this.getAttribute('class').indexOf('sel') !== -1) ? null : this.dataset.key;
          render(); renderPeriod();
        });
        if (hasEv) {
          var cnt = document.createElement('span');
          cnt.className = 'daycnt';
          cnt.textContent = hasEv.length + (hasEv.length === 1 ? ' событие' : (hasEv.length < 5 ? ' события' : ' событий'));
          a.appendChild(cnt);
        }
        td.appendChild(a);
        tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
  }

  function fmtDate(isoStr) {
    var p = isoStr.split('-');
    return parseInt(p[2], 10) + ' ' + MONTHS_GEN[parseInt(p[1], 10) - 1] + ' ' + p[0];
  }

  function eventRow(ev) {
    var div = document.createElement('div');
    div.className = 'event';
    var meta = (ev.time || '') + (ev.time_end ? '\u2013' + ev.time_end : '') + (ev.city ? ' · ' + ev.city : '');
    div.innerHTML = '<div class="edate"><div class="hday">' + ev.date.slice(8) + '</div><div class="hmeta">' + meta + '</div>' +
      (ev.source ? '<div class="hlink"><a href="' + ev.source + '" target="_blank" rel="noopener">' + ev.id + '</a></div>' : '') + '</div>' +
      '<div class="edesc"><a class="nohover" href="' + ev.url + '"><div class="pretitle">' + (ev.lecturer || '') + '</div>' +
      '<div class="title">' + ev.title + '</div><div class="lectory">' + (ev.lectory || '') + '</div></a>' +
      '<div class="sublink">' + (ev.place || '') + '</div>' +
      (ev.price ? '<div class="price">' + ev.price + '</div>' : '') + '</div>';
    return div;
  }

  function byDateList() {
    var keys = Object.keys(byDate).sort();
    var frag = document.createDocumentFragment();
    keys.forEach(function (k) {
      if (k.indexOf(year + '-' + pad(month + 1)) !== 0) return;
      byDate[k].forEach(function (ev) { frag.appendChild(eventRow(ev)); });
    });
    return frag;
  }

  function renderPeriod() {
    period.innerHTML = '';
    var h = document.createElement('h2'); h.className = 'month';
    if (selected) {
      h.textContent = fmtDate(selected);
    } else {
      h.textContent = MONTHS[month] + ' ' + year;
    }
    period.appendChild(h);
    var rows = selected ? (byDate[selected] || []).map(function (ev) { return eventRow(ev); })
                        : Array.prototype.slice.call(byDateList().childNodes);
    if (!rows.length) {
      period.appendChild(document.createTextNode('Нет событий.'));
    } else {
      rows.forEach(function (node) { period.appendChild(node); });
    }
  }

  btnPrev.addEventListener('click', function () { month--; selected = null; render(); renderPeriod(); });
  btnNext.addEventListener('click', function () { month++; selected = null; render(); renderPeriod(); });

  render();
  renderPeriod();
})();
'''
    open(os.path.join(JS_DIR, 'calendar.js'), 'w', encoding='utf-8').write(js)

def build_toolbar_js():
    snap = snapshot_str()
    js = r'''/* Кнопка «Обновить данные»: вопрос «Да/Нет», прогресс и результат — в панели под кнопкой.
   После успешного обновления страница перечитывается целиком (location.reload). */
(function () {
  var btns = [].slice.call(document.querySelectorAll('.js-update'));
  var modal = document.getElementById('modal-update');
  if (!btns.length || !modal) return;
  var ok = modal.querySelector('[data-mp="ok"]');
  var cancel = modal.querySelector('[data-mp="cancel"]');
  var isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  var SNAPSHOT = '/*SNAPSHOT*/';
  var timer = null;
  // активная панель — та, что под нажатой кнопкой (кнопок может быть две)
  var cur = null;
  var panel = null, progress = null, bar = null, msg = null, status = null, actions = null;

  function usePanel(btn) {
    cur = btn;
    var box = document.getElementById(btn.getAttribute('data-panel') || '');
    if (!box) return;
    panel = box;
    progress = box.querySelector('.update-progress');
    bar = box.querySelector('.bar-fill');
    msg = box.querySelector('.bar-msg');
    status = box.querySelector('.update-status');
    actions = box.querySelector('.update-actions');
    var cl = box.querySelector('.update-actions .tbtn');
    if (cl && !cl.dataset.wired) { cl.dataset.wired = '1'; cl.addEventListener('click', hidePanel); }
  }

  modal.hidden = true; // страховка: окно всегда закрыто при загрузке

  function showConfirm() { modal.hidden = false; }
  function hideModal() { modal.hidden = true; }
  function showProgress(m) {
    panel.hidden = false;
    status.hidden = true;
    actions.hidden = true;
    progress.hidden = false;
    setProgress(0, m || 'Начинаем обновление…');
  }
  function setProgress(p, m) {
    bar.style.width = Math.round(p) + '%';
    msg.textContent = m;
  }
  function showResult(txt, isErr) {
    if (timer) { clearInterval(timer); timer = null; }
    panel.hidden = false;
    progress.hidden = true;
    status.textContent = txt;
    status.style.color = isErr ? '#8c2f2f' : '#2e5d2e';
    status.hidden = false;
    actions.hidden = false;
    if (!isErr) {
      // Обновление удалось — перечитываем страницу целиком, чтобы новые данные отобразились.
      setTimeout(function () { location.reload(); }, 1200);
    }
  }
  function hidePanel() {
    panel.hidden = true;
    if (timer) { clearInterval(timer); timer = null; }
  }
  function reportText(r) {
    if (!r) return 'Данные обновлены, отчёт не сохранился.';
    var lines = [];
    lines.push('Добавлено: ' + (r.added || []).length);
    lines.push('Изменено: ' + (r.changed || []).length);
    lines.push('Удалено: ' + (r.removed || []).length);
    lines.push('Всего в календаре: ' + (r.total || 0));
    return lines.join('\n');
  }
  function startUpdate() {
    hideModal();
    showProgress();
    fetch('/api/update', { method: 'POST' }).then(function (res) {
      if (res.status === 409) { showResult('Обновление уже идёт.', true); return; }
      timer = setInterval(poll, 700);
    }).catch(function () {
      showResult('Не удалось связаться с сервером. Убедитесь, что serve.py запущен.', true);
    });
  }
  function poll() {
    fetch('/api/update/status').then(function (r) { return r.json(); }).then(function (s) {
      setProgress(s.percent, s.message || '');
      if (!s.running) {
        if (timer) { clearInterval(timer); timer = null; }
        if (s.error) {
          showResult('Ошибка:\n' + s.error, true);
        } else {
          var extra = s.commit ? '\nКоммит: ' + s.commit : '';
          if ((s.report && (s.report.added.length || s.report.changed.length || s.report.removed.length)) || s.commit) {
            showResult(s.message + '\n\n' + reportText(s.report) + extra, false);
          } else {
            showResult(s.message, false);
          }
        }
      }
    }).catch(function () {});
  }

  btns.forEach(function (btn) {
    btn.addEventListener('click', function () {
      usePanel(btn);
      if (isLocal) { showConfirm(); return; }
      panel.hidden = false;
      progress.hidden = true;
      actions.hidden = false;
      status.style.color = '#444';
      status.textContent = 'Обновление работает только на локальном сервере.\n'
        + 'Запустите в терминале: python serve.py\n'
        + 'и откройте http://localhost:8000\n'
        + '\nПоследнее обновление данных: ' + SNAPSHOT;
      status.hidden = false;
    });
  });
  ok.addEventListener('click', startUpdate);
  cancel.addEventListener('click', hideModal);
})();
'''.replace('/*SNAPSHOT*/', snap)
    open(os.path.join(JS_DIR, 'toolbar.js'), 'w', encoding='utf-8').write(js)

POST_JS = r'''/* Кнопка «Пост в Телеграм»: выбор дат выпадающими списками (по 7 дней,
   от первой актуальной даты) и формирование поста.
   Правила — .opencode/skills/telegram-post/SKILL.md; поля событий подготовлены
   сборщиком (место без инициалов, цена, подзаголовок). */
(function () {
  var POST_EVENTS = /*POST_EVENTS*/;
  var btns = [].slice.call(document.querySelectorAll('.js-post'));
  var modal = document.getElementById('modal-post');
  if (!btns.length || !modal) return;
  var fFrom = document.getElementById('pp-from');
  var fTo = document.getElementById('pp-to');
  var preview = document.getElementById('pp-preview');
  var btnGen = document.getElementById('pp-gen');
  var btnCopy = document.getElementById('pp-copy');
  var cur = { text: '' };

  /* --- даты (Москва, UTC+3) --- */
  function mskNow() {
    var now = new Date();
    var utc = now.getTime() + now.getTimezoneOffset() * 60000;
    return new Date(utc + 3 * 3600000);
  }
  function iso(d) {
    var y = d.getUTCFullYear();
    var m = ('0' + (d.getUTCMonth() + 1)).slice(-2);
    var day = ('0' + d.getUTCDate()).slice(-2);
    return y + '-' + m + '-' + day;
  }
  function addDays(isoStr, n) {
    var p = isoStr.split('-');
    return iso(new Date(Date.UTC(+p[0], +p[1] - 1, +p[2] + n)));
  }
  function wdNum(isoStr) {
    var p = isoStr.split('-');
    return new Date(Date.UTC(+p[0], +p[1] - 1, +p[2])).getUTCDay();
  }
  function ddmm(isoStr) {
    var p = isoStr.split('-');
    return p[2] + '.' + p[1];
  }

  /* --- актуальные даты: от первой даты с событиями, окно 7 дней --- */
  var dates = POST_EVENTS.map(function (e) { return e.date; })
    .filter(function (d, i, a) { return a.indexOf(d) === i; })
    .sort();
  var firstDate = dates[0];
  var lastDate = dates[dates.length - 1];

  function countOn(d) {
    var n = 0;
    POST_EVENTS.forEach(function (e) { if (e.date === d) n++; });
    return n;
  }

  /* список дат длиной win дней начиная с from; +n опций, если их меньше win */
  function rangeDates(from, win) {
    var out = [];
    for (var i = 0; i < win; i++) {
      var d = addDays(from, i);
      if (d > lastDate) break;
      out.push(d);
    }
    return out;
  }

  function firstEventOnOrAfter(isoStr) {
    var p = POST_EVENTS.filter(function (e) { return e.date >= isoStr; });
    return p.length ? p[0].date : lastDate;
  }
  function lastEventOnOrBefore(isoStr) {
    var p = POST_EVENTS.filter(function (e) { return e.date <= isoStr; });
    return p.length ? p[p.length - 1].date : firstDate;
  }

  function defaultToFor(from) {
    // правило «до» для выбранной начальной даты (как раньше)
    var wd = wdNum(from);
    var target = 2;            // Вс -> Вт
    if (wd === 5 || wd === 6) target = 0;  // Пт/Сб -> Вс
    else if (wd === 3 || wd === 4) target = 5;  // Ср/Чт -> Пт
    else if (wd === 1 || wd === 2) target = 3;  // Пн/Вт -> Ср
    return addDays(from, (target - wd + 7) % 7);
  }

  function fillFrom() {
    // от первой актуальной даты — все даты до последнего события
    fFrom.innerHTML = '';
    var list = rangeDates(firstDate, 9999);
    list.forEach(function (d) {
      var opt = document.createElement('option');
      opt.value = d;
      opt.textContent = ddmm(d) + ' (' + countOn(d) + ')';
      fFrom.appendChild(opt);
    });
  }

  function fillTo() {
    var from = fFrom.value || firstDate;
    var old = fTo.value;
    fTo.innerHTML = '';
    var list = rangeDates(from, 7);
    list.forEach(function (d) {
      var opt = document.createElement('option');
      opt.value = d;
      opt.textContent = ddmm(d) + ' (' + countOn(d) + ')';
      fTo.appendChild(opt);
    });
    // если прежняя конечная дата есть в новом диапазоне — оставляем её,
    // иначе ставим дату по умолчанию для выбранной начальной (не позже последней)
    var def = defaultToFor(from);
    if (def > lastDate) def = lastDate;
    fTo.value = (old && list.indexOf(old) !== -1) ? old : def;
  }

  /* --- имена дней недели в винительном падеже после «в» --- */
  var WD_ACC = ['воскресенье', 'понедельник', 'вторник', 'среду', 'четверг', 'пятницу', 'субботу'];

  function mskMidnightTs(isoStr) {
    var p = isoStr.split('-');
    return Math.floor(Date.UTC(+p[0], +p[1] - 1, +p[2]) / 1000 - 10800);
  }
  function dayUrl(isoStr) {
    return 'https://elementy.ru/events?archive=2&evdate=' + mskMidnightTs(isoStr) + '&period=d&from=tg';
  }

  function buildPost(from, to) {
    var inRange = POST_EVENTS.filter(function (e) {
      return e.date >= from && e.date <= to;
    }).sort(function (a, b) {
      return a.date === b.date
        ? ((a.time_start || '99:99') < (b.time_start || '99:99') ? -1 : 1)
        : (a.date < b.date ? -1 : 1);
    });
    var days = [];
    inRange.forEach(function (e) {
      if (days.indexOf(e.date) === -1) days.push(e.date);
    });
    days.sort();
    if (!days.length) return 'В выбранном диапазоне нет событий.';

    var first = WD_ACC[wdNum(days[0])];
    var links = days.map(function (d) {
      return WD_ACC[wdNum(d)] + '|' + dayUrl(d);
    });
    var introDays = links.length === 1 ? links[0]
      : links.slice(0, -1).join(', ') + ' и ' + links[links.length - 1];
    var prep = first === 'вторник' ? 'во ' : 'в ';
    var intro = 'Научно-популярные лекции|https://elementy.ru/events?from=tg ' + prep + introDays + ':';

    var blocks = inRange.map(function (e) {
      var p1 = [e.date.slice(8) + '.' + e.date.slice(5, 7)];
      if (e.time_start) p1.push(e.time_start);
      if (e.city) p1.push(e.city);
      var loc = e.place;
      if (e.price) loc += ' ' + e.price;
      if (loc) p1.push(loc);
      var lines = [p1.join(', ')];
      if (e.lecturer) lines.push('**' + e.lecturer + '**');
      lines.push((e.lecturer ? e.title : '**' + e.title + '**') + '|' + e.url + (e.subtitle || ''));
      return lines.join('\n');
    });

    return intro + '\n\n' + blocks.join('\n\n');
  }

  function render() {
    var from = fFrom.value || '';
    var to = fTo.value || '';
    if (from > to) return;
    cur.text = buildPost(from, to);
    preview.textContent = cur.text;
  }

  function open() {
    fillFrom();
    fFrom.value = firstEventOnOrAfter(iso(mskNow()));
    fillTo();
    render();
    modal.hidden = false;
  }

  function flashCopied() {
    btnCopy.textContent = 'Скопировано';
    setTimeout(function () { btnCopy.textContent = 'Копировать'; }, 1500);
  }
  function legacyCopy() {
    var ta = document.createElement('textarea');
    ta.value = cur.text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    flashCopied();
  }
  function copyText() {
    if (!cur.text) return;
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(cur.text).then(flashCopied, legacyCopy);
    } else {
      legacyCopy();
    }
  }

  fFrom.addEventListener('change', function () {
    if (fTo.value < fFrom.value) fTo.value = defaultToFor(fFrom.value);
    fillTo();
    render();
  });
  fTo.addEventListener('change', render);
  btns.forEach(function (b) { b.addEventListener('click', open); });
btnGen.addEventListener('click', render);
  btnCopy.addEventListener('click', copyText);
  document.getElementById('pp-close').addEventListener('click', function () { modal.hidden = true; });
  modal.addEventListener('click', function (ev) {
    if (ev.target === modal) modal.hidden = true;
  });
})();
'''

def build_prototypes_js():
    open(os.path.join(JS_DIR, 'prototypes.js'), 'w', encoding='utf-8').write(PROTOTYPES_JS)

PROTOTYPES_JS = r'''
/* Прототипы лекций: показ и скрытие, фильтры, комментарии, обратная связь,
   правка HTML. Работает на всех страницах сайта. Действия и правка — только
   на локальном сервере (localhost); на GitHub Pages кнопки скрываются. */
(function () {
  'use strict';

  var IS_LOCAL = /^(localhost|127\.0\.0\.1|\[::1\])$/i.test(location.hostname);
  var K_MODE = 'nk_mode', K_HIDDEN = 'nk_hidden', K_ORG = 'nk_organizers',
      K_ORG_ALL = 'nk_organizers_all';

  // ------------------------------------------------------------------ утилиты
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function kids(el) { return Array.prototype.slice.call(el.children); }
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function copyText(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-9999px';
    document.body.appendChild(ta);
    ta.select();
    var ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  }
  function copyWith(text) {
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      return Promise.resolve(copyText(text));
    }
    // Современный буфер обмена может «зависнуть» (нет фокуса, запрет,
    // старое разрешение) — тогда не показываем отклик очень долго:
    // через 700 мс пробуем старый способ, чтобы пользователь всегда
    // увидел результат.
    return Promise.race([
      navigator.clipboard.writeText(text).then(function () { return true; },
        function () { return copyText(text); }),
      new Promise(function (res) {
        setTimeout(function () { res(copyText(text)); }, 700);
      })
    ]);
  }
  /* Копирование с понятным откликом: если браузер не дал доступ к буферу,
     сообщаем об этом, а не делаем вид, что всё получилось. */
  function copyReport(text) {
    if (!text) { toast('Нечего копировать: значение пустое', true); return; }
    copyWith(text).then(function (ok) {
      if (ok) toast('Код скопирован в буфер обмена');
      else toast('Браузер не дал доступ к буферу — выделите код и нажмите Ctrl+C', true);
    });
  }

  function toast(msg, err) {
    var old = $('.pj-toast');
    if (old) old.parentNode.removeChild(old);
    var d = document.createElement('div');
    d.className = 'pj-toast' + (err ? ' err' : '');
    d.textContent = msg;
    document.body.appendChild(d);
    setTimeout(function () { if (d.parentNode) d.parentNode.removeChild(d); }, err ? 7000 : 2500);
  }

  // ------------------------------------------------ перетаскивание модальных окон
  document.addEventListener('mousedown', function (e) {
    var t = e.target;
    if (!t || !t.classList || !t.classList.contains('modal-title')) return;
    var m = t.parentNode;
    if (!m || !m.classList || !m.classList.contains('modal')) return;
    var r = m.getBoundingClientRect();
    var dx = e.clientX - r.left, dy = e.clientY - r.top;
    m.style.position = 'fixed';
    m.style.margin = '0';
    function mv(ev) {
      m.style.left = Math.min(Math.max(2, ev.clientX - dx), window.innerWidth - 60) + 'px';
      m.style.top = Math.min(Math.max(2, ev.clientY - dy), window.innerHeight - 30) + 'px';
    }
    function up() {
      document.removeEventListener('mousemove', mv);
      document.removeEventListener('mouseup', up);
    }
    document.addEventListener('mousemove', mv);
    document.addEventListener('mouseup', up);
    e.preventDefault();
  });

  // ---------------------------------------------------------- диалог правки/заметки
  var ov = null, box = null;
  function ensureOverlay() {
    if (ov) return;
    ov = document.createElement('div');
    ov.className = 'modal-overlay';
    ov.hidden = true;
    ov.style.alignItems = 'flex-start';
    ov.style.justifyContent = 'flex-start';
    box = document.createElement('div');
    box.className = 'modal';
    ov.appendChild(box);
    document.body.appendChild(ov);
    ov.addEventListener('mousedown', function (e) { if (e.target === ov) closeModal(); });
  }
  /* Окно ставим рядом с полем (по возможности не перекрывая его): справа, если
     помещается, иначе слева, иначе по центру экрана. */
  function openModal(html, near) {
    ensureOverlay();
    box.className = 'modal';
    box.innerHTML = html;
    ov.hidden = false;
    box.style.left = '';
    box.style.top = '';
    if (near && near.getBoundingClientRect) {
      var r = near.getBoundingClientRect();
      box.style.position = 'fixed';
      var w = box.offsetWidth, h = box.offsetHeight;
      var left = r.right + 16;
      if (left + w > window.innerWidth - 8) left = r.left - w - 16;
      if (left < 8) left = Math.max(8, (window.innerWidth - w) / 2);
      var top = r.top - 10;
      if (top + h > window.innerHeight - 8) top = Math.max(8, window.innerHeight - h - 8);
      box.style.left = left + 'px';
      box.style.top = top + 'px';
    } else {
      box.style.position = '';
      ov.style.alignItems = '';
      ov.style.justifyContent = '';
    }
    return box;
  }
  function closeModal() {
    if (!ov) return;
    ov.hidden = true;
    box.innerHTML = '';
    modalDirty = null;
  }
  function wireModal(b, onBtn) {
    b.addEventListener('click', function (e) {
      var x = e.target.getAttribute && e.target.getAttribute('data-x');
      if (x) onBtn(x, e.target);
    });
  }

  /* Отслеживаем, менял ли пользователь содержимое окна. modalDirty — функция,
     возвращающая true, если содержимое отличается от исходного. */
  var modalDirty = null;
  function trackDirty(get) { modalDirty = get; }
  function isDirty() { return !!(modalDirty && modalDirty()); }
  function hasText(get) { return !!(get() || '').replace(/[ \\t\\r\\n]+/g, ''); }

  /* Окно подтверждения поверх текущего: спрашиваем, нельзя ли закрыть/удалить.
     Возвращает промис, который resolves в true (да) или false (нет). */
  var ov2 = null, box2 = null;
  function askConfirm(title, text, okLabel, okClass) {
    return new Promise(function (res) {
      if (!ov2) {
        ov2 = document.createElement('div');
        ov2.className = 'modal-overlay';
        ov2.hidden = true;
        box2 = document.createElement('div');
        box2.className = 'modal modal-confirm';
        ov2.appendChild(box2);
        document.body.appendChild(ov2);
      }
      box2.innerHTML = '<div class="modal-title">' + esc(title) + '</div>'
        + '<div class="modal-body"><p class="modal-hint">' + esc(text) + '</p></div>'
        + '<div class="modal-actions">'
        + '<button type="button" class="tbtn sec" data-c="no">Отмена</button>'
        + '<button type="button" class="tbtn ' + (okClass || 'del') + '" data-c="yes">'
        + esc(okLabel) + '</button></div>';
      ov2.hidden = false;
      ov2.style.alignItems = '';
      ov2.style.justifyContent = '';
      function done(v) { ov2.hidden = true; box2.innerHTML = ''; res(v); }
      ov2.onclick = function (e) {
        var c = e.target.getAttribute && e.target.getAttribute('data-c');
        if (c === 'yes') return done(true);
        if (c === 'no' || e.target === ov2) return done(false);
      };
      box2.querySelector('[data-c="no"]').focus();
    });
  }
  /* ESC закрывает окно. Если в нём были несохранённые изменения, нужно нажать
     ESC дважды (второе нажатие показывает подсказку и закрывает без сохранения)
     — иначе несохранённый текст пропал бы случайно. */
  var escArmed = false;
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') { escArmed = false; return; }
    if (ov2 && !ov2.hidden) { e.preventDefault(); ov2.hidden = true; box2.innerHTML = ''; return; }
    if (!ov || ov.hidden) { escArmed = false; return; }
    e.preventDefault();
    if (isDirty() && !escArmed) {
      escArmed = true;
      toast('В окне несохранённые изменения: ESC ещё раз — закрыть без сохранения');
      return;
    }
    escArmed = false;
    closeModal();
  });

  // ------------------------------------------------------------------ сервер
  function api(payload) {
    return fetch('/api/proto', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().catch(function () { return { ok: false, error: 'сервер не ответил' }; })
        .then(function (j) {
          if (r.status === 404 || (j && j.error === 'not found')) {
            throw new Error('сервер запущен старой версией — закройте его и снова '
              + 'запустите «python serve.py»');
          }
          if (!r.ok || !j.ok) throw new Error(j.error || ('ошибка ' + r.status));
          return j;
        });
    });
  }
  function reload() {
    if (/\/event\//.test(location.pathname)) location.href = '../index.html';
    else location.reload();
  }
  /* run(): сохранить на сервере и перезагрузить. reload() со страницы прототипа
     уводит в список — этим и пользуется сохранение обратной связи и комментария.
     stay=true — остаться на текущей странице (перечитать её на месте): так
     работают удаление комментария/обратной связи и кнопка «Скрыть»
     (замечание пользователя 27.09.2026). */
  function run(payload, okMsg, stay) {
    toast('Сохраняю…');
    return api(payload).then(function () {
      toast(okMsg);
      setTimeout(stay ? function () { location.reload(); } : reload, 400);
    }).catch(function (e) { toast('Не получилось: ' + e.message, true); });
  }
  function pageId() {
    var el = $('.ptop[data-id]');
    return el ? el.getAttribute('data-id') : null;
  }

  // ------------------------------------------- шапка окна: к какому событию
  /* При открытии из списка показываем дату, автора и название события. */
  function subLine(box) {
    var card = box.closest ? box.closest('.event.proto') : null;
    if (!card) return '';
    var when = card.getAttribute('data-where') || card.getAttribute('data-date') || '';
    var who = card.getAttribute('data-lecturer') || '';
    var what = card.getAttribute('data-title') || '';
    if (!when && !who && !what) return '';
    return '<div class="modal-sub">' + esc([when, who, what].filter(Boolean).join(' · ')) + '</div>';
  }

  // ---------------------------------------------------------------- комментарий
  function openComment(box) {
    var id = box.getAttribute('data-id');
    var b = openModal(
      '<div class="modal-title">Комментарий</div>'
      + subLine(box)
      + '<div class="modal-hint">Виден вам и агентам, на сайте «Элементов» его не будет. '
      + 'Пустой комментарий удаляется.</div>'
      + '<div class="modal-body"><textarea id="pj-ta" spellcheck="false"'
      + ' placeholder="Например: проверить дату на сайте организатора"></textarea></div>'
      + '<div class="modal-actions"><button type="button" class="tbtn sec" data-x="cancel">Закрыть</button>'
      + '<button type="button" class="tbtn" data-x="save">Сохранить</button></div>',
      null);
    b.classList.add('modal-note-win', 'modal-drag', 'modal-resize');
    var ta = $('#pj-ta', b);
    var orig = (box.getAttribute('data-comment') || '');
    ta.value = orig;
    ta.focus();
    trackDirty(function () { return ta.value.trim() !== orig.trim(); });
    wireModal(b, function (x) {
      if (x === 'cancel') {
        /* непустой комментарий (пробелы не считаем) — спрашиваем подтверждение */
        if (!hasText(function () { return ta.value; })) return closeModal();
        return askConfirm('Закрыть без сохранения?',
          'Комментарий не будет сохранён — текст пропадёт.', 'Закрыть без сохранения')
          .then(function (yes) { if (yes) closeModal(); });
      }
      if (x === 'save') {
        var v = ta.value;
        closeModal();
        run({ action: 'comment', id: id, value: v },
          v.replace(/[ \\t\\r\\n]+/g, '') ? 'Комментарий сохранён' : 'Комментарий удалён');
      }
    });
  }

  // ----------------------------------------------------------- обратная связь
  function openFeedback(box) {
    var id = box.getAttribute('data-id');
    var b = openModal(
      '<div class="modal-title">Обратная связь</div>'
      + subLine(box)
      + '<div class="modal-hint">Что нужно поменять в прототипе. Это задача агенту: исправьте '
      + 'описание, потом вернитесь и снимите галочку «Переделать».</div>'
      + '<div class="modal-body"><textarea id="pj-ta" spellcheck="false"'
      + ' placeholder="Что исправить в описании прототипа"></textarea>'
      + '<label class="pj-cb"><input type="checkbox" id="pj-rb"'
      + (box.getAttribute('data-rebuild') === '1' ? ' checked' : '')
      + '> Переделать (событие нужно создать заново)</label></div>'
      + '<div class="modal-actions"><button type="button" class="tbtn sec" data-x="cancel">Закрыть</button>'
      + '<button type="button" class="tbtn" data-x="save">Сохранить</button></div>',
      null);
    b.classList.add('modal-note-win', 'modal-drag', 'modal-resize');
    var ta = $('#pj-ta', b), cb = $('#pj-rb', b);
    var orig = (box.getAttribute('data-feedback') || '');
    var origRb = box.getAttribute('data-rebuild') === '1';
    ta.value = orig;
    ta.focus();
    trackDirty(function () { return ta.value.trim() !== orig.trim() || cb.checked !== origRb; });
    wireModal(b, function (x) {
      if (x === 'cancel') {
        if (!hasText(function () { return ta.value; }) && cb.checked === origRb) return closeModal();
        return askConfirm('Закрыть без сохранения?',
          'Обратная связь не будет сохранена — текст пропадёт.', 'Закрыть без сохранения')
          .then(function (yes) { if (yes) closeModal(); });
      }
      if (x === 'save') {
        var v = ta.value, rb = cb.checked;
        closeModal();
        /* после сохранения обратной связи — сразу в список: задача уже передана агенту */
        run({ action: 'feedback', id: id, value: v, rebuild: rb },
          (v.replace(/[ \\t\\r\\n]+/g, '') || rb) ? 'Обратная связь сохранена' : 'Обратная связь удалена');
      }
    });
  }

  // --------------------------------------------------------------------- правка
  function openEdit(fb, area, key, name, value) {
    var b = openModal(
      '<div class="modal-title">Правка: ' + esc(name) + '</div>'
      + '<div class="modal-hint">Правится HTML-код. «Сохранить» перезапишет значение и пересоберёт '
      + 'сайт; правка работает только на локальном сервере.</div>'
      + '<div class="modal-body"><textarea id="pj-ta" spellcheck="false"></textarea></div>'
      + '<div class="modal-actions">'
      + '<button type="button" class="tbtn sec" data-x="cancel">Закрыть</button>'
      + '<button type="button" class="tbtn sec" data-x="copy">Скопировать</button>'
      + '<button type="button" class="tbtn" data-x="save">Сохранить</button></div>',
      null);
    b.classList.add('modal-edit', 'modal-drag', 'modal-resize');
    $('#pj-ta', b).value = value || '';
    $('#pj-ta', b).focus();
    wireModal(b, function (x) {
      if (x === 'cancel') return closeModal();
      if (x === 'copy') { copyReport($('#pj-ta', b).value); return; }
      if (x === 'save') {
        var v = $('#pj-ta', b).value;
        closeModal();
        run({ action: 'field', id: pageId(), area: area, key: key, value: v },
          'Сохранено, сайт пересобран');
      }
    });
  }

  // ------------------------------------------------------------------ удаление
  function openDelete(box) {
    var id = box.getAttribute('data-id');
    var b = openModal(
      '<div class="modal-title">Удалить прототип?</div>'
      + subLine(box)
      + '<div class="modal-hint">Прототип <b>' + esc(id) + '</b> уберётся с сайта, а его папка '
      + 'перенесётся в <code>data/prototypes/_archive/</code> — безвозвратно ничего не пропадёт. '
      + 'Понадобится снова — вернём папку на место.</div>'
      + '<div class="modal-actions"><button type="button" class="tbtn sec" data-x="cancel">Закрыть</button>'
      + '<button type="button" class="tbtn del" data-x="del">Удалить</button></div>', null);
    b.classList.add('modal-note-win', 'modal-drag');
    wireModal(b, function (x) {
      if (x === 'cancel') return closeModal();
      if (x === 'del') { closeModal(); run({ action: 'delete', id: id }, 'Прототип удалён (в архиве)'); }
    });
  }

  // -------------------------------------------------------------- обработчики
  document.addEventListener('click', function (e) {
    /* иконка удаления у выведенного комментария / обратной связи */
    var un = e.target.closest ? e.target.closest('.usernotes .un-del') : null;
    if (un && IS_LOCAL) {
      var ubox = un.closest('.usernotes');
      var uact = un.getAttribute('data-act');
      var uid = ubox.getAttribute('data-id');
      var what = uact === 'del-feedback' ? 'обратную связь' : 'комментарий';
      e.stopPropagation();
      return askConfirm('Удалить ' + what + '?',
        'Текст будет удалён из файла состояния. Отменить это будет нельзя.',
        'Удалить', 'del').then(function (yes) {
          if (!yes) return;
          run({ action: uact === 'del-feedback' ? 'feedback' : 'comment',
                id: uid, value: '', rebuild: false },
            what === 'обратная связь' ? 'Обратная связь удалена' : 'Комментарий удалён',
            true);
        });
    }
    var pb = e.target.closest ? e.target.closest('.pbtns .pb') : null;
    if (pb && IS_LOCAL) {
      var pbox = pb.closest('.pbtns');
      var act = pb.getAttribute('data-act');
      var id = pbox.getAttribute('data-id');
      if (act === 'comment') return openComment(pbox);
      if (act === 'feedback') return openFeedback(pbox);
      if (act === 'delete') return openDelete(pbox);
      if (act === 'hide') {
        var hidden = pbox.getAttribute('data-hidden') === '1';
        run({ action: 'hide', id: id, hidden: !hidden },
          hidden ? 'Прототип показан' : 'Прототип скрыт', true);
      }
      return;
    }
    var fb = e.target.closest ? e.target.closest('.fbtns .fb') : null;
    if (!fb) return;
    var wrap = fb.closest('.fbtns');
    var val = wrap.getAttribute('data-text');
    if (val == null) val = '';
    if (fb.getAttribute('data-act') === 'copy') { copyReport(val); return; }
    if (fb.getAttribute('data-act') === 'copyid') {
      copyReport(fb.getAttribute('data-text') || '');
      return;
    }
    if (IS_LOCAL) openEdit(fb, wrap.getAttribute('data-area'), wrap.getAttribute('data-key'),
      wrap.getAttribute('data-name'), val);
  });

  // на не-локальном сайте (GitHub Pages) кнопки правки и действия не показываем
  if (!IS_LOCAL) {
    $$('.pbtns').forEach(function (b) { b.hidden = true; });
    $$('.fbtns .fb[data-act=edit]').forEach(function (b) { b.style.display = 'none'; });
  }

  // ========================================================= главная: фильтры
  var main = $('.idxmain');
  if (!main) return;

  var radios = $$('input[name=vmode]');
  var cbHidden = $('#v-showhidden');
  var btnOrg = $('#btn-organizers');
  var orgBoxes = function () { return $$('#org-list input[type=checkbox]'); };
  var mode = load(K_MODE) || 'all';
  var showHidden = load(K_HIDDEN) === '1';

  function chosenOrg() {
    try { return JSON.parse(load(K_ORG) || 'null'); } catch (e) { return null; }
  }
  function knownOrg() {
    try { return JSON.parse(load(K_ORG_ALL) || 'null'); } catch (e) { return null; }
  }
  function curOrg() {
    var b = orgBoxes();
    return b.length ? b.filter(function (x) { return x.checked; }).map(function (x) { return x.value; }) : null;
  }
  function orgAll() { return orgBoxes().map(function (x) { return x.value; }); }
  function isVisible(ev) {
    var kind = ev.getAttribute('data-kind');
    var m = radios.filter(function (r) { return r.checked; })[0];
    var md = m ? m.value : 'all';
    if (md === 'el' && kind !== 'el') return false;
    if (md === 'proto' && kind !== 'proto') return false;
    if (kind !== 'proto') return true;
    if ((' ' + ev.className + ' ').indexOf(' hidden ') >= 0 && !(cbHidden && cbHidden.checked)) return false;
    var c = curOrg();
    return !c || c.indexOf(ev.getAttribute('data-organizer') || '') >= 0;
  }
  function countsLine(cnt) {
    var ds = Object.keys(cnt).sort();
    if (!ds.length) return '';
    return ds.map(function (d) {
      var p = d.split('-');
      return p[2] + '.' + p[1] + ': ' + cnt[d];
    }).join('. ') + '.';
  }
  /* Прячет невидимые события, пересчитывает счётчики дней в неделях, прячет
     пустые недели и месяцы и правит оглавление. */
  function applyFilter() {
    var els = kids(main), any = false, i = 0;
    while (i < els.length) {
      var el = els[i];
      if (el.tagName !== 'H2') { i++; continue; }
      var monthVisible = false, j = i + 1;
      while (j < els.length && els[j].tagName !== 'H2') {
        if (els[j].tagName === 'H3') {
          var counts = {}, cnt = null, wvis = false, k = j + 1;
          while (k < els.length && els[k].tagName !== 'H2' && els[k].tagName !== 'H3') {
            var it = els[k];
            if (it.classList.contains('event')) {
              var vis = isVisible(it);
              it.hidden = !vis;
              if (vis) {
                wvis = true;
                var d = it.getAttribute('data-date') || '';
                counts[d] = (counts[d] || 0) + 1;
              }
            } else if (it.classList.contains('weekcount')) { cnt = it; }
            k++;
          }
          els[j].hidden = !wvis;
          if (cnt) { cnt.hidden = !wvis; cnt.textContent = countsLine(counts); }
          if (wvis) monthVisible = true;
          j = k;
        } else { j++; }
      }
      el.hidden = !monthVisible;
      if (monthVisible) any = true;
      i = j;
    }
    var toc = $('.toc');
    if (toc) {
      $$('a[href^="#"]', toc).forEach(function (a) {
        var t = document.getElementById(a.getAttribute('href').slice(1));
        var li = a.parentNode;
        if (li && li.tagName === 'LI') li.hidden = !t || t.hidden;
      });
    }
    var none = $('#v-empty');
    if (none) none.hidden = any;
  }

  // организаторы: восстанавливаем сохранённый выбор до первого расчёта.
  // Важно: сохранённый список знает только те организации, которые были на
  // странице в момент сохранения. Новый организатор (например, СПбГУ) в нём
  // отсутствует — раньше он молча снимался, и его прототип не показывался.
  // Поэтому для знакомых берём сохранённое состояние, а новые
  // оставляем включёнными.
  var savedOrg = chosenOrg();
  if (savedOrg) {
    var wasKnown = knownOrg();
    orgBoxes().forEach(function (b) {
      b.checked = wasKnown && wasKnown.indexOf(b.value) < 0
        ? true
        : savedOrg.indexOf(b.value) >= 0;
    });
  }

  radios.forEach(function (r) {
    if (r.value === mode) r.checked = true;
    r.addEventListener('change', function () { store(K_MODE, r.value); applyFilter(); });
  });
  if (cbHidden) {
    cbHidden.checked = showHidden;
    cbHidden.addEventListener('change', function () {
      store(K_HIDDEN, cbHidden.checked ? '1' : '0');
      applyFilter();
    });
  }
  if (btnOrg) {
    btnOrg.addEventListener('click', function () {
      var chosen = chosenOrg();
      if (chosen) {
        var wasKnown = knownOrg();
        orgBoxes().forEach(function (b) {
          b.checked = (wasKnown && wasKnown.indexOf(b.value) < 0)
            ? true
            : chosen.indexOf(b.value) >= 0;
        });
      }
      $('#modal-organizers').hidden = false;
    });
  }
  ['all', 'none', 'inv'].forEach(function (what) {
    var b = $('#org-' + what);
    if (!b) return;
    b.addEventListener('click', function () {
      orgBoxes().forEach(function (x) {
        if (what === 'all') x.checked = true;
        else if (what === 'none') x.checked = false;
        else x.checked = !x.checked;
      });
    });
  });
  var orgOk = $('#org-ok');
  if (orgOk) {
    orgOk.addEventListener('click', function () {
      store(K_ORG, JSON.stringify(curOrg()));
      store(K_ORG_ALL, JSON.stringify(orgAll()));
      $('#modal-organizers').hidden = true;
      applyFilter();
    });
  }
  var orgOv = $('#modal-organizers');
  if (orgOv) {
    orgOv.addEventListener('click', function (e) { if (e.target === orgOv) orgOv.hidden = true; });
  }

  // фильтры — явные: показываем, что именно сейчас включено, и даём сбросить
  function doResetFilters() {
    var all = orgAll();
    store(K_MODE, 'all');
    store(K_HIDDEN, '0');
    store(K_ORG, JSON.stringify(all));
    store(K_ORG_ALL, JSON.stringify(all));
    mode = 'all';
    showHidden = false;
    radios.forEach(function (r) { r.checked = (r.value === 'all'); });
    orgBoxes().forEach(function (b) { b.checked = true; });
    if (cbHidden) cbHidden.checked = false;
    applyFilter();
    filterNote();
  }
  var btnReset = $('#btn-reset-filters');
  if (btnReset) btnReset.addEventListener('click', doResetFilters);
  var btnReset2 = $('#btn-reset-filters-2');
  if (btnReset2) btnReset2.addEventListener('click', doResetFilters);

  function filterNote() {
    var note = $('#filter-note');
    if (!note) return;
    var m = radios.filter(function (r) { return r.checked; })[0];
    var parts = [];
    if (m && m.value === 'el') parts.push('только «Элементы»');
    if (m && m.value === 'proto') parts.push('только прототипы');
    if (cbHidden && cbHidden.checked) parts.push('показаны скрытые');
    var c = curOrg();
    if (c) {
      var all = orgAll();
      if (c.length === 0) parts.push('организаторы: ни одного');
      else if (c.length < all.length) parts.push('организаторы: ' + c.join(', '));
    }
    if (!parts.length) { note.hidden = true; return; }
    note.hidden = false;
    $('#filter-note-text').textContent = 'Фильтры включены (' + parts.join('; ')
      + ') — показаны не все события.';
  }
  applyFilter();
  filterNote();
  if (main) {
    var mo = new MutationObserver(function () { filterNote(); });
    mo.observe(main, { attributes: true, childList: true, subtree: true,
                       attributeFilter: ['hidden'] });
  }
})();
'''

def build_post_js():
    post = []
    for e in evs:
        post.append({
            'date': e['date_iso'],
            'time_start': e.get('time_start') or '',
            'city': e.get('city') or '',
            'place': clean_place(e.get('place') or ''),
            'price': price_txt(e.get('price_short') or ''),
            'lecturer': e.get('lecturer') or '',
            'title': e.get('title') or '',
            'subtitle': post_subtitle(e),
            'url': (e.get('url') or '') + '?period=m&from=tg',
        })
    data = json.dumps(post, ensure_ascii=False, indent=1)
    js = POST_JS.replace('/*POST_EVENTS*/', data)
    open(os.path.join(JS_DIR, 'post.js'), 'w', encoding='utf-8').write(js)

def copy_favicon():
    for name in ('favicon.ico', 'favicon.png'):
        src = os.path.join(ROOT, 'assets', name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(SITE, name))

def write_robots():
    with open(os.path.join(SITE, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write('User-agent: *\nDisallow: /\n')

def verify_calendar():
    # Калибровка недельной сетки. Неделя = Пн–Вс, все недели месяца показываются
    # (даже без событий), каждая неделя ограничена границами месяца.
    # 1: понедельник должен быть началом недели самого себя.
    monday = datetime.date(2026, 9, 28)   # понедельник
    assert week_start(monday) == monday
    assert week_start(monday + datetime.timedelta(days=6)) == monday  # воскресенье в той же неделе
    # 2: эталонная полная сетка недель (все недели месяца, включая пустые).
    ref = {
        202609: ['01–06.09', '07–13.09', '14–20.09', '21–27.09', '28–30.09'],
        202610: ['01–04.10', '05–11.10', '12–18.10', '19–25.10', '26–31.10'],
        202611: ['01.11', '02–08.11', '09–15.11', '16–22.11', '23–29.11', '30.11'],
        202612: ['01–06.12', '07–13.12', '14–20.12', '21–27.12', '28–31.12'],
    }
    for ym, expected in ref.items():
        y, m = divmod(ym, 100) if ym >= 202600 else (ym // 100, ym % 100)
        labels = [wl for _ws, wl, _days in month_weeks(y, m)]
        assert labels == expected, 'Сетка недель %d-%02d не совпала: %s (ожидалось %s)' % (y, m, labels, expected)
    assert sum(len(days) for _ws, _l, days in month_weeks(2026, 2)) == 28  # февраль 2026 простой
    print('Календарная сетка недель: OK (неделя Пн–Вс, все недели месяца показаны)')

def main():
    verify_calendar()
    progress(20, 'Прототипы…')
    notes = load_prototypes()
    for n in notes:
        print('  прототип: ' + n)
    print('Прототипы: всего %d, показано %d, скрыто %d (из них дублей «Элементов»: %d), в архив: %d'
          % (PROTO_SUMMARY['total'], PROTO_SUMMARY['shown'], PROTO_SUMMARY['hidden'],
             PROTO_SUMMARY['dup'], PROTO_SUMMARY['archived']))
    progress(30, 'Страница событий…')
    build_index()
    progress(55, 'Страницы событий…')
    build_event_pages()
    build_reload_js()
    progress(75, 'Календарь…')
    build_calendar()
    build_calendar_js()
    build_toolbar_js()
    build_post_js()
    build_prototypes_js()
    with open(os.path.join(CSS_DIR, 'style.css'), 'w', encoding='utf-8') as f:
        f.write(CSS)
    copy_favicon()
    write_robots()
    progress(100, 'Сайт собран.')
    print('Done. Pages:', len(items) + 3)

if __name__ == '__main__':
    main()