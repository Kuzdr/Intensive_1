# -*- coding: utf-8 -*-
r"""Сводка кандидатов мониторинга ВДНХ по сохранённым снимкам (26.11.2026).

Не делает сетевых запросов: читает только data/raw/cdp/*.json,
data/events.json и data/prototypes/*/prototype.json.

    python -X utf8 tools\vdnh_monitor_report.py
    python -X utf8 tools\vdnh_monitor_report.py --dry-run   # только проверить
"""
import difflib
import html as H
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "cdp")
MON = os.path.join(ROOT, "data", "monitor")
SWEEP = os.path.join(ROOT, "data", "sweep")
TODAY = date(2026, 11, 26)
DRY = "--dry-run" in sys.argv[1:]   # проверить классификацию, ничего не перезаписать
MONTHS = {
    "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
    "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11,
    "декабря": 12,
}


def load(path):
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def registry_ids(path):
    """(VD|TP, id) → статус из операционного реестра обхода.

    Решения пользователя хранятся в `data/sweep/known_events.json`; без этой
    сверки отвергнутые лекции каждый раз снова попадали бы в «Нужно».
    """
    if not os.path.isfile(path):
        return {}
    reg = load(path)
    out = {}
    for rec in reg.get("lectories", {}).get("vdnh", {}).get("events", []):
        m = re.match(r"^(VD|TP)-(\d+)", rec.get("key", ""))
        if m:
            out[(m.group(1), m.group(2))] = rec.get("status", "")
    return out


