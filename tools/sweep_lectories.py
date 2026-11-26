# -*- coding: utf-8 -*-
"""Регулярный обход лекториев: что нового появилось в источниках.

Два редактируемых файла (обычный JSON, можно править в блокноте):

  data/sweep/lectories.json     — список лекториев и ссылок на источники;
  data/sweep/known_events.json  — реестр уже проверенных событий со статусом.

Статусы реестра:
  candidate   — найдено, решение ещё не принято;
  added       — добавлено в прототип/на сайт;
  on_elementy — уже опубликовано на «Элементах»;
  rejected    — отвергнуто (причина в note);
  duplicate   — дубль опубликованного (ID в note).

Прошедшие события (дата раньше сегодняшней) НИКОГДА не показываются и не
добавляются в реестр. Для кандидатов поле `review` управляет выдачей:
  include — явно подходит, вносить;
  doubt   — сомнительно, показать отдельно;
  hide    — заведомо не подходит, не показывать.
Выдача кандидатов всегда полная: ключ, дата/время, автор, заголовок, URL.

Использование:
  python -X utf8 tools\\sweep_lectories.py --list
  python -X utf8 tools\\sweep_lectories.py
  python -X utf8 tools\\sweep_lectories.py --lectory pryamaya --refresh
  python -X utf8 tools\\sweep_lectories.py --bootstrap
  python -X utf8 tools\\sweep_lectories.py --mark PR-8935 candidate --note "дублей нет"
  python -X utf8 tools\\sweep_lectories.py --json report.json
"""
import argparse
import datetime
import glob
import io
import json
import os
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP_DIR = os.path.join(ROOT, "data", "sweep")
CONFIG_PATH = os.path.join(SWEEP_DIR, "lectories.json")
REGISTRY_PATH = os.path.join(SWEEP_DIR, "known_events.json")
AVAIL_LOG = os.path.join(ROOT, ".opencode", "skills", "event-description",
                         "reference", "availability_log.md")
STATUSES = ("candidate", "added", "on_elementy", "rejected", "duplicate",
            "undecided", "needs_update")


def load_json(path, fallback):
    # utf-8-sig читает и обычный UTF-8, и файл с BOM. 22.11.2026 BOM в
    # known_events.json заставил старый код вернуть пустой fallback, и CLI
    # перезаписал реестр из 124 событий семью. Возвращаем fallback только
    # когда явно просят (для реестра передаём None — см. main()).
    try:
        with io.open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as exc:                       # noqa: BLE001
        sys.stderr.write("ОШИБКА чтения %s: %s\n" % (path, exc))
        return fallback


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def today():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def today_date():
    return datetime.date.today().isoformat()


def future(event):
    """Прошедшее событие не попадает ни в отчёт, ни в реестр."""
    return (event.get("date") or "")[:10] >= today_date()


def print_candidates(events):
    """Полный список кандидатов со ссылками (правило пользователя 22.11.2026)."""
    groups = [("include", "ЯВНО ВНОСИТЬ"), ("doubt", "СОМНИТЕЛЬНЫЕ"),
              (None, "КАНДИДАТЫ")]
    shown = 0
    for review, header in groups:
        rows = [e for e in events if e.get("review") == review] if review else [
            e for e in events if e.get("review") not in ("include", "doubt", "hide")]
        if not rows:
            continue
        print("  %s (%d):" % (header, len(rows)))
        for e in rows:
            author = e.get("author") or "автор не указан"
            print("    %s | %s %s | %s | %s"
                  % (e["key"], e.get("date") or "?", e.get("time") or "",
                     author, e.get("title") or "?"))
            print("      %s" % e.get("url", "?"))
            shown += 1
    if not shown:
        print("  кандидатов нет")


def print_registry_candidates(reg, key, name, proto=None):
    """Кандидаты из реестра — даже у лекториев без автоматического сборщика."""
    proto = prototype_urls() if proto is None else proto
    events = [e for e in registry_events(reg, key)
              if future(e) and e.get("status") == "candidate"
              and e.get("review") != "hide"]
    events, done = split_prototyped(events, proto)
    print_prototyped(name, done)
    if not events:
        return 0
    print("\n%s: кандидатов в реестре %d" % (name, len(events)))
    print_candidates(events)
    return len(events)


