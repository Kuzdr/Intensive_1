# -*- coding: utf-8 -*-
"""Детерминированная проверка прототипа описания события «Научного календаря».

Запускается из-под PowerShell ОБЯЗАТЕЛЬНО перед показом пользователю любого
прототипа (формальные поля + HTML-код описания), в связке с проходами
`proofreading` (п. 0) и `post-check`. Валидатор повторяет МЕХАНИКУ правил из
скиллов (nbsp, «ё», тире, кавычки, сущности) и находит расхождения, которые
пропускает «внимательный» проход по памяти.

Использование (PowerShell):

    python -X utf8 tools\\check_prototype.py prototype.txt

Файл с прототипом: формальные поля (по строке / по абзацу) И HTML-код
описания — как он отправляется пользователю. Правила не живут здесь: при
изменении правила правим скилл, а этот файл — только зеркало механики.
"""
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
    """nbsp сразу после двухбуквенных предлогов и «но»/«не» — нельзя."""
    words = list(TWO_LETTER) + list(NO_NBSP_WORDS)
    pat = re.compile(
        r"(?<![%s])((?:%s))%s(?=[%s])" % (CYR, "|".join(words), SENT, CYR),
        re.UNICODE,
    )
    return [m for m in pat.finditer(t)]


def p_nbsp_missing_after_number(t: str):
    """Число + ОБЫЧНЫЙ пробел + слово — должен быть nbsp («10 октября»).

    ИСКЛЮЧЕНИЕ: число уже привязано nbsp к слову ДО него («Лекция&nbsp;1
    курса…») — тогда к слову ПОСЛЕ число не относится, и nbsp после числа
    НЕ нужен. Число принадлежит одному соседнему слову: либо «после»
    («1&nbsp;миллион»), либо «до» («Лекция&nbsp;1»); к обоим сразу —
    запрещено. Записано пользователем 26.09.2026 (прототип Усанова,
    TP-4206645).
    """
    pat = re.compile(r"\d +(?=[А-Яа-яЁё])", re.UNICODE)
    return [
        m
        for m in pat.finditer(t)
        if not (m.start() > 0 and t[m.start() - 1] == SENT)
    ]


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


def p_entities_typo(t: str):
    return list(
        re.finditer(r"&(?:mdash|ndash|#8212|#8211|#151|#150);", t)
    )


def frag(t: str, m) -> str:
    s = max(0, m.start() - 4)
    return "…" + t[s : m.end() + 4].replace("\n", " ").strip() + "…"


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    orig = load(sys.argv[1])
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