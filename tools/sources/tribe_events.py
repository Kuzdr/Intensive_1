# -*- coding: utf-8 -*-
"""Адаптер источника на движке The Events Calendar (WordPress/tribe_events).

Используется сайтами лекториев (у «Архэ» — arhe.msk.ru). Со страницы события
берёт: заголовок, точные даты начала/конца (JSON-LD, с годом), HTML-текст
лекции, картинку и подключённый виджет Timepad (`data-twf2s-event--id` +
`data-timepad-customized`), что даёт связку «сайт + Timepad».

Движок один для всех сайтов на The Events Calendar — поэтому адаптер общий,
а не «архэшный». Специфика «Архэ» (адресный блок, шаблон описания) — в
драйвере `tools/arhe_prototype.py`.

Использование:

    python -X utf8 tools\\sources\\tribe_events.py "https://arhe.msk.ru/?post_type=tribe_events&p=157231"
    python -X utf8 tools\\sources\\tribe_events.py <url> --json out.json
    python -X utf8 tools\\sources\\tribe_events.py <url> --file saved.html

Кэш: data/raw/arhe/<идентификатор>.html (папка в .gitignore).
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
CACHE = os.path.join(ROOT, "data", "raw", "arhe")

TIMEPAD_CUSTOMIZED = {
    "13612": "arhe-events.timepad.ru",
    "44486": "tsentr-arhe-v-sankt-peter.timepad.ru",
}


def _slug(value):
    m = re.search(r"p=(\d+)", value or "")
    if m:
        return "p" + m.group(1)
    return hashlib.md5((value or "").encode("utf-8")).hexdigest()[:12]


def parse(html, url=""):
    """HTML страницы tribe_events -> нормализованный словарь события."""
    canonical = ""
    m = re.search(r'rel="canonical"[^>]*href="([^"]+)"', html)
    if m:
        canonical = m.group(1)

    title = ""
    m = re.search(r"<title>(.*?)</title>", html, re.S)
    if m:
        title = P.html_to_text(m.group(1)).split("|")[0]
    title = re.sub(r"\s*[-–—]\s*Центр Архэ\s*$", "", title).strip()

    start = ""
    m = re.search(r'"startDate"\s*:\s*"([^"]+)"', html)
    if m:
        start = m.group(1)
    end = ""
    m = re.search(r'"endDate"\s*:\s*"([^"]+)"', html)
    if m:
        end = m.group(1)
    date_iso = start[:10] if start else ""
    time_start = start[11:16] if len(start) >= 16 else ""

    date_human = ""
    m = re.search(r'tribe-event-date-start">(.*?)</span>', html, re.S)
    if m:
        date_human = P.html_to_text(m.group(1))

    tp_id = tp_cust = ""
    m = re.search(r'data-timepad-customized="(\d+)"[^>]*data-twf2s-event--id="(\d+)"', html)
    if not m:
        m = re.search(r'data-twf2s-event--id="(\d+)"[^>]*data-timepad-customized="(\d+)"', html)
        if m:
            tp_id, tp_cust = m.group(1), m.group(2)
    if m and not tp_id:
        tp_cust, tp_id = m.group(1), m.group(2)

    image = ""
    m = re.search(r'og:image"[^>]*content="([^"]+)"', html)
    if m:
        image = m.group(1)

    body = P.html_block(html, 'class="tribe-events-single-event-description')

    return {
        "source": "tribe_events",
        "id": _slug(url),
        "url": url or canonical,
        "canonical": canonical,
        "title": title,
        "start_iso": start,
        "end_iso": end,
        "date_iso": date_iso,
        "time_start": time_start,
        "date_human": date_human,
        "timepad_id": tp_id,
        "timepad_customized": tp_cust,
        "timepad_account": TIMEPAD_CUSTOMIZED.get(tp_cust, ""),
        "timepad_url": ("https://%s/event/%s/" % (TIMEPAD_CUSTOMIZED[tp_cust], tp_id)
                        if tp_cust in TIMEPAD_CUSTOMIZED and tp_id else ""),
        "image": image,
        "body_html": body,
    }


def read(value, refresh=False, file=None):
    if file:
        html = io.open(file, encoding="utf-8", errors="replace").read()
    else:
        html = P.http_get(value, os.path.join(CACHE, _slug(value) + ".html"), refresh)
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
