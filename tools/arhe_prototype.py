# -*- coding: utf-8 -*-
"""Сборка прототипов описаний событий Центра «Архэ» (data/prototypes/<ID>/prototype.json).

Отдельный драйвер лектория — потому что у «Архэ» ДВА источника (свой сайт
arhe.msk.ru + регистрация на Timepad) и свой образец описания. Но весь разбор
берётся из общих адаптеров, а вся анкетная механика — из `tools/protolib.py`:
здесь только специфика «Архэ».

Что делает:
  1. читает страницу события arhe.msk.ru (`sources/tribe_events`) и страницу
     Timepad (`sources/timepad`) — с кэшем, без повторных загрузок;
  2. сливает их (год/даты — с сайта; билеты/цена/возраст — с Timepad);
  3. механически собирает поля 0–14 (привязка, даты, место, цена, лекторий…);
  4. собирает `desc_html` (шапка + аннотация + KLBLOCK + blockquote) и
     `extra_html` (стоимость, регистрация, адрес площадки, контакты, ссылки);
  5. автора ищет на «Элементах» (`sources/elementy`), иначе берёт из данных;
  6. пишет `prototype.json` и прогоняет валидатор `tools/check_prototype.py`.

Прозаические куски (текст аннотации, отформатированный план курса, «Лекцию
прочитает …») задаются в `tools/arhe_data.py` — генератор их не выдумывает, но
правильно оформляет (nbsp, KLBLOCK, blockquote) и складывает в нужные поля.

Использование:
    python -X utf8 tools\\arhe_prototype.py TP-4223719
    python -X utf8 tools\\arhe_prototype.py TP-4223719 --check       # не писать, показать
    python -X utf8 tools\\arhe_prototype.py --all
    python -X utf8 tools\\arhe_prototype.py TP-4223719 --no-validate
"""
import datetime
import importlib.util
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources"))
import protolib as P                    # noqa: E402
import timepad as tp                    # noqa: E402
import tribe_events as tribe            # noqa: E402

ROOT = P.ROOT
DATA_FILE = os.path.join(ROOT, "tools", "arhe_data.py")


