# -*- coding: utf-8 -*-
"""Проверка валидности скиллов «Научного календаря».

Запускается из-под PowerShell ПЕРЕД КАЖДЫМ КОММИТОМ и после запуска
проекта/новой сессии (обязательное правило проекта, см. AGENTS.md).
Проверяет детерминированно:

1. в каждом каталоге `.opencode/skills/*` есть файл `SKILL.md`;
2. YAML-frontmatter (`name:`, `description:` между строками `---`) валиден
   (парсится штатным YAML-парсером, без ошибок синтаксиса); есть
   `name:` и `description:`, и `name` совпадает с именем каталога скилла;
3. все упоминаемые в `SKILL.md` локальные пути (`tools/…`,
   `reference/…`, `data/…`, `.opencode/…`) указывают на существующие
   файлы (сначала относительно папки скилла, затем корня проекта);
4. YAML-файлы упомянутых путей читаются (нет поломанной структуры);
5. МЕХАНИКА `tools/check_prototype.py` не ломает дословные вставки:
   режим `--fix` не правит текст внутри `verbatim_fragments`
   (регрессия 29.09.2026 — блок автора с «Элементов» расходился с оригиналом);
6. МЕХАНИКА кнопки ID источника: `build.py` распознаёт числовой ID
   в адресе сайта-источника и не берёт ID там, где его нет
   («Элементы», ВДНХ, Timepad, Архэ — правило 30.09.2026, сайты
   ВДНХ);
7. МЕХАНИКА правил nbsp: списки однобуквенных и двухбуквенных слов
   проверяются ВСЕХ регистров, включая заглавные «В тени…», «А вы…»
   (регрессия 30.09.2026, прототипы TP-4190696 и TP-4190703).

Требует PyYAML (проверка YAML детерминированным парсером, а не «на глаз»).

Использование:

    python -X utf8 tools\\check_skills.py

Код возврата: 0 — всё ОК, 1 — найдены проблемы (коммитить нельзя).
"""
import os
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_DIR = os.path.join(ROOT, ".opencode", "skills")

# Пути, которые ищем в тексте SKILL.md (локальные, не URL)
PATH_TOKEN = re.compile(
    r"(?:tools|reference|data|\.opencode)[/\\][A-Za-z0-9_.\-/\\]+"
)
# Символы, которые не могут стоять в конце пути (мусор из предложения)
TRAIL = ".,;:()\"'`*«»"


def norm(p: str) -> str:
    """`tools\\x` → `tools/x`, срезаем концевые знаки препинания."""
    p = p.replace("\\", "/").strip()
    return p.rstrip(TRAIL)


def parse_frontmatter(text: str):
    """Возвращает (meta, error). meta — dict из YAML-шапки между первыми
    `---`/`---`, error — текст ошибки YAML-парсинга или None."""
    if not text.startswith("---"):
        return {}, "нет YAML-frontmatter (файл не начинается с `---`)"
    end = text.find("\n---", 4)
    if end == -1:
        return {}, "не найдена закрывающая строка `---`"
    body = text[4:end]
    if yaml is None:
        return {}, "не установлен PyYAML (`python -X utf8 -m pip install pyyaml`)"
    try:
        meta = yaml.safe_load(body)
    except yaml.YAMLError as e:
        return {}, "YAML невалиден: %s" % e
    if not isinstance(meta, dict):
        return {}, "YAML-frontmatter должен быть словарём (получено %s)" % type(meta).__name__
    return meta, None


def check_skill(dir_path: str) -> list:
    """Проверяет один скилл. Возвращает список проблем (пустой — ОК)."""
    problems = []
    name = os.path.basename(dir_path)
    md = os.path.join(dir_path, "SKILL.md")
    if not os.path.isfile(md):
        return ["нет файла SKILL.md в %s" % name]

    with open(md, encoding="utf-8") as f:
        text = f.read()
    if text.startswith("\ufeff"):
        text = text[1:]  # снимаем BOM (некоторые редакторы его дописывают)

    meta, yerr = parse_frontmatter(text)
    if yerr:
        problems.append(yerr)
    else:
        if not meta.get("name"):
            problems.append("в frontmatter нет `name`")
        elif meta["name"] != name:
            problems.append("`name` (%s) != имя каталога (%s)" % (meta["name"], name))
        if not meta.get("description"):
            problems.append("в frontmatter нет `description`")

    for raw in PATH_TOKEN.findall(text):
        p = norm(raw)
        if not p:
            continue
        full = os.path.join(dir_path, p)
        if os.path.exists(full):
            if p.endswith((".yaml", ".yml", ".json")) and os.path.isfile(full):
                try:
                    open(full, encoding="utf-8").close()
                except OSError as e:
                    problems.append("путь %s: не читается (%s)" % (p, e))
            continue
        full = os.path.join(ROOT, p)
        if os.path.exists(full):
            continue
        problems.append("путь %s не найден (ни в скилле %s, ни в корне)" % (p, name))
    return problems


def check_verbatim_fix() -> list:
    """--fix не должен трогать дословные вставки (verbatim_fragments).

    Готовый блок с «Элементов» вставляется как есть: обычные пробелы внутри
    него — норма, и «причёсывание» тире/nbsp ломает дословность.
    """
    problems = []
    path = os.path.join(ROOT, "tools", "check_prototype.py")
    if not os.path.isfile(path):
        return problems
    import importlib.util
    spec = importlib.util.spec_from_file_location("_cp_mech", path)
    cp = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(cp)
    except Exception as e:                       # noqa: BLE001
        return ["tools/check_prototype.py не импортируется: %s" % e]
    frag = ["кафедры естественно-научных и гуманитарных дисциплин"]
    text = ("<p>Лекция 3&nbsp;октября про 15 и о 6 книгах. Факультет "
            + frag[0] + ".</p>")
    out, _n = cp.apply_fixes(text, frag)
    if frag[0] not in out:
        problems.append("--fix исказил дословный фрагмент (verbatim_fragments)")
    if "&nbsp;и" not in out or "&nbsp;книгах" not in out:
        problems.append("--fix перестал править nbsp вне дословных фрагментов")
    return problems