def log_unavailable(url, exc, attempts=1):
    """Обязательная запись об ошибке доступа (правило 10.10.2026)."""
    os.makedirs(os.path.dirname(AVAIL_LOG), exist_ok=True)
    with io.open(AVAIL_LOG, "a", encoding="utf-8") as f:
        f.write("\n## %s — обход лекториев: недоступен источник\n"
                % datetime.datetime.now().strftime("%d.%m.%Y, %H:%M"))
        f.write("- URL: `%s`\n" % url)
        f.write("- Тип ошибки: %s: %s\n" % (type(exc).__name__, exc))
        f.write("- Попыток: %d. Интервалы: повторить через 1 минуту, "
                "затем через 5 минут.\n" % attempts)
        f.write("- Итог: событие не получено; реестр не изменён. "
                "Повторить обход после восстановления доступа.\n")


def prototype_urls():
    """URL событий, для которых уже есть прототип (общая сверка для всех)."""
    urls = set()
    for p in glob.glob(os.path.join(ROOT, "data", "prototypes", "*",
                                    "prototype.json")):
        try:
            with io.open(p, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:                          # noqa: BLE001
            continue
        for u in [data.get("url")] + list(data.get("sources") or []):
            if u:
                urls.add(str(u).rstrip("/"))
    return urls


def split_prototyped(events, proto):
    """Одинаковая для всех лекториев сверка: убрать уже оформленные прототипом.

    Повод: 22.11.2026 лекция Соколовой (TP-4297595, тот же URL) попала в
    кандидаты, потому что проверка была только в сборщике «Прямой речи».
    """
    usual, done = [], []
    for e in events:
        if str(e.get("url", "")).rstrip("/") in proto:
            done.append(e)
        else:
            usual.append(e)
    return usual, done


def print_prototyped(name, events):
    """Показать, что уже оформлено прототипом и в кандидаты не идёт."""
    if not events:
        return
    print("\n%s: уже есть прототип — не кандидаты (%d):" % (name, len(events)))
    for e in events:
        print("    %s | %s | %s"
              % (e["key"], e.get("date") or "?", e.get("title") or "?"))


def collect_pryamaya(lectory, refresh=False):
    import collect_pryamaya as CP
    out = []
    for e in CP.collect_all():
        out.append({
            "key": e["key"], "date": e["date"], "time": e["time"],
            "title": e["title"], "subtitle": e["subtitle"],
            "author": e["author"], "url": e["url"],
            "source_status": "candidate",
            "note": "Найдено в афише, решение не принято",
        })
    return out


def collect_arhe(lectory, refresh=False):
    import arhe_diff as AD
    calendar = AD.load_calendar(refresh=refresh)
    proto_ids = AD.load_prototype_ids()
    elementy = AD.load_elementy_dates(refresh=refresh)
    mapping = {
        "NEW": ("candidate", "Кандидат по диффу «Архэ»"),
        "dup?": ("candidate", "Тот же автор в тот же день на «Элементах» — сверить"),
        "proto": ("added", "Есть прототип TP-<timepad-id>"),
        "dup": ("on_elementy", "Дубль события «Элементов» (совпадение даты и заголовка)"),
        "course": ("rejected", "Страница курса, не отдельная лекция"),
        "skip": ("rejected", "Не по правилам отбора карточки «Архэ»"),
    }
    out = []
    for e in calendar:
        st = AD.classify(e, proto_ids, elementy)
        status, note = mapping[st]
        tp = e.get("timepad_id")
        out.append({
            "key": ("TP-" + str(tp)) if tp else ("AR-" + str(e["tip"])),
            "date": str(e["date"])[:10], "time": "",
            "title": e["title"], "subtitle": "",
            "author": "", "url": e.get("timepad_url") or e.get("arhe_url", ""),
            "source_status": status, "note": note,
        })
    return out


COLLECTORS = {"pryamaya": collect_pryamaya, "arhe": collect_arhe}


def lectory_map(cfg):
    return {x["key"]: x for x in cfg.get("lectories", [])}


def registry_events(reg, key):
    node = reg.setdefault("lectories", {}).setdefault(key, {"events": []})
    return node.setdefault("events", [])


def index(events):
    return {e["key"]: e for e in events}


# --- Распознавание одного события из двух источников -----------------------
# Повод (правило пользователя 22.11.2026): лекцию Сердотецкого нашли дважды —
# в Timepad ЗИЛ и на сайте zilcc.ru — и подали как два разных события.
# Идентичность = дата + нормализованный заголовок (или автор, если заголовка
# нет). Ключи и URL у одного события в разных источниках разные, поэтому
# сверять их нельзя.

_TITLE_NOISE = ("лекция", "онлайн лекция", "открытая лекция", "онлайнлекция",
                "открытая встреча московского астрономического клуба")


def norm_words(value):
    """ё→е, нижний регистр, только буквы/цифры и пробелы — для сравнения."""
    text = unicodedata.normalize("NFKC", str(value or "")).lower().replace("ё", "е")
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch)
        elif ch.isspace():
            out.append(" ")
    return " ".join("".join(out).split())


