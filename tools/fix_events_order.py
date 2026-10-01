# -*- coding: utf-8 -*-
r"""Починить порядок событий в data/events.json (разовая миграция на поле ord).

Порядок событий внутри одной даты-времени на сайте должен совпадать с
порядком на «Элементах». Раньше он держался только на стабильности сортировки
и нигде не записывался. Скрипт проставляет каждому событию поле ord — номер
внутри своей группы (1, 2, 3…) — в том порядке, в каком события уже стоят
в файле, и пересортировывает файл по ключу (дата, время, ord).

Порядок в файле получен с афиши «Элементов» при прошлой загрузке, поэтому
скрипт ничего не меняет на сайте: он лишь делает этот порядок явным.
Поле pos (сырая позиция в афише) в файл не пишется — оно нужно только
на время сбора, иначе новое событие сдвигало бы чужие номера и в отчёте
появлялись бы ложные «изменения».

    python -X utf8 tools\fix_events_order.py [--dry]

После правки запустите проверку:

    python -X utf8 tools\check_events_order.py
"""
import io
import json
import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import orderlib as ORD  # noqa: E402

DATA = os.path.join(ROOT, 'data', 'events.json')


def main():
    dry = '--dry' in sys.argv[1:]
    events = json.load(io.open(DATA, encoding='utf-8'))
    before = [(e.get('id'), e.get('ord')) for e in events]
    # порядок берём из текущего файла: pos не записываем, он протухает
    ORD.assign_order(events)
    after = [(e.get('id'), e.get('ord')) for e in events]
    added = sum(1 for oid, o in before if o is None)
    same_order = [b[0] for b in before] == [a[0] for a in after]
    print('Событий: %d, поле ord проставлено: %d' % (len(events), added))
    print('Порядок в файле после сортировки: %s'
          % ('тот же' if same_order else 'ИЗМЕНИЛСЯ — посмотрите diff'))
    problems = ORD.check_order(events)
    if problems:
        print('ОШИБОК: %d' % len(problems))
        for p in problems:
            print('  ' + p)
        return 1
    if dry:
        print('\nЭто был --dry, файл не тронут.')
        return 0
    # переводы строк — как у scrape.py (CRLF в Windows), иначе весь файл
    # развернётся в diff
    with io.open(DATA, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=1)
    print('\nИТОГ: порядок сохранён и записан в поле ord.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
