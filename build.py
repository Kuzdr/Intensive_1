# -*- coding: utf-8 -*-
"""Сборка статического сайта из data/events.json -> site/"""
import os, re, json, datetime, html as H, shutil

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

MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
MONTHS_NOM = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
WEEKDAYS = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']

def esc(s):
    return H.escape(s or '')

def fmt_date_ru(iso):
    y, m, d = map(int, iso.split('-'))
    return '%d %s %d' % (d, MONTHS_GEN[m - 1], y)

def fmt_date_short(iso):
    y, m, d = map(int, iso.split('-'))
    return '%02d.%02d' % (d, m)

def fmt_time(e):
    t = e.get('time_start') or ''
    if e.get('time_end'):
        t += '\u2013' + e['time_end']
    return t

def month_label(iso):
    y, m, d = map(int, iso.split('-'))
    return '%s %d' % (MONTHS_NOM[m - 1], y)

def url_detail(e, prefix=''):
    return prefix + 'event/%s.html' % e['id']

def annot_snippet(e, limit=260):
    a = re.sub(r'\s+', ' ', (e.get('annot') or '')).strip()
    if not a:
        return ''
    if len(a) > limit:
        a = a[:limit].rstrip(' ,;:') + '…'
    return a

def card(e, prefix=''):
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
    return f'''<div class="event">
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

def footer(prefix=''):
    return f'''<div class="footer">
  <div class="wrap">
    <div class="source">Данные: <a href="https://elementy.ru/events" target="_blank">elementy.ru/events</a> — предстоящие события (снимок от 16.09.2026).</div>
    <div class="note">Прототип. Не является официальным сайтом «Элементов». Уточняйте условия у организаторов.</div>
  </div>
</div>'''

def page(title, body, active, prefix=''):
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
</body>
</html>'''

TOOLBAR = '''<div class="toolbar">
  <button type="button" class="tbtn" id="btn-update">Обновить данные</button>
  <div class="toolbar-more" title="Место для будущих кнопок (пост для Телеграма, обход источников, фильтры показа)"></div>
</div>'''

PANEL = '''<div class="update-panel" id="update-panel" hidden>
  <div class="update-progress" id="up-progress" hidden>
    <div class="bar"><div class="bar-fill" id="up-bar"></div></div>
    <div class="bar-msg" id="up-msg"></div>
  </div>
  <div class="update-status" id="up-status"></div>
  <div class="update-actions" id="up-actions" hidden>
    <button type="button" class="tbtn sec" id="up-close">Закрыть</button>
  </div>
</div>'''

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

def build_index():
    body_parts = ['<h1>Календарь событий</h1>',
                  '<p class="intro">Предстоящие научно-популярные лекции, встречи и круглые столы. Открывайте событие, чтобы узнать подробности и стоимость.</p>',
                  TOOLBAR,
                  PANEL]
    cur_month = None
    for e in evs:
        ml = month_label(e['date_iso'])
        if ml != cur_month:
            cur_month = ml
            body_parts.append(f'<h2 class="month">{esc(ml)}</h2>')
        body_parts.append(card(e))
    body_parts.append(MODAL)
    body_parts.append('<script src="js/toolbar.js"></script>')
    body = '\n'.join(body_parts)
    open(os.path.join(SITE, 'index.html'), 'w', encoding='utf-8').write(page('Календарь событий', body, 'events'))

def render_memo(e, prefix):
    m = e.get('detail_html') or ''
    m = m.replace('\\', '/')
    m = m.replace('assets/img/', prefix + 'assets/img/')
    return m

