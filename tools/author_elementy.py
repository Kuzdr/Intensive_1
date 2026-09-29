# -*- coding: utf-8 -*-
"""Извлечение блока автора с elementy.ru для прототипов (скилл event-description).

Ищет события автора через поиск «Элементов», разбирает блок
`<div class='about authors'>` на странице события и возвращает:
pretitle (Фамилия Имя Отчество), HTML-блок описания и фото.

Использование:
    python -X utf8 tools\\author_elementy.py "Алексей Решетун"
    python -X utf8 tools\\author_elementy.py --names data\\raw\\mm_lecturers.txt
    python -X utf8 tools\\author_elementy.py "Ольга Сажина" --out data\\raw\\authors.json
    python -X utf8 tools\\author_elementy.py --event 450571          # одна страница
    python -X utf8 tools\\author_elementy.py "Дмитрий Соболев" --refresh

Кэш HTML: data/raw/elementy/<id>.html (папка в .gitignore).
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "raw", "elementy")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
FIND = "https://elementy.ru/find?objs=eltevents&words=%s"
EVENT = "https://elementy.ru/events/%s/"


def fetch(url):
    import requests
    r = requests.get(url, timeout=40, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.text


def page_html(event_id, refresh=False):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "%s.html" % event_id)
    if os.path.isfile(path) and not refresh:
        with io.open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    html = fetch(EVENT % event_id)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    time.sleep(0.4)
    return html


def search_events(name):
    """Список id событий из выдачи поиска «Элементов» (сначала свежие)."""
    url = FIND % urllib.parse.quote_plus(name)
    html = fetch(url)
    pairs = re.findall(r"/events/(\d+)/([A-Za-z0-9_\-]+)", html)
    seen, out = set(), []
    for eid, slug in pairs:
        if eid in seen:
            continue
        seen.add(eid)
        out.append((int(eid), slug))
    out.sort(reverse=True)
    return out


INVISIBLE = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff\u00ad\u180e"), None)


def denoise(s):
    """Убирает невидимые символы (BOM/zero-width) и двойные пробелы.

    Скрытые символы в блоке автора — мусор выгрузки «Элементов»
    (например, «202\ufeff3» вместо «2023»), а не часть готового текста:
    правило «копировать дословно» относится к типографике, а не к мусору.
    """
    return re.sub(r"[ \t]{2,}", " ", s.translate(INVISIBLE)).strip()


def clean(html):
    html = html.strip()
    html = re.sub(r"^<p>\s*", "", html)
    html = re.sub(r"\s*</p>$", "", html)
    return html


def parse_authors(html):
    """[{pretitle, text, photo}] из блоков 'about authors' страницы события."""
    out = []
    chunks = html.split("about authors")[1:]
    for ch in chunks:
        m_pre = re.search(r"<div class=['\"]pretitle['\"]>(.*?)</div>", ch, re.S)
        m_txt = re.search(r"<div class=['\"]text['\"]>(.*?)</div>\s*</div>", ch, re.S)
        m_img = re.search(r"<img[^>]+src=['\"]([^'\"]+)['\"][^>]*>", ch)
        if not m_txt:
            continue
        text = re.sub(r"\s+", " ", m_txt.group(1)).strip()
        text = re.sub(r"\s+>", ">", text)
        text = denoise(text)
        if not text:
            continue
        photo = ""
        if m_img:
            photo = m_img.group(1)
            if photo.startswith("/"):
                photo = "https://elementy.ru" + photo
            elif photo.startswith("images/"):
                photo = "https://elementy.ru/" + photo
        out.append({
            "pretitle": denoise(clean(m_pre.group(1))) if m_pre else "",
            "block_html": text,
            "photo": photo,
        })
    return out


def surname(name):
    return name.split()[0].lower()


def find_author(name, refresh=False, max_pages=4):
    """Ищет блок автора по фамилии. Возвращает dict или None."""
    target = surname(name)
    for eid, _slug in search_events(name)[:max_pages]:
        try:
            html = page_html(eid, refresh=refresh)
        except Exception as e:
            print("   ! %s: %s" % (eid, e), file=sys.stderr)
            continue
        for a in parse_authors(html):
            hay = ("%s %s" % (a["pretitle"], a["block_html"])).lower()
            if target in hay or name.split()[-1].lower() in hay:
                a["event_id"] = eid
                a["event_url"] = EVENT % eid
                a["query"] = name
                return a
    return None


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    refresh = "--refresh" in args
    out_path = None
    if "--out" in args:
        i = args.index("--out")
        out_path = args[i + 1]
        del args[i:i + 2]
    event_only = None
    if "--event" in args:
        i = args.index("--event")
        event_only = args[i + 1]
        del args[i:i + 2]
    if "--names" in args:
        i = args.index("--names")
        names = [s.strip() for s in
                 io.open(args[i + 1], encoding="utf-8").read().split("\n") if s.strip()]
        del args[i:i + 2]
    else:
        names = [s for s in args if not s.startswith("--")]

    result = []
    if event_only:
        for a in parse_authors(page_html(event_only, refresh=refresh)):
            a["event_id"] = event_only
            a["event_url"] = EVENT % event_only
            print("   ФИО: %s" % a["pretitle"])
            print("   Фото: %s" % a["photo"])
            print("   Блок: %s" % a["block_html"])
            result.append(a)
    else:
        for n in names:
            print("= %s" % n)
            a = find_author(n, refresh=refresh)
            if not a:
                print("   НЕ НАЙДЕН на «Элементах» -> новый автор")
                result.append({"query": n, "found": False})
                continue
            print("   %s" % a["event_url"])
            print("   ФИО: %s" % a["pretitle"])
            print("   Фото: %s" % a["photo"])
            print("   Блок: %s" % a["block_html"][:400])
            a["found"] = True
            result.append(a)
    if out_path:
        with io.open(out_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, indent=1)
        print("\nСохранено: %s" % out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
