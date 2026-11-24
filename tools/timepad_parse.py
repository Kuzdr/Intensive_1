# -*- coding: utf-8 -*-
r"""Разбор сохранённой страницы Timepad (DOM из tools\cdp_read.py).

Повторяющиеся события Timepad часто открываются на «старой» дате: в тексте
анонса может стоять дата первой лекции, а актуальная — в массиве
`recurring_events` модели `evModel`. Скрипт печатает и то и другое, чтобы
дату/цену можно было сверить с афишей и телеграм-каналом организатора.

    python -X utf8 tools\cdp_read.py tp4257910 https://fondnauk.timepad.ru/event/4257910/
    python -X utf8 tools\timepad_parse.py data\raw\cdp\tp4257910.html

Вывод: заголовок, город, площадка, возраст, даты всех повторов с ценами,
видимый текст анонса.
"""
import argparse
import html as H
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ev_model(t):
    m = re.search(
        r'<script type="application/twfdata" id="evModel">\s*'
        r'\(function\(\)\s*\{\s*return\s*(\{.*?\})\s*;\s*\}\)\(\);\s*</script>',
        t, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def visible_text(t):
    s = re.sub(r"<script[\s\S]*?</script>", " ", t)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s)
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|div|li|h[1-6]|tr|section)>", "\n", s)
    s = H.unescape(re.sub(r"<[^>]+>", " ", s))
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip()
                     for line in s.splitlines() if line.strip())


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dom", help="путь к сохранённому DOM-файлу")
    ap.add_argument("--full", action="store_true", help="печатать полный текст анонса")
    a = ap.parse_args()
    path = a.dom if os.path.isabs(a.dom) else os.path.join(ROOT, a.dom)
    t = io.open(path, encoding="utf-8", errors="replace").read()

    m = re.search(r"<title>(.*?)</title>", t, re.S)
    if m:
        print("TITLE:", H.unescape(m.group(1).strip()))
    d = ev_model(t)
    if not d:
        print("Модель evModel не найдена — страница, возможно, с капчей")
    else:
        for k in ("id", "name", "organization_name", "city", "place",
                  "date_human", "age", "reg_open"):
            if k in d:
                print("%s: %s" % (k.upper(), json.dumps(d[k], ensure_ascii=False)))
        print("ПОВТОРЫ:")
        import datetime
        for e in d.get("recurring_events") or []:
            end = e.get("timestamp_end")
            end_txt = (datetime.datetime.fromtimestamp(end).strftime("%H:%M")
                       if isinstance(end, (int, float)) else "?")
            print("  id=%s  %s  %s–%s  цена=%s  недоступно=%s" % (
                e.get("id"), e.get("date"), e.get("time"),
                end_txt, e.get("min_price"), e.get("unavaliable")))
            print("    iso=%s" % e.get("date_iso8601"))
    txt = visible_text(t)
    if a.full:
        print("\nТЕКСТ:\n" + txt)
    else:
        print("\nТЕКСТ (первые 2000 символов):\n" + txt[:2000])


if __name__ == "__main__":
    main()
