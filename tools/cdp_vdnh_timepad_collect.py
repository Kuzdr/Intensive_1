# -*- coding: utf-8 -*-
r"""Сбор афиш.Timepad всех источников ВДНХ через Edge/CDP.

Каждая лента открывается в Edge и листается через ?page=N, но только до
ПЕРВОГО прошедшего события: дальше в ленте идут старые даты, и собирать их
не нужно. Снимки DOM и карточки сохраняются в data\raw\cdp\.

    python -X utf8 tools\cdp_vdnh_timepad_collect.py
"""
import html as H
import io
import json
import os
import re
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_vdnh_collect import Browser, ROOT, OUTDIR

FEEDS = [
    ("lektorij", "https://lektorij-vdnh.timepad.ru/events/"),
    ("cosmos", "https://cosmos-vdnh.timepad.ru/events/"),
    ("slovo", "https://slovo-vdnh.timepad.ru/events/"),
    ("atom", "https://atom-lab.timepad.ru/events/"),
    ("biotech", "https://muzey-biotekh.timepad.ru/events/"),
]
CARD_RE = re.compile(r'<div class="t-card t-card_event[^"]*"')
MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11,
    "декабря": 12,
}
TODAY = date.today()


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", H.unescape(s)).strip()


def is_past(date_text):
    """Прошедшее событие: метка «назад» в ленте либо дата раньше сегодня."""
    low = date_text.lower()
    if "назад" in low:
        return True
    m = re.search(r'\b(\d{1,2})\s+([а-яё]+)', low)
    if not m:
        return False
    month = MONTHS.get(m.group(2))
    if not month:
        return False
    day = int(m.group(1))
    year = TODAY.year
    if (month, day) < (TODAY.month, TODAY.day):
        year += 1
    return date(year, month, day) < TODAY


def parse_cards(t):
    chunks = CARD_RE.split(t)[1:]
    cards = []
    for ch in chunks:
        m = re.search(r'<a href="(https?://[\w.-]*timepad\.ru/event/(\d+)/[^"]*)"[^>]*>\s*(.*?)\s*</a>',
                      ch, re.S)
        if not m:
            continue
        info = re.search(r'<p class="t-card_event__info">(.*?)</p>', ch, re.S)
        desc = re.search(r'<p class="t-description">(.*?)</p>', ch, re.S)
        date_text = clean(info.group(1)) if info else ""
        cards.append({
            "id": int(m.group(2)),
            "url": m.group(1),
            "title": clean(m.group(3)),
            "date": date_text,
            "past": is_past(date_text),
            "desc": (clean(desc.group(1))[:500] if desc else ""),
        })
    return cards


def navigate(b, url):
    b.n += 1
    mid = b.n
    b.ws.send(json.dumps({"id": mid, "method": "Page.navigate",
                          "params": {"url": url}}))
    while True:
        msg = json.loads(b.ws.recv())
        if msg.get("id") == mid:
            break
    last = ""
    for _ in range(25):
        try:
            cur = b.evaljs("location.href")
            state = b.evaljs("document.readyState")
            body = b.evaljs("document.body.innerText")
            if cur == url and state == "complete" and len(body) > 400:
                time.sleep(2)
                return
            last = (cur, state, len(body))
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("страница не загрузилась: %s, последнее %s" % (url, last))


def main():
    b = Browser(FEEDS[0][1], needle="timepad.ru", wait=12)
    all_cards = {}
    try:
        for tag, url in FEEDS:
            cards = []
            known_ids = set()
            stop = False
            for page in range(1, 9):
                u = url if page == 1 else url + "?page=%d" % page
                navigate(b, u)
                t = b.evaljs("document.documentElement.outerHTML")
                path = os.path.join(OUTDIR, "vdnh_tp_%s_p%d.html" % (tag, page))
                with io.open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(t)
                found = parse_cards(t)
                print("%s p%d: %d карточек, %s" % (
                    tag, page, len(found), os.path.basename(path)))
                if not found:
                    print("  стоп: страница пуста")
                    break
                # Главное правило: при первом же прошедшем событии прекращаем
                # обход ленты и не открываем следующие страницы.
                for c in found:
                    if c["past"]:
                        print("  стоп: первое прошедшее событие %s — %s" % (
                            c["id"], c["date"]))
                        stop = True
                        break
                    if c["id"] not in known_ids:
                        cards.append(c)
                        known_ids.add(c["id"])
                if stop:
                    break
            all_cards[tag] = {"url": url, "count": len(cards), "cards": cards}
            print("  ИТОГО %s: %d будущих событий" % (tag, len(cards)))
    finally:
        b.close()
    out = os.path.join(OUTDIR, "vdnh_timepad_all_cards.json")
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(all_cards, f, ensure_ascii=False, indent=2)
    print("Файл:", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
