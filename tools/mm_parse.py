# -*- coding: utf-8 -*-
"""Разбор сайта лектория Medio Modo (mediomodo.ru) в структурированный JSON.

Зачем: страницы анонсов Medio Modo сделаны на Tilda, и нужные данные (название,
город, площадка, дата, время, цена, возраст, тексты, лекторы, «Как добраться»,
контакты) лежат в блоках Tilda. Этот скрипт выкачивает страницы и раскладывает
их по полям - чтобы потом составлять прототипы описаний (скилл
event-description, data/prototypes/*/prototype.json) без ручного копания в HTML.

Сайт Tilda Store, поэтому есть два источника ссылки на событие:
  * каталог (Tilda Store API) - перечисляет все карточки афиши;
  * сама страница события (https://mediomodo.ru/<slug>) - полное описание.

Использование:
    # список slug из файла (по одному в строке, пустые строки и # игнорируются)
    python -X utf8 tools\\mm_parse.py --slugs-file data\\raw\\mm_slugs.txt

    # отдельные события
    python -X utf8 tools\\mm_parse.py --slugs sazhina-msk-krotovye-nory yoklmn-fest

    # весь каталог афиши: сначала ссылка на карточки, потом разбор страниц
    python -X utf8 tools\\mm_parse.py --catalog --limit 5

    # перекачать заново, минуя кэш, и напечатать отчёт по событию
    python -X utf8 tools\\mm_parse.py --slugs yudaev-spb-kvantovaya-mekhanika --refresh --report

Кэш HTML: data\\raw\\mediomodo\\<slug>.html (папка в .gitignore, как и прочие
сырые данные). JSON: data\\raw\\mediomodo\\events.json + events.txt (отчёт).

Код возврата: 0 - ОК, 1 - ошибка (нет сети/файла, пустой разбор).
"""
import argparse
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "data", "raw", "mediomodo")
BASE = "https://mediomodo.ru/"

# Каталог афиши (Tilda Store). Параметры видны в JS страницы https://mediomodo.ru/afisha
STORE_API = "https://store.tildaapi.com/api/getproductslist/"
STORE_PARAMS = {
    "storepartuid": "426312392462",
    "recid": "665365158",
    "getparts": "1",
    "getoptions": "1",
    "size": "300",
    "flag_root": "withroot",
}

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# Невидимые символы, которыми набиты цены и даты в Tilda («1500р», «ЕСОД﻿»).
INVISIBLE = "\u200b\u200c\u200d\u2060\ufeff"
# Служебные блоки Tilda (меню, подвал, попапы, карусели «похожие», счётчики).
SKIP_TYPES = {
    "360", "978", "966", "228", "282", "327", "227", "120", "390", "367",
    "215", "131", "191", "240", "255_wrong",
}
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря")


# ---------------------------------------------------------------- утилиты

def denoise(s):
    """Убрать невидимые символы и BOM, нормализовать пробелы."""
    for ch in INVISIBLE:
        s = s.replace(ch, "")
    return s


