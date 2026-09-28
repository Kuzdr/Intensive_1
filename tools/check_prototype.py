# -*- coding: utf-8 -*-
"""Детерминированная проверка прототипа описания события «Научного календаря».

Запускается из-под PowerShell ОБЯЗАТЕЛЬНО перед показом пользователю любого
прототипа (формальные поля + HTML-код описания), в связке с проходами
`proofreading` (п. 0) и `post-check`. Валидатор повторяет МЕХАНИКУ правил из
скиллов (nbsp, «ё», тире, кавычки, сущности) и находит расхождения, которые
пропускает «внимательный» проход по памяти.

Использование (PowerShell):

    python -X utf8 tools\\check_prototype.py data\\prototypes\\<ID>\\prototype.json

    python -X utf8 tools\\check_prototype.py prototype.txt

Первый способ — основной: скрипт сам собирает текст ИЗ prototype.json
(все формальные поля, заголовок, аннотация карточки, описание, доп. информация,
блок автора) и дополнительно проверяет поле 1 «Привязка» по формуле.
Второй — для проверки текста, набранного в чат.

Правила не живут здесь: при изменении правила правим скилл, а этот файл —
только зеркало механики.
"""
import datetime
import io
import json
import os
import re
import sys

# --- нормализация: приводим все варианты nbsp к «±», чтобы регулярки простые
ENTITIES_NBSP = {
    "&nbsp;": "\u00A0",
    "&#160;": "\u00A0",
    "&#xa0;": "\u00A0",
}
NBSP_SYM = "\u00A0"
SENT = "\u00B1"  # sentinel для nbsp в проанализированном тексте

ONE_LETTER = ("в", "с", "к", "о", "у", "и", "а")  # после них nbsp обязателен
TWO_LETTER = ("от", "на", "по", "из", "за", "до", "для")  # после них nbsp НЕЛЬЗЯ
NO_NBSP_WORDS = ("но", "не")  # nbsp не ставим

CYR = r"а-яёА-ЯЁ"

# «ё» в словах-инвариантах — ставить НЕЛЬЗЯ (скилл `proofreading`, п. 1)
YO_INVARIANTS = (
    "ещё", "Ещё", "её", "Её",
    "учёный", "Учёный", "учёные", "Учёные",
    "идёт", "Идёт", "вперёд", "Вперёд",
    # обычные глаголы (будущее время) — без смыслоразличительной пары;
    # «ё» лишняя (прототип Секачевой, урок 26.09.2026)
    "пойдёт", "Пойдёт", "пройдёт", "Пройдёт",
    "разберёт", "Разберёт", "разберём", "Разберём",
)

# Слова для проверки «ё» — из tools/yo_words.txt (пополняемый список).
# Категории файла (заголовки «# -- N -- …»):
#   1 — проверить ТОЛЬКО эту конкретную форму (не нужна ли «ё»);
#   2 — проверить во всех формах (механически — по начальной форме);
#   3 — всегда писать с «ё» в ЭТОЙ форме (без «ё» — ошибка);
#   4 — всегда писать с «ё» во всех формах (по основе слова, ошибка).
# Слово с ЗАГЛАВНОЙ буквы в файле — проверять, только если в тексте оно
# написано с заглавной.


def load_yo_list(path: str) -> dict:
    """Читает tools/yo_words.txt → {номер_категории: [слова]}."""
    cats = {1: [], 2: [], 3: [], 4: []}
    head_re = re.compile(r"^#\s*--\s*(\d)\s*--")
    cur = None
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            m = head_re.match(line)
            if m:
                cur = int(m.group(1))
                continue
            if line.startswith("#") or cur not in cats:
                continue
            cats[cur].append(line)
    return cats


