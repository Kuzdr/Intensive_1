# -*- coding: utf-8 -*-
r"""Сбор афиш.Timepad всех источников ВДНХ через Edge/CDP.

Каждая лента открывается в Edge и листается через ?page=N. Прошедшие карточки
в НАЧАЛЕ ленты (бывает у КЦ ЗИЛ) пропускаются: они не граница обхода.
Останавливаемся на первом прошедшем событии ПОСЛЕ блока будущих («вторая
граница») — дальше в ленте идут старые даты. Снимки DOM и карточки
сохраняются в data\raw\cdp\. Функции is_past()/parse_cards()/
select_future_cards() пригодны для любой Timepad-афиши, не только ВДНХ.

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
PAST_WORDS = ("назад", "вчера", "позавчера")
FUTURE_WORDS = ("через ", "сегодня", "завтра", "послезавтра")


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", H.unescape(s)).strip()


def is_past(date_text):
    """Прошедшее событие по метке в ленте либо по дате раньше сегодняшней.

    Timepad показывает относительные метки: «через 3 дня», «сегодня»,
    «завтра» — будущее; «10 часов назад», «вчера», «позавчера» — прошедшее.
    Метки важнее календарной даты: «24 ноября … позавчера» — прошедшее,
    даже если до конца месяца ещё есть дни.
    """
    low = date_text.lower()
    if any(word in low for word in PAST_WORDS):
        return True
    if any(word in low for word in FUTURE_WORDS):
        return False
    m = re.search(r'\b(\d{1,2})\s+([а-яё]+)(?:\s+(\d{4}))?', low)
    if not m:
        return False
    month = MONTHS.get(m.group(2))
    if not month:
        return False
    day = int(m.group(1))
    if m.group(3):
        return date(int(m.group(3)), month, day) < TODAY
    # Год в ленте не указан: день/месяц раньше сегодняшнего — уже прошло.
    return (month, day) < (TODAY.month, TODAY.day)


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


def select_future_cards(found, seen_future=False, log=None):
    """Выбрать будущие карточки до «второй границы» ленты.

    Прошедшие карточки в начале ленты пропускаются (у КЦ ЗИЛ 26.11.2026
    первых пять карточек прошедшие, затем 15 будущих). Останавливаемся
    на ПЕРВОМ прошедшем событии после того, как встретилось будущее, —
    на этой «второй границе» начинается архив.
    """
    future = []
    stop = False
    say = log or (lambda message: None)
    for card in found:
        if card["past"]:
            if seen_future:
                say("  стоп: прошедшее событие после блока будущих %s — %s"
                    % (card["id"], card["date"]))
                stop = True
                break
            say("  пропущено прошедшее в начале ленты: %s — %s"
                % (card["id"], card["date"]))
            continue
        seen_future = True
        future.append(card)
    return future, seen_future, stop


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
            seen_future = False
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
                # Прошедшие в начале — не граница; стоп только после блока
                # будущих. Следующую страницу открываем, если границы нет.
                page_future, seen_future, stop = select_future_cards(
                    found, seen_future, print)
                for c in page_future:
                    if c["id"] not in known_ids:
                        cards.append(c)
                        known_ids.add(c["id"])
                if stop:
                    break
                if not page_future and not seen_future:
                    print("  стоп: на странице только прошедшие, будущих в ленте нет")
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