def title_key(event):
    """Нормализованный заголовок без типовых приставок («Лекция…»)."""
    text = norm_words(event.get("title"))
    for word in _TITLE_NOISE:
        if text.startswith(word):
            text = text[len(word):].strip()
            break
    return text


def same_event(a, b):
    """Одно ли событие (в разных источниках)? Дата + заголовок или автор."""
    if (a.get("date") or "")[:10] != (b.get("date") or "")[:10]:
        return False
    ta, tb = title_key(a), title_key(b)
    aa, ab = norm_words(a.get("author")), norm_words(b.get("author"))
    # Одинаковые дата и заголовок — надёжный дубль (автора может не быть).
    if ta and tb and ta == tb:
        return True
    # Один заголовок — начало/конец другого (сайт добавляет «Лекция …
    # преподавателя …» к тому же названию): короткий должен быть не меньше
    # 12 знаков и не короче 40% длинного, иначе это случайное совпадение.
    if ta and tb and ta != tb:
        short, long = sorted((ta, tb), key=len)
        if len(short) >= 12 and len(short) * 100 >= len(long) * 40 \
                and (short in long):
            return True
    # Совпавший автор на ту же дату, когда хотя бы один заголовок отсутствует.
    if aa and ab and aa == ab and (not ta or not tb):
        return True
    return False


def find_existing(reg, event, exclude_keys=None):
    """Найти в реестре уже учтённое событие; вернуть (лекторий, запись)."""
    exclude = set(exclude_keys or ())
    for lkey, node in reg.get("lectories", {}).items():
        for rec in node.get("events", []):
            if rec.get("key") in exclude:
                continue
            if same_event(event, rec):
                return lkey, rec
    return None


def check_registry_duplicates(reg):
    """Все пары событий реестра, которые на самом деле одно событие."""
    rows = []
    seen = []
    for lkey, node in reg.get("lectories", {}).items():
        for rec in node.get("events", []):
            for other_lkey, other in seen:
                if same_event(rec, other):
                    rows.append((lkey, rec, other_lkey, other))
            seen.append((lkey, rec))
    return rows


def cmd_check_dups(reg):
    rows = check_registry_duplicates(reg)
    if not rows:
        print("Дублей между источниками в реестре нет.")
        return 0
    print("ОДНО СОБЫТИЕ, ДВЕ ЗАПИСИ В РЕЕСТРЕ (%d):" % len(rows))
    for lkey, rec, other_lkey, other in rows:
        print("  %s | %s | %s" % (rec.get("key"), rec.get("date") or "?",
                                 rec.get("title") or "?"))
        print("    %s — %s" % (other_lkey, other.get("key")))
        print("    %s" % (rec.get("url") or "?"))
        print("    %s" % (other.get("url") or "?"))
    return 0


def cmd_list(cfg, args):
    print("СПИСОК ЛЕКТОРИЕВ (редактируйте: %s)" % os.path.relpath(
        CONFIG_PATH, ROOT))
    for x in cfg.get("lectories", []):
        flag = "включён" if x.get("enabled") else "выключен"
        coll = x.get("collector") or "—"
        print("\n%s [%s] | сборщик: %s" % (x["name"], flag, coll))
        print("  ключ: %s" % x["key"])
        for s in x.get("sources", []):
            print("  - %s: %s%s"
                  % (s.get("kind", "источник"), s.get("url", "?"),
                     (" — " + s["note"]) if s.get("note") else ""))
        if x.get("criteria"):
            print("  отбор: %s" % x["criteria"])
    return 0


