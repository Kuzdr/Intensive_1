# -*- coding: utf-8 -*-
"""Общая механика прототипов «Научного календаря» (без привязки к источнику).

Здесь живёт только то, что одинаково для ЛЮБОГО лектория: типографика
(nbsp/«ё»/тире), расчёт поля 1 «Привязка», даты, цены, сборка полей автора
(7.1–7.6), имя файла фотографии, чтение/запись `prototype.json` и запуск
валидатора `tools/check_prototype.py`.

Разбор источников — в `tools/sources/*` (по движку сайта, а не по лекторию),
а сборка конкретного прототипа — в драйвере лектория (напр.
`tools/arhe_prototype.py`). Драйверы не дублируют механику: они вызывают
функции отсюда.

Раньше эта логика была внутри `tools/mm_prototype.py`; теперь она вынесена,
чтобы ею пользовались все лектории (Medio Modo переведём на неё отдельно).
"""
import datetime
import gzip
import html as html_mod
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO_DIR = os.path.join(ROOT, "data", "prototypes")
CHECK_PROTOTYPE = os.path.join(ROOT, "tools", "check_prototype.py")

WD = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота",
      "воскресенье"]
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
MONTHS_NOM = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
              "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]

# Латиница для имени файла фотографии (поле 7.6).
LAT = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
       "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
       "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
       "ф": "f", "х": "kh", "ц": "c", "ч": "ch", "ш": "sh", "щ": "sch",
       "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}

DASH = "—&nbsp;"
CYR = "а-яёА-ЯЁ"
ONE_LETTER = "вскоуиа"
ABBR_DOT = ("д", "ул", "корп", "стр", "г", "им", "пр", "пер", "бул", "наб", "ш")
# Слова, где «ё» не пишется (список согласован с check_prototype.py).
YO_INVARIANTS = ("ещё", "её", "учёный", "учёные", "идёт", "вперёд", "пойдёт",
                 "пройдёт", "разберёт", "разберём")
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI",
         "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX")
TAG_RE = re.compile(r"<[^>]+>")
INVISIBLE = re.compile("[\\u200b-\\u200f\\u202a-\\u202e\\ufeff\\u2060\\u00ad]")


UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def http_get(url, cache_path=None, refresh=False, tries=3, min_size=2000):
    """GET с кэшем на диск: если файл уже есть — без повторной загрузки.

    Кэш решает жалобу «одни и те же страницы качаются по нескольку раз за
    проход»: скачали один раз — дальше читаем с диска.
    """
    if cache_path and os.path.isfile(cache_path) and not refresh \
            and os.path.getsize(cache_path) >= min_size:
        return io.open(cache_path, encoding="utf-8", errors="replace").read()
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
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                io.open(cache_path, "w", encoding="utf-8", newline="").write(t)
            return t
        except Exception as e:      # noqa: BLE001 - сеть бывает капризной
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise IOError("не удалось скачать %s: %r" % (url, last))


# ------------------------------------------------------------------ даты

def d(s):
    return datetime.date(*map(int, s.split("-")))


def ru_date(dt):
    return "%d %s %d" % (dt.day, MONTHS[dt.month - 1], dt.year)


def weekday_ru(dt):
    return WD[dt.weekday()].capitalize()


def today():
    return datetime.date.today()


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
    """Поле 1: ГГГГ.ММ.ДД + цифра часа + (для 13–20 ч) цифра минут."""
    dt = d(date_iso)
    hh, mm = int(time_str[:2]), int(time_str[3:5])
    return "%04d.%02d.%02d%s" % (dt.year, dt.month, dt.day, binding_index(hh, mm))


# ------------------------------------------------------------------ цены

def price_rub(price_human):
    """«от 1200 ₽» -> «от 1200&nbsp;руб.» (None, если не распознано)."""
    m = re.match(r"^\s*(от\s+)?([\d\s\u00a0]+)\s*₽\s*$", price_human or "")
    if not m:
        return None
    num = re.sub(r"[\s\u00a0]+", "", m.group(2))
    lead = "от " if m.group(1) else ""
    return "%s%s&nbsp;руб." % (lead, num)


