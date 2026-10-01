# -*- coding: utf-8 -*-
"""Проверка ДК ЗИЛ по датам: сравнение с «Элементами» начинаем с даты.

Пользователь 01.10.2026: сначала смотрим афишу «Элементов» за нужную дату.
Если на эту дату нет события с похожим автором и названием — всё, проверка
закончена, больше смотреть нечего.
"""
import datetime
import io
import os
import re
import sys

import requests

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
MSK = datetime.timezone(datetime.timedelta(hours=3))
CACHE = 'data/raw/elementy'


def fetch(url, cache_name=None):
    if cache_name:
        os.makedirs(CACHE, exist_ok=True)
        path = os.path.join(CACHE, cache_name)
        if os.path.isfile(path):
            return io.open(path, encoding='utf-8', errors='replace').read()
    h = requests.get(url, timeout=40, headers={'User-Agent': UA}).text
    if cache_name:
        io.open(path, 'w', encoding='utf-8', newline='\n').write(h)
    return h


def day_url(d):
    ts = int(datetime.datetime(d.year, d.month, d.day, tzinfo=MSK).timestamp())
    return 'https://elementy.ru/events?archive=2&evdate=%d&period=d' % ts


def month_url(d):
    ts = int(datetime.datetime(d.year, d.month, 1, tzinfo=MSK).timestamp())
    return 'https://elementy.ru/events?archive=2&evdate=%d&period=m' % ts


def strip(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = s.replace('&nbsp;', ' ').replace('&laquo;', '«').replace('&raquo;', '»')
    s = re.sub(r'&#\d+;|&[a-z]+;', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def events_on(url, cache_name):
    """Карточки афиши: id, авторы, название, лекторий, площадка, время."""
    h = fetch(url, cache_name)
    out = []
    for m in re.finditer(r'<div class="past">(.*?)<div class=.cl.></div>', h, re.S):
        seg = m.group(1)
        link = re.search(r'href="/events/(\d+)/', seg)
        if not link:
            continue
        title = re.search(r'<div class=.title.>(.*?)</div>', seg, re.S)
        who = re.search(r"<div class='pretitle'>(.*?)</div>", seg, re.S)
        lectory = re.search(r"<div class='sublink2'>(.*?)</div>", seg, re.S)
        place = re.findall(r"<div class='sublink'>(.*?)</div>", seg, re.S)
        tm = re.findall(r"<div class='htimes subhead'>(.*?)</div>", seg, re.S)
        out.append({
            'id': link.group(1),
            'title': strip(title.group(1)) if title else '',
            'authors': strip(who.group(1)) if who else '',
            'lectory': strip(lectory.group(1)) if lectory else '',
            'place': strip(place[-1]) if place else '',
            'weekday': strip(tm[0]) if len(tm) > 0 else '',
            'time': strip(tm[1]) if len(tm) > 1 else '',
        })
    return out


def words(s):
    return set(w for w in re.findall(r'[А-Яа-яЁёA-Za-z]{4,}', s.lower()))


def similar(a, b, share=0.5):
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= share


def check(date_str, title, authors=(), share=0.5):
    """Основная проверка: что «Элементы» показывают в этот день."""
    d = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
    url = day_url(d)
    evs = events_on(url, 'day_%s.html' % d.strftime('%Y%m%d'))
    print('=== %s — на «Элементах» событий: %d ===' % (date_str, len(evs)))
    for e in evs:
        flag = ''
        if similar(title, e['title'], share):
            flag = '  <-- ПОХОЖЕ НА НАЗВАНИЕ'
        if any(similar(a, e['authors'], share) for a in authors):
            flag += '  <-- ПОХОЖИЙ АВТОР'
        print('  id=%-7s %-46s %s%s' % (e['id'], e['title'][:46], e['authors'][:34], flag))
    if not evs:
        print('  (пусто — на эту дату событий нет; дальше можно не проверять)')
    return evs


def check_month(month_str):
    d = datetime.datetime.strptime(month_str, '%m.%Y').date()
    url = month_url(d)
    evs = events_on(url, 'month_%s.html' % d.strftime('%Y%m'))
    print('=== %s — на «Элементах» событий: %d ===' % (month_str, len(evs)))
    return evs


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'day':
        check(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif cmd == 'month':
        for e in check_month(sys.argv[2]):
            print('  id=%-7s %s' % (e['id'], e['title'][:70]))