_YO_LESS = str.maketrans("ёЁ", "еЕ")
_YO_VOWELS = "аеиоуыэюяАЕИОУЫЭЮЯ"
# Типичные падежные/родовые окончания для поиска «во всех формах» (первый
# вариант — само слово без окончания). Ограниченный набор — чтобы «небо» не
# ловило «небосклон»/«небесный».
_YO_ENDINGS = (
    "", "а", "о", "я", "е", "ь", "у", "ю", "ы", "и",
    "ом", "ем", "ам", "ям", "ах", "ях", "ов", "ев",
    "ой", "ей", "ий", "ая", "ое", "ые", "ых", "ую", "юю",
    "ами", "ями", "ого", "ему",
)


def _find_yo_forms(t: str, words, all_forms=False, allow_suffix=False):
    """Ищет формы слов из списка без «ё». Возвращает [(match, слово_из_списка)].
    Слово с ЗАГЛАВНОЙ буквы в списке — находим, только если в тексте оно
    написано с заглавной (правило файла yo_words.txt).
    all_forms — «во всех формах»: основа без конечной гласной + типичные
    окончания. allow_suffix — разрешить произвольное окончание (не используем,
    оставлено запасным)."""
    hits = []
    CYR_LOW = "а-яё"
    for w in words:
        base = w.translate(_YO_LESS)
        if all_forms:
            core = base[:-1] if base[-1] in _YO_VOWELS else base
            tail = "(?:%s)" % "|".join(re.escape(e) for e in _YO_ENDINGS)
        else:
            core = base
            tail = re.escape("")
        if w[0].isupper():
            pat = re.compile(
                r"(?<![%s])(%s%s)(?![%s])" % (CYR, re.escape(core), tail, CYR),
                re.UNICODE,
            )
        else:
            pat = re.compile(
                r"(?<![%s])(%s%s)(?![%s])" % (CYR, re.escape(core), tail, CYR),
                re.IGNORECASE | re.UNICODE,
            )
        for m in pat.finditer(t):
            hits.append((m, w))
    hits.sort(key=lambda hm: hm[0].start())
    return hits


