# -*- coding: utf-8 -*-
"""Дифф календаря «Архэ» с прототипами и «Элементами» (рекуррентный проход).

Отвечает на вопрос «что нового появилось в Архэ» за один запуск:

  1. читает календарь arhe.msk.ru (tools/scrape_arhe.py);
  2. отмечает события, у которых уже есть прототип в data/prototypes/
     (сверка по Timepad ID: TP-<id> — ключ прототипа «Архэ»);
  3. помечает ДУБЛИ по правилу «дубль = совпадение даты»: ищет событие
     той же даты в data/events.json (снимок «Элементов»);
  4. помечает страницы-курсы (не лекции) и события, которые по правилам
     карточки «Архэ» НЕ берём (Рябов — декабристы, Рябчиков — музыка);
  5. остальное выводит как КАНДИДАТОВ (для ручного разбора/согласования).

Использование:
    python -X utf8 tools\\arhe_diff.py                -- от сегодня
    python -X utf8 tools\\arhe_diff.py --from 2026-10-19 --to 2026-11-30
    python -X utf8 tools\\arhe_diff.py --json out.json -- сырой результат
    python -X utf8 tools\\arhe_diff.py --refresh      -- заново качать календарь

Календарь кэшируется в data/raw/arhe_calendar.json (.gitignore);
без --refresh берётся кэш, если ему меньше суток.
Код возврата: 0 — ок.
"""
import argparse
import datetime
import glob
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrape_arhe as SA                       # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
CAL_CACHE = os.path.join(RAW, "arhe_calendar.json")

# Не берём по карточке «Архэ» (решение 10.10.2026): чистая история без
# связи с естественными науками и искусство/музыка. Фильтр — по автору.
SKIP_RE = re.compile(r"Рябов|Рябчиков", re.I)
# Страницы курсов (не лекции) — в календаре есть сами по себе.
COURSE_TITLE_RE = re.compile(r"^Курс\b", re.I)


