# -*- coding: utf-8 -*-
"""Читатель событий Центра «Архэ» (arhe.msk.ru).

Календарь лектория — на движке The Events Calendar:

    https://arhe.msk.ru/?post_type=tribe_events

В HTML календаря каждое событие описано скрытым тултипом
`id="tribe-events-tooltip-content-<post_id>"`, где `<post_id>` — id записи
события (не путать с `?p=` из адресной строки: рабочий числовой URL обычно
на единицу больше, а у части событий числовой `?p=` вообще не резолвится —
тогда используется каноническая ссылка `?tribe_events=<слаг>`).

Главное: на странице каждого события подключён виджет Timepad

    <script ... data-twf2s-event--id="4232561"
            data-timepad-customized="44486" ...>

`data-twf2s-event--id` — это ID события на Timepad, и он находится, даже
если событие ещё не появилось в списке лекций Timepad. `data-timepad-
customized` задаёт аккаунт:

    13612 — arhe-events.timepad.ru            (Москва)
    44486 — tsentr-arhe-v-sankt-peter.timepad.ru (Санкт-Петербург)

Так для любого события «Архэ» получается пара источников: страница
arhe.msk.ru и страница Timepad.

Использование:

    python -X utf8 tools\\scrape_arhe.py                       -- весь календарь
    python -X utf8 tools\\scrape_arhe.py --from 2026-10-04     -- события не раньше даты
    python -X utf8 tools\\scrape_arhe.py --to 2026-10-31       -- события не позже даты
    python -X utf8 tools\\scrape_arhe.py --json out.json       -- сохранить в JSON
    python -X utf8 tools\\scrape_arhe.py <url события>         -- разобрать одну страницу
    python -X utf8 tools\\scrape_arhe.py <url> --file page.html -- разобрать локально

Код возврата: 0 — разобрано, 1 — ошибка.
"""
import argparse
import html as html_mod
import io
import json
import os
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"
CAL_URL = "https://arhe.msk.ru/?post_type=tribe_events"
EVENT_URL = "https://arhe.msk.ru/?post_type=tribe_events&p=%s"

TIMEPAD_ACCOUNTS = {
    "13612": "https://arhe-events.timepad.ru/event/%s/",
    "44486": "https://tsentr-arhe-v-sankt-peter.timepad.ru/event/%s/",
}

TOOLTIP_RE = re.compile(r'id="tribe-events-tooltip-content-(\d+)"')
TIME_RE = re.compile(r'<time datetime="([^"]+)"')
HREF_RE = re.compile(r'href="(https?://arhe\.msk\.ru/\?tribe_events=[^"]+)"')
TITLE_RE = re.compile(r'calendar-event-tooltip-title[^>]*>\s*<a[^>]*>(.*?)</a>', re.S)
SCRIPT_RE = re.compile(r'<script[^>]*data-twf2s-event--id="(\d+)"[^>]*>', re.S)
CUSTOMIZED_RE = re.compile(r'data-timepad-customized="(\d+)"')
PAGE_TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
DATE_START_RE = re.compile(r'tribe-event-date-start">(.*?)</span>', re.S)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(fragment: str) -> str:
    if not fragment:
        return ""
    t = re.sub(r"<[^>]+>", "", fragment)
    return html_mod.unescape(t).strip()


def timepad_url(event_id: str, customized: str) -> str:
    tmpl = TIMEPAD_ACCOUNTS.get(customized)
    if tmpl:
        return tmpl % event_id
    return "https://timepad.ru/event/%s/" % event_id


def parse_timepad(page: str):
    """(id события Timepad, аккаунт-customized) или (None, None)."""
    m = SCRIPT_RE.search(page)
    if not m:
        return None, None
    tag = m.group(0)
    cust = CUSTOMIZED_RE.search(tag)
    return m.group(1), (cust.group(1) if cust else None)


def parse_calendar(page: str):
    """Список событий календаря: дата, название, id тултипа, канонический URL."""
    parts = TOOLTIP_RE.split(page)
    seen, events = {}, []
    for k in range(1, len(parts) - 1, 2):
        pid = parts[k]
        seg = parts[k + 1][:5000]
        m_dt = TIME_RE.search(seg)
        m_href = HREF_RE.search(seg)
        m_title = TITLE_RE.search(seg)
        if pid in seen:
            continue
        seen[pid] = True
        events.append({
            "tip": pid,
            "date": m_dt.group(1) if m_dt else "",
            "title": clean(m_title.group(1)) if m_title else "",
            "slug_url": m_href.group(1) if m_href else "",
        })
    events.sort(key=lambda e: (e["date"], e["tip"]))
    return events