# ------------------------------------------------------------------ HTML-текст

def denoise(s):
    s = INVISIBLE.sub("", s or "")
    return re.sub(r"[ \t]{2,}", " ", s).strip()


def _visible_segments(t):
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
    """Расстановка nbsp по правилам скилла proofreading (разд. 2).

    Весь nbsp снимается и ставится заново: после однобуквенных предлогов/союзов,
    перед «—», между инициалами, после адресных сокращений, между числом и
    словом, вокруг римских цифр. «ё» в словах-инвариантах убирается. Текст
    внутри тегов (href, class) не трогается.
    """
    t = INVISIBLE.sub("", t or "")
    t = t.replace("&nbsp;", " ").replace("\u00a0", " ")
    t = re.sub(r"[ \t]{2,}", " ", t)

    def fix(chunk):
        chunk = re.sub(r"(?<![%s])([%s]) (?=[%s])" % (CYR, ONE_LETTER, CYR),
                       r"\1&nbsp;", chunk)
        chunk = re.sub(r"([%s0-9»)]+) —" % CYR, r"\1&nbsp;—", chunk)
        chunk = chunk.replace("—&nbsp;", "— ")
        chunk = re.sub(r"(?<![А-ЯЁ])([А-ЯЁ])\. ([А-ЯЁ])\.", r"\1.&nbsp;\2.", chunk)
        chunk = re.sub(r"(?<![А-ЯЁ])([А-ЯЁ])\. ([А-ЯЁ][а-яё]{2,})", r"\1.&nbsp;\2", chunk)
        chunk = re.sub(r"\b(%s)\. (?=[0-9А-Яа-яЁё])" % "|".join(ABBR_DOT),
                       r"\1.&nbsp;", chunk)
        chunk = re.sub(r"(?<=[0-9]) (?=[А-Яа-яЁё])", "&nbsp;", chunk)
        chunk = re.sub(r"(?<=Лекция) (?=[0-9])", "&nbsp;", chunk)
        rom = "|".join(sorted(ROMAN, key=len, reverse=True))
        chunk = re.sub(r"(?<=[%s0-9]) (%s)\b" % (CYR, rom), "&nbsp;\\1", chunk)
        chunk = re.sub(r"\b(%s) " % rom, "\\1&nbsp;", chunk)
        for w in YO_INVARIANTS:
            cap = w[0].upper() + w[1:]
            chunk = re.sub(r"\b%s\b" % cap, cap.replace("ё", "е"), chunk)
            chunk = re.sub(r"\b%s\b" % w, w.replace("ё", "е"), chunk)
        return chunk

    out = []
    for s, e, is_tag in _visible_segments(t):
        out.append(t[s:e] if is_tag else fix(t[s:e]))
    return "".join(out)


def pas_online(txt):
    """Добавляет « и ОНЛАЙН» перед финальной точкой HTML-абзаца/строки."""
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
    """Текст источника -> список HTML-абзацев; перечисления «—» -> <ul><li>."""
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


def html_block(html, marker):
    """HTML-блок: <div>, в котором встречается `marker`, до парного </div>."""
    i = html.find(marker)
    if i < 0:
        return ""
    s = html.rfind("<div", 0, i)
    depth = 0
    j = s
    while j < len(html):
        m = re.compile(r"<(/?)div\b[^>]*>").search(html, j)
        if not m:
            break
        depth += -1 if m.group(1) == "/" else 1
        j = m.end()
        if depth == 0:
            return html[s:j]
    return ""


def html_to_text(s):
    s = re.sub(r"<br\s*/?>", "\n", s or "")
    s = re.sub(r"</(?:p|div|li|h\d)>", "\n", s)
    s = TAG_RE.sub("", s)
    s = html_mod.unescape(s)
    return denoise(re.sub(r"\n\s*\n+", "\n", s))