def load_calendar(refresh=False):
    if not refresh and os.path.isfile(CAL_CACHE):
        age = datetime.datetime.now().timestamp() - os.path.getmtime(CAL_CACHE)
        if age < 24 * 3600:
            with io.open(CAL_CACHE, encoding="utf-8") as f:
                return json.load(f)
    # полный календарь (без --from/--to): + последующие месяцы через
    # tribe-bar-date, т.к. одна страница отдаёт только ближайшие события
    events, seen = [], set()
    for date_arg in ("", "&tribe-bar-date=2026-11-15", "&tribe-bar-date=2026-12-15"):
        page = SA.fetch(SA.CAL_URL + date_arg)
        for e in SA.parse_calendar(page):
            if e["tip"] in seen:
                continue
            seen.add(e["tip"])
            e["slug_url"] = e.get("slug_url") or ""
            events.append(e)
    # обогащение: URL страницы + timepad id (по каждой странице события)
    out = []
    for e in sorted(events, key=lambda x: (x["date"], x["tip"])):
        src = e["slug_url"] or (SA.EVENT_URL % e["tip"])
        try:
            body = SA.fetch(src)
        except Exception as exc:               # noqa: BLE001
            sys.stderr.write("  (%s) ошибка: %s\n" % (e["title"][:40], exc))
            body = ""
        tp_id, cust = SA.parse_timepad(body) if body else (None, None)
        e["arhe_url"] = SA.resolve_arhe_url(e["tip"], e["slug_url"]) if body else src
        e["timepad_id"] = tp_id
        e["timepad_url"] = SA.timepad_url(tp_id, cust) if tp_id else ""
        out.append(e)
    os.makedirs(RAW, exist_ok=True)
    with io.open(CAL_CACHE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


def load_prototype_ids():
    """Timepad ID всех существующих прототипов «Архэ»."""
    ids = set()
    for p in glob.glob(os.path.join(ROOT, "data", "prototypes", "*", "prototype.json")):
        name = os.path.basename(os.path.dirname(p))
        if name.startswith("TP-"):
            ids.add(name[3:])
    return ids


def load_elementy_dates(refresh=False):
    """Индекс будущих событий «Элементов» по дате ('12.11').

    Источник — data/raw/elementy/events_list.json (полный список
    предстоящих, его же читает check_elementy_by_date.py); если кэша нет —
    строим из data/events.json. Значение дня — список
    {"id", "title", "lecturer"}.
    """
    import check_elementy_by_date as CED       # свой же кэш и парсер
    by_date = {}
    try:
        events = CED.load(refresh)
    except Exception:                          # noqa: BLE001
        events = None
    if not events:
        path = os.path.join(ROOT, "data", "events.json")
        try:
            with io.open(path, encoding="utf-8") as f:
                data = json.load(f)
            events = data if isinstance(data, list) else data.get("events", [])
        except Exception:                      # noqa: BLE001
            return by_date
    for ev in events:
        d = str(ev.get("date_dot") or "")
        if not d and ev.get("date_iso"):
            d = _dot(str(ev["date_iso"])[:10])
        if d:                                   # '12.11' — ключ как у календаря
            by_date.setdefault(d, []).append({
                "id": str(ev.get("id", "")),
                "title": str(ev.get("title") or ""),
                "lecturer": str(ev.get("lecturer") or ""),
            })
    return by_date


def _tokens(title):
    """Значимые слова заголовка для сопоставления (без предлогов и т.п.)."""
    t = re.sub(r"[«»\"':;,.!?()]", " ", title.lower())
    return {w for w in t.split() if len(w) >= 4 and w not in
            {"лекция", "онлайн", "научно", "популярный", "лекторий"}}


def _same_title(t1, t2):
    """Похожие заголовки? Дубль требует И даты, И заголовка (правило
    «дубль = совпадение даты, а не похожего заголовка» — заголовок один,
    но подтверждаем датой). Порог — пересечение значимых слов."""
    a, b = _tokens(t1), _tokens(t2)
    if not a or not b:
        return False
    inter = len(a & b)
    return inter / min(len(a), len(b)) >= 0.6


def _same_author(cal_title, el_lecturer):
    """Автор из заголовка календаря («Онлайн-лекция Михаила Магида «…»»)
    против lecturer «Элементов» («Михаил Магид»).

    Сравниваем ТОЛЬКО фамилию (последнее слово у «Элементов») — иначе
    имя «Александр» совпало бы у разных людей (Бутягин/Гетлиннг).
    Общее начало ≥5 ловит Магид/Магида, Квартальнов/Квартальнова."""
    if not el_lecturer:
        return False
    surname = el_lecturer.strip().split()[-1].lower()
    if len(surname) < 5:
        return False
    return any(w[:5] == surname[:5]
               for w in re.findall(r"[А-Яа-яЁё]{5,}", cal_title.lower()))


def _dot(date_iso):
    """2026-11-12 -> 12.11 (ключевой вид даты «Элементов»)."""
    return "%s.%s" % (date_iso[8:10], date_iso[5:7])


def classify(ev, proto_ids, elt_by_date):
    """Статус события: proto | dup | dup? | course | skip | NEW.

    dup  — в тот же день на «Элементах» событие с ПОХОЖИМ заголовком;
    dup? — в тот же день событие ТОГО ЖЕ АВТОРА, но другой заголовок:
           нужно сверить глазами (мог быть переименован).
    Совпадения одной даты недостаточно: в любой день на «Элементах» есть
    чужие события.
    """
    if ev["timepad_id"] and ev["timepad_id"] in proto_ids:
        return "proto"
    day = elt_by_date.get(_dot(ev["date"][:10]), [])
    for el in day:
        if _same_title(ev["title"], el["title"]):
            return "dup"
    for el in day:
        if _same_author(ev["title"], el.get("lecturer")):
            return "dup?"
    if COURSE_TITLE_RE.match(ev["title"]):
        return "course"
    if SKIP_RE.search(ev["title"]):
        return "skip"
    return "NEW"


def main():
    ap = argparse.ArgumentParser(description="Дифф календаря «Архэ»")
    ap.add_argument("--from", dest="date_from", default="", metavar="YYYY-MM-DD")
    ap.add_argument("--to", dest="date_to", default="", metavar="YYYY-MM-DD")
    ap.add_argument("--json", dest="json_out", metavar="FILE")
    ap.add_argument("--refresh", action="store_true", help="заново качать календарь")
    args = ap.parse_args()

    events = load_calendar(refresh=args.refresh)
    proto_ids = load_prototype_ids()
    elt_by_date = load_elementy_dates(refresh=args.refresh)

    if args.date_from:
        events = [e for e in events if e["date"][:10] >= args.date_from]
    if args.date_to:
        events = [e for e in events if e["date"][:10] <= args.date_to]

    rows = []
    for e in events:
        st = classify(e, proto_ids, elt_by_date)
        day = elt_by_date.get(_dot(e["date"][:10]), [])
        if st == "dup":
            matched = [x for x in day if _same_title(e["title"], x["title"])]
        elif st == "dup?":
            matched = [x for x in day
                       if _same_author(e["title"], x.get("lecturer"))]
        else:
            matched = []
        rows.append({"status": st, "date": e["date"][:10],
                     "title": e["title"], "timepad_id": e.get("timepad_id"),
                     "arhe_url": e.get("arhe_url", ""),
                     "timepad_url": e.get("timepad_url", ""),
                     "dup_of": matched})

    order = {"NEW": 0, "dup?": 1, "dup": 2, "course": 3, "skip": 4,
             "proto": 5}
    rows.sort(key=lambda r: (order[r["status"]], r["date"]))

    print("ДИФФ КАЛЕНДАРЯ «АРХЭ» — %d событий" % len(rows))
    print("  прототипов уже есть: %d | дублей: %d | сверить (тот же автор"
          " в этот день): %d | страниц курсов: %d | не берём: %d |"
          " КАНДИДАТОВ: %d"
          % (sum(1 for r in rows if r["status"] == "proto"),
             sum(1 for r in rows if r["status"] == "dup"),
             sum(1 for r in rows if r["status"] == "dup?"),
             sum(1 for r in rows if r["status"] == "course"),
             sum(1 for r in rows if r["status"] == "skip"),
             sum(1 for r in rows if r["status"] == "NEW")))
    labels = {"NEW": "КАНДИДАТ", "dup?": "СВЕРИТЬ ", "dup": "ДУБЛЬ   ",
              "course": "КУРС    ", "skip": "НЕ БЕРЁМ", "proto": "ПРОТОТИП"}
    print()
    for r in rows:
        print("%s %s | %s" % (labels[r["status"]], r["date"], r["title"][:95]))
        if r["status"] in ("NEW", "dup?"):
            print("             timepad: %s" % (r["timepad_url"] or "(нет)"))
            print("             архэ:    %s" % (r["arhe_url"] or "—"))
        if r["status"] in ("dup", "dup?"):
            for x in r["dup_of"]:
                print("             elementy: %s %s | %s"
                      % (x["id"], x.get("lecturer") or "", x["title"]))

    if args.json_out:
        with io.open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
        print("\nJSON: %s" % os.path.abspath(args.json_out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