def load_data():
    spec = importlib.util.spec_from_file_location("arhe_proto_data", DATA_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def merge(cfg):
    """Читает оба источника и сливает в одно событие."""
    site = tribe.read(cfg["arhe"], file=cfg.get("arhe_file"))
    reg = tp.read(cfg.get("timepad") or site.get("timepad_url"),
                  file=cfg.get("timepad_file"))
    date_iso = cfg.get("date_iso") or site.get("date_iso") or ""
    time_start = cfg.get("time_start") or site.get("time_start") or reg.get("time_start") or ""
    time_end = cfg.get("time_end") or reg.get("time_end") or ""
    return {"site": site, "reg": reg, "date_iso": date_iso,
            "time_start": time_start, "time_end": time_end}


def build_fields(ev, cfg, venue, today_dt):
    dt = P.d(ev["date_iso"])
    site, reg = ev["site"], ev["reg"]
    title = P.nbsp_normalize(cfg["title"])
    city = venue["city"]
    short = venue["short"]
    online = venue.get("online", False)
    lectory = cfg.get("lectory") or "Лекторий Культурно-просветительского центра «Архэ»"
    course = cfg.get("course")  # {n, name, author_gen}

    place2 = "%s, %s%s" % (city, short, " и&nbsp;ОНЛАЙН" if online else "")
    short_online = "%s%s" % (short, " и&nbsp;ОНЛАЙН" if online else "")
    fields = []
    fields.append(P.field("0", "ID события", cfg["id"]))
    fields.append(P.field("1", "Привязка", P.binding(ev["date_iso"], ev["time_start"])))
    dates = []
    P.date_fields(dates, ev["date_iso"], ev["time_start"], ev["time_end"],
                  city, short_online, today_dt)
    day7 = dates.pop()          # «7» ставится позже, после 6.4
    fields += dates

    if course:
        line = "«%s»<br>Лекция&nbsp;%d курса %s «%s»" % (
            title, course["n"], course["author_gen"], course["name"])
        line4 = "«%s». Лекция&nbsp;%d курса %s «%s»" % (
            title, course["n"], course["author_gen"], course["name"])
        sub = "%s. Лекция&nbsp;%d" % (course["name"], course["n"])
    else:
        gen = cfg.get("author_gen") or ""
        line = "%s %s «%s»" % (cfg.get("type", "Лекция"), gen, title)
        line4 = line
        sub = "Научно-популярный лекторий «Архэ»"
    fields.append(P.field("3", "Полный заголовок с подзаголовком", line))
    fields.append(P.field("4", "Полный заголовок без подзаголовка", line4))
    fields.append(P.field("5", "Название лекции", title))
    fields.append(P.field("6", "Подзаголовок", sub))
    fields.append(P.field("6.1", "Тип", cfg.get("type", "Лекция")))
    fields.append(P.field("6.2", "Место (из списка)", "%s, %s" % (city, short)))
    fields.append(P.field("6.3", "Лекторий", lectory))
    fields.append(P.field("6.4", "Тематики", P.nbsp_normalize(", ".join(cfg.get("topics") or [])) or "—"))
    fields.append(day7)
    fields.append(P.field("8", "Место", place2))
    fields.append(P.field("9", "Источники", "\n".join(cfg["sources"])))
    fields.append(P.field("10", "URL регистрации/покупки билета", cfg.get("registration", "")))
    fields.append(P.field("11", "Стоимость", P.nbsp_normalize(cfg.get("price", "")) or "—"))
    fields.append(P.field("12", "Возрастные ограничения", cfg.get("age") or reg.get("age") or "—"))
    fields.append(P.field("14", "Аудитория", cfg.get("audience") or "Для всех"))
    return fields


def para(s):
    """Нормализует nbsp и оборачивает в <p>, если кусок уже не блок.

    Куски с готовыми nbsp считаются предформатированными; их только оборачиваем.
    """
    if s.lstrip().startswith("<"):
        return s
    body = s if ("&nbsp;" in s or "\u00a0" in s) else P.nbsp_normalize(s)
    return "<p>%s</p>" % body


def build_desc(ev, cfg, venue):
    online = venue.get("online", False)
    parts = [P.lead_field({}, ev["date_iso"], ev["time_start"], ev["time_end"],
                          venue["city"], venue["short"], online)]
    if cfg.get("intro"):
        parts.append(para(cfg["intro"]))
    parts.append("<KLBLOCK eltclub_authors_about/>")
    if cfg.get("theme"):
        parts.append(para(cfg["theme"]))
    parts.append('<blockquote class="small">')
    for b in cfg.get("body") or []:
        parts.append(para(b))
    if cfg.get("plan"):
        parts.append(para(cfg["plan"]))
    if cfg.get("post_plan"):
        parts.append(para(cfg["post_plan"]))
    if cfg.get("closer"):
        parts.append(para(cfg["closer"]))
    parts.append("</blockquote>")
    return "\n\n".join(parts)


def build_extra(ev, cfg, venue):
    reg = ev["reg"]
    out = []
    if cfg.get("price_extra"):
        out.append(para(cfg["price_extra"]))
    if cfg.get("registration"):
        out.append('<p><a href="%s" target="_blank">Регистрация и&nbsp;оплата</a>.</p>'
                   % cfg["registration"])
    out.append(venue["addr_html"])
    if cfg.get("contacts"):
        out.append(para(cfg["contacts"]))
    out.append("<!-- @@@ -->")
    links = cfg.get("info_links")
    if not links:
        links = []
        for src in cfg["sources"]:
            label = cfg.get("source_labels", {}).get(src, "на сайте организатора")
            links.append('Информация о&nbsp;лекции <a href="%s" target="_blank">%s</a>.'
                         % (src, label))
        if links:
            links[-1] = links[-1][:-1]
    out.append('<p class="small">%s</p>' % "<br>\n\n".join(links))
    out.append('<p class="small"><a href="http://arhe.msk.ru/?page_id=369" '
               'target="_blank">О&nbsp;Лектории Центра «Архэ»</a></p>')
    return out


def build_authors(cfg):
    out = []
    for a in cfg.get("authors") or []:
        if a.get("on_elementy"):
            fields = P.author_known_fields(a["name"], a.get("full_name"),
                                           a.get("block_html", ""), a.get("photo", ""))
            out.append({"name": a["name"], "photo": a.get("photo", ""),
                        "on_elementy": True, "block_html": a.get("block_html", ""),
                        "fields": fields})
        else:
            fields = P.author_new_fields(a["name"], a.get("block_html", ""), a.get("photo", ""))
            out.append({"name": a["name"], "photo": a.get("photo", ""),
                        "on_elementy": False, "block_html": a.get("block_html", ""),
                        "fields": fields})
    return out


def build(cfg, today_dt=None):
    data = load_data()
    venue = data.VENUES[cfg["venue"]]
    ev = merge(cfg)
    if not ev["date_iso"] or not ev["time_start"]:
        raise SystemExit("нет даты/времени: проверьте источники " + cfg["id"])
    today_dt = today_dt or P.today()
    authors = build_authors(cfg)
    proto = {
        "id": cfg["id"],
        "lectory": cfg.get("lectory") or "Лекторий Культурно-просветительского центра «Архэ»",
        "date_iso": ev["date_iso"],
        "time_start": ev["time_start"],
        "time_end": ev["time_end"],
        "city": venue["city"],
        "place": "%s, %s%s" % (venue["city"], venue["short"],
                               " и ОНЛАЙН" if venue.get("online") else ""),
        "lecturer": cfg.get("lecturer") or (cfg.get("authors") or [{}])[0].get("name", ""),
        "title": P.nbsp_normalize(cfg["title"]),
        "types": cfg.get("types") or ["Лекция"],
        "topics": cfg.get("topics") or [],
        "price_short": cfg.get("price_short", ""),
        "annot": cfg.get("annot", ""),
        "url": cfg.get("url") or cfg["registration"] or cfg["sources"][0],
        "sources": cfg["sources"],
        "fields": build_fields(ev, cfg, venue, today_dt),
        "desc_html": build_desc(ev, cfg, venue),
        "extra_html": build_extra(ev, cfg, venue),
        "authors": authors,
        "verbatim_fragments": cfg.get("verbatim_fragments") or [],
        "photo_file": "",
        "notes": cfg.get("notes", ""),
    }
    return proto


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    no_validate = "--no-validate" in sys.argv

    def opt(name):
        for i, a in enumerate(sys.argv):
            if a == name and i + 1 < len(sys.argv):
                return sys.argv[i + 1]
            if a.startswith(name + "="):
                return a.split("=", 1)[1]
        return None

    arhe_file, tp_file = opt("--arhe-file"), opt("--tp-file")
    data = load_data()
    ids = sorted(data.EVENTS) if ("--all" in sys.argv or not args) else args
    for pid in ids:
        cfg = data.EVENTS.get(pid)
        if not cfg:
            print("НЕТ ДАННЫХ: %s" % pid)
            continue
        cfg = dict(cfg)
        cfg.setdefault("id", pid)
        if arhe_file:
            cfg["arhe_file"] = arhe_file
        if tp_file:
            cfg["timepad_file"] = tp_file
        proto = build(cfg)
        if check:
            print(json.dumps(proto, ensure_ascii=False, indent=1))
            continue
        path = P.write_prototype(proto)
        print("OK %s -> %s" % (pid, path))
        if not no_validate:
            rc, out = P.validate(path)
            print("валидатор: rc=%d" % rc)
            print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