def load(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def analyze(text: str) -> str:
    for ent, sym in ENTITIES_NBSP.items():
        text = text.replace(ent, sym)
    text = text.replace(NBSP_SYM, SENT)
    return text


def p_nbsp_missing_after_one_letter(t: str):
    """Однобуквенный предлог/союз + ОБЫЧНЫЙ пробел — должен быть nbsp."""
    pat = re.compile(
        r"(?<![%s])([%s])\s+(?=[%s])" % (CYR, "".join(ONE_LETTER), CYR),
        re.UNICODE,
    )
    return [m for m in pat.finditer(t)]


def p_nbsp_after_two_letter(t: str):
    """nbsp сразу после двухбуквенных предлогов и «но»/«не» — нельзя.

    Дальше может идти ЛЮБОЕ слово, число или открывающая кавычка: правило
    «nbsp только после однобуквенных» действует и на цифры, и на «ёлочки».
    Реальный пропуск (26.09.2026, СПбГУ): «по&nbsp;1762 год» — после «по»
    nbsp не ставится никогда, а не только перед буквой.
    """
    words = list(TWO_LETTER) + list(NO_NBSP_WORDS)
    pat = re.compile(
        r"(?<![%s])((?:%s))%s(?=[%s0-9«„])" % (CYR, "|".join(words), SENT, CYR),
        re.UNICODE,
    )
    return [m for m in pat.finditer(t)]


def p_nbsp_missing_after_number(t: str):
    """Число + ОБЫЧНЫЙ пробел + слово — должен быть nbsp («10 октября»).

    ИСКЛЮЧЕНИЕ 1: число уже привязано nbsp к слову ДО него («Лекция&nbsp;1
    курса…») — тогда к слову ПОСЛЕ число не относится, и nbsp после числа
    НЕ нужен. Число принадлежит одному соседнему слову: либо «после»
    («1&nbsp;миллион»), либо «до» («Лекция&nbsp;1»); к обоим сразу —
    запрещено. Записано пользователем 26.09.2026 (прототип Усанова,
    TP-4206645).
    ИСКЛЮЧЕНИЕ 2: строки-даты формальных полей 2.1 «Начало события»,
    2.3 «Поставить», 2.4 «Снять» (вида «01 октября 2026», только дата на
    строке, без слова «года») — nbsp после числа НЕ ставим. Записано
    пользователем 26.09.2026 (прототип TP-4218939, лекция Секачевой).
    Ограничено частью файла ДО первого HTML-тега — в самих HTML-кодах
    правила nbsp не меняются.
    """
    pat = re.compile(r"\d +(?=[А-Яа-яЁё])", re.UNICODE)
    bound = t.find("<")
    if bound < 0:
        bound = len(t)
    adm = _admin_date_only_spans(t, bound)
    out = []
    for m in pat.finditer(t):
        # Ищем начало ВСЕЙ последовательности цифр, а не последней цифры:
        # для многозначных чисел («из&nbsp;11 знаков», «Лекция&nbsp;12 курса»)
        # совпадение начинается с последней цифры, и проверка «перед числом»
        # сдвинулась бы на цифру. Исправлено 26.09.2026.
        i = m.start()
        while i > 0 and t[i - 1].isdigit():
            i -= 1
        if i > 0 and t[i - 1] == SENT:
            continue
        # ИСКЛЮЧЕНИЕ 3: число привязано дефисом к слову ДО него
        # («Просветитель»-2016 в номинации, книга 2005 года и т.п.) —
        # nbsp после числа не нужен. Проверяем, что дефис стоит после
        # слова/закрывающей кавычки, а не внутри числового интервала
        # («5–10 дней» с дефисом такого вида не бывает).
        if i > 0 and t[i - 1] == '-' and i >= 2 and (
                t[i - 2].isalpha() or t[i - 2] in ('»', '„', '№')):
            continue
        if any(s <= m.start() < e for s, e in adm):
            continue
        out.append(m)
    return out


_ADMIN_DATE_LINE = re.compile(
    r"^\d{1,2}\s+([а-яё]+)\s+\d{4}\s*$", re.MULTILINE | re.UNICODE
)
_ADMIN_MONTHS = {
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
}


def _admin_date_only_spans(t: str, bound: int):
    """Позиции строк-дат формальных полей 2.1/2.3/2.4 («01 октября 2026»)."""
    spans = []
    for m in _ADMIN_DATE_LINE.finditer(t):
        if m.end() > bound:
            continue
        if m.group(1).lower() in _ADMIN_MONTHS:
            spans.append((m.start(), m.end()))
    return spans


def p_nbsp_double_number(t: str):
    """Число между двумя nbsp — запрещено: число не может относиться сразу
    к обоим соседним словам. Правильно с одной стороны обычный пробел:
    «Лекция&nbsp;1 курса…» (число привязано к «Лекция»).

    ИСКЛЮЧЕНИЕ: левый nbsp после ОДНОБУКВЕННОГО предлога/союза
    («В&nbsp;2025&nbsp;году») — это обязательный nbsp после предлога (п. 1),
    он не привязывает число к левому слову; число относится только к слову
    справа, двойной привязки нет.
    """
    out = []
    for m in re.finditer(r"%s\d+%s" % (SENT, SENT), t):
        left = t[m.start() - 1] if m.start() > 0 else ""
        if left.lower() in ONE_LETTER:
            continue
        out.append(m)
    return out


def p_nbsp_missing_initials(t: str):
    """Инициалы + ОБЫЧНЫЙ пробел + (инициал|фамилия) — должен быть nbsp.

    Тут инициалы: заглавная + точка, перед которой НЕ соседняя заглавная
    (иначе это последняя буква аббревиатуры: «США. Как…» — не инициалы).
    """
    pat_ii = re.compile(r"(?<![А-ЯЁ])[А-ЯЁ]\. +[А-ЯЁ]\.", re.UNICODE)  # М. В.
    pat_is = re.compile(
        r"(?<![А-ЯЁ])[А-ЯЁ]\. +[А-ЯЁ][а-яё]{2,}", re.UNICODE
    )  # М. Ломоносов
    hits = [m for m in pat_ii.finditer(t)] + [m for m in pat_is.finditer(t)]
    hits.sort(key=lambda m: m.start())
    return hits


def p_nbsp_missing_nauka(t: str):
    """Частное правило: «NAUKA 0+» — nbsp между NAUKA и числом обязателен."""
    pat = re.compile(r"NAUKA +\d\+", re.UNICODE)
    return [m for m in pat.finditer(t)]


def p_nbsp_before_dash_missing(t: str):
    """Перед «—» (в середине предложения) ОБЯЗАТЕЛЬНО nbsp."""
    pat = re.compile(r"([%s0-9»)])\s+—" % CYR, re.UNICODE)
    return [m for m in pat.finditer(t)]


def p_nbsp_after_dash(t: str):
    """После «—» НИКОГДА не ставим nbsp (только обычный пробел)."""
    pat = re.compile(r"—%s" % SENT, re.UNICODE)
    return [m for m in pat.finditer(t)]


def p_nbsp_around_en_dash(t: str):
    """Тире-интервал «–» (числа/время): nbsp рядом НЕ ставим."""
    pat = re.compile(r"(?:%s–)|(?:–%s)" % (SENT, SENT), re.UNICODE)
    return [m for m in pat.finditer(t)]


def p_invariant_yo(t: str):
    hits = []
    for w in YO_INVARIANTS:
        for m in re.finditer(re.escape(w), t):
            hits.append(m)
    hits.sort(key=lambda m: m.start())
    return hits


def p_all_yo(t: str):
    return list(re.finditer(r"[ёЁ]", t))


def p_org_name_warning(t: str):
    """Наводка: nbsp между обычными много-буквенными словами (без чисел,
    инициалов, сокращений с точкой) — вероятно, nbsp внутри названия.
    Случаи «от&nbsp;…», «до&nbsp;…» etc. здесь не дублируем (это ошибка
    п. 2), поэтому отсекаем левое слово == двухбуквенный предлог/«но»/«не»."""
    pat = re.compile(
        r"(?<![%s])([%s]{2,})%s(?=[%s]{2,})" % (CYR, CYR, SENT, CYR),
        re.UNICODE,
    )
    banned = set(TWO_LETTER) | set(NO_NBSP_WORDS)
    return [m for m in pat.finditer(t) if m.group(1).lower() not in banned]


def p_straight_quotes(t: str):
    # кавычки в HTML-атрибутах (внутри <…>) не считаем: маскируем теги
    masked = re.sub(r"<[^>]+>", lambda m: " " * len(m.group(0)), t)
    return [m for m in re.finditer(r'"', masked)]


def p_lapki_without_outer(t: str):
    """Лапки „…“ без внешних ёлочек — ошибка (правило скилла post-check п. 9a).

    Лапки допустимы ТОЛЬКО как вложенные кавычки внутри «…». Если вокруг
    «…» нет, единственные кавычки должны быть ёлочками.
    Из реальной обратной связи (26.09.2026, Gerasimov): в формальном поле
    5 «Название лекции» стояло „всечеловеческий“ без внешних кавычек.
    """
    masked = re.sub(r"<[^>]+>", lambda m: " " * len(m.group(0)), t)
    hits = []
    for m in re.finditer("“", masked):
        open_idx = masked.rfind("„", 0, m.start())
        if open_idx < 0:
            hits.append(m)          # закрывающая без открывающей
            continue
        before, after = masked[:open_idx], masked[m.end():]
        inside = before.rfind("«") > before.rfind("»") and after.find("»") > -1
        if not inside:
            hits.append(m)
    for m in re.finditer("„", masked):          # одиночная открывающая
        if masked.find("“", m.end()) == -1:
            hits.append(m)
    hits.sort(key=lambda m: m.start())
    return hits


def p_entities_typo(t: str):
    return list(
        re.finditer(r"&(?:mdash|ndash|#8212|#8211|#151|#150);", t)
    )


# --- правила, добавленные по обратной связи пользователя 28.09.2026 ----------

ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
         "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX")


