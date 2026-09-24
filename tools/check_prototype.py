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
    """Число + ОБЫЧНЫЙ пробел + слово — должен быть nbsp («10 октября»)."""
    pat = re.compile(r"\d +(?=[А-Яа-яЁё])", re.UNICODE)
    return [m for m in pat.finditer(t)]


def p_nbsp_missing_initials(t: str):
    """Инициалы + ОБЫЧНЫЙ пробел + (инициал|фамилия) — должен быть nbsp."""
    pat_ii = re.compile(r"[А-ЯЁ]\. +[А-ЯЁ]\.", re.UNICODE)  # М. В.
    pat_is = re.compile(r"[А-ЯЁ]\. +[А-ЯЁ][а-яё]{2,}", re.UNICODE)  # М. Ломоносов
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