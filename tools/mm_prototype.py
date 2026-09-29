# -*- coding: utf-8 -*-
"""Сборка прототипов описаний для событий Medio Modo (data/prototypes/<ID>/prototype.json).

Зачем инструмент: 30 прототипов Medio Modo собираются по одному образцу
(событие 450571 / прототип MM-261003-Krotovye-nory), а поля 1–14 почти
полностью механические (привязка, даты, город, площадка, цена, адрес).
Скрипт берёт их из events.json (tools/mm_parse.py) и authors.json
(tools/author_elementy.py), а СОДЕРЖАНИЕ (аннотация, текст лекции,
«Дополнительная информация», примечания) задаётся вручную в
data/raw/mm_proto_data.py — там же словари VENUES (адресные блоки по
площадкам) и EVENTS (по одному словарю на событие).

Использование:
    python -X utf8 tools\\mm_prototype.py                 # все события из EVENTS
    python -X utf8 tools\\mm_prototype.py liberman-msk    # только один slug
    python -X utf8 tools\\mm_prototype.py --check         # только показать, без записи

Формат EVENTS[slug]:
    venue      : ключ из VENUES (площадка: адрес, проезд, карта, поле 6.2/8/13)
    gen        : имя лектора в родительном падеже («Валерии Либерман») для полей 3–4
    title      : «Название лекции» (поле 5)
    topics     : тематики из reference/lists/theme.md (поле 6.4)
    types      : тип из reference/lists/type.md (поле 6.1), по умолчанию «Лекция»
    audience   : поле 14, по умолчанию «Для всех»
    intro      : HTML второго абзаца шапки (может отсутствовать)
    body       : список HTML-абзацев аннотации (текст лекции из источника)
    closer     : HTML закрывающего абзаца «Лекцию прочитает …» (может отсутствовать)
    extra      : список HTML-строк «Дополнительной информации» (сверх общих блоков)
    notes      : примечания к прототипу
    authors    : список ФИО лекторов (в авторском блоке берётся из authors.json)
    no_buy     : True — не добавлять строку «Стоимость билетов …»
    no_contacts: True — не добавлять блок «Контакты организатора»
"""
import datetime
import importlib.util
import io
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROTO_DIR = os.path.join(ROOT, "data", "prototypes")
DATA_FILE = os.path.join(RAW, "mm_proto_data.py")
EVENTS_JSON = os.path.join(RAW, "mediomodo", "events.json")
AUTHORS_JSON = os.path.join(RAW, "authors.json")

WD = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
MONTHS_NOM = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
              "авг��ст", "сентябрь", "октябрь", "ноябрь", "декабрь"]

# Общие блоки «Дополнительной информации» лектория (из опубликованного
# прототипа MM-261003-Krotovye-nory, образец 450571).
ORG_LINKS = [
    "<!-- @@@ -->",
    '<p class="small">Информация о&nbsp;лекции <a href="{url}" target="_blank">'
    'на сайте Medio Modo</a>.</p>',
    '<p class="small">Medio Modo <a href="https://vk.com/mediomodo" '
    'target="_blank">ВКонтакте</a> и <a href="https://t.me/mediomodo" '
    'target="_blank">в&nbsp;Телеграме</a>.</p>',
]
PHONE = "+7(915)248-97-37"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def d(s):
    return datetime.date(*map(int, s.split("-")))


def binding_index(hh, mm):
    """Индекс времени поля 1 «Привязка» — та же формула, что в check_prototype.py."""
    if hh <= 12:
        head = "0"
    elif hh <= 20:
        head = str(hh - 12)
    else:
        head = "9"
    if not (13 <= hh <= 20) or mm == 0:
        return head
    return head + ("4" if mm < 30 else ("6" if mm == 30 else "8"))


def binding(date_iso, time_str):
    dt = d(date_iso)
    hh, mm = int(time_str[:2]), int(time_str[3:5])
    return "%04d.%02d.%02d%s" % (dt.year, dt.month, dt.day, binding_index(hh, mm))


def price_rub(price_human):
    """«от 1200 ₽» -> «от 1200&nbsp;руб.»."""
    m = re.match(r"^\s*(от\s+)?([\d\s]+)\s*₽\s*$", price_human or "")
    if not m:
        return None
    num = re.sub(r"\s+", "", m.group(2))
    lead = "от " if m.group(1) else ""
    return "%s%s&nbsp;руб." % (lead, num)


DASH = "—&nbsp;"