class _Span:
    """Псевдосовпадение регулярного выражения: нужно только для отчёта."""

    def __init__(self, start, end, group=""):
        self._s, self._e, self._g = start, end, group

    def start(self):
        return self._s

    def end(self):
        return self._e

    def group(self, n=0):
        return self._g


def p_roman_spacing(t: str):
    """Римские цифры в номерах (Петра&nbsp;I, Екатерины&nbsp;II) требуют
    неразбиваемого пробела.

    Перед римской цифрой nbsp обязателен. После — только если дальше идёт
    слово или запятая («Петра&nbsp;I&nbsp;до», «Екатерины&nbsp;II,&nbsp;…»);
    после цифры точка, кавычка или конец фразы — там ничего не нужно.
    В URL и именах файлов правило не применяем.
    """
    pat = re.compile(
        r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % "|".join(ROMAN),
        re.UNICODE,
    )
    out = []
    for m in pat.finditer(t):
        before = t[m.start() - 1] if m.start() else ""
        after = t[m.end()] if m.end() < len(t) else ""
        if before in "-_/\\.:0123456789" or after in "-_/\\.:0123456789":
            continue                      # часть URL, имени файла, времени
        if before != SENT:
            out.append(m)
            continue
        if after == " " or (after and (after.isalpha() or after == ",")):
            if after != SENT:
                out.append(m)
    return out


