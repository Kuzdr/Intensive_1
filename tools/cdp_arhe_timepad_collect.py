# -*- coding: utf-8 -*-
r"""Сбор будущих событий двух лент Timepad центра «Архэ» через Edge/CDP.

    python -X utf8 tools\cdp_arhe_timepad_collect.py

Ленты: arhe-events (Москва/общая) и tsentr-arhe-v-sankt-peter (СПб).
Пагинация идёт до «второй границы»: прошедшие карточки в начале ленты
пропускаются, стоп — на первой прошедшей после блока будущих. Снимки DOM
сохраняются в data\raw\cdp\, результат — arhe_timepad_all_cards.json.
Механика остановки и разбора карточек заимствована из
tools\cdp_vdnh_timepad_collect.py.
"""
import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_vdnh_collect import Browser, ROOT, OUTDIR
from cdp_vdnh_timepad_collect import navigate, parse_cards, select_future_cards

FEEDS = [
    ("arhe_msk", "https://arhe-events.timepad.ru/events/"),
    ("arhe_spb", "https://tsentr-arhe-v-sankt-peter.timepad.ru/events/"),
]


def load_page(b, url, path):
    """Загрузить страницу с 2 повторами при сбое; вернуть DOM."""
    last = ""
    for attempt in range(1, 4):
        try:
            navigate(b, url)
            text = b.evaljs("document.documentElement.outerHTML")
            if len(text) > 1000:
                with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                return text
            last = "пустой DOM (%d символов)" % len(text)
        except Exception as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
        print("  повтор %d/3: %s" % (attempt, last))
        time.sleep(3)
    raise RuntimeError("не удалось прочитать %s: %s" % (url, last))


def main():
    all_cards = {}
    b = Browser(FEEDS[0][1], needle="timepad.ru", wait=12)
    try:
        for tag, url in FEEDS:
            cards = []
            known_ids = set()
            seen_future = False
            for page in range(1, 7):
                u = url if page == 1 else url + "?page=%d" % page
                path = os.path.join(OUTDIR, "arhe_tp_%s_p%d.html" % (tag, page))
                text = load_page(b, u, path)
                found = parse_cards(text)
                print("%s p%d: %d карточек" % (tag, page, len(found)))
                if not found:
                    print("  стоп: страница пуста")
                    break
                page_future, seen_future, stop = select_future_cards(
                    found, seen_future, print)
                for c in page_future:
                    if c["id"] not in known_ids:
                        cards.append(c)
                        known_ids.add(c["id"])
                if stop:
                    break
                if not page_future and not seen_future:
                    print("  стоп: будущих в ленте нет")
                    break
            all_cards[tag] = {"url": url, "count": len(cards), "cards": cards}
            print("ИТОГО %s: %d будущих событий" % (tag, len(cards)))
    finally:
        b.close()
    out = os.path.join(OUTDIR, "arhe_timepad_all_cards.json")
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)
    print("Файл:", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