def pas_online(txt):
    """Добавляет « и ОНЛАЙН» перед финальной точкой HTML-абзаца."""
    t = txt.rstrip()
    if t.endswith(".</p>"):
        return t[:-5] + " и&nbsp;ОНЛАЙН.</p>"
    if t.endswith("."):
        return t[:-1] + " и&nbsp;ОНЛАЙН."
    return t + " и&nbsp;ОНЛАЙН."


def dash_item(line):
    t = re.sub(r"^[—–-]\s*&nbsp;\s*|^[—–-]\s+", "", line)
    return "<li>%s</li>" % t.strip()


def paragraphs(html):
    """Текст лекции источника -> список HTML-блоков для аннотации.

    Абзацы разделены в источнике пустой строкой (`<br /><br />`), отдельные
    пункты перечисления — одиночным `<br />` и начинаются с «—»: они
    собираются в `<ul><li>`, как на «Элементах» (450580).
    """
    html = (html or "").strip()
    out = []
    for chunk in re.split(r"<br\s*/?>\s*<br\s*/?>", html):
        chunk = re.sub(r"^<p[^>]*>|</p>$", "", chunk.strip()).strip()
        if not chunk:
            continue
        lines = [x.strip() for x in re.split(r"<br\s*/?>", chunk) if x.strip()]
        if len(lines) > 1 and all(x.startswith(("—", "&nbsp;—", "-&nbsp;")) for x in lines):
            out.append("<ul>\n" + "\n".join(dash_item(x) for x in lines) + "\n</ul>")
        else:
            out.append("<p>%s</p>" % chunk)
    return out


def source_body(ev, cfg=None):
    """Абзацы аннотации из текста лекции источника (nbsp приводится к правилам).

    По умолчанию берётся только sections[0] — основной текст лекции: остальные
    блоки источника (предупреждение о видеосъёмке, адрес, промокоды) в описание
    не переносятся. Для фестивалей программа лежит во втором блоке, поэтому
    номера нужных блоков перечисляются в `body_sections` конфига.
    """
    cfg = cfg or {}
    secs = ev.get("sections") or [{}]
    out = []
    for i in cfg.get("body_sections") or [0]:
        if i < len(secs):
            out.extend(nbsp_normalize(x) for x in paragraphs(secs[i].get("html") or ""))
    return out or [nbsp_normalize(x) for x in paragraphs(secs[0].get("html") or "")]


def author_sentence(name, descr):
    """Закрывающий абзац: имя + описание ИЗ ИСТОЧНИКА (не блок «Элементов»).

    По скиллу разд. 3в, п. 2: описание из источника живёт в тексте лекции,
    а стандартное описание из базы «Элементов» — в KLBLOCK (поле 7.4).
    Первая буква строчная, точка выносится за </i> (образец MM-261003).
    """
    t = re.sub(r"<[^>]+>", "", descr or "").strip()
    t = re.sub(r"\s+", " ", t).strip().rstrip(".")
    if not t:
        return ""
    t = t[0].lower() + t[1:]
    t = nbsp_normalize(t)
    return "<p>Лекцию прочитает <b><i>%s</i></b>&nbsp;— <i>%s</i>.</p>" % (name, t)


CYR = "а-яёА-ЯЁ"
ONE_LETTER = "вскоуиа"
NO_NBSP_BEFORE = ("от", "на", "по", "из", "за", "до", "для", "но", "не", "ли")
ABBR_DOT = ("д", "ул", "корп", "стр", "г", "им", "пр", "пер", "бул", "наб", "ш")
# «ё» в этих словах не пишется (скилл proofreading, п. 1) — список тот же,
# что у валидатора tools/check_prototype.py (YO_INVARIANTS).
YO_INVARIANTS = ("ещё", "её", "учёный", "учёные", "идёт", "вперёд", "пойдёт",
                 "пройдёт", "разберёт", "разберём")
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI",
         "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX")
TAG_RE = re.compile(r"<[^>]+>")
INVISIBLE = re.compile("[\\u200b-\\u200f\\u202a-\\u202e\\ufeff\\u2060\\u00ad]")


def _visible_segments(t):
    """Разбивает HTML на видимые куски и теги: [(start, end, is_tag)]."""
    out = []
    pos = 0
    for m in TAG_RE.finditer(t):
        if m.start() > pos:
            out.append((pos, m.start(), False))
        out.append((m.start(), m.end(), True))
        pos = m.end()
    if pos < len(t):
        out.append((pos, len(t), False))
    return out