def check_nbsp_case() -> list:
    """Правила nbsp после однобуквенных/двухбуквенных — ВСЕ РЕГИСТРЫ.

    Регрессия 30.09.2026 (прототипы TP-4190696 «В тени космических
    гигантов» и TP-4190703): списки ONE_LETTER/TWO_LETTER записаны в
    нижнем регистре, и без re.IGNORECASE заглавные «В тени…», «А вы…»
    не проверялись — ошибка проходила валидатор молча.
    """
    problems = []
    path = os.path.join(ROOT, "tools", "check_prototype.py")
    if not os.path.isfile(path):
        return problems
    import importlib.util
    spec = importlib.util.spec_from_file_location("_cp_case", path)
    cp = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(cp)
    except Exception as e:                       # noqa: BLE001
        return ["tools/check_prototype.py не импортируется: %s" % e]

    nb = "\u00a0"
    cases = [
        # (текст, ожидаем ошибку, комментарий)
        ("В тени космических гигантов", True, "заглавная «В» + обычный пробел"),
        ("в тени космических гигантов", True, "строчная «в» + обычный пробел"),
        ("В" + nb + "тени космических гигантов", False, "после «В» уже nbsp"),
        ("А вы знаете", True, "заглавная «А» + обычный пробел"),
        ("А" + nb + "вы знаете", False, "после «А» уже nbsp"),
        ("Космос и косметика", True, "«и» + обычный пробел"),
        ("Космос и" + nb + "косметика", False, "после «и» уже nbsp"),
        ("На лекции вы узнаете", False, "после «На» обычный пробел — верно"),
        ("На" + nb + "лекции вы узнаете", True, "после «На» nbsp запрещён"),
        ("на" + nb + "лекции вы узнаете", True, "после «на» nbsp запрещён"),
        ("Но" + nb + "это не так", True, "после «Но» nbsp запрещён"),
        ("Но это не так", False, "после «Но» обычный пробел — верно"),
        ("По" + nb + "1762 год", True, "после «По» nbsp запрещён"),
        ("по 1762 год", False, "после «по» обычный пробел — верно"),
    ]
    for text, want_hit, comment in cases:
        norm = cp.analyze(text)
        hit = (bool(cp.p_nbsp_missing_after_one_letter(norm))
               or bool(cp.p_nbsp_after_two_letter(norm)))
        if hit != want_hit:
            problems.append("nbsp-правило для %r дало ошибку=%s, ожидалось %s (%s)"
                            % (text, hit, want_hit, comment))
    return problems


def check_source_ids() -> list:
    """Кнопка ID источника распознаётся только там,
    где ID есть (и не берёт лишних кнопок).

    Правило пользователя 30.09.2026: у сайтов ВДНХ есть
    числовой ID в адресе, но кнопка его не была.
    """
    problems = []
    path = os.path.join(ROOT, "build.py")
    if not os.path.isfile(path):
        return problems
    import importlib.util
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)          # build.py импортирует protolib
    spec = importlib.util.spec_from_file_location("_build_mech", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:                   # noqa: BLE001
        return ["build.py не импортируется: %s" % e]
    cases = [
        ("https://elementy.ru/events/449133/Ekskursiya_lektsiya",
         ("449133", "Элементы")),
        ("https://vdnh.ru/events/3930/", ("3930", "ВДНХ")),
        ("https://cosmos-vdnh.timepad.ru/event/4190121/",
         ("4190121", "Timepad")),
        ("https://arche.ru/events/12345", ("12345", "Архэ")),
    ]
    for url, want in cases:
        got = tuple(mod.source_num_id(url))
        if got != want:
            problems.append("source_num_id(%s) = %r, ожидалось %r"
                            % (url, got, want))
    for url in ("https://vdnh.ru/places/maket-kosmicheskogo-korablya-buran/",
                "https://vdnh.ru/",
                "https://polymus.ru/events/detail/novgorod"):
        if mod.source_num_id(url)[0] is not None:
            problems.append("source_num_id(%s) выдал лишний ID" % url)
    return problems


def main() -> None:
    if not os.path.isdir(SKILLS_DIR):
        print("нет каталога .opencode/skills")
        sys.exit(1)

    skill_dirs = sorted(d for d in os.listdir(SKILLS_DIR)
                        if os.path.isdir(os.path.join(SKILLS_DIR, d)))
    if not skill_dirs:
        print("в .opencode/skills нет скиллов")
        sys.exit(1)

    ok = True
    for d in skill_dirs:
        problems = check_skill(os.path.join(SKILLS_DIR, d))
        tag = "OK  " if not problems else "FAIL"
        print("%s %s" % (tag, d))
        for p in problems:
            print("     - %s" % p)
        ok = ok and not problems

    mech = check_verbatim_fix()
    print("%s механика: --fix не трогает verbatim_fragments"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_nbsp_case()
    print("%s механика: правила nbsp учитывают регистр букв"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_source_ids()
    print("%s механика: кнопка ID источника"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    print()
    if ok:
        print("РЕЗУЛЬТАТ: все скиллы валидны.")
        sys.exit(0)
    print("РЕЗУЛЬТАТ: найдены проблемы — исправить и прогнать заново.")
    sys.exit(1)


if __name__ == "__main__":
    main()