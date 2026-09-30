# -*- coding: utf-8 -*-
"""Читатель события Политехнического музея (polymus.ru).

Вытаскивает из страницы события (https://polymus.ru/events/detail/<slug>)
формальные данные события, название, даты, возраст, флаг «онлайн» и
полный HTML-текст описания (detail_text) вместе со ссылками регистрации
tickets.polymus.ru.

Данные на странице лежат в JSON-блоке `id="__NUXT_DATA__"` (сериализация
devalue: значения ссылаются на элементы массива по индексу). Скрипт
разрешает ссылки и превращает блок в обычный Python-объект, из которого
берёт `data.event-item.item`.

Использование:

    python -X utf8 tools\\scrape_polymus.py https://polymus.ru/events/detail/<slug>
    python -X utf8 tools\\scrape_polymus.py <slug>            -- короткая форма
    python -X utf8 tools\\scrape_polymus.py <url> --file page.html -- не качать

Код возврата: 0 — событие извлечено, 1 — ошибка.
"""
import argparse
import json
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"
NEXT_RE = re.compile(r'<script[^>]*id="__NUXT_DATA__"[^>]*>(.*?)</script>', re.S)
TICKET_RE = re.compile(r"https?://tickets\.polymus\.ru/event/[0-9A-F]{10,}")
WRAPPERS = ("ShallowReactive", "Reactive", "Selection")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_payload(html: str):
    """Возвращает сырой массив `__NUXT_DATA__` или бросает ValueError."""
    m = NEXT_RE.search(html)
    if not m:
        raise ValueError("на странице не найден JSON-блок __NUXT_DATA__")
    return json.loads(m.group(1).strip())


class NuxtData:
    """Разрешение ссылок devalue: число в позиции значения = индекс в массиве."""

    def __init__(self, arr):
        self.arr = arr
        self._memo = {}

    def node(self, i):
        v = self.arr[i]
        if isinstance(v, int) and 0 <= v < len(self.arr):
            v = self.arr[v]
        if isinstance(v, (list, dict)):
            key, r = self._memo.get(i, (None, None))
            if r is None:
                r = self._resolve(v)
                self._memo[i] = (True, r)
            return r
        return v

    def _resolve(self, v):
        if isinstance(v, list):
            if len(v) == 2 and v[0] == "Reactive" and isinstance(v[1], int):
                return self.node(v[1])
            if v and v[0] in WRAPPERS and len(v) == 2 and isinstance(v[1], int):
                return v[1] if v[0] == "Selection" else self.node(v[1])
            return [self.val(x) for x in v]
        if isinstance(v, dict):
            return {k: self.val(x) for k, x in v.items()}
        return v

    def val(self, x):
        if isinstance(x, int) and 0 <= x < len(self.arr):
            n = self._resolve(self.arr[x])
            self._memo[x] = (True, n)
            return n
        if isinstance(x, (list, dict)):
            return self._resolve(x)
        return x


def find_event(root) -> dict:
    """Возвращает объект `data.event-item.item` из разрешённого дерева."""
    try:
        item = root["data"]["event-item"]["item"]
    except (KeyError, TypeError):
        raise ValueError("в данных нет блока event-item.item (не страница события?)")
    if not isinstance(item, dict) or not item.get("name"):
        raise ValueError("пустой объект события на странице")
    return item


def get_place(item: dict) -> dict:
    place = item.get("related", {}).get("place", [])
    return place[0].get("properties", {}) if place else {}


def dump(msg: str):
    sys.stdout.write(msg + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url", help="URL события вида /events/detail/<slug> или просто <slug>")
    ap.add_argument("--file", metavar="HTML", help="разбирать локально сохранённый HTML, не качать")
    args = ap.parse_args(argv)

    url = args.url
    if not url.startswith("http"):
        url = "https://polymus.ru/events/detail/" + url.lstrip("/")

    try:
        html = open(args.file, encoding="utf-8", errors="replace").read() if args.file else fetch(url)
        nd = NuxtData(load_payload(html))
        item = find_event(nd.node(0))
    except Exception as exc:  # сеть, парсинг, отсутствие события
        sys.stderr.write("Ошибка: %s\n" % exc)
        return 1

    p = item.get("properties", {})
    place = get_place(item)
    dump("СОБЫТИЕ ПОЛИТЕХНИЧЕСКОГО МУЗЕЯ")
    dump("ID: %s" % item.get("id"))
    dump("Название: %s" % item.get("name"))
    dump("Код (slug): %s" % item.get("code"))
    dump("Тип: %s" % p.get("type"))
    dump("Дата начала: %s" % p.get("date_start"))
    dump("Дата конца: %s" % p.get("date_end"))
    dump("Возраст: %s" % p.get("age_limit"))
    dump("Онлайн: %s" % p.get("online"))
    dump("Статус: %s" % p.get("status"))
    dump("Площадка: %s" % place.get("address"))
    dump("Раздел: %s" % item.get("section"))
    dump("Аннотация (seo-описание):")
    dump((item.get("seo", {}).get("section_meta_description") or "").strip())
    dt = item.get("detail_text") or ""
    dump("ТЕКСТ ОПИСАНИЯ (HTML), %d знаков:" % len(dt))
    dump(dt.strip())
    dump("ССЫЛКИ РЕГИСТРАЦИИ tickets.polymus.ru:")
    links = sorted(set(TICKET_RE.findall(dt)))
    for l in links:
        dump(l)
    if not links:
        dump("(не найдено)")
    return 0


if __name__ == "__main__":
    sys.exit(main())