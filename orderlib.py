# -*- coding: utf-8 -*-
"""Порядок событий на сайте = порядок на «Элементах».

На «Элементах» список упорядочен по дате и времени начала. Когда дата и время
совпадают, решает скрытое поле «привязка» (у нас это формальное поле 1
прототипа, см. protolib.FIELD_ORDER). Само значение привязки одинаково у
событий одной даты-времени, поэтому порядок внутри такой группы на «Элементах»
задан тем, в каком порядке события стоят в афише.

Раньше это было неявно: порядок зависел от стабильности сортировки Python и от
того, в каком порядке скрипт сложил события в файл. Теперь порядок хранится
явно полем `ord` — это номер события ВНУТРИ своей группы (одна дата + одно
время), 1, 2, 3… в том порядке, в каком события идут в афише «Элементов».

Ключ сортировки на сайте: (дата, время, ord). Он полный — порядок однозначен
и не «плавает» между запусками.
"""
NO_TIME = '99:99'


def slot_of(ev):
    """Ключ группы: дата + время начала (как на «Элементах»)."""
    return (ev.get('date_iso') or '9999-99-99', ev.get('time_start') or NO_TIME)


def ord_key(ev):
    """Ключ сортировки события «Элементов»: дата, время, затем поле ord."""
    d, t = slot_of(ev)
    return (d, t, ord_of(ev), id_key(ev))


def proto_key(ev):
    """Ключ сортировки прототипа.

    Прототип на «Элементах» ещё не опубликован, поэтому его настоящее место в
    группе неизвестно. Детерминированное правило: события «Элементов» раньше
    прототипов, прототипы между собой — по алфавиту ID папки.
    """
    d, t = slot_of(ev)
    if ev.get('kind') == 'el':
        return (d, t, 0, ord_of(ev), id_key(ev))
    return (d, t, 1, 0, str(ev.get('id') or ''))


def id_key(ev):
    """Числовой ID «Элементов» как число (для одинаковых ord) либо 0."""
    s = str(ev.get('id') or '')
    return int(s) if s.isdigit() else 0


def ord_of(ev):
    """Значение поля ord; для старых записей без него — хвост сортировки."""
    v = ev.get('ord')
    return v if isinstance(v, int) else 10 ** 6


def assign_order(events):
    """Проставить ord по порядку афиши и вернуть события в порядке сайта.

    Порядок внутри группы берётся из поля `pos` — позиции карточки в афише
    «Элементов» (её проставляет scrape.parse_list_page). События без `pos`
    (например, когда список не перечитывали) сохраняют прежний ord, а при его
    отсутствии идут в хвост группы по числовому ID.
    """
    groups = {}
    for ev in events:
        groups.setdefault(slot_of(ev), []).append(ev)
    for slot, group in groups.items():
        group.sort(key=lambda e: (e['pos'] if isinstance(e.get('pos'), int)
                                  else 10 ** 6, id_key(e)))
        for i, ev in enumerate(group, 1):
            ev['ord'] = i
    events.sort(key=ord_key)
    return events


def check_order(events):
    """Проверить, что порядок в файле держится ключом (дата, время, ord).

    Возвращает список строк с проблемами; пустой список — порядок в порядке.
    Проверяем и сами значения ord, и то, что файл отсортирован по ним.
    """
    problems = []
    groups = {}
    for pos, ev in enumerate(events, 1):
        groups.setdefault(slot_of(ev), []).append((pos, ev))
    for (d, t), group in sorted(groups.items()):
        ords = [ev.get('ord') for _, ev in group]
        if any(not isinstance(v, int) or v < 1 for v in ords):
            missing = [str(ev.get('id')) for _, ev in group
                       if not isinstance(ev.get('ord'), int) or ev['ord'] < 1]
            problems.append('%s %s: нет поля ord у событий %s'
                            % (d, t, ', '.join(missing)))
            continue
        if sorted(ords) != list(range(1, len(group) + 1)):
            problems.append('%s %s: ord должен быть 1..%d, а получилось %s'
                            % (d, t, len(group),
                               ', '.join('%s=%d' % (ev.get('id'), ev['ord'])
                                         for _, ev in group)))
        got = [ev['ord'] for _, ev in group]
        if got != sorted(got):
            problems.append('%s %s: файл не отсортирован по ord (идут %s)'
                            % (d, t, ', '.join(str(o) for o in got)))
    # порядок групп должен идти по дате, затем по времени
    keys = [slot_of(ev) for ev in events]
    if keys != sorted(keys):
        problems.append('файл не отсортирован по дате и времени')
    return problems


def diff_order(old, fresh_by_id, new_order):
    """События, у которых «Элементы» поменяли место внутри группы.

    old — прежние события (как в data/events.json), fresh_by_id — новые по id,
    new_order — id -> ord, посчитанный по афише.
    """
    changed = []
    for oid, o in old.items():
        was = o.get('ord')
        now = new_order.get(oid)
        if now is None or not isinstance(was, int):
            continue
        if was != now:
            changed.append({
                'id': oid,
                'title': o.get('title'),
                'date': o.get('date_iso'),
                'time': o.get('time_start'),
                'was': was,
                'now': now,
            })
    return changed


def slot_name(ev):
    """Человекочитаемое имя группы для сообщений."""
    d, t = slot_of(ev)
    return '%s, %s' % (d, t if t != NO_TIME else 'время не указано')
