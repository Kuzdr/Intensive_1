# -*- coding: utf-8 -*-
r"""Чтение страницы события «Элементов»: только СВОЁ событие и свежие образцы.

Правило пользователя 23.11.2026: при разборе `elementy.ru/events/<id>/...`
учитываются только блоки самого события — `mb itemhead event` (шапка: дата,
автор, заголовок, площадка) и `itemblock memo` (описание). Блок под заголовком
«Ближайшие события» содержит карточки ДРУГИХ событий: их `sublink2`,
`sublink`, заголовки и даты к текущему событию отношения не имеют. Список
лекториев в форме фильтра — тоже не данные события.

Повод: страница 449173 (08.10.2025, Чумаков, Библиотека им. Гагарина).
Строка «Вечерняя школа Политехнического музея» в `sublink2` там относится
к карточке события 450833 после `<h2>Ближайшие события</h2>`; в собственном
блоке 449173 подзаголовка (`sublink2`) нет.

Второе правило пользователя (23.11.2026): в качестве образцов НЕ используем
события до марта 2026. Граница — 01.03.2026 включительно.

    python -X utf8 tools\elementy_detail.py <saved_page.html>
"""
import datetime
import re
import sys

NEAREST_HEAD = re.compile(r"<h2[^>]*>\s*Ближайшие\s+события\s*</h2>", re.I)
MEMO_START = re.compile(r"<div class=['\"]itemblock memo['\"]>", re.I)
HEAD_START = re.compile(r"<div class=['\"]mb itemhead event['\"]>", re.I)
DATE_IN_HEAD = re.compile(
    r"<div class=['\"]hdates['\"]>\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", re.I)
MIN_SAMPLE_DATE = datetime.date(2026, 3, 1)


def _close_div(html: str, start: int) -> int:
    """Позиция после парной `</div>` для `<div>` на позиции `start`."""
    depth = 0
    for m in re.finditer(r"<(/?)div\b", html[start:], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return start + m.end() + 1  # m.end() стоит после «div», съедаем «>»
    return len(html)


def _strip_nearest(html: str) -> str:
    """Убрать чужие карточки между «Ближайшими событиями» и своим memo."""
    m = NEAREST_HEAD.search(html)
    if not m:
        return html
    tail = html[m.end():]
    memo = MEMO_START.search(tail)
    end = memo.start() if memo else len(tail)
    return html[:m.start()] + "\n" + tail[end:]


def own_event_parts(html: str):
    """Вернуть пару (шапка, описание) только текущего события."""
    src = _strip_nearest(html)
    head = HEAD_START.search(src)
    if not head:
        return "", ""
    head_end = _close_div(src, head.start())
    memo = MEMO_START.search(src, head_end)
    memo_end = _close_div(src, memo.start()) if memo else head_end
    return (src[head.start():head_end].strip(),
            src[memo.start():memo_end].strip() if memo else "")


def own_event_html(html: str) -> str:
    """Шапка и описание своего события, без чужих карточек и меню."""
    head, memo = own_event_parts(html)
    if head or memo:
        return (head + "\n" + memo).strip()
    return _strip_nearest(html)


def event_date(html: str):
    """Дата события в формате `ГГГГ-ММ-ДД` — только из его собственной шапки."""
    head, _ = own_event_parts(html)
    m = DATE_IN_HEAD.search(head)
    if not m:
        return None
    return "%04d-%02d-%02d" % (int(m.group(3)), int(m.group(2)), int(m.group(1)))


def sample_too_old(html: str) -> bool:
    """Истинно, если образец датирован до 01.03.2026.

    Нет даты в шапке — решение принимаем вручную (False), а не угадываем.
    """
    iso = event_date(html)
    if not iso:
        return False
    return datetime.date(*[int(x) for x in iso.split("-")]) < MIN_SAMPLE_DATE


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    with open(sys.argv[1], "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    head, memo = own_event_parts(html)
    print("СВОЯ ШАПКА:")
    print(head or "(не найдена)")
    print("\nСВОЁ ОПИСАНИЕ:")
    print(memo or "(не найдено)")
    print("\nДАТА: %s; ОБРАЗЕЦ ДО 03.2026: %s"
          % (event_date(html) or "не найдена", "да" if sample_too_old(html) else "нет"))


if __name__ == "__main__":
    main()
