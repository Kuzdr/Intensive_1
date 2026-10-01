# -*- coding: utf-8 -*-
r"""Сверка события с «Элементами»: сначала по дате.

Пользователь 01.10.2026: список будущих событий берём со страницы
https://elementy.ru/events БЕЗ параметров — там всегда все предстоящие
события, отсортированные по дате и времени (календарь-виджет на странице
показывает текущий месяц, но сами события — все, включая ноябрь и декабрь).

Если на нужную дату нет события с похожим названием или автором —
проверка закончена, дальше смотреть нечего.

    python -X utf8 tools\check_elementy_by_date.py 12.11.2026 "Рентгеновские методы" "Корнейчик"
    python -X utf8 tools\check_elementy_by_date.py --place "Культурный центр ЗИЛ"
    python -X utf8 tools\check_elementy_by_date.py --refresh          # обновить снимок
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scrape  # noqa: E402  разбор страницы elementy.ru/events уже реализован там

CACHE = os.path.join('data', 'raw', 'elementy', 'events_list.json')


def load(refresh=False):
    """Все предстоящие события «Элементов» (снимок кэшируется)."""
    if os.path.isfile(CACHE) and not refresh:
        return json.load(io.open(CACHE, encoding='utf-8'))
    events = scrape.parse_list_page()
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(events, io.open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return events


def words(s):
    return set(w for w in re.findall(r'[А-Яа-яЁёA-Za-z]{4,}', (s or '').lower()))


def similar(a, b, share=0.5):
    wa, wb = words(a), words(b)
    if not wa or not wb:
        return False
    return len(wa & wb) / len(wa | wb) >= share


def norm_date(date_str):
    """12.11.2026 -> 12.11 ; возвращает None, если формат не понят."""
    m = re.match(r'^(\d{1,2})\.(\d{1,2})(?:\.\d{4})?$', date_str.strip())
    return '%02d.%02d' % (int(m.group(1)), int(m.group(2))) if m else None


def show(e):
    return '  id=%-7s %-5s %-34s %-46s %s' % (
        e['id'], e.get('time') or '', (e.get('lecturer') or '')[:34],
        (e.get('title') or '')[:46], e.get('place') or e.get('lectory') or '')


def check_day(events, date_str, *needles):
    """Что «Элементы» показывают в этот день; подсвечивает совпадения."""
    d = norm_date(date_str)
    day = [e for e in events if e.get('date_dot') == d]
    print('=== %s — на «Элементах» событий: %d ===' % (date_str, len(day)))
    for e in day:
        flags = ''
        for n in needles:
            if similar(n, e.get('title')):
                flags += '  <== ПОХОЖЕ НАЗВАНИЕ'
            if similar(n, e.get('lecturer')):
                flags += '  <== ПОХОЖИЙ АВТОР'
        print(show(e) + flags)
    if not day:
        print('  (на эту дату событий нет — дубля нет, дальше можно не проверять)')
    return day


def check_place(events, place):
    """Все предстоящие события площадки/лектория — чтобы собрать всё у одной конторы."""
    rows = [e for e in events
            if place.lower() in ((e.get('place') or '') + ' ' + (e.get('lectory') or '')).lower()]
    rows.sort(key=lambda e: (e.get('date_dot') or '', e.get('time') or ''))
    print('=== %s — предстоящих событий: %d ===' % (place, len(rows)))
    for e in rows:
        print(show(e) + '  [%s]' % (e.get('lectory') or '-'))
    return rows


def check_words(events, *needles):
    """Поиск по названию/автору во всём списке будущих."""
    for n in needles:
        hits = [e for e in events
                if n.lower() in ((e.get('title') or '') + ' ' + (e.get('lecturer') or '')).lower()]
        print('=== %s — совпадений: %d ===' % (n, len(hits)))
        for e in hits:
            print(show(e))


if __name__ == '__main__':
    argv = sys.argv[1:]
    refresh = '--refresh' in argv
    argv = [a for a in argv if a != '--refresh']
    ev = load(refresh)
    if argv and argv[0] == '--place':
        check_place(ev, argv[1])
    elif argv and argv[0] == '--find':
        check_words(ev, *argv[1:])
    elif argv and norm_date(argv[0]):
        check_day(ev, *argv)
    else:
        print('Всего предстоящих на «Элементах»: %d' % len(ev))
        print('Использование:')
        print('  <дата> [название] [автор]   — что «Элементы» показывают в этот день')
        print('  --place "Площадка"           — все будущие события площадки')
        print('  --find Слово                 — поиск по названию/автору')
