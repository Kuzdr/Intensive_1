# -*- coding: utf-8 -*-
"""Цена события Политехнического музея из API билетов tickets.polymus.ru.

hash берётся из ссылки регистрации события: tickets.polymus.ru/event/<HEX>.
Отправляем POST /api/no-scheme с телом {"hash": "<HEX>"} и печатаем дату,
название, цены и категории. Все цены «0» = участие бесплатное.

Использование:

    python -X utf8 tools\\polymus_price.py <HEX>
    python -X utf8 tools\\polymus_price.py https://tickets.polymus.ru/event/<HEX>

Код возврата: 0 — ответ получен, 1 — ошибка.
"""
import json
import sys
import urllib.request

URL = 'https://tickets.polymus.ru/api/no-scheme'
HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0',
    'Referer': 'https://tickets.polymus.ru/',
}


def fetch(hash_hex):
    req = urllib.request.Request(
        URL, data=json.dumps({'hash': hash_hex}).encode('utf-8'),
        headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    arg = argv[1]
    hash_hex = arg.rstrip('/').rsplit('/', 1)[-1]
    try:
        data = fetch(hash_hex)
    except Exception as e:
        print('ОШИБКА запроса к %s: %s' % (URL, e))
        return 1

    resp = data.get('response') or {}
    action = resp.get('action') or {}
    print('Название:', action.get('action_ru'))
    prices = resp.get('price') or []
    for p in prices:
        print('  %s %s: price=%s, сервис=%s' % (
            p.get('action_day'), p.get('category_ru'),
            p.get('price'), p.get('priceservise')))
    free = prices and all(str(p.get('price')) == '0' for p in prices)
    print('ИТОГ:', 'бесплатно (все категории price=0)' if free
          else 'ЕСТЬ ПЛАТНЫЕ КАТЕГОРИИ — проверить вручную')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