def nbsp_normalize(t, skip_verbatim=False):
    """Приводит расстановку nbsp к правилам скилла proofreading (разд. 2).

    Источник (Tilda) расставляет nbsp после всех подряд слов, поэтому:
    1) весь nbsp снимается, 2) ставится заново только по правилам —
    после однобуквенных предлогов/союзов, перед «—», между инициалами,
    после адресных сокращений с точкой и после числа перед словом.
    Видимый текст правится, содержимое тегов (href, class) — нет.
    """
    t = INVISIBLE.sub("", t)
    t = t.replace("&nbsp;", " ").replace("\u00a0", " ")
    t = re.sub(r"[ \t]{2,}", " ", t)

    def fix(chunk):
        # 1) после однобуквенных предлогов и союзов
        chunk = re.sub(r"(?<![%s])([%s]) (?=[%s])" % (CYR, ONE_LETTER, CYR),
                       r"\1&nbsp;", chunk)
        # 2) перед тире в середине предложения (после тире — обычный пробел)
        chunk = re.sub(r"([%s0-9»)]+) —" % CYR, r"\1&nbsp;—", chunk)
        chunk = chunk.replace("—&nbsp;", "— ")
        # 3) инициалы: «И. О.» и «И.&nbsp;О. Фамилия»
        chunk = re.sub(r"(?<![А-ЯЁ])([А-ЯЁ])\. ([А-ЯЁ])\.", r"\1.&nbsp;\2.", chunk)
        chunk = re.sub(r"(?<![А-ЯЁ])([А-ЯЁ])\. ([А-ЯЁ][а-яё]{2,})", r"\1.&nbsp;\2", chunk)
        # 4) адресные сокращения с точкой: «ул.&nbsp;Тверская», «д.&nbsp;11/11»
        chunk = re.sub(r"\b(%s)\. (?=[0-9А-Яа-яЁё])" % "|".join(ABBR_DOT),
                       r"\1.&nbsp;", chunk)
        # 5) число + слово («10 октября»); перед числом nbsp — только после
        #    однобуквенного предлога (п. 1) и в «Лекция&nbsp;1 курса»
        chunk = re.sub(r"(?<=[0-9]) (?=[А-Яа-яЁё])", "&nbsp;", chunk)
        chunk = re.sub(r"(?<=Лекция) (?=[0-9])", "&nbsp;", chunk)
        # 6) римская цифра в номере — nbsp с обеих сторон («Петра&nbsp;I&nbsp;до»)
        rom = "|".join(sorted(ROMAN, key=len, reverse=True))
        chunk = re.sub(r"(?<=[%s0-9]) (%s)\b" % (CYR, rom), "&nbsp;\\1", chunk)
        chunk = re.sub(r"\b(%s) " % rom, "\\1&nbsp;", chunk)
        # 7) «ё» в словах-инвариантах не пишется (п. 1)
        for w in YO_INVARIANTS:
            cap = w[0].upper() + w[1:]
            chunk = re.sub(r"\b%s\b" % cap, w[0].upper() + w[1:].replace("ё", "е"), chunk)
            chunk = re.sub(r"\b%s\b" % w, w.replace("ё", "е"), chunk)
        return chunk

    segs = _visible_segments(t)
    out, prev = [], ""
    for s, e, is_tag in segs:
        if is_tag:
            out.append(t[s:e])
        else:
            chunk = t[s:e]
            if prev and not prev.endswith(" ") and not chunk.startswith(" "):
                # граница абзаца/тега не должна склеивать слова
                pass
            out.append(fix(chunk))
            prev = chunk
    return "".join(out)


def lecturer_name(ev):
    """Имя лектора источника: первый из списка лекторов."""
    ls = ev.get("lecturers") or []
    return (ls[0].get("name") or "").strip() if ls else ""


def proto_id(ev, cfg):
    """ID прототипа: MM-<ГГММДД>-<slug источника> (как у MM-261003-Krotovye-nory)."""
    if cfg.get("id"):
        return cfg["id"]
    dt = d(ev["date_iso"])
    return "MM-%s-%s" % (dt.strftime("%y%m%d"), ev["slug"])