# Буквенные сокращения: ВНУТРИ ставим nbsp («и&nbsp;т.&nbsp;п.»), после
# последней точки — обычный пробел.


def p_abbrev_spacing(t: str):
    """Внутри буквенных сокращений («и т. п.», «т. е.», «и др.») — только
    неразбиваемые пробелы. Обычный пробел внутри — ошибка."""
    sep = r"[\s%s]" % SENT
    pats = [
        r"и%s+т\.%s+п\." % (sep, sep),
        r"и%s+т\.%s+д\." % (sep, sep),
        r"т\.%s+е\." % sep,
        r"т\.%s+п\." % sep,
        r"и%s+др\." % sep,
        r"см\.%s+т\.%s+е\." % (sep, sep),
    ]
    out = []
    for p in pats:
        for m in re.finditer(r"(?<![А-Яа-яЁё])%s(?![А-Яа-яЁё])" % p, t, re.UNICODE):
            base = m.start()
            for rel in re.finditer(r"\s", m.group(0)):
                a = base + rel.start()
                out.append(_Span(a, a + 1, " "))
    return out


def p_raw_nbsp_in_data(raw: str):
    """Настоящий U+00A0 в данных запрещён: в prototype.json неразбиваемый
    пробел записывается текстом `&nbsp;` (решение пользователя 28.09.2026),
    иначе его не видно глазами и он теряется при копировании.

    analyze() превращает его в sentinel, поэтому проверяем ИСХОДНЫЙ текст.
    """
    return [m for m in re.finditer("\u00A0", raw)]


def frag(t: str, m) -> str:
    s = max(0, m.start() - 4)
    return "…" + t[s : m.end() + 4].replace("\n", " ").strip() + "…"


# ------------------------------------------------- режим --json (сам прототип)

