# -*- coding: utf-8 -*-
"""Адаптер источника Timepad (любой аккаунт: Архэ, ВДНХ и т.п.).

Страница события Timepad содержит заэкранированный JSON объекта события (в нём
id, название, дата-«человеческая», город, адрес, организатор, билеты, картинка)
и HTML-блок полного описания `data-qa="block-event-full-description"` (текст
лекции, план курса и т.п.).

Год в объекте НЕ хранится — его передаёт вызывающий код (у «Архэ» год берётся
со страницы arhe.msk.ru; для Timepad без второго источника год задаётся вручную).

Использование:

    python -X utf8 tools\\sources\\timepad.py https://arhe-events.timepad.ru/event/4223719/
    python -X utf8 tools\\sources\\timepad.py 4223719 --json out.json
    python -X utf8 tools\\sources\\timepad.py 4223719 --file saved.html

Кэш: data/raw/timepad/<id>.html (папка в .gitignore, как прочие сырые данные).
"""
import hashlib
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import protolib as P  # noqa: E402

ROOT = P.ROOT
CACHE = os.path.join(ROOT, "data", "raw", "timepad")
ACCOUNTS = {
    "arhe-events": "arhe-events.timepad.ru",
    "tsentr-arhe-v-sankt-peter": "tsentr-arhe-v-sankt-peter.timepad.ru",
}
EVENT_URL = "https://%s.timepad.ru/event/%s/"


def event_id(value):
    """ID события из URL или чистой строки."""
    m = re.search(r"timepad\.ru/event/(\d+)", value or "")
    if m:
        return m.group(1)
    m = re.match(r"^\s*(\d+)\s*$", value or "")
    return m.group(1) if m else ""


def account_of(html, url=""):
    m = re.search(r"//([a-z0-9\-]+)\.timepad\.ru/", (url or "") + html)
    return m.group(1) if m else ""


def _json_object(html, anchor='"has_promocode"'):
    """Заэкранированный JSON объекта события по балансу фигурных скобок."""
    idx = html.find(anchor)
    if idx < 0:
        return None
    start = html.rfind("{", 0, idx)
    depth = 0
    for j in range(start, len(html)):
        if html[j] == "{":
            depth += 1
        elif html[j] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start:j + 1])
                except ValueError:
                    return None
    return None


def _times(date_human):
    """(начало, конец) из «23 октября c 19:00 до 20:30» или «… в 19:00»."""
    t = (date_human or "").replace("\u00a0", " ").replace("\u2009", " ")
    m = re.search(r"(\d{1,2}:\d{2})\s*(?:до|[–—-])\s*(\d{1,2}:\d{2})", t)
    if m:
        return m.group(1), m.group(2)
    m = re.search(r"(\d{1,2}:\d{2})", t)
    return (m.group(1), "") if m else ("", "")


def parse(html, url=""):
    """HTML страницы Timepad -> нормализованный словарь события."""
    obj = _json_object(html) or {}
    acc = account_of(html, url) or obj.get("subdomain") or ""
    eid = str(obj.get("id") or event_id(url))

    title = obj.get("name") or ""
    if not title:
        m = re.search(r'og:title"[^>]*content="([^"]+)"', html)
        title = m.group(1) if m else ""
    title = re.sub(r"\s*/\s*События на TimePad\.ru\s*$", "", title)
    title = P.html_to_text(title).replace("\n", " ").strip()

    date_human = obj.get("date_human") or ""
    tstart, tend = _times(date_human)
    if not tstart:
        tstart = obj.get("time") or ""

    month_num = 0
    if obj.get("month"):
        for i, m in enumerate(P.MONTHS, 1):
            if m == obj["month"]:
                month_num = i
                break
    elif date_human:
        for i, m in enumerate(P.MONTHS, 1):
            if m in date_human:
                month_num = i
                break

    body = P.html_block(html, 'data-qa="block-event-full-description"')

    am = re.search(r'title-age-limit"[^>]*>\s*([^<]+?)\s*<', html)

    tickets = []
    for t in obj.get("tickets") or []:
        if isinstance(t, dict) and t.get("price") is not None:
            tickets.append({"name": t.get("name") or "", "price": int(t["price"])})
    prices = [t["price"] for t in tickets if t["price"]]

    return {
        "source": "timepad",
        "id": eid,
        "url": (EVENT_URL % (acc, eid)) if (acc and eid) else (url or ""),
        "account": acc,
        "title": title,
        "date_human": date_human,
        "datetime_human": obj.get("datetime") or "",
        "day": int(obj["day"]) if str(obj.get("day") or "").isdigit() else None,
        "month": obj.get("month") or "",
        "month_num": month_num,
        "weekday": int(obj["day_of_week"]) if str(obj.get("day_of_week") or "").isdigit() else None,
        "year": None,
        "date_iso": None,
        "time_start": tstart,
        "time_end": tend,
        "city": obj.get("city") or "",
        "place": P.html_to_text(obj.get("place") or "").replace("\n", " ").strip().rstrip("."),
        "organization": P.html_to_text(obj.get("organization_name") or ""),
        "age": am.group(1).strip() if am else "",
        "image": obj.get("image") or "",
        "tickets": tickets,
        "price_min": min(prices) if prices else None,
        "body_html": body,
    }


def read(value, refresh=False, file=None):
    """Прочитать событие: по URL/id (с кэшем) или из локального файла.

    URL берётся как есть (аккаунт не угадываем). Для «голого» ID по умолчанию
    используется московский аккаунт «Архэ» (arhe-events); иначе передайте URL.
    """
    eid = event_id(value)
    if file:
        html = io.open(file, encoding="utf-8", errors="replace").read()
    elif re.match(r"^\s*https?://", value or ""):
        name = eid or hashlib.md5(value.encode("utf-8")).hexdigest()[:12]
        html = P.http_get(value, os.path.join(CACHE, name + ".html"), refresh)
    elif eid:
        html = P.http_get(EVENT_URL % ("arhe-events", eid),
                          os.path.join(CACHE, eid + ".html"), refresh)
    else:
        html = P.http_get(value, os.path.join(CACHE, "page.html"), refresh)
    return parse(html, value)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    refresh = "--refresh" in args
    file = None
    if "--file" in args:
        i = args.index("--file")
        file = args[i + 1]
        del args[i:i + 2]
    out = None
    if "--json" in args:
        i = args.index("--json")
        out = args[i + 1]
        del args[i:i + 2]
    val = [a for a in args if not a.startswith("--")][0]
    ev = read(val, refresh=refresh, file=file)
    text = json.dumps(ev, ensure_ascii=False, indent=2)
    if out:
        io.open(out, "w", encoding="utf-8").write(text)
        print("JSON: %s" % out)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
