# -*- coding: utf-8 -*-
"""Обновление справочных списков из выпадающих списков админки «Элементов».

Списки нужны для формальных полей 6.1-6.4 прототипов описаний событий
(скилл event-description): Тип, Аудитория, Место проведения, Лекторий, Тематика.

ВАЖНО: полные seлекты видны ТОЛЬКО на странице события elementy.ru (на /events
список урезан до значений текущей выдачи!). Поэтому источником выступает URL
любой страницы события - автоматически берём первый elementy-URL из
data/events.json, либо URL из аргумента командной строки.

Результат: перезаписываются файлы reference/lists/*.md в скилле
event-description. Запускается вручную и по расписанию GitHub Actions
(.github/workflows/update-admin-lists.yml), в основном список площадок часто
обновляется - его нужно перечитывать раз в день.

Использование:
    python -X utf8 tools\\update_admin_lists.py
    python -X utf8 tools\\update_admin_lists.py https://elementy.ru/events/...
    python -X utf8 tools\\update_admin_lists.py --html <локальный файл>   (без сети)
Код возврата: 0 — ОК, 1 — ошибка.
"""
import io
import os
import re
import sys
import html
import json
import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, ".opencode", "skills", "event-description")
OUT_DIR = os.path.join(SKILL, "reference", "lists")

# Порядок селектов (как в админке) -> файл, название для заголовка
SELECTS = [
    ("xtypid", "type.md", "Тип события"),
    ("audid", "audience.md", "Аудитория"),
    ("plcid", "place.md", "Место проведения"),
    ("lctid", "lectorium.md", "Лекторий"),
    ("prjid", "theme.md", "Тематика"),
]
# Замечания к файлам (одно на список, где нужен текст о регулярном обновлении)
NOTES = {
    "type.md": "",
    "audience.md": "",
    "place.md": (
        "ПРАВИЛО: этот список обновляется часто - перечитывать его раз в день\n"
        "по расписанию (см. tools/update_admin_lists.py и workflow"
        " update-admin-lists), а также по требованию пользователя.\n"
    ),
    "lectorium.md": "",
    "theme.md": "",
}


def norm_text(t: str) -> str:
    """Отступы -> пробелы, теги/сущности -> текст."""
    # 1) отступы уровня (-&nbsp; -&nbsp;&nbsp; ...) -> 2 пробела на уровень
    for n in range(8, 0, -1):
        marker = "-&nbsp;" * n + "&nbsp;"
        if t.startswith(marker):
            t = "  " * n + t[len(marker):]
            break
    # 2) мусор
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&nbsp;", " ").replace("&#160;", " ")
    t = html.unescape(t)
    return t.strip()


def extract_selects(raw: str):
    """Возвращает {name: [(value, text), ...]} без плейсхолдера <>.</option>"""
    out = {}
    for name, _fn, _label in SELECTS:
        m = re.search(
            r'<select[^>]*name=[\'"]?\s*%s[\'"]?[^>]*>(.*?)</select>' % name,
            raw, re.S)
        if not m:
            raise RuntimeError("в HTML не найден селект `%s`" % name)
        opts = re.findall(
            r'<option[^>]*?value=[\'"]?([^\'">\s]*)[\'"]?[^>]*>(.*?)</option>',
            m.group(1), re.S)
        out[name] = [(v, norm_text(t)) for v, t in opts if v and norm_text(t)]
    return out


def render_file(label: str, rows, note: str, date_str: str) -> str:
    lines = ["# %s" % label, ""]
    lines.append("Список из выпадающего списка админки «Элементов». "
                 "Формат строки: `ID : значение`;")
    lines.append("уровень вложенности показан отступом в 2 пробела. "
                 "Полные селекты берутся")
    lines.append("со страницы события elementy.ru (на /events список урезан "
                 "до значений текущей выдачи!).")
    lines.append("")
    if note:
        lines.append(note.strip())
        lines.append("")
    lines.append("Дата снятия: %s" % date_str)
    lines.append("")
    lines.append("Всего значений: %d" % len(rows))
    lines.append("")
    for v, t in rows:
        lines.append("%s : %s" % (v, t))
    return "\n".join(lines) + "\n"


def main() -> None:
    args = [a for a in sys.argv[1:]]
    url_or_html = None
    use_file = False
    if args:
        if args[0] == "--html":
            use_file = True
            url_or_html = os.path.abspath(args[1]) if len(args) > 1 else None
        else:
            url_or_html = args[0]

    if not use_file and not url_or_html:
        epath = os.path.join(ROOT, "data", "events.json")
        if os.path.isfile(epath):
            ev = json.load(io.open(epath, encoding="utf-8"))
            for e in ev:
                if isinstance(e, dict) and str(e.get("url", "")).startswith(
                        "https://elementy.ru/events/"):
                    url_or_html = e["url"]
                    break
    if not url_or_html:
        print("ОШИБКА: не найден elementy-URL в data/events.json; "
              "укажите URL события аргументом.")
        sys.exit(1)

    if use_file:
        raw = io.open(url_or_html, encoding="utf-8", errors="replace").read()
        print("Источник: файл %s" % url_or_html)
    else:
        import requests
        print("Источник: %s" % url_or_html)
        raw = requests.get(url_or_html, timeout=30,
                           headers={"User-Agent": "Mozilla/5.0"}).text

    data = extract_selects(raw)
    today = datetime.date.today().strftime("%d.%m.%Y")
    os.makedirs(OUT_DIR, exist_ok=True)
    all_ok = True
    for name, fn, label in SELECTS:
        rows = data.get(name, [])
        if not rows:
            print("  %-12s -> %-12s ПРОПУЩЕН (0 значений)" % (name, fn))
            all_ok = False
            continue
        body = render_file(label, rows, NOTES.get(fn, ""), today)
        io.open(os.path.join(OUT_DIR, fn), "w", encoding="utf-8",
                newline="\n").write(body)
        print("  %-12s -> %-12s %d значений" % (name, fn, len(rows)))
    print()
    if not all_ok:
        print("РЕЗУЛЬТАТ: ошибка (какой-то список пуст).")
        sys.exit(1)
    print("РЕЗУЛЬТАТ: списки обновлены в %s (дата снятия %s)."
          % (os.path.relpath(OUT_DIR, ROOT), today))


if __name__ == "__main__":
    main()