def proto_text(p: dict) -> str:
    """Весь текст прототипа, который видит пользователь: формальные поля,
    заголовок, аннотация карточки, описание, доп. информация, авторский блок.

    Собираем ОТ САМОГО JSON, а не вручную: ручной список уже упускал блоки
    (аннотацию карточки, описание автора) — и ошибки в них проходили незамеченными.

    Значения полей разделяем строкой «=====» и НЕ подписываем номерами полей:
    иначе номер склеивается со значением и даёт ложные срабатывания правил nbsp
    («2.1 06 октября» превращается в пару «1» + «06»).
    """
    SEP = "====="
    parts = [SEP]

    def add(s):
        if s and str(s).strip():
            parts.append(str(s).strip())
            parts.append(SEP)

    for f in p.get("fields") or []:
        add(f.get("value"))
    add(p.get("title"))
    add(p.get("annot"))
    add(p.get("lecturer"))
    add(p.get("desc_html"))
    for x in p.get("extra_html") or []:
        add(x)
    aus = p.get("authors")
    if not isinstance(aus, list) or not aus:
        aus = [p["author"]] if isinstance(p.get("author"), dict) else []
    for a in aus:
        add(a.get("name"))
        add(a.get("block_html"))
    return "\n".join(parts)


def field_value(p: dict, n: str) -> str:
    for f in p.get("fields") or []:
        if f.get("n") == n:
            return f.get("value") or ""
    return ""


def binding_index(hour: int, minute: int) -> str:
    """Индекс времени поля 1 «Привязка» (скилл event-description, разд. 3, п. 1).

    Одна цифра по часу: 12 часов и раньше — «0», 13…20 часов — «час − 12»,
    21 час и позже — «9».

    Вторая цифра (минуты) дописывается ТОЛЬКО для времени 13:00–20:59:
    :00 — не дописывается, до :30 — «4», ровно :30 — «6», после :30 — «8».
    Вне этого диапазона минуты в привязке не участвуют.

    Примеры: 19:00 → …7; 19:30 → …76; 19:45 → …78; 11:30 → …0; 22:45 → …9.
    """
    if hour <= 12:
        head = "0"
    elif hour <= 20:
        head = str(hour - 12)
    else:
        head = "9"
    if not (13 <= hour <= 20) or minute == 0:
        return head
    return head + ("4" if minute < 30 else ("6" if minute == 30 else "8"))


def binding_hint(hh: int, mm: int) -> str:
    """Пояснение к ожидаемой второй цифре привязки (для сообщения об ошибке)."""
    if not (13 <= hh <= 20):
        return "для этого времени вторая цифра не ставится"
    if mm == 0:
        return "начало ровно в час — минуты не дописываются"
    return "минуты: до :30 — 4, ровно :30 — 6, после :30 — 8"


def check_binding(p: dict):
    """Проверка поля 1 «Привязка» по prototype.json. Возвращает
    [(уровень, сообщение), ...]: уровень 'ОШИБКА' или 'НАВОДКА'."""
    out = []
    v = field_value(p, "1").strip()
    if not v:
        out.append(("ОШИБКА", "нет поля 1 «Привязка» "
                    "(если время начала известно — поле обязательно)"))
        return out
    date_iso = (p.get("date_iso") or "")[:10]
    tm = (p.get("time_start") or "").strip()[:5]
    if not date_iso or not re.match(r"^\d{2}:\d{2}$", tm):
        out.append(("НАВОДКА", "в JSON нет date_iso/time_start — "
                    "привязку «%s» проверить нечем" % v))
        return out
    try:
        d = datetime.date(*map(int, date_iso.split("-")))
    except Exception:
        out.append(("НАВОДКА", "не разобралась дата события «%s»" % date_iso))
        return out
    hh, mm = int(tm[:2]), int(tm[3:5])
    idx = binding_index(hh, mm)
    padded = "%04d.%02d.%02d" % (d.year, d.month, d.day)
    # ведущие нули в дате — наводка, а не ошибка: сверяем все варианты записи
    variants = [padded,
                "%04d.%d.%02d" % (d.year, d.month, d.day),
                "%04d.%02d.%d" % (d.year, d.month, d.day),
                "%04d.%d.%d" % (d.year, d.month, d.day)]
    if v == padded + idx:
        return out
    if v in [x + idx for x in variants[1:]]:
        out.append(("НАВОДКА", "дата в привязке «%s» без ведущих нулей — "
                    "сверить формат с «Элементами» (обычно %s)" % (v, padded)))
        return out
    if any(v.startswith(x) for x in variants):
        out.append(("ОШИБКА", "индекс времени в привязке «%s» != «%s» "
                    "(начало %s; %s)" % (v, idx, tm, binding_hint(hh, mm))))
    else:
        out.append(("ОШИБКА", "привязка «%s» не соответствует дате события "
                    "(для начала в %s ожидалось %s)" % (v, tm, padded + idx)))
    return out