def text_blocks(s):
    """Верхнеуровневые блоки HTML по порядку: <p>, <ul>, <ol>, заголовки.

    Нужно, чтобы из «сырого» тела источника (с вложенными div-обёртками)
    аккуратно вычленить абзацы и списки — без обёрток и вложенного мусора.
    """
    out = []
    pat = re.compile(r"<(p|ul|ol|h[1-6])\b[^>]*>.*?</\1>", re.S | re.I)
    for m in pat.finditer(s or ""):
        blk = re.sub(r"\s+", " ", m.group(0)).strip()
        blk = re.sub(r'>\s+<', '><', blk)
        out.append(blk)
    return out


# ------------------------------------------------------------------ поля

def photo_file_name(full_name):
    """Поле 7.6: familiya-imya_120.jpg."""
    parts = full_name.split()
    fam, im = parts[-1], parts[0]
    tr = lambda s: "".join(LAT.get(c, c) for c in s.lower())
    return "%s-%s_120.jpg" % (tr(fam), tr(im))


def field(n, name, value):
    return {"n": n, "name": name, "value": value}


def date_fields(fields, date_iso, time_start, time_end, city, place_short, today_dt):
    """Добавляет поля 2, 2.1–2.4, 7 — механические даты/время."""
    dt = d(date_iso)
    nxt = dt + datetime.timedelta(days=1)
    fields.append(field("2", "Дата события", "%s, %s, %s, %s" % (
        dt.strftime("%d.%m.%Y"), city, place_short, time_start)))
    fields.append(field("2.1", "Начало события", ru_date(dt)))
    fields.append(field("2.2", "Время начала", time_start))
    fields.append(field("2.3", "Поставить", ru_date(today_dt)))
    fields.append(field("2.4", "Снять", ru_date(nxt)))
    tr = "%s–%s" % (time_start, time_end) if time_end else time_start
    fields.append(field("7", "Дата и время", "%s, %d&nbsp;%s %d&nbsp;года, %s" % (
        weekday_ru(dt), dt.day, MONTHS[dt.month - 1], dt.year, tr)))


def lead_field(fields, date_iso, time_start, time_end, city, place, online):
    """Первое поле описания — абзац-шапка <p class="small">."""
    dt = d(date_iso)
    place_head = place if online else re.sub(r" и&nbsp;ОНЛАЙН$", "", place)
    onl = " и&nbsp;ОНЛАЙН" if online else ""
    return '<p class="small"><b>%s, %d&nbsp;%s %d&nbsp;года, %s, %s, %s%s.</b></p>' % (
        weekday_ru(dt), dt.day, MONTHS[dt.month - 1], dt.year,
        ("%s–%s" % (time_start, time_end)) if time_end else time_start,
        city, place_head, onl)


def author_new_fields(name, block_html, photo):
    """Поля 7.x для НОВОГО автора (нет на «Элементах»)."""
    inv = "%s %s" % (name.split()[-1], name.split()[0])
    return [
        field("7.1", "Инвертированное имя", inv),
        field("7.2", "Стандартное имя", name),
        field("7.4", "Описание автора", block_html),
        field("7.5", "Фото из источников", photo or "—"),
        field("7.6", "Файл фотографии", photo_file_name(name)),
    ]


def author_known_fields(name, full_name, block_html, photo):
    """Поля 7.x для автора С «Элементов» (7.6 не заполняется)."""
    return [
        field("7.1", "Инвертированное имя", full_name or name),
        field("7.2", "Стандартное имя", name),
        field("7.3", "Полное имя", full_name or name),
        field("7.4", "Описание автора", block_html),
        field("7.5", "Фото из источников", photo or ""),
    ]


# ------------------------------------------------------------------ запись/проверка

def write_prototype(proto):
    path = os.path.join(PROTO_DIR, proto["id"], "prototype.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(proto, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return path


def validate(path, fix=False, only=None):
    """Запускает tools/check_prototype.py. Возвращает (rc, текст вывода)."""
    cmd = [sys.executable, "-X", "utf8", CHECK_PROTOTYPE, "--json", path]
    if fix:
        cmd.append("--fix")
    if only:
        cmd += ["--only", only]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


if __name__ == "__main__":
    print(__doc__)