def norm(s):
    s = H.unescape(s or "").lower().replace("\xa0", " ")
    s = re.sub(r"\b(лекция|лекции|лекцию|лекции-концерт|лекция-презентация)\b", " ", s)
    s = re.sub(r"[«»\"“”‘’'()\[\]:.,!?;—–\-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def sim(a, b):
    aa, bb = norm(a), norm(b)
    if not aa or not bb:
        return 0.0
    return difflib.SequenceMatcher(None, aa, bb).ratio()


def match(a, b):
    """Совпадение названий: вложенность значимых слов или высокая похожесть."""
    ta, tb = set(norm(a).split()), set(norm(b).split())
    if not ta or not tb:
        return False
    if len(ta) >= 2 and ta <= tb:
        return True
    if len(tb) >= 2 and tb <= ta:
        return True
    return len(ta & tb) / float(len(ta | tb)) >= 0.72 or sim(a, b) >= 0.85


def parse_vdnh_date(s, time_text=""):
    low = (s or "").lower()
    d = TODAY
    if "сегодня" in low:
        d = TODAY
    elif "завтра" in low and "послезавтра" not in low:
        d = TODAY + timedelta(days=1)
    elif "послезавтра" in low:
        d = TODAY + timedelta(days=2)
    else:
        m = re.search(r"\b(\d{1,2})\s+([а-яё]+)", low)
        if m and m.group(2) in MONTHS:
            month, day = MONTHS[m.group(2)], int(m.group(1))
            year = TODAY.year
            if (month, day) < (TODAY.month, TODAY.day):
                year += 1
            d = date(year, month, day)
    tm = re.search(r"(\d{2}:\d{2})", time_text or s or "")
    return d.strftime("%d.%m.%Y"), (tm.group(1) if tm else "")


def parse_tp_date(s):
    low = (s or "").lower()
    d = None
    if "ближайшее" in low:
        m = re.search(r"ближайшее\s+(\d{1,2})\s+([а-яё]+)", low)
        if m and m.group(2) in MONTHS:
            month, day = MONTHS[m.group(2)], int(m.group(1))
            year = TODAY.year
            if (month, day) < (TODAY.month, TODAY.day):
                year += 1
            d = date(year, month, day)
    else:
        m = re.search(r"\b(\d{1,2})\s+([а-яё]+)", low)
        if m and m.group(2) in MONTHS:
            month, day = MONTHS[m.group(2)], int(m.group(1))
            year = TODAY.year
            if (month, day) < (TODAY.month, TODAY.day):
                year += 1
            d = date(year, month, day)
    tm = re.search(r"(?:c|с)\s+(\d{2}:\d{2})", low)
    end = re.search(r"до\s+(\d{2}:\d{2})", low)
    return (d.strftime("%d.%m.%Y") if d else ""), (tm.group(1) if tm else ""), (
        end.group(1) if end else "")


def prelim(title, badges=(), url=""):
    t = title.lower()
    b = " ".join(badges).lower()
    if ("концерт" in b or "концерт" in t) and "лекция-концерт" not in t:
        return "Не нужно", "концерт"
    if "спектакл" in t or "спектакл" in b:
        return "Не нужно", "спектакль"
    if "детск" in t or "детям" in b:
        return "Не нужно", "детская программа"
    if "мастер-класс" in t or "мастер-класс" in b:
        return "Не нужно", "мастер-класс"
    if "серия событий" in t or "экзамен" in t or "гидов-переводчиков" in t:
        return "Не нужно", "экскурсия/экзамен для узкой группы"
    if "обзорная экскурсия" in t and "лекц" not in t:
        return "Не нужно", "обзорная экскурсия"
    if "с живым саундтреком" in t:
        return "Не нужно", "концерт/саундтрек"
    if "творческая встреча" in t:
        return "Сомнительные", "творческая встреча, не лекция — нужны критерии/подтверждение"
    if "дегустац" in t:
        return "Сомнительные", "дегустация — нужны критерии/подтверждение"
    if "лекция-концерт" in t:
        return "Сомнительные", "смешанный формат — нужны критерии/подтверждение"
    if "лекц" in t or "лекции" in b or "экскурсия-лекция" in t or "экскурсия - лекция" in t:
        return "Нужно", ""
    return "Сомнительные", "тип неясен — нужны критерии/подтверждение"


def main():
    site = load(os.path.join(ROOT, "data", "events.json"))
    reg_status = registry_ids(os.path.join(SWEEP, "known_events.json"))
    protos = []
    pdir = os.path.join(ROOT, "data", "prototypes")
    for name in os.listdir(pdir):
        p = os.path.join(pdir, name, "prototype.json")
        if os.path.isfile(p):
            x = load(p)
            protos.append((name, x.get("title", ""), x.get("url", "")))

    records = []
    # vdnh.ru: афиша с фильтром «Лекции» + страница Лектория
    for tag, source in (("afisha", "vdnh_site"), ("lektorij", "vdnh_site")):
        data = load(os.path.join(RAW, "vdnh_events_%s_cards.json" % tag))
        for c in data["cards"]:
            d, tm = parse_vdnh_date(c.get("date", ""), c.get("date", ""))
            title = c.get("title", "")
            cls, why = prelim(title, c.get("badges", []))
            records.append({
                "source": source, "source_tag": tag,
                "external_id": re.search(r"/events/(\d+)", c.get("href", "")).group(1)
                if re.search(r"/events/(\d+)", c.get("href", "")) else "",
                "url": "https://vdnh.ru" + c.get("href", ""),
                "title": title, "date": d, "time": tm,
                "class": cls, "why": why, "links": ["https://vdnh.ru" + c.get("href", "")],
            })
    # Timepad ВДНХ
    tp = load(os.path.join(RAW, "vdnh_timepad_all_cards.json"))
    source_map = {"lektorij": "vdnh_lektorij_timepad", "cosmos": "vdnh_cosmos_timepad",
                  "slovo": "vdnh_slovo_timepad", "atom": "vdnh_atom_lab_timepad",
                  "biotech": "vdnh_muzey_biotech_timepad"}
    for tag, data in tp.items():
        for c in data["cards"]:
            if c.get("past"):
                continue
            d, tm, end = parse_tp_date(c.get("date", ""))
            title = c.get("title", "")
            cls, why = prelim(title)
            records.append({
                "source": source_map[tag], "source_tag": tag,
                "external_id": str(c["id"]), "url": c["url"], "title": title,
                "date": d, "time": tm, "time_end": end,
                "class": cls, "why": why, "links": [c["url"]],
            })

    # Объединяем дубли между источниками по названию+дате.
    groups = []
    for r in records:
        found = None
        for g in groups:
            if match(r["title"], g["title"]) and r["date"] == g["date"]:
                found = g
                break
        if found:
            for link in r["links"]:
                if link not in found["links"]:
                    found["links"].append(link)
            if r["time"] and not found["time"]:
                found["time"] = r["time"]
            found.setdefault("ids", {})[r["source"]] = r["external_id"]
            if r["class"] != "Не нужно" and found["class"] == "Не нужно":
                found["class"], found["why"] = r["class"], r["why"]
        else:
            r["ids"] = {r["source"]: r["external_id"]}
            groups.append(r)

    # Сверка с сайтом и прототипами.
    for g in groups:
        site_hits = [x for x in site if match(g["title"], x.get("title", ""))]
        same_date = [x for x in site_hits
                     if x.get("date_dot", "")[:5] == g["date"][:5]]
        g["published"] = same_date[0]["id"] if same_date else ""
        g["site_other_date"] = [(x["id"], x.get("date_dot")) for x in site_hits if not same_date]
        proto_hits = [n for n, t, u in protos
                      if match(g["title"], t) or
                      any(str(i) == n.split("-")[-1] for i in
                          re.findall(r"\d+", " ".join(g["links"])))]
        g["prototype"] = proto_hits[0] if proto_hits else ""
        # Сверяем и с операционным реестром: решение пользователя по лекции
        # не должно теряться при следующем проходе sources.
        prev = []
        deferred = False
        for src, eid in sorted(g.get("ids", {}).items()):
            eid = str(eid)
            prefix = "VD" if src == "vdnh_site" else "TP"
            st = reg_status.get((prefix, eid), "")
            if st:
                prev.append("%s-%s (%s)" % (prefix, eid, st))
                if st == "undecided":
                    deferred = True
        g["previous"] = prev
        if g["published"] or g["prototype"]:
            g["final"] = "Уже обработано"
        elif deferred:
            g["final"] = "Не решено"
            g["why"] = "отложено решение пользователя: " + ", ".join(prev)
        elif prev:
            g["final"] = "Уже обработано"
            g["why"] = "ранее рассмотрено: " + ", ".join(prev)
        else:
            g["final"] = g["class"]

    need = sorted([g for g in groups if g["final"] == "Нужно"],
                  key=lambda x: (x["date"], x["time"]))
    doubt = sorted([g for g in groups if g["final"] == "Сомнительные"],
                   key=lambda x: (x["date"], x["time"]))
    notneed = sorted([g for g in groups if g["final"] == "Не нужно"],
                     key=lambda x: (x["date"], x["time"]))
    done = sorted([g for g in groups if g["final"] == "Уже обработано"],
                  key=lambda x: (x["date"], x["time"]))
    deferred = sorted([g for g in groups if g["final"] == "Не решено"],
                      key=lambda x: (x["date"], x["time"]))

    def row(g):
        links = " ".join("<a href=\"%s\">%s</a>" % (u, u.rstrip("/").split("/")[-1])
                         for u in g["links"][:3])
        return "| %s | %s | %s | %s | %s |" % (
            g["date"], g["time"], g["title"].replace("|", "\\|"), links,
            g.get("why", "") or "—")

    out = []
    out.append("# Обзор источников ВДНХ — 26 ноября 2026")
    out.append("")
    out.append("## Что проверено")
    out.append("")
    out.append("- `vdnh.ru/events/` — кнопка «Все фильтры» → «Лекции» → «Применить», "
               "3 нажатия «Показать еще»: 31 карточка, кнопка исчезла.")
    out.append("- `vdnh.ru/lektorij/` — 33 карточки, 4 нажатия «Показать еще».")
    out.append("- `?subject=kosmos`, `?subject=slovo` — те же 31 карточка, "
               "параметр выборку не меняет.")
    out.append("- Timepad: lektorij (20 + 3 будущие на page=2), cosmos (10 future), "
               "slovo (5), atom-lab (0), biotech (0). "
               "**Обход остановлен при первом же прошедшем событии** "
               "(lektorij — `4300020`, 25 ноября; cosmos — `4298115`, 22 ноября; "
               "slovo — `4245070`, 22 ноября; atom — `2906339`, 1 июня 2024; "
               "biotech — `4052141`, 11 июля). Страницы `page=3..8` ошибочно "
               "скачанного первого прохода удалены.")
    out.append("")
    out.append("Всего уникальных будущих событий после объединения источников: %d. "
               "Из них уже опубликовано/с прототипом и ранее решено — %d, "
               "«Не нужно» — %d, «Нужно» — %d, «Сомнительные» — %d, "
               "«Не решено» — %d." % (
                   len(groups), len(done), len(notneed), len(need), len(doubt),
                   len(deferred)))
    out.append("")
    out.append("## Нужно (новые лекции, нет на сайте и без прототипа)")
    out.append("")
    out.append("| Дата | Время | Название | Ссылки | Комментарий |")
    out.append("|---|---|---|---|---|")
    out.extend(row(g) for g in need)
    out.append("")
    out.append("## Сомнительные (нужны критерии/подтверждение пользователя)")
    out.append("")
    out.append("| Дата | Время | Название | Ссылки | Комментарий |")
    out.append("|---|---|---|---|---|")
    out.extend(row(g) for g in doubt)
    out.append("")
    out.append("## Не решено (отложено ранее)")
    out.append("")
    out.append("| Дата | Время | Название | Ссылки | Комментарий |")
    out.append("|---|---|---|---|---|")
    out.extend(row(g) for g in deferred)
    out.append("")
    out.append("## Не нужно")
    out.append("")
    out.append("%d событий: концерты, спектакли, детские программы, мастер-классы, "
               "обзорные экскурсии, серии и экзамены. Полный список — "
               "`data/monitor/vdnh_not_needed_2026-11-26.json`." % len(notneed))
    out.append("")
    out.append("## Уже обработано")
    out.append("")
    out.append("%d событий: либо уже на сайте (`data/events.json`), либо с готовым "
               "прототипом, либо с решением в реестре. Повторно не загружаются." % len(done))
    out.append("")
    out.append("## Реестр и отложенные решения")
    out.append("")
    out.append("- `data/monitor/known_by_source.json` — все просмотренные ID.")
    out.append("- `data/sweep/known_events.json` — операционный реестр; отчёт сверяет "
               "с ним каждый ID и не предлагает уже решенные события заново.")
    out.append("- `data/monitor/pending.json` — «Нужно», «Сомнительные» и «Не решено», "
               "решение пользователя ожидается.")
    counts = Counter(reg_status.values())
    out.append("- Статусы в реестре ВДНХ: " + ", ".join(
        "%s — %d" % (k, v) for k, v in sorted(counts.items())) + ".")
    out.append("")
    out.append("")
    text = "\n".join(out)
    path = os.path.join(MON, "run_vdnh_2026-11-26.md")
    if not DRY:
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    print("Отчёт:", os.path.relpath(path, ROOT) + (" (dry-run, не записан)" if DRY else ""))
    print("Нужно=%d Сомнительные=%d Не нужно=%d Обработано=%d Не решено=%d" % (
        len(need), len(doubt), len(notneed), len(done), len(deferred)))
    for g in need:
        print("  НУЖНО", g["date"], g["time"], g["title"][:80])

    # Файл «Не нужно»
    p = os.path.join(MON, "vdnh_not_needed_2026-11-26.json")
    if not DRY:
        # Старые решения не теряем: открытый список — это история отказов,
        # а не список только текущего прохода.
        old = load(p) if os.path.isfile(p) else []
        seen = {(str(x.get("source")), str(x.get("external_id"))) for x in old}
        fresh = []
        for g in notneed:
            row = {k: g[k] for k in ("url", "title", "date", "time", "why", "links")}
            row["source"] = g["source"]
            row["external_id"] = g["ids"].get(g["source"], "")
            if (str(row["source"]), str(row["external_id"])) not in seen:
                old.append(row)
                seen.add((str(row["source"]), str(row["external_id"])))
                fresh.append(row)
        with io.open(p, "w", encoding="utf-8", newline="\n") as f:
            json.dump(old, f, ensure_ascii=False, indent=2)
        print("Не нужно: добавлено новых %d, всего в списке %d"
              % (len(fresh), len(old)))

    # Обновление known_by_source.json
    known_path = os.path.join(MON, "known_by_source.json")
    known = load(known_path)
    for g in groups:
        for src, eid in g.get("ids", {}).items():
            if not eid:
                continue
            bucket = known["sources"].setdefault(src, [])
            existing = next((x for x in bucket if str(x.get("external_id")) == str(eid)), None)
            if existing:
                existing["last_seen"] = "2026-11-26"
                continue
            bucket.append({
                "external_id": str(eid), "url": g["links"][0],
                "first_seen": "2026-11-26", "last_seen": "2026-11-26",
                "title_hint": g["title"][:120],
                "status": g["final"],
            })
    if not DRY:
        with io.open(known_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(known, f, ensure_ascii=False, indent=2)

    # Отложенные решения
    pend_path = os.path.join(MON, "pending.json")
    pend = load(pend_path)
    pend["items"] = [{
        "source": g["source"], "external_id": g["ids"].get(g["source"], ""),
        "date": g["date"], "time": g["time"], "title": g["title"],
        "links": g["links"], "status": g["final"],
        "note": g.get("why", "") or "Новый кандидат, решение пользователя ожидается",
    } for g in need + doubt + deferred]
    if not DRY:
        with io.open(pend_path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(pend, f, ensure_ascii=False, indent=2)
    print("pending:", os.path.relpath(pend_path, ROOT), len(pend["items"]),
          "(dry-run, не записан)" if DRY else "")


if __name__ == "__main__":
    main()