def main() -> None:
    args = [a for a in sys.argv[1:] if a]
    if not args:
        print(__doc__)
        sys.exit(2)
    json_mode = False
    proto = None
    if args[0] in ("--json", "-j"):
        json_mode = True
        if len(args) < 2:
            print("укажите путь к prototype.json")
            sys.exit(2)
        with io.open(args[1], encoding="utf-8") as f:
            proto = json.load(f)
        orig = proto_text(proto)
    else:
        orig = load(args[0])
    t = analyze(orig)

    hard = []
    warns = []

    def display(segment):
        """Для вывода: обратно превращаем sentinel nbsp в «&nbsp;»."""
        return segment.replace(SENT, "&nbsp;")

    def emit(tag, msg, m, *, is_warn=False):
        (warns if is_warn else hard).append(
            (tag, msg, ctx(t, m.start()), frag(t, m), display)
        )

    for m in p_nbsp_missing_after_one_letter(t):
        emit("1", "нет nbsp после однобуквенного «%s»" % m.group(1), m)
    for m in p_nbsp_after_two_letter(t):
        emit("2", "nbsp после «%s» — нельзя" % m.group(1), m)
    for m in p_nbsp_missing_after_number(t):
        emit("1a", "нет nbsp между числом и словом", m)
    for m in p_nbsp_double_number(t):
        emit("1d", "nbsp с обеих сторон числа — число привязано к обоим соседним словам, запрещено", m)
    for m in p_nbsp_missing_initials(t):
        emit("1b", "нет nbsp между инициалами/инициалом и фамилией", m)
    for m in p_nbsp_missing_nauka(t):
        emit("1c", "частное правило: ожидается «NAUKA&nbsp;0+» (nbsp между NAUKA и числом)", m)
    for m in p_nbsp_before_dash_missing(t):
        emit("3", "нет nbsp ПЕРЕД «—»", m)
    for m in p_nbsp_after_dash(t):
        emit("4", "nbsp ПОСЛЕ «—» — нельзя", m)
    for m in p_nbsp_around_en_dash(t):
        emit("5", "nbsp рядом с тире-интервалом «–» — нельзя", m)
    for m in p_invariant_yo(t):
        emit("6", "«ё» в слове-инварианте — убрать", m)
    for m in p_entities_typo(t):
        emit("7", "сущность тире в HTML (использовать символ —/–)", m)
    for m in p_org_name_warning(t):
        emit("8", "nbsp между обычными словами (название организации?)", m, is_warn=True)
    for m in p_straight_quotes(t):
        emit("9", 'прямые кавычки " — заменить на «»/„“', m, is_warn=True)
    for m in p_lapki_without_outer(t):
        emit("9a", "лапки „…“ без внешних ёлочек — заменить на «…»", m)
    for m in p_roman_spacing(t):
        emit("1f", "римская цифра без nbsp с обеих сторон («Петра&nbsp;I&nbsp;до»)", m)
    for m in p_abbrev_spacing(t):
        emit("1g", "внутри сокращения обычный пробел — нужен nbsp («и&nbsp;т.&nbsp;п.»)", m)
    for m in p_raw_nbsp_in_data(orig):
        # позиция — в исходном тексте, поэтому контекст строим из orig
        s = max(0, m.start() - 30)
        seg = orig[s: m.end() + 30].replace("\n", " ")
        hard.append(("1h", "настоящий U+00A0 в данных — писать текстом «&nbsp;»",
                     seg, seg, lambda x: x.replace("\u00A0", "<U+00A0>")))
    if json_mode:
        for level, msg in check_binding(proto):
            (hard if level == "ОШИБКА" else warns).append(
                ("1e", msg, "", msg, display)
            )

    # Слова для проверки «ё» из tools/yo_words.txt (пополняемый список)
    try:
        yo_list = load_yo_list(os.path.join(os.path.dirname(os.path.abspath(__file__)), "yo_words.txt"))
    except FileNotFoundError:
        yo_list = {}

    # категория 1 — проверить конкретную форму, не нужна ли «ё» (наводка)
    for m, w in _find_yo_forms(t, yo_list.get(1, [])):
        emit("6a", "по списку yo_words: «%s» — проверить, не нужна ли „ё“" % m.group(0), m, is_warn=True)
    # категория 2 — проверить во всех формах (наводка)
    for m, w in _find_yo_forms(t, yo_list.get(2, []), all_forms=True):
        emit("6b", "по списку yo_words: «%s» — проверить во всех формах, не нужна ли „ё“" % m.group(0), m, is_warn=True)
    # категория 3 — всегда с «ё» в этой форме (ошибка)
    for m, w in _find_yo_forms(t, yo_list.get(3, [])):
        emit("6c", "по списку yo_words: «%s» — здесь всегда нужна „ё“" % m.group(0), m)
    # категория 4 — всегда с «ё» во всех формах (ошибка, по основе слова)
    for m, w in _find_yo_forms(t, yo_list.get(4, []), all_forms=True):
        emit("6d", "по списку yo_words: «%s» — всегда нужна „ё“ (во всех формах)" % m.group(0), m)

    print("=== ОШИБКИ (исправить обязательно) ===")
    if not hard:
        print("нет")
    for tag, msg, c, f, disp in hard:
        print("%s  %-52s :: %s" % ("ОШИБКА", msg, disp(c)))
        print("        найден фрагмент: %s" % disp(f))
    print()
    print("=== НАВОДКИ (проверить вручную по post-check) ===")
    if not warns:
        print("нет")
    for tag, msg, c, f, disp in warns:
        print("%-9s %-52s :: %s" % ("НАВОДКА", msg, disp(c)))
        print("        фрагмент: %s" % disp(f))

    yo = p_all_yo(t)
    already = set(m.start() for m in p_invariant_yo(t))
    extra_yo = [m for m in yo if m.start() not in already]
    print()
    print("=== СПРАВОЧНО: все «ё» в тексте (проверить каждую по скиллу) ===")
    if not yo:
        print("нет")
    for m in yo:
        lbl = "ИНВАРИАНТ" if m.start() in already else "Проверить"
        print("%-10s «%s» :: %s" % (lbl, m.group(0), ctx(t, m.start()).replace(SENT, "&nbsp;")))

    print()
    if hard:
        print(
            "РЕЗУЛЬТАТ: найдено ошибок %d, наводок %d — исправить и прогнать заново."
            % (len(hard), len(warns))
        )
        sys.exit(1)
    if warns or yo:
        print("РЕЗУЛЬТАТ: ошибок нет, наводок %d (проверить вручную)." % len(warns))
        sys.exit(0)
    print("РЕЗУЛЬТАТ: ошибок нет, наводок нет.")


def ctx(t: str, start: int, span: int = 48) -> str:
    s = max(0, start - span // 2)
    return t[s : s + span].replace("\n", "\\n")


if __name__ == "__main__":
    main()