def resolve_arhe_url(tip: str, slug_url: str) -> str:
    """Числовая ссылка на страницу события или канонический слаг.

    Проверено 04.10.2026 на календаре «Архэ»:
      * `?p=<tooltip>` — 404, сам tooltip ID в чистом виде не работает;
      * `?post_type=tribe_events&p=<tooltip>` — 200 и именно страница события
        (`single-tribe_events`); это правильная числовая ссылка;
      * `?p=<tooltip+1>` — тоже 200, но отдаёт обычную запись WordPress
        (`single-post`) с тем же заголовком, то есть зеркало, не событие;
      * у части событий (`Жизнь подо льдом`, `Белка и ее орех`) `?p=<tooltip+1>`
        отдаёт 404, так что зеркало есть не всегда.

    Поэтому сначала пробуем `?post_type=tribe_events&p=<tooltip>`, затем
    зеркало `?p=<tooltip+1>`, и только потом канонический слаг.
    """
    candidates = [
        "https://arhe.msk.ru/?post_type=tribe_events&p=%s" % tip,
        "https://arhe.msk.ru/?p=%d" % (int(tip) + 1),
    ]
    mirror = None
    for url in candidates:
        try:
            page = fetch(url)
        except Exception:
            continue
        if "single-tribe_events" in page:
            return url
        if mirror is None and "single-post" in page:
            mirror = url
    return mirror or slug_url or EVENT_URL % tip


def page_when(page: str) -> str:
    m = DATE_START_RE.search(page)
    return clean(m.group(1)) if m else ""


def parse_event_page(page: str, url: str):
    """Разбор одной страницы события (для режима <url>)."""
    m_title = PAGE_TITLE_RE.search(page)
    title = clean(m_title.group(1)) if m_title else ""
    tp_id, cust = parse_timepad(page)
    tip = None
    m_pid = re.search(r"postid-(\d+)", page)
    if m_pid:
        tip = m_pid.group(1)
    return {
        "url": url,
        "title": title,
        "when": page_when(page),
        "tip": tip,
        "timepad_id": tp_id,
        "timepad_url": timepad_url(tp_id, cust) if tp_id else "",
    }


def dump(msg: str = ""):
    sys.stdout.write(msg + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url", nargs="?", help="URL одной страницы события (иначе весь календарь)")
    ap.add_argument("--from", dest="date_from", metavar="YYYY-MM-DD", help="события не раньше даты")
    ap.add_argument("--to", dest="date_to", metavar="YYYY-MM-DD", help="события не позже даты")
    ap.add_argument("--json", dest="json_out", metavar="FILE", help="сохранить результат в JSON")
    ap.add_argument("--file", metavar="HTML", help="разбирать локально сохранённый HTML, не качать")
    args = ap.parse_args(argv)

    # --- режим одной страницы ---
    if args.url:
        url = args.url if args.url.startswith("http") else EVENT_URL % args.url
        try:
            page = io.open(args.file, encoding="utf-8", errors="replace").read() if args.file else fetch(url)
        except Exception as exc:
            sys.stderr.write("Ошибка: %s\n" % exc)
            return 1
        ev = parse_event_page(page, url)
        dump("СОБЫТИЕ ЦЕНТРА «АРХЭ»")
        dump("Источник: %s" % ev["url"])
        dump("Название: %s" % ev["title"])
        if ev["when"]:
            dump("Дата и время: %s" % ev["when"])
        dump("ID страницы архе (тултип): %s" % (ev["tip"] or "—"))
        dump("Timepad ID: %s" % (ev["timepad_id"] or "—"))
        dump("Timepad URL: %s" % (ev["timepad_url"] or "—"))
        if args.json_out:
            with io.open(args.json_out, "w", encoding="utf-8") as f:
                json.dump(ev, f, ensure_ascii=False, indent=2)
        return 0

    # --- режим календаря ---
    try:
        page = io.open(args.file, encoding="utf-8", errors="replace").read() if args.file else fetch(CAL_URL)
    except Exception as exc:
        sys.stderr.write("Ошибка: %s\n" % exc)
        return 1

    events = parse_calendar(page)
    if args.date_from:
        events = [e for e in events if e["date"][:10] >= args.date_from]
    if args.date_to:
        events = [e for e in events if e["date"][:10] <= args.date_to]

    result, errors = [], 0
    for e in events:
        src = e["slug_url"] or (EVENT_URL % e["tip"])
        rec = dict(e)
        try:
            body = fetch(src)
        except Exception as exc:
            sys.stderr.write("  (%s) ошибка загрузки: %s\n" % (e["title"][:40], exc))
            errors += 1
            body = ""
        tp_id, cust = parse_timepad(body) if body else (None, None)
        rec["arhe_url"] = resolve_arhe_url(e["tip"], e["slug_url"])
        rec["timepad_id"] = tp_id
        rec["timepad_url"] = timepad_url(tp_id, cust) if tp_id else ""
        result.append(rec)

    dump("СОБЫТИЯ «ЦЕНТРА АРХЭ» — календарь %s" % CAL_URL)
    dump("Всего: %d" % len(result))
    dump()
    for e in result:
        dump("%s | %s" % (e["date"][:16].replace("T", " "), e["title"]))
        dump("    архе:   %s" % (e["arhe_url"] or "—"))
        dump("    timepad: %s" % (e["timepad_url"] or "(не найден)"))
    if errors:
        dump()
        dump("Ошибок загрузки: %d" % errors)

    if args.json_out:
        with io.open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        dump("JSON сохранён: %s" % os.path.abspath(args.json_out))

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