def build_event_pages():
    n = len(evs)
    for i, e in enumerate(evs):
        nav_prev = nav_next = ''
        if i > 0:
            p = evs[i - 1]
            nav_prev = f'<a class="pagenav prev" href="{p["id"]}.html"><span>Предыдущее</span><b>{esc(p["title"])}</b><i>{esc(fmt_date_short(p["date_iso"]))} · {esc(p["lecturer"] or "")}</i></a>'
        if i < n - 1:
            nxt = evs[i + 1]
            nav_next = f'<a class="pagenav next" href="{nxt["id"]}.html"><span>Следующее</span><b>{esc(nxt["title"])}</b><i>{esc(fmt_date_short(nxt["date_iso"]))} · {esc(nxt["lecturer"] or "")}</i></a>'
        reg = ''
        if e.get('reg_links'):
            links = ' · '.join(
                f'<a href="{esc(l["href"])}" target="_blank" rel="noopener">{esc(l["text"])}</a>' for l in e['reg_links'])
            reg = f'<div class="reglinks"><span class="lbl">Регистрация:</span> {links}</div>'
        upd_src = ''
        if e.get('updated'):
            upd_src = f'<div class="upd-src">Обновлено: {esc(e.get("updated_at", ""))}</div>'
        body = f'''<div class="crumb"><a href="../index.html">Календарь событий</a> » <span>{esc(e['title'] or '')}</span></div>
  <div class="detailblk">
    {render_memo(e, '../')}
  </div>
  <div class="sourcebox">
    <div class="price-short">Стоимость: <b>{esc(e['price_short'] or 'не указана')}</b></div>
    {upd_src}
    {reg}
    <div class="src">Источник: <a href="{esc(e['url'])}" target="_blank" rel="noopener">страница на elementy.ru</a> (ID {esc(e['id'])})</div>
  </div>
  <div class="pagenavs">
    {nav_prev}{nav_next}
  </div>'''
        open(os.path.join(EVENT_DIR, e['id'] + '.html'), 'w', encoding='utf-8').write(
            page(e['title'] or ('Событие ' + e['id']), body, 'events', '../'))

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
* { box-sizing: border-box; }
body { margin: 0; background: #f4f1ea; color: #222; font: 14px/1.5 Arial, Helvetica, sans-serif; }
a { color: #005e8a; text-decoration: none; }
a:hover { color: #02334d; }
.wrap { max-width: 920px; margin: 0 auto; padding: 0 16px; }

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

.month { font: normal 22px/1.2 Georgia, serif; color: #8a7040; border-bottom: 1px solid #ddd5c3; padding-bottom: 6px; margin: 26px 0 14px; }

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
.itemblock.memo { background: #fff; border: 1px solid #ddd5c3; padding: 18px 22px; }
.itemblock.memo p { margin: 10px 0; }
.itemblock.memo .small { font-size: 12.5px; color: #333; }
.itemblock.memo blockquote { background: #f3efdc; border-left: 3px solid #c8bb8f; margin: 12px 0; padding: 10px 14px; }
.itemblock.memo blockquote p { margin: 6px 0; }
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
.toolbar-more { flex: 1 1 auto; min-width: 120px; border: 1px dashed #cfc4a6; border-radius: 4px; min-height: 36px; }

.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal-overlay[hidden] { display: none; }
.modal { background: #fff; max-width: 560px; width: 92%; border-radius: 8px; padding: 22px 24px; box-shadow: 0 10px 40px rgba(0,0,0,.3); }
.modal-title { font: bold 20px/1.3 Georgia, serif; color: #3a2f16; margin-bottom: 10px; }
.modal-hint { font-size: 14px; color: #444; line-height: 1.5; }
.modal-actions { margin-top: 18px; display: flex; gap: 10px; justify-content: flex-end; flex-wrap: wrap; }

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
    js = r'''/* Кнопка «Обновить данные»: вопрос «Да/Нет», прогресс и результат — в панели под кнопкой */
(function () {
  var btn = document.getElementById('btn-update');
  var modal = document.getElementById('modal-update');
  if (!btn || !modal) return;
  var ok = document.getElementById('mp-ok');
  var cancel = document.getElementById('mp-cancel');
  var panel = document.getElementById('update-panel');
  var progress = document.getElementById('up-progress');
  var bar = document.getElementById('up-bar');
  var msg = document.getElementById('up-msg');
  var status = document.getElementById('up-status');
  var actions = document.getElementById('up-actions');
  var isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
  var timer = null;

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
          showResult(s.message + '\n\n' + reportText(s.report) + extra, false);
        }
      }
    }).catch(function () {});
  }

  btn.addEventListener('click', function () {
    if (isLocal) { showConfirm(); return; }
    panel.hidden = false;
    progress.hidden = true;
    actions.hidden = false;
    status.style.color = '#444';
    status.textContent = 'Обновление работает только на локальном сервере.\nЗапустите в терминале: python serve.py\nи откройте http://localhost:8000';
    status.hidden = false;
  });
  ok.addEventListener('click', startUpdate);
  cancel.addEventListener('click', hideModal);
  document.getElementById('up-close').addEventListener('click', hidePanel);
})();
'''
    open(os.path.join(JS_DIR, 'toolbar.js'), 'w', encoding='utf-8').write(js)

def copy_favicon():
    for name in ('favicon.ico', 'favicon.png'):
        src = os.path.join(ROOT, 'assets', name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(SITE, name))

def main():
    progress(30, 'Страница событий…')
    build_index()
    progress(55, 'Страницы событий…')
    build_event_pages()
    progress(75, 'Календарь…')
    build_calendar()
    build_calendar_js()
    build_toolbar_js()
    with open(os.path.join(CSS_DIR, 'style.css'), 'w', encoding='utf-8') as f:
        f.write(CSS)
    copy_favicon()
    progress(100, 'Сайт собран.')
    print('Done. Pages:', len(evs) + 3)

if __name__ == '__main__':
    main()