def do_sweep(cfg, reg, args):
    only = args.lectory
    rows, errors = [], []
    proto = prototype_urls()          # одна сверка на все лектории
    for lectory in cfg.get("lectories", []):
        key = lectory["key"]
        if only and key != only:
            continue
        if not lectory.get("enabled"):
            print("\n%s: выключен в списке — пропущен" % lectory["name"])
            continue
        coll_name = lectory.get("collector")
        if not coll_name:
            if not print_registry_candidates(reg, key, lectory["name"], proto):
                print("\n%s: сборщик не назначен — только источники в списке"
                      % lectory["name"])
            continue
        if coll_name not in COLLECTORS:
            print("\n%s: НЕИЗВЕСТНЫЙ сборщик %s" % (lectory["name"], coll_name))
            errors.append((key, "неизвестный сборщик " + coll_name))
            continue
        try:
            found = COLLECTORS[coll_name](lectory, refresh=args.refresh)
        except Exception as exc:                   # noqa: BLE001
            print("\n%s: ОШИБКА ИСТОЧНИКА — %s: %s"
                  % (lectory["name"], type(exc).__name__, exc))
            log_unavailable(str(lectory.get("sources", [{}])[0].get("url", "?")),
                            exc)
            errors.append((key, str(exc)))
            continue
        past = len(found) - sum(1 for e in found if future(e))
        found = [e for e in found if future(e)]
        found, done = split_prototyped(found, proto)
        print_prototyped(lectory["name"], done)
        known = index(registry_events(reg, key))
        new = [e for e in found if e["key"] not in known]
        # Одно событие из двух источников не считаем двумя новыми: ищем его
        # отпечаток (дата + заголовок/автор) во всём реестре.
        source_dups = []
        fresh = []
        for e in new:
            match = find_existing(reg, e, exclude_keys={e["key"]})
            if match:
                source_dups.append((e, match[1]))
            else:
                fresh.append(e)
        if source_dups:
            print("\n%s: уже в реестре под другим ключом — НЕ новые (%d):"
                  % (lectory["name"], len(source_dups)))
            for e, rec in source_dups:
                print("    %s → %s | %s | %s"
                      % (e["key"], rec.get("key"), e.get("date") or "?",
                         e.get("title") or "?"))
                print("      %s" % e.get("url", "?"))
        new = fresh
        counts = {}
        for e in found:
            st = known[e["key"]]["status"] if e["key"] in known else "new"
            counts[st] = counts.get(st, 0) + 1
        print("\n%s: всего %d (прошедших скрыто %d, уже с прототипом %d), "
              "НОВЫХ %d | %s"
              % (lectory["name"], len(found) + len(done), past, len(done),
                 len(new),
                 ", ".join("%s=%d" % (k, v) for k, v in sorted(counts.items()))
                 or "реестр пуст"))
        for e in new:
            print("  НОВОЕ %s %s | %s | %s"
                  % (e["date"] or "?", e["time"] or "  ", e["key"], e["title"]))
            print("        %s" % e["url"])
            if e.get("subtitle"):
                print("        %s" % e["subtitle"])
        waiting = [dict(e, review=known[e["key"]].get("review"))
                   for e in found if e["key"] in known
                   and known[e["key"]].get("status") == "candidate"]
        if waiting:
            print("  ждут решения: %d" % len(waiting))
            print_candidates(waiting)
        rows.append({"lectory": key, "name": lectory["name"],
                     "total": len(found) + len(done), "new": new,
                     "source_duplicates": [{"key": e["key"],
                                            "registry_key": rec.get("key")}
                                           for e, rec in source_dups],
                     "prototyped": [e["key"] for e in done], "counts": counts})
        if args.update_seen:
            for e in found + done:
                if e["key"] in known:
                    known[e["key"]]["last_seen"] = today()
            save_json(REGISTRY_PATH, reg)
    if args.json_out:
        save_json(args.json_out, {"date": today(), "lectories": rows,
                                  "errors": errors})
        print("\nJSON: %s" % os.path.abspath(args.json_out))
    if errors:
        print("\nОШИБКИ ИСТОЧНИКОВ: %d (записаны в availability_log.md)"
              % len(errors))
    return 0


def do_bootstrap(cfg, reg, args):
    """Добавить в реестр все найденные события, которых там ещё нет."""
    lm = lectory_map(cfg)
    added = 0
    proto = prototype_urls()          # та же сверка, что и при обходе
    for lectory in cfg.get("lectories", []):
        key = lectory["key"]
        if args.lectory and key != args.lectory:
            continue
        coll_name = lectory.get("collector")
        if not lectory.get("enabled") or not coll_name:
            continue
        try:
            found = COLLECTORS[coll_name](lectory, refresh=args.refresh)
        except Exception as exc:                   # noqa: BLE001
            print("%s: ОШИБКА ИСТОЧНИКА — %s" % (lectory["name"], exc))
            log_unavailable(str(lectory.get("sources", [{}])[0].get("url", "?")),
                            exc)
            continue
        found = [e for e in found if future(e)]
        found, done = split_prototyped(found, proto)
        done_keys = {e["key"] for e in done}
        known = index(registry_events(reg, key))
        node = reg["lectories"].setdefault(key, {"name": lectory["name"],
                                                 "events": []})
        node["name"] = lectory["name"]
        for e in found + done:
            if e["key"] in known:
                continue
            # Тот же отпечаток уже есть в реестре (событие из второго
            # источника) — не создаём вторую запись, дописываем URL к первой.
            match = find_existing(reg, e, exclude_keys={e["key"]})
            if match:
                old = match[1]
                urls = old.setdefault("also_urls", [])
                if e.get("url") and e["url"] not in urls:
                    urls.append(e["url"])
                old["note"] = (old.get("note", "") +
                               " | ещё источник: %s" % e["key"]).strip(" |")
                old["updated"] = today()
                print("%s: тот же отпечаток, что %s — вторая запись не создана"
                      % (e["key"], old.get("key")))
                continue
            rec = dict(e)
            rec["status"] = ("added" if e["key"] in done_keys
                             else e["source_status"])
            if e["key"] in done_keys:
                rec["note"] = "Есть прототип в data/prototypes/"
            rec["first_seen"] = today()
            rec["last_seen"] = rec["first_seen"]
            node.setdefault("events", []).append(rec)
            added += 1
        print("%s: в реестре %d событий"
              % (lectory["name"], len(node.get("events", []))))
    save_json(REGISTRY_PATH, reg)
    print("\nДобавлено в реестр: %d. Файл: %s"
          % (added, os.path.relpath(REGISTRY_PATH, ROOT)))
    return 0


