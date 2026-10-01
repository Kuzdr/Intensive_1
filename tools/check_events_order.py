# -*- coding: utf-8 -*-
r"""Проверка порядка событий в data/events.json.

Порядок на сайте должен совпадать с порядком на «Элементах»: дата, время
начала, затем поле ord (номер события внутри своей пары дата+время).
Скрипт проверяет, что поле ord у всех событий есть, в каждой группе идёт
1..N без пропусков и что файл отсортирован по этому ключу.

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
    events = json.load(io.open(DATA, encoding='utf-8'))
    problems = ORD.check_order(events)
    groups = {}
    for ev in events:
        groups.setdefault(ORD.slot_of(ev), []).append(ev)
    same = {k: v for k, v in groups.items() if len(v) > 1}
    print('Событий: %d, групп (дата+время): %d, групп с совпадением: %d'
          % (len(events), len(groups), len(same)))
    for slot, group in sorted(same.items()):
        print('  %s %s: %s' % (slot[0], slot[1], ', '.join(
            '%s) %s' % (ev.get('ord') or '-', ev.get('id')) for ev in group)))
    if problems:
        print('\nОШИБОК: %d' % len(problems))
        for p in problems:
            print('  ' + p)
        return 1
    print('\nИТОГ: порядок верный — дата, время, поле ord; расхождений нет.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
