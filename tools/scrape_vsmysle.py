# -*- coding: utf-8 -*-
"""Читатель анонса сообщества «ВСмысле» (vsmysle.spb.ru).

Страница анонса — обычный Bitrix-HTML, без JSON-блоков. Скрипт вытаскивает:
заголовок, дату и время, адрес, текст описания (HTML), блок «Цена»,
ссылки регистрации (Яндекс Афиша — очно, Timepad — онлайн-трансляция)
и признак онлайна.

Использование:

    python -X utf8 tools\\scrape_vsmysle.py https://vsmysle.spb.ru/community/afisha/<slug>
    python -X utf8 tools\\scrape_vsmysle.py <slug>            -- короткая форма
    python -X utf8 tools\\scrape_vsmysle.py <url> --file page.html -- не качать

Код возврата: 0 — анонс разобран, 1 — ошибка.
"""
import argparse
import html as html_mod
import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"
BASE = "https://vsmysle.spb.ru/community/afisha/"

DESC_OPEN = '<div class="content catalog-detail__detailtext" itemprop="description">'
DESC_END = '<div class="tab-pane hidden" id="char">'
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S)
OG_DESC_RE = re.compile(r'<meta property="og:description" content="([^"]*)"')
ADDRESS_RE = re.compile(r'<div class="address__text[^"]*">(.*?)</div>', re.S)
PRICE_RE = re.compile(r"<b>Цена:</b>(.*?)(?:<p>|</div>)", re.S)
BIO_RE = re.compile(r"<b>([^<>]{3,})</b>\s*[—-]\s*([^<>]+?)</p>")
TICKET_RE = re.compile(r"https?://widget\.afisha\.yandex\.ru/[^\"'<> ]+")
TIMEPAD_RE = re.compile(r"https?://[a-z0-9.-]*timepad\.ru/event/\d+/?#?")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(fragment: str) -> str:
    """HTML-фрагмент → текст: <br> = перенос строки, теги снимаются."""
    t = re.sub(r"(?i)<br\s*/?>", "\n", fragment)
    t = re.sub(r"<[^>]+>", "", t)
    t = html_mod.unescape(t)
    lines = [re.sub(r"[ \t\u00a0]+", " ", l).strip() for l in t.splitlines()]
    return "\n".join(l for l in lines if l)


def uniq(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def dump(msg: str = ""):
    sys.stdout.write(msg + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url", help="URL анонса /community/afisha/<slug> или просто <slug>")
    ap.add_argument("--file", metavar="HTML", help="разбирать локально сохранённый HTML, не качать")
    args = ap.parse_args(argv)

    url = args.url
    if not url.startswith("http"):
        url = BASE + url.strip("/") + "/"

    try:
        page = open(args.file, encoding="utf-8", errors="replace").read() if args.file else fetch(url)
    except Exception as exc:  # сеть или файл
        sys.stderr.write("Ошибка: %s\n" % exc)
        return 1

    start = page.find(DESC_OPEN)
    end = page.find(DESC_END)
    if start < 0 or end < 0 or end < start:
        sys.stderr.write("Ошибка: на странице не найден блок описания (не страница анонса?)\n")
        return 1
    desc_html = page[start + len(DESC_OPEN):end].rstrip()
    desc_html = re.sub(r"(?:\s*</div>\s*)+$", "", desc_html).strip()

    title = TITLE_RE.search(page)
    title = html_mod.unescape(title.group(1)).strip() if title else ""
    title = re.sub(r"\s*[-–—]\s*ВСмысле\s*$", "", title)

    og = OG_DESC_RE.search(page)
    when = html_mod.unescape(og.group(1)).strip() if og else ""

    addr = ADDRESS_RE.search(page)
    address = clean(addr.group(1)) if addr else ""

    price = PRICE_RE.search(desc_html)
    prices = clean(price.group(1)) if price else ""

    bio = ""
    b = BIO_RE.search(desc_html)
    if b:
        bio = "%s — %s" % (clean(b.group(1)), clean(b.group(2)))

    dump("АНОНС СООБЩЕСТВА «ВСМЫСЛЕ»")
    dump("Источник: %s" % url)
    dump("Название: %s" % title)
    dump("Дата и время: %s" % when)
    dump("Адрес: %s" % address.replace("\n", ", "))
    dump("Онлайн-трансляция: %s" % ("есть" if TIMEPAD_RE.search(page) else "нет"))
    if bio:
        dump("Лектор: %s" % bio)
    dump("Цена (из источника):")
    for line in prices.splitlines():
        dump("  " + line)
    dump("ТЕКСТ ОПИСАНИЯ (HTML), %d знаков:" % len(desc_html))
    dump(desc_html)
    dump("ССЫЛКИ РЕГИСТРАЦИИ (очно, Яндекс Афиша):")
    for l in uniq(TICKET_RE.findall(page)):
        dump(l)
    dump("ССЫЛКИ РЕГИСТРАЦИИ (онлайн, Timepad):")
    for l in uniq(TIMEPAD_RE.findall(page)):
        dump(l)
    dump("ПРОЧИЕ ССЫЛКИ ИЗ ОПИСАНИЯ:")
    for l in uniq(re.findall(r'href="(https?://(?!widget\.afisha|soobshchestvo-vsmysle\.timepad)[^"]+)"', desc_html)):
        dump(l)
    return 0


if __name__ == "__main__":
    sys.exit(main())