def fields_for(ev, cfg, venue, today):
    dt = d(ev["date_iso"])
    hh, mm = ev["time"].split(":")
    price = price_rub(ev.get("price_human") or "")
    title = cfg["title"]
    lecturer = lecturer_name(ev)
    # «Лекция <имя в родительном падеже> «Название»»; для фестиваля и
    # других типов формат можно переопределить через `head_line`.
    who = cfg.get("gen") or lecturer
    line = cfg.get("head_line") and nbsp_normalize(cfg["head_line"]) \
        or ("Лекция %s «%s»" % (who, title))
    nxt = dt + datetime.timedelta(days=1)
    city = ev.get("city") or ""
    f = []

    def add(n, name, value):
        f.append({"n": n, "name": name, "value": value})

    add("0", "ID события", proto_id(ev, cfg))
    add("1", "Привязка", binding(ev["date_iso"], ev["time"]))
    add("2", "Дата события", "%s, %s, %s, %s" % (
        dt.strftime("%d.%m.%Y"), city, venue["short"], ev["time"]))
    # Событие с несколькими лекторами (фестивали): в админке у каждого
    # дополнительного лектора своя строка 2.b/2.c, 4.b/4.c, 7.b/7.c
    # с его названием лекции (названия берутся из `author_titles`).
    atitles = cfg.get("author_titles") or {}
    atitles = {k: nbsp_normalize(v) for k, v in atitles.items()}
    for j, a in enumerate(cfg.get("authors") or []):
        if j == 0:
            continue
        suf = "bcdefgh"[j - 1]
        add("2." + suf, "Дата события (лектор %d)" % (j + 1),
            "%s, %s, %s, %s" % (dt.strftime("%d.%m.%Y"), city, venue["short"], ev["time"]))
        add("4." + suf, "Полный заголовок без подзаголовка (лектор %d)" % (j + 1),
            "Лекция %s «%s»" % (a, atitles.get(a) or ""))
        add("7." + suf, "Дата и время (лектор %d)" % (j + 1),
            "%s, %d&nbsp;%s %d&nbsp;года, %s" % (
                WD[dt.weekday()].capitalize(), dt.day, MONTHS[dt.month - 1],
                dt.year, ev["time"]))
    add("2.1", "Начало события", "%d %s %d" % (dt.day, MONTHS[dt.month - 1], dt.year))
    add("2.2", "Время начала", ev["time"])
    add("2.3", "Поставить", "%d %s %d" % (today.day, MONTHS[today.month - 1], today.year))
    add("2.4", "Снять", "%d %s %d" % (nxt.day, MONTHS[nxt.month - 1], nxt.year))
    add("3", "Полный заголовок с подзаголовком", "Medio Modo<br>%s" % line)
    add("4", "Полный заголовок без подзаголовка", line)
    add("5", "Название лекции", title)
    add("6", "Подзаголовок", "Medio Modo")
    tlist = cfg.get("types") or ["Лекция"]
    if isinstance(tlist, str):
        tlist = [tlist]
    add("6.1", "Тип", ", ".join(tlist))
    add("6.2", "Место (из списка)", venue["place"])
    add("6.3", "Лекторий", "Medio Modo")
    # 6.4: значения тематик — из списка ДОСЛОВНО, но в поле 6.4 они
    # приводятся к правилам nbsp («Наука&nbsp;в России»); сам список значений
    # в prototype.json остаётся дословным (его ищет пользователь в админке).
    add("6.4", "Тематики",
        nbsp_normalize(", ".join(cfg.get("topics") or [])) or "—")
    add("7", "Дата и время", "%s, %d&nbsp;%s %d&nbsp;года, %s" % (
        WD[dt.weekday()].capitalize(), dt.day, MONTHS[dt.month - 1], dt.year, ev["time"]))
    add("8", "Место", "%s, %s" % (city, venue["short"]))
    add("9", "Источники", ev["url"])
    add("10", "URL регистрации/покупки билета", ev["url"])
    add("11", "Стоимость", price or "—")
    add("12", "Возрастные ограничения", (ev.get("contacts") or {}).get("age") or "—")
    add("13", "Адрес", venue["address"])
    add("14", "Аудитория", cfg.get("audience") or "Для всех")
    return f