def do_mark(cfg, reg, args):
    status = args.mark_status
    if status not in STATUSES:
        print("Неизвестный статус. Допустимо: %s" % ", ".join(STATUSES))
        return 2
    lm = lectory_map(cfg)
    candidates = []
    for key, node in reg.get("lectories", {}).items():
        for e in node.get("events", []):
            if e["key"] == args.mark and (not args.lectory or key == args.lectory):
                candidates.append((key, e))
    if len(candidates) > 1 and not args.lectory:
        print("Ключ встречен несколько раз — укажите --lectory: %s"
              % ", ".join(k for k, _ in candidates))
        return 2
    if candidates:
        key, rec = candidates[0]
    else:
        key = args.lectory or "pryamaya"
        if key not in lm:
            print("Лекторий %s нет в списке" % key)
            return 2
        rec = {"key": args.mark}
        registry_events(reg, key).append(rec)
        print("Запись добавлена в реестр (заполните поля при необходимости)")
    rec["status"] = status
    for field in ("date", "title", "url", "author"):
        val = getattr(args, field)
        if val:
            rec[field] = val
    if args.note:
        rec["note"] = args.note
    rec["updated"] = today()
    rec.setdefault("first_seen", today())
    rec.setdefault("last_seen", rec["first_seen"])
    save_json(REGISTRY_PATH, reg)
    print("%s: %s → %s" % (args.mark, key, status))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Обход лекториев: что нового")
    ap.add_argument("--list", action="store_true", help="показать список лекториев")
    ap.add_argument("--lectory", help="только один лекторий (ключ)")
    ap.add_argument("--refresh", action="store_true", help="обновить кэши источников")
    ap.add_argument("--bootstrap", action="store_true",
                    help="добавить найденные события в реестр")
    ap.add_argument("--mark", metavar="KEY", help="поменять статус события")
    ap.add_argument("--mark-status", metavar="STATUS", choices=STATUSES,
                    help="новый статус для --mark")
    ap.add_argument("--note", help="причина/заметка для --mark")
    ap.add_argument("--date", help="дата events для новой записи")
    ap.add_argument("--title", help="заголовок для новой записи")
    ap.add_argument("--url", help="ссылка для новой записи")
    ap.add_argument("--author", help="автор для новой записи")
    ap.add_argument("--update-seen", action="store_true",
                    help="обновить last_seen у известных событий")
    ap.add_argument("--check-dups", action="store_true",
                    help="показать события, найденные дважды (один отпечаток)")
    ap.add_argument("--json", dest="json_out", help="сохранить отчёт в JSON")
    args = ap.parse_args()

    cfg = load_json(CONFIG_PATH, {})
    if not cfg.get("lectories"):
        print("Нет списка лекториев: %s" % CONFIG_PATH)
        return 2
    # fallback=None: при ошибке чтения НЕ перезаписываем реестр (урок BOM
    # 22.11.2026, когда пустой fallback стёр 124 события).
    reg = load_json(REGISTRY_PATH, None)
    if reg is None:
        print("ОШИБКА: не удалось прочитать реестр %s — выход без изменений"
              % REGISTRY_PATH)
        return 2

    if args.check_dups:
        return cmd_check_dups(reg)
    if args.list:
        return cmd_list(cfg, args)
    if args.mark:
        if not args.mark_status:
            print("Для --mark укажите --mark-status")
            return 2
        return do_mark(cfg, reg, args)
    if args.bootstrap:
        return do_bootstrap(cfg, reg, args)
    return do_sweep(cfg, reg, args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
