# -*- coding: utf-8 -*-
"""Сборщик афиши лектория «Прямая речь» (переиспользуемый).

В отличие от `_tmp_scripts/collect_pryamaya.py`, не привязан к одному
сохранённому HTML-файлу: сам обходит все страницы афиши `/?page=N`
до пустой/повторяющейся и возвращает список событий.

Использование:
    python -X utf8 tools\\collect_pryamaya.py
    python -X utf8 tools\\collect_pryamaya.py --page 3
    python -X utf8 tools\\collect_pryamaya.py --json out.json
    python -X utf8 tools\\collect_pryamaya.py --file saved.html

Ключ события — `PR-<lecture_id>`, где lecture_id берётся из пути картинки
`/img/lectures/<id>/`. Он не меняется, если организатор переименовал лекцию
(так, у Шустова в адресе осталось «Как взломать культурный код Японии»,
а заголовок на странице уже «Культурный код Японии»).
"""
import argparse
import datetime
import html as html_mod
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://www.pryamaya.ru/"
AFISHA = BASE + "?page=%d"
UA = "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"

MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5,
    "июня": 6, "июля": 7, "августа": 8, "сентября": 9, "октября": 10,
    "ноября": 11, "декабря": 12,
}

CARD_RE = re.compile(
    r'<a[^>]*class="grid-card"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.S)
TITLE_RE = re.compile(r'grid-card__title[^>]*>\s*(.*?)\s*</div>', re.S)
SUBTITLE_RE = re.compile(r'grid-card__subtitle[^>]*>\s*(.*?)\s*</div>', re.S)
FOOTER_RE = re.compile(r'grid_card__footer-item[^>]*>\s*(.*?)\s*</div>', re.S)
AUTHOR_RE = re.compile(r'person-badge__name[^>]*>\s*(.*?)\s*</div>', re.S)
AGE_RE = re.compile(r'age-warn-badge[^>]*>\s*(.*?)\s*</div>', re.S)
BADGE_RE = re.compile(r'grid-card__badge[^>]*>\s*(.*?)\s*</div>', re.S)
LECTURE_ID_RE = re.compile(r'lectures(?:%2F|/)(\d+)', re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(fragment: str) -> str:
    if not fragment:
        return ""
    return html_mod.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def parse_date(text: str) -> str:
    """Приблизительная ISO-дата из подписи карточки ('пн 14 декабря, 19:30').

    Год определяем по текущему: если месяц уже прошёл — следующий год.
    Для диапазонов ('4–8 января') берём первое число, для нескольких дат
    ('26 ноября и 21 декабря') — первую.
    """
    m = re.search(r"(\d{1,2})\s+([а-яё]+)", text, re.I)
    if not m:
        return ""
    day = int(m.group(1))
    month = MONTHS.get(m.group(2).lower())
    if not month or not 1 <= day <= 31:
        return ""
    today = datetime.date.today()
    year = today.year + (1 if month < today.month else 0)
    try:
        return datetime.date(year, month, day).isoformat()
    except ValueError:
        return ""


def parse_time(text: str) -> str:
    m = re.search(r"\b(\d{1,2}:\d{2})\b", text)
    return m.group(1) if m else ""


def parse_page(page: str) -> list:
    """События одной страницы афиши."""
    out = []
    for m in CARD_RE.finditer(page):
        href, body = m.group(1), m.group(2)
        url = urllib.parse.urljoin(BASE, html_mod.unescape(href))
        lm = LECTURE_ID_RE.search(body)
        key = "PR-" + lm.group(1) if lm else url
        footer = [clean(x) for x in FOOTER_RE.findall(body)]
        title_m = TITLE_RE.search(body)
        sub_m = SUBTITLE_RE.search(body)
        author_m = AUTHOR_RE.search(body)
        age_m = AGE_RE.search(body)
        date_txt = footer[0] if footer else ""
        out.append({
            "key": key,
            "url": url,
            "title": clean(title_m.group(1)) if title_m else "",
            "subtitle": clean(sub_m.group(1)) if sub_m else "",
            "date_text": date_txt,
            "date": parse_date(date_txt),
            "time": parse_time(date_txt),
            "place": footer[1] if len(footer) > 1 else "",
            "author": clean(author_m.group(1)) if author_m else "",
            "age": clean(age_m.group(1)) if age_m else "",
            "labels": [clean(x) for x in BADGE_RE.findall(body)],
        })
    return out


def collect_all(max_pages: int = 50) -> list:
    """Все страницы афиши до пустой/повторяющейся страницы."""
    seen, events = set(), []
    for page_no in range(1, max_pages + 1):
        page = fetch(AFISHA % page_no)
        rows = parse_page(page)
        keys = [e["key"] for e in rows]
        if not rows or (keys and set(keys) <= seen):
            break
        for e in rows:
            if e["key"] not in seen:
                seen.add(e["key"])
                events.append(e)
    return sorted(events, key=lambda e: (e["date"], e["time"], e["key"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="Сборщик афиши «Прямой речи»")
    ap.add_argument("--page", type=int, help="только одна страница афиши")
    ap.add_argument("--file", help="готовый HTML вместо запроса к сайту")
    ap.add_argument("--json", dest="json_out", help="сохранить результат в JSON")
    args = ap.parse_args()

    if args.file:
        with io.open(args.file, encoding="utf-8") as f:
            events = parse_page(f.read())
    elif args.page:
        events = parse_page(fetch(AFISHA % args.page))
    else:
        events = collect_all()

    print("АФИША «ПРЯМОЙ РЕЧИ» — %d событий" % len(events))
    for e in events:
        print("%s %s %s | %s | %s | %s"
              % (e["date"] or "?", e["time"] or "  ", e["key"],
                 e["title"], e["author"], e["url"]))
        if e["subtitle"]:
            print("      %s" % e["subtitle"])
        if e["labels"]:
            print("      [%s]" % ", ".join(e["labels"]))

    if args.json_out:
        with io.open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=1)
        print("\nJSON: %s" % os.path.abspath(args.json_out))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
