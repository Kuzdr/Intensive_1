# -*- coding: utf-8 -*-
"""Адаптер «Элементов» (Поиск/авторы) — обёртка над tools/author_elementy.py.

Даёт генераторам прототипов единый способ проверить автора на elementy.ru:
    a = elementy.find_author("Михаил Магид")
    if a: {"found": True, "name", "full_name", "block_html", "photo", "event_url"}
    else: {"found": False, "query": ...}

Кэш HTML: data/raw/elementy/<id>.html (в .gitignore). Вид руки — библиотека
author_elementy.fetch (requests). Если нужна живая сеть, а запрос упал — надо
сообщить пользователю и записать в reference/availability_log.md (AGENTS.md).
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import author_elementy  # noqa: E402

ROOT = author_elementy.ROOT


def cached_result(path, data):
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def search(name, refresh=False, cache_path=None):
    """Ищет автора: находит его событие и блок «about authors».

    Возвращает {"found": bool, ...}. Для on_elementy в конфиге прототипа
    достаточно found; полные поля авторских анкет собирает способ
    `known_cfg(name, full_name, block_html, photo)`.
    """
    try:
        a = author_elementy.find_author(name, refresh=refresh)
    except Exception as e:
        a = None
        note = {"found": False, "query": name, "error": repr(e)}
        return cached_result(cache_path, note)
    if not a:
        return cached_result(cache_path, {"found": False, "query": name})
    out = {
        "found": True,
        "query": name,
        "name": author_elementy.clean(a["pretitle"]).replace("&nbsp;", "\u00a0") or name,
        "full_name": author_elementy.clean(a["pretitle"]).replace("&nbsp;", "\u00a0"),
        "block_html": a["block_html"],
        "photo": a["photo"],
        "event_id": a["event_id"],
        "event_url": a["event_url"],
    }
    return cached_result(cache_path, out)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    refresh = "--refresh" in sys.argv
    for n in args:
        r = search(n, refresh=refresh)
        print(json.dumps(r, ensure_ascii=False, indent=1))