def desc_for(ev, cfg, venue, auths):
    dt = d(ev["date_iso"])
    online = " и&nbsp;ОНЛАЙН" if ev.get("online") else ""
    parts = ['<p class="small"><b>%s, %d&nbsp;%s %d&nbsp;года, %s, %s, %s%s.</b></p>' % (
        WD[dt.weekday()].capitalize(), dt.day, MONTHS[dt.month - 1], dt.year,
        ev["time"], ev.get("city") or "", venue["head"], online)]
    if online:
        # Число в названии площадки («LOFT 13») + союз «и»: валидатор требует
        # nbsp после числа — привязываем «13» к «и» («LOFT 13&nbsp;и&nbsp;ОНЛАЙН»).
        parts[0] = re.sub(r"(\d) +и&nbsp;ОНЛАЙН", r"\1&nbsp;и&nbsp;ОНЛАЙН", parts[0])
    if cfg.get("intro") is not None:
        payload = nbsp_normalize(cfg["intro"])
        parts.append(pas_online(payload) if ev.get("online") else payload)
    else:
        parts.append("<p>Лекция <b><i>%s</i> «%s»</b>%s.</p>"
                     % (cfg.get("gen") or lecturer_name(ev) or "", cfg["title"],
                        " и&nbsp;ОНЛАЙН" if ev.get("online") else ""))
    parts.append("<KLBLOCK eltclub_authors_about/>")
    parts.append('<blockquote class="small">')
    if cfg.get("body"):
        parts.extend(nbsp_normalize(x) for x in cfg["body"])
    else:
        parts.extend(source_body(ev, cfg))
    closer = cfg.get("closer")
    if closer is True:
        # Описание автора ищем в источнике ПО ИМЕНИ, а не по индексу: порядок
        # лекторов в конфиге (программа фестиваля) может отличаться от
        # порядка в блоке «О лекторе» на странице источника.
        src = {x.get("name"): x for x in (ev.get("lecturers") or [])}
        for a in auths:
            s0 = src.get(a["name"]) or {}
            s = author_sentence(a["name"], s0.get("descr") or s0.get("role")
                                or a.get("block_html"))
            if s:
                parts.append(s)
    elif closer:
        parts.append(closer)
    parts.append("</blockquote>")
    return "\n\n".join(parts)


def extra_for(ev, cfg, venue):
    out = []
    price = price_rub(ev.get("price_human") or "")
    if price and not cfg.get("no_buy"):
        out.append('<p>Стоимость билетов: <b>%s</b> <a href="%s" target="_blank">'
                   'Купить билет</a>.</p>' % (price, ev["url"]))
    out.extend(nbsp_normalize(x) for x in (cfg.get("extra") or []))
    if not cfg.get("no_contacts"):
        out.append("<p><b>Контакты организатора:</b> %s.</p>" % PHONE)
    out.append(venue["addr_html"])
    for t in ORG_LINKS:
        out.append(t.format(url=ev["url"]) if "{url}" in t else t)
    return out


LAT = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
       "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
       "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
       "ф": "f", "х": "h", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
       "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}


def photo_file_name(full_name):
    """Поле 7.6: familiya-imya_120.jpg (скилл, разд. 2, п. 7.6)."""
    parts = full_name.split()
    fam, im = parts[-1], parts[0]
    tr = lambda s: "".join(LAT.get(c, c) for c in s.lower())
    return "%s-%s_120.jpg" % (tr(fam), tr(im))