def html_to_text(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"</(p|div|li|h\d)>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = (s.replace("&nbsp;", "\u00a0").replace("&amp;", "&")
          .replace("&laquo;", "\u00ab").replace("&raquo;", "\u00bb")
          .replace("&quot;", '"').replace("&#39;", "'")
          .replace("&mdash;", "\u2014").replace("&ndash;", "\u2013"))
    s = denoise(s)
    s = re.sub(r"[ \t\u00a0]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def cut_html(s, limit=None):
    """Обрезать HTML до закрывающего тега, убрав хвост со служебными вложенными div."""
    depth = 0
    for m in re.finditer(r"<(/?)div\b[^>]*>", s):
        if m.group(1) == "/":
            depth -= 1
            if depth <= 0:
                s = s[:m.end()]
                break
        else:
            depth += 1
    if limit and len(s) > limit:
        s = s[:limit]
    return s.strip()


def first_group(pattern, text, flags=re.S):
    """Первая группа (или всё совпадение, если групп нет) по паттерну."""
    m = re.search(pattern, text, flags)
    if not m:
        return ""
    return m.group(1) if m.groups() else m.group(0)


# ---------------------------------------------------------------- загрузка

def get(url, cache_path=None, refresh=False, tries=3):
    if cache_path and os.path.exists(cache_path) and not refresh \
            and os.path.getsize(cache_path) > 20000:
        return io.open(cache_path, encoding="utf-8").read()
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,*/*",
                "Accept-Language": "ru-RU,ru;q=0.9",
                "Accept-Encoding": "gzip",
            })
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
            t = data.decode("utf-8", "replace")
            if cache_path:
                io.open(cache_path, "w", encoding="utf-8", newline="").write(t)
            return t
        except Exception as e:      # noqa: BLE001 - сеть бывает капризной
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise IOError("не удалось скачать %s: %r" % (url, last))


def fetch_catalog(refresh=False):
    """Каталог афиши: [{slug, url, title, date, price}, ...]."""
    qs = "&".join("%s=%s" % (k, v) for k, v in STORE_PARAMS.items())
    raw = get(STORE_API + "?" + qs,
              os.path.join(CACHE, "catalog_api.json"), refresh)
    data = json.loads(raw)
    products = data.get("products") or []
    out = []
    for p in products:
        url = p.get("url") or ""
        m = re.search(r"mediomodo\.ru/([^/?#]+)", url)
        if not m:
            continue
        out.append({
            "slug": m.group(1),
            "url": "https://mediomodo.ru/" + m.group(1),
            "title": denoise(p.get("title") or ""),
            "part": (p.get("parts") or [{}])[0] if p.get("parts") else {},
        })
    return out


# ---------------------------------------------------------------- разбор

def rec_blocks(t):
    """[(rec_id, record_type, html), ...] по порядку следования на странице."""
    out = []
    for seg in re.split(r'(?=<div id="rec\d+")', t)[1:]:
        m = re.match(r'<div id="rec(\d+)"[^>]*data-record-type="(\d+)"', seg)
        if not m:
            m2 = re.match(r'<div id="rec(\d+)"', seg)
            if not m2:
                continue
            out.append((m2.group(1), "?", seg))
        else:
            out.append((m.group(1), m.group(2), seg))
    return out


def parse_card_items(t):
    """Пункты «карточки» на обложке: город+площадка, дата, время, цена, онлайн."""
    items = []
    for m in re.finditer(r't1060__item-text[^>]*>(.*?)(?=</div>|<div)', t, re.S):
        v = denoise(html_to_text(m.group(1)))
        v = v.strip()
        if v and v not in items and "#rec" not in v and "{" not in v:
            items.append(v)
    return items


def parse_cover(t):
    title = ""
    m = re.search(r'class="t1060__title[^"]*"[^>]*field="title"[^>]*>(.*?)</div>', t, re.S)
    if m:
        title = html_to_text(m.group(1))
    cover = first_group(r'data-content-cover-bg="([^"]+)"', t)
    caption = ""
    cm = re.search(r'aria-label="([^"]+)"[^>]*itemscope', t)
    if cm:
        caption = denoise(cm.group(1))
    if not cover:
        cover = first_group(r'<meta itemprop="image" content="([^"]+)"', t)
    return title, cover, caption


def parse_sections(blocks):
    """Подзаголовки (T225/T255) и следующие за ними текстовые блоки (T004/T106)."""
    sections = []
    pending = None
    for _rid, rt, seg in blocks:
        if rt == "255":
            h = first_group(r'field="title"[^>]*>(.*?)</h\d>', seg, re.S)
            d = first_group(r'field="descr"[^>]*>(.*?)</div>', seg, re.S)
            if h:
                pending = {"heading": html_to_text(h), "html": "", "text": ""}
                if d:
                    pending["html"] = cut_html(d)
                    pending["text"] = html_to_text(d)
                    sections.append(pending)
                    pending = None
        elif rt in ("106", "4"):
            body = first_group(r'field="text"[^>]*>(.*?)</div>\s*</div>', seg, re.S)
            if not body:
                body = first_group(r'field="text"[^>]*>(.*)', seg, re.S)
            if body:
                body = cut_html(body)
                item = {"heading": pending["heading"] if pending else "",
                        "html": body, "text": html_to_text(body)}
                sections.append(item)
                pending = None
    return sections


def parse_lecturers(blocks):
    """Карточки лекторов (T847): имя, должность, описание, фото."""
    people = []
    for _rid, rt, seg in blocks:
        if rt != "847":
            continue
        for li in re.findall(r'<li\b.*?</li>', seg, re.S):
            name = html_to_text(first_group(
                r'field="li_title__\d+"[^>]*>(.*?)</(?:h\d|div)>', li, re.S))
            descr = first_group(r'field="li_descr__\d+"[^>]*>(.*?)</div>', li, re.S)
            photo = first_group(r'data-original="([^"]+)"', li)
            if not photo:
                photo = first_group(r'<img[^>]+src="([^"]+)"', li, re.S)
            if not name and not descr:
                continue
            people.append({
                "name": name,
                "role": first_line(html_to_text(descr)),
                "descr": html_to_text(descr),
                "photo": photo,
            })
    return people


def first_line(s):
    for ln in s.split("\n"):
        if ln.strip():
            return ln.strip()
    return ""


def parse_howto(sections):
    for s in sections:
        if "добрать" in s["heading"]:
            return s
    return None


def parse_about(sections):
    for s in sections:
        if "лектор" in s["heading"].lower():
            return s
    return None


def parse_contacts(t, blocks):
    """Телефон, почта, возраст, ссылки на билеты."""
    t650 = ""
    for _rid, rt, seg in blocks:
        if rt == "650":
            t650 = seg
            break
    seg = t650 or t
    phone = first_group(r"\+7[\s(]*\d{3}\)?[\s\u00a0-]*\d{3}[\s\u00a0-]*\d{2}[\s\u00a0-]*\d{2}", seg)
    email = first_group(r"[\w.\-+]+@[\w.\-]+\.\w+", seg)
    age = ""
    am = re.search(r"(\d{1,2}\+)\s*</?[^>]*>?\s*Возрастное", seg)
    if am:
        age = am.group(1)
    if not age:
        am = re.search(r"(\d{1,2}\+)[^<]{0,80}Возрастное", denoise(html_to_text(seg)))
        if am:
            age = am.group(1)
    buy = []
    for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, re.S):
        label = html_to_text(m.group(2).split("<")[0])
        if len(label) > 40:
            continue
        low = label.lower()
        if any(k in low for k in ("купить", "билет", "регистрац", "записаться")):
            buy.append({"url": m.group(1).replace("&amp;", "&"),
                        "label": label})
    # убрать дубли
    uniq, seen = [], set()
    for b in buy:
        if b["url"] not in seen:
            seen.add(b["url"])
            uniq.append(b)
    return {"phone": phone, "email": email, "age": age, "buy_links": uniq}


def parse_map(blocks):
    """Координаты встроенной карты Tilda.

    ВНИМАНИЕ: у большинства страниц это заглушка шаблона (координаты Москвы
    55.751979 / 37.617499) - реальной метки площадки на ней нет. Такие случаи
    помечаем is_template=True, чтобы не принять их за адрес.
    """
    for _rid, rt, seg in blocks:
        if rt == "125":
            x = first_group(r'data-map-x="([-\d.]+)"', seg)
            y = first_group(r'data-map-y="([-\d.]+)"', seg)
            z = first_group(r'data-map-zoom="([-\d.]+)"', seg)
            if x and y:
                lat, lon = float(x), float(y)
                return {"lat": lat, "lon": lon, "zoom": z,
                        "is_template": abs(lat - 55.751979) < 0.01
                                        and abs(lon - 37.617499) < 0.01}
    return {}


def split_city_venue(item):
    if "," in item:
        city, venue = item.split(",", 1)
        return city.strip(), venue.strip()
    return "", item.strip()


def parse_date_time_price(items):
    date = time_ = price = online = ""
    for v in items:
        if re.search(r"\d{4}\s*$", v) and re.search(r"\d{1,2}\s+\w+", v):
            date = v
        elif re.match(r"^\d{1,2}[:.]\d{2}", v):
            time_ = v
        elif re.search(r"[₽р]", v) and re.search(r"\d", v):
            price = v
        elif "нлайн" in v:
            online = v
    return date, time_, price, online


def to_iso_date(date_human):
    m = re.search(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})", date_human.lower())
    if not m:
        return ""
    day, mon, year = int(m.group(1)), m.group(2), m.group(3)
    if mon not in MONTHS:
        return ""
    return "%s-%02d-%02d" % (year, MONTHS.index(mon) + 1, day)


def parse_page(slug, html):
    blocks = rec_blocks(html)
    title_cover, cover, caption = parse_cover(html)
    items = parse_card_items(html)
    where = items[0] if items else ""
    city, venue = split_city_venue(where)
    date_h, time_h, price_h, online = parse_date_time_price(items[1:])
    sections = parse_sections(blocks)
    howto = parse_howto(sections)
    about = parse_about(sections)
    seo = html_to_text(first_group(r"<title>(.*?)</title>", html))
    return {
        "slug": slug,
        "url": BASE + slug,
        "title": title_cover or denoise(seo.split("|")[0]).strip(" ."),
        "title_first_line": (title_cover or denoise(seo.split("|")[0])).split("\n")[0].strip(" ."),
        "title_cover_lines": [x for x in title_cover.split("\n") if x.strip()],
        "seo_title": denoise(seo),
        "cover": cover,
        "cover_caption": caption,
        "city": city,
        "venue": venue,
        "venue_where": where,
        "date_human": date_h,
        "date_iso": to_iso_date(date_h),
        "time": time_h,
        "price_human": price_h,
        "online": online,
        "card_items": items,
        "sections": sections,
        "description": [s for s in sections if not s["heading"]],
        "howto": howto,
        "about_lecturers": about,
        "lecturers": parse_lecturers(blocks),
        "contacts": parse_contacts(html, blocks),
        "map": parse_map(blocks),
    }


# ---------------------------------------------------------------- отчёт

def report(ev):
    out = []
    a = out.append
    a("=" * 78)
    a("СЛАГ:      %s" % ev["slug"])
    a("URL:       %s" % ev["url"])
    a("НАЗВАНИЕ:  %s" % ev["title"])
    a("ГОРОД:     %s" % ev["city"])
    a("ПЛОЩАДКА:  %s" % ev["venue"])
    a("ДАТА:      %s  ->  %s" % (ev["date_human"], ev["date_iso"]))
    a("ВРЕМЯ:     %s" % ev["time"])
    a("ЦЕНА:      %s" % ev["price_human"])
    if ev["online"]:
        a("ОНЛАЙН:    %s" % ev["online"])
    a("ВОЗРАСТ:   %s" % ev["contacts"]["age"])
    a("ТЕЛЕФОН:   %s" % ev["contacts"]["phone"])
    a("ПОЧТА:     %s" % ev["contacts"]["email"])
    a("ОБЛОЖКА:   %s" % ev["cover"])
    a("ПОДПИСЬ:   %s" % ev["cover_caption"])
    for b in ev["contacts"]["buy_links"]:
        a("БИЛЕТ:     %s  (%s)" % (b["url"], b["label"]))
    a("КАРТА:     %s" % (ev["map"] or "-"))
    if ev["map"].get("is_template"):
        a("           ^ это ЗАГЛУШКА шаблона (координаты Москвы), не метка площадки")
    a("--- ТЕКСТЫ ---")
    for s in ev["sections"]:
        if s["heading"]:
            a("### %s" % s["heading"])
        a(s["text"] if s["text"] else "(пусто)")
        a("")
    a("--- ЛЕКТОРЫ ---")
    for p in ev["lecturers"]:
        a("* %s — %s" % (p["name"], p["role"]))
        a("  фото: %s" % p["photo"])
        a("  %s" % p["descr"])
    return "\n".join(out)


# ---------------------------------------------------------------- main

def read_slugs(args):
    slugs = []
    if args.slugs:
        slugs += [s.strip() for s in args.slugs if s.strip()]
    if args.slugs_file:
        for ln in io.open(args.slugs_file, encoding="utf-8").read().splitlines():
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                slugs.append(ln)
    if args.catalog:
        cat = fetch_catalog(args.refresh)
        io.open(os.path.join(CACHE, "catalog.json"), "w", encoding="utf-8").write(
            json.dumps(cat, ensure_ascii=False, indent=1))
        print("каталог: %d карточек -> data/raw/mediomodo/catalog.json" % len(cat))
        for c in cat:
            slugs.append(c["slug"])
    if args.limit:
        slugs = slugs[:args.limit]
    seen, uniq = set(), []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq


def main():
    ap = argparse.ArgumentParser(description="Разбор анонсов mediomodo.ru")
    ap.add_argument("--slugs", nargs="*", help="slug'ы событий (без https://)")
    ap.add_argument("--slugs-file", help="файл со списком slug'ов")
    ap.add_argument("--catalog", action="store_true", help="взять slug'и из каталога афиши")
    ap.add_argument("--limit", type=int, default=0, help="только первые N событий")
    ap.add_argument("--refresh", action="store_true", help="перекачать, не брать кэш")
    ap.add_argument("--report", action="store_true", help="печать текстовый отчёт")
    ap.add_argument("--out", default=os.path.join(CACHE, "events.json"))
    args = ap.parse_args()

    if not os.path.isdir(CACHE):
        os.makedirs(CACHE)
    slugs = read_slugs(args)
    if not slugs:
        print("не задано ни одного события", file=sys.stderr)
        return 1

    events, bad = [], []
    for i, slug in enumerate(slugs, 1):
        try:
            html = get(BASE + slug, os.path.join(CACHE, slug + ".html"), args.refresh)
            ev = parse_page(slug, html)
            events.append(ev)
            print("[%2d/%2d] %-42s %s | %s | %s" % (
                i, len(slugs), slug[:42], ev["date_iso"] or "???",
                ev["city"] or "?", ev["venue"][:40]))
        except Exception as e:      # noqa: BLE001
            bad.append((slug, repr(e)))
            print("[%2d/%2d] %-42s ОШИБКА %r" % (i, len(slugs), slug[:42], e))
        time.sleep(0.4)

    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps(events, ensure_ascii=False, indent=1))
    rep = os.path.splitext(args.out)[0] + ".txt"
    io.open(rep, "w", encoding="utf-8").write(
        "\n\n".join(report(e) for e in events))
    print("\nразобрано %d из %d; ошибок %d" % (len(events), len(slugs), len(bad)))
    print("JSON: %s\nотчёт: %s" % (args.out, rep))
    for slug, err in bad:
        print("  ! %s: %s" % (slug, err))
    if args.report and events:
        print("\n" + report(events[0]))
    return 1 if not events else 0


if __name__ == "__main__":
    sys.exit(main())
