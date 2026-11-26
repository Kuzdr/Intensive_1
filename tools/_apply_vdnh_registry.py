# -*- coding: utf-8 -*-
"""Решение пользователя 26.11.2026 в отчёте и реестре лекториев."""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
NOTE = "решение пользователя 26.11.2026"

# 1. Отчёт мониторинга: добавить раздел с финальным решением.
report_path = ROOT / "data/monitor/run_vdnh_2026-11-26.md"
report = report_path.read_text(encoding="utf-8")
marker = "## Реестр и отложенные решения\n"
addition = """## Решение пользователя 26.11.2026

Из 15 оставшихся кандидатов (после выбора двух лекций):

- **Прототипы созданы:** «Космическое право» (4184 / Timepad 4288577) и
  «От Большого взрыва и дальше» (4266 / Timepad 4314826). У второй
  регистрация откроется за 14 дней до события (≈04.12.2026) — прототип
  помечен `needs_update` и будет переделан после открытия регистрации.
- **Не решено:** Фрейд (4248 / Timepad 4306394) и Юнг (4249 / Timepad
  4306436) — вернуться к ним позже.
- **Отвергнуто (не нужно):** остальные 13 кандидатов — 4308, 4287, 4305,
  4197, 427512, 4302, 4198, 4258, 4195, 4265, 4280, 4013, 4246.
  Добавлены в `vdnh_not_needed_2026-11-26.json`.

"""
if "## Решение пользователя 26.11.2026" not in report:
    report = report.replace(marker, addition + marker)
    report = report.replace(
        "- `data/monitor/pending.json` — «Нужно» и «Сомнительные», решение пользователя ожидается.\n",
        "- `data/monitor/pending.json` — 15 событий: 2 «Не решено» и 13 «Не нужно» (после решения пользователя).\n",
    )
report_path.write_text(report, encoding="utf-8")

# 2. Реестр лекториев: новые статусы и отметки.
reg_path = ROOT / "data/sweep/known_events.json"
reg_text = reg_path.read_text(encoding="utf-8-sig")
reg = json.loads(reg_text)
reg["note"] = ("Статусы: candidate (ждёт решения), added (в прототипе/на сайте), "
               "on_elementy (уже на «Элементах»), rejected (отвергнуто, причина в note), "
               "duplicate (дубль, ID в note), undecided (не решено, вернуться позже), "
               "needs_update (в прототипе, требуется обновление источника).")
events = reg["lectories"]["vdnh"]["events"]
by_key = {e["key"]: e for e in events}

REJECT = {
    "TP-4324253": ("2026-12-06", "15:00", "Дмитрий Шостакович: свидетель эпохи"),
    "TP-4322622": ("2026-12-06", "18:00", "Иосиф Бродский: посох пилигрима"),
    "TP-4324269": ("2026-12-08", "19:00", "К выходу «Приключений Клиффа Бута»"),
    "VD-427512": ("2026-12-12", "17:00", "Конституции советской эпохи: история в павильонах ВДНХ"),
    "TP-4324239": ("2026-12-16", "19:00", "Даниил Хармс: абсурдист и джентльмен"),
    "TP-4299971": ("2026-12-26", "14:00", "Я – проектировщик! Вера Мухина у истоков дизайна"),
    "TP-4311045": ("2026-11-29", "18:00", "Музыкально-театральные проекты Алексея Верстовского"),
    "TP-4318382": ("2026-12-01", "19:00", "Дмитрий Шостакович и русский музыкальный авангард"),
    "VD-4013": ("2026-11-26", "19:30", "Любовь с первого аромата"),
    "VD-4246": ("2026-11-28", "17:00", "Наследие Марлена Хуциева"),
}
ALREADY = {
    "TP-4299938": "Рабочий и колхозница: Вера Мухина на международных выставках",
    "TP-4314300": "Шостакович: страх, смех и «Нос»",
    "TP-4299896": "Битва титанов: Вера Мухина и Парижская выставка 1925 года",
}
UNDECIDED = {
    "TP-4306394": "Зигмунд Фрейд: человек, который знает, что тебе снилось",
    "TP-4306436": "Карл Густав Юнг: НЛО, Таро и твоя тёмная сторона",
}

for key, (date, time, title) in REJECT.items():
    if key in by_key:
        rec = by_key[key]
    else:
        rec = {"key": key, "date": date, "time": time, "title": title,
               "url": "", "source_status": "candidate",
               "first_seen": "2026-11-26", "last_seen": "2026-11-26"}
        events.append(rec)
    rec["status"] = "rejected"
    rec["review"] = "hide"
    rec["note"] = "%s: отвергнуто" % NOTE
    rec["updated"] = "2026-11-26"

for key in list(ALREADY) + list(UNDECIDED):
    if key in by_key:
        by_key[key]["note"] = ("%s: %s" % (
            NOTE, "оставить не решённым" if key in UNDECIDED else "отвергнуто"))
        by_key[key]["updated"] = "2026-11-26"
        if key in UNDECIDED:
            by_key[key]["status"] = "undecided"
            by_key[key]["review"] = "hide"
        else:
            by_key[key]["status"] = "rejected"
            by_key[key]["review"] = "hide"

for key, date, time, title, status, note in (
        ("TP-4288577", "2026-12-13", "19:20", "Космическое право", "added",
         "Прототип создан 26.11.2026; ссылка на Timepad найдена в Nuxt-данных страницы ВДНХ."),
        ("TP-4314826", "2026-12-18", "19:00",
         "От Большого взрыва и дальше: что понятно, а что не совсем", "needs_update",
         "Прототип создан 26.11.2026; регистрация откроется за 14 дней до события (≈04.12.2026) — переделать после открытия.")):
    if key in by_key:
        rec = by_key[key]
    else:
        rec = {"key": key, "date": date, "time": time, "title": title,
               "url": "", "source_status": "candidate",
               "first_seen": "2026-11-26", "last_seen": "2026-11-26"}
        events.append(rec)
    rec["status"] = status
    rec["review"] = "include"
    rec["note"] = note
    rec["updated"] = "2026-11-26"

reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")

# 3. Скрипт реестра: разрешить новые статусы.
script_path = ROOT / "tools/sweep_lectories.py"
script = script_path.read_text(encoding="utf-8")
script = script.replace(
    "   duplicate   — дубль опубликованного (ID в note).\n",
    "   duplicate   — дубль опубликованного (ID в note);\n"
    "   undecided   — не решено, вернуться позже;\n"
    "   needs_update — в прототипе, но требуется обновление источника.\n")
script = script.replace(
    'STATUSES = ("candidate", "added", "on_elementy", "rejected", "duplicate")',
    'STATUSES = ("candidate", "added", "on_elementy", "rejected", "duplicate",\n'
    '            "undecided", "needs_update")')
script_path.write_text(script, encoding="utf-8")
print("report and registry updated; vdnh events:", len(events))