def authors_for(ev, cfg, authors_db):
    out = []
    for name in cfg.get("authors") or [lecturer_name(ev)]:
        rec = None
        for a in authors_db:
            if a.get("query") == name:
                rec = a
                break
        if rec is None or not rec.get("found"):
            block = (cfg.get("new_authors") or {}).get(name, "")
            photo = (cfg.get("new_photos") or {}).get(name, "")
            inv = "%s %s" % (name.split()[-1], name.split()[0])
            out.append({
                "name": name,
                "photo": photo,
                "on_elementy": False,
                "block_html": block,
                "fields": [
                    {"n": "7.1", "name": "Инвертированное имя", "value": inv},
                    {"n": "7.2", "name": "Стандартное имя", "value": name},
                    {"n": "7.4", "name": "Описание автора", "value": block},
                    {"n": "7.5", "name": "Фото из источников", "value": photo or "—"},
                    {"n": "7.6", "name": "Файл фотографии",
                     "value": photo_file_name(name)},
                ],
            })
            continue
        pre = rec.get("pretitle") or name
        inv = pre
        out.append({
            "name": name,
            "photo": rec.get("photo") or "",
            "on_elementy": True,
            "block_html": rec.get("block_html") or "",
            "fields": [
                {"n": "7.1", "name": "Инвертированное имя", "value": inv},
                {"n": "7.2", "name": "Стандартное имя", "value": name},
                {"n": "7.3", "name": "Полное имя", "value": pre},
                {"n": "7.4", "name": "Описание автора", "value": rec.get("block_html") or ""},
                {"n": "7.5", "name": "Фото из источников", "value": rec.get("photo") or ""},
            ],
        })
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    data = load_module(DATA_FILE, "mm_proto_data")
    events = json.load(io.open(EVENTS_JSON, encoding="utf-8"))
    if isinstance(events, dict):
        events = events.get("events", events)
    if isinstance(events, dict):
        events = list(events.values())
    ev_by_slug = {e["slug"]: e for e in events}
    authors_db = json.load(io.open(AUTHORS_JSON, encoding="utf-8"))
    today = datetime.date.today()

    # Площадки: значения из списка «Элементов» (place) и тексты, которые мы
    # пишем сами (head, short, address), приводятся к правилам nbsp. Блок
    # addr_html нормализуется тоже, кроме скопированных с «Элементов»
    # дословных блоков (у них addr_verbatim = True).
    for v in data.VENUES.values():
        for k in ("place", "short", "head", "address"):
            if v.get(k):
                v[k] = nbsp_normalize(v[k])
        if v.get("addr_html") and not v.get("addr_verbatim"):
            v["addr_html"] = nbsp_normalize(v["addr_html"])

    slugs = args or sorted(data.EVENTS)
    made = 0
    for slug in slugs:
        cfg = data.EVENTS.get(slug)
        if cfg is None:
            print("НЕТ ДАННЫХ: %s" % slug)
            continue
        ev = ev_by_slug.get(slug)
        if ev is None:
            print("НЕТ СОБЫТИЯ: %s" % slug)
            continue
        venue = data.VENUES[cfg["venue"]]
        auths = authors_for(ev, cfg, authors_db)
        # Название и прочие прозаические поля приводим к правилам nbsp
        # (союз «и» в заголовке — обычное дело: «Кишечник и мозг»).
        cfg = dict(cfg)
        cfg["title"] = nbsp_normalize(cfg["title"])
        if cfg.get("annot"):
            cfg["annot"] = nbsp_normalize(cfg["annot"])
        annot = cfg.get("annot") or "Лекция %s «%s» в&nbsp;лектории «Medio Modo»." % (
            cfg.get("gen") or lecturer_name(ev), cfg["title"])
        if ev.get("online"):
            annot = pas_online(annot)
        p = {
            "id": proto_id(ev, cfg),
            "lectory": "Medio Modo",
            "date_iso": ev["date_iso"],
            "time_start": ev["time"],
            "time_end": cfg.get("time_end", ""),
            "city": ev.get("city") or "",
            "place": venue["short"],
            "lecturer": cfg.get("lecturer") or lecturer_name(ev),
            "title": cfg["title"],
            "types": ([cfg["types"]] if isinstance(cfg.get("types"), str)
                      else (cfg.get("types") or ["Лекция"])),
            "topics": cfg.get("topics") or [],
            "price_short": (price_rub(ev.get("price_human") or "") or "").replace("&nbsp;", " "),
            "annot": annot,
            "url": ev["url"],
            "sources": cfg.get("sources") or [ev["url"]],
            "fields": fields_for(ev, cfg, venue, today),
            "desc_html": desc_for(ev, cfg, venue, auths),
            "extra_html": extra_for(ev, cfg, venue),
            "authors": auths,
            # Дословная вставка с «Элементов» (скилл разд. 3г): фрагмент должен
            # СОВПАДАТЬ с текстом прототипа побайтово, иначе валидатор не находит
            # вхождение. Поэтому берём block_html как есть (со ссылками и тегами):
            # оголённый текст с <a href> внутри не был бы непрерывным.
            "verbatim_fragments": cfg.get("verbatim_fragments")
                or [a["block_html"] for a in auths
                    if a.get("on_elementy") and a.get("block_html")],
            "photo_file": "",
            "notes": cfg.get("notes", ""),
        }
        path = os.path.join(PROTO_DIR, p["id"], "prototype.json")
        if check:
            print("=" * 70)
            print(json.dumps(p, ensure_ascii=False, indent=1))
            continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(p, f, ensure_ascii=False, indent=1)
            f.write("\n")
        made += 1
        print("OK %s -> %s" % (slug, p["id"]))
    if not check:
        print("\nГотово прототипов: %d" % made)
    return 0


if __name__ == "__main__":
    sys.exit(main())
