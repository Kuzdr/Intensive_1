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
   (регрессия 30.09.2026, прототипы TP-4190696 и TP-4190703);
8. МЕХАНИКА абзацев описания: между блоками (</p>, </ul>, </blockquote>
   и следующим блочным тегом) обязана быть пустая строка — слитный
   `</p><p>` склеивает абзацы (урок TP-4211635, 19.10.2026);
9. МЕХАНИКА фото автора: у автора с on_elementy=true поле photo
   обязано быть заполнено (урок TP-4211635: на опубликованной странице
   у автора не было фото);
10. МЕХАНИКА вложенных кавычек: вторые «ёлочки» внутри «ёлочек» —
   ошибка, `--fix` переводит их в „лапки“ (ошибка 18.11.2026,
   EXP-261206: название с цитатой внутри);
11. МЕХАНИКА поля 7.4: «Описание автора» начинается с заглавной буквы,
   `--fix` поднимает первую букву (ошибка 18.11.2026, три прототипа
   «Экспериментаниума»).
 12. МЕХАНИКА дедупликации обхода: одно событие из двух источников
    (Timepad + сайт) распознаётся по дате и заголовку/автору, а реестр
    с BOM читается и не перезаписывается пустым (урок 22.11.2026).

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
    r"(?:tools|reference|data|\.opencode)[/\\][A-Za-z0-9_.+\-/\\]+"
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
        ("https://arhe.msk.ru/?post_type=tribe_events&p=157528",
         ("157528", "Архэ")),
        ("https://lectory2.ru/#lecture_1003", ("1003", "Живой город")),
    ]
    for url, want in cases:
        got = tuple(mod.source_num_id(url))
        if got != want:
            problems.append("source_num_id(%s) = %r, ожидалось %r"
                            % (url, got, want))
    for url in ("https://vdnh.ru/places/maket-kosmicheskogo-korablya-buran/",
                "https://vdnh.ru/",
                "https://arhe.msk.ru/",
                "https://lectory2.ru/",
                "https://polymus.ru/events/detail/novgorod"):
        if mod.source_num_id(url)[0] is not None:
            problems.append("source_num_id(%s) выдал лишний ID" % url)
    return problems


def check_yo_mertvec() -> list:
    """«мертвец» — НИКОГДА не через «ё» (правило пользователя 07.10.2026).

    Ударение на последний слог («мертвЕц», «мертвецА») — ё взяться
    неоткуда. Проверяем обе стороны: слово с «ё» ловится как ошибка
    (и автоправится --fix в «е»), слово без «ё» — не трогается.
    """
    problems = []
    path = os.path.join(ROOT, "tools", "check_prototype.py")
    if not os.path.isfile(path):
        return problems
    import importlib.util
    spec = importlib.util.spec_from_file_location("_cp_mertvec", path)
    cp = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(cp)
    except Exception as e:                       # noqa: BLE001
        return ["tools/check_prototype.py не импортируется: %s" % e]

    cases = [
        ("В клетке лежал мёртвец", True, "«мёртвец» с ё — ошибка"),
        ("Мёртвец лежал в клетке", True, "«Мёртвец» с заглавной — ошибка"),
        ("мёртвеца", True, "форма «мёртвеца» с ё — ошибка"),
        ("мертвец в клетке", False, "«мертвец» без ё — верно, не трогаем"),
        ("мертвеца", False, "«мертвеца» без ё — верно"),
        ("мертвецА", False, "«мертвецА» без ё — верно"),
    ]
    for text, want_hit, comment in cases:
        hit = bool(cp.p_invariant_yo(cp.analyze(text)))
        if hit != want_hit:
            problems.append("инвариант «мёртвец» для %r дал срабатывание=%s, "
                            "ожидалось %s (%s)" % (text, hit, want_hit, comment))
    fixed, _n = cp.apply_fixes("Мёртвец", None)
    if "ё" in fixed or "Мертвец" not in fixed:
        problems.append("--fix не убрал «ё» из «Мёртвец» (стало %r)" % fixed)
    return problems


def _load_cp(tag: str):
    """Импортирует tools/check_prototype.py; (модуль, problems)."""
    path = os.path.join(ROOT, "tools", "check_prototype.py")
    if not os.path.isfile(path):
        return None, ["нет tools/check_prototype.py"]
    import importlib.util
    spec = importlib.util.spec_from_file_location(tag, path)
    cp = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(cp)
    except Exception as e:                   # noqa: BLE001
        return None, ["tools/check_prototype.py не импортируется: %s" % e]
    return cp, []


def check_block_breaks() -> list:
    """Между блоками </p>/</ul>/</blockquote> и следующим блочным тегом
    обязана быть пустая строка (урок TP-4211635, 19.10.2026: описание
    без деления на абзацы — внутри blockquote стояло `</p><p>` слитно).
    Ловим слитный `</p><p>` и один перенос `</p>\\n<p`."""
    cp, problems = _load_cp("_cp_blocks")
    if cp is None:
        return problems
    cases = [
        ("<p>Один.</p><p>Два.</p>", True, "абзацы слитно"),
        ("<p>Один.</p>\n<p>Два.</p>", True, "между абзацами один перенос"),
        ("<p>Один.</p>\n\n<p>Два.</p>", False, "пустая строка — верно"),
        ("</p>\n\n<ul>\n<li>Раз</li>\n<li>Два</li>\n</ul>\n\n<p>Три.</p>",
         False, "список с переносами — верно"),
        ("</p>\n\n<ul><li>Раз</li><li>Два</li></ul>", False,
         "слитные элементы списка — не абзацы, не наша проверка"),
        ("</p><ul>", True, "список приклеен к абзацу"),
        ("</ul><p>", True, "абзац приклеен к списку"),
        ("<blockquote class=\"small\">\n\n<p>Аннотация.</p>\n\n<p>Ещё.</p>\n\n</blockquote>",
         False, "blockquote с пустыми строками — верно"),
        ("</p>\n\n<blockquote><p>Аннотация.</p></blockquote>", False,
         "blockquote после пустой строки — верно"),
    ]
    for text, want_hit, comment in cases:
        hit = bool(cp.p_block_breaks(text))
        if hit != want_hit:
            problems.append("проверка абзацев для %r дала срабатывание=%s, "
                            "ожидалось %s (%s)" % (text, hit, want_hit, comment))
    return problems


def check_author_photo() -> list:
    """У автора с on_elementy=true фото обязано быть заполнено
    (урок TP-4211635, 19.10.2026: опубликованная страница — без фото)."""
    cp, problems = _load_cp("_cp_aphoto")
    if cp is None:
        return problems
    cases = [
        ({"authors": [{"name": "X", "on_elementy": True, "photo": ""}]},
         True, "on_elementy без фото"),
        ({"authors": [{"name": "X", "on_elementy": True,
                       "photo": "https://elementy.ru/images/eltevents/x_100.jpg"}]},
         False, "on_elementy с фото"),
        ({"authors": [{"name": "Y", "on_elementy": False, "photo": ""}]},
         False, "новый автор без фото — не этот пункт"),
        ({"authors": []}, False, "авторов нет"),
    ]
    for proto, want_hit, comment in cases:
        hit = bool(cp.author_photo_problems(proto))
        if hit != want_hit:
            problems.append("проверка фото автора для %r дала срабатывание=%s, "
                            "ожидалось %s (%s)" % (proto, hit, want_hit, comment))
    return problems


def check_nested_quotes() -> list:
    """Вторые «ёлочки» ВНУТРИ «ёлочек» — ошибка: вложенная цитата — „лапки“.

    Ошибка 18.11.2026 (прототип EXP-261206-gubin-mifologiya-nauki):
    название с цитатой внутри стояло целиком в ёлочках. Проверяем обе
    стороны и автоправку --fix.
    """
    cp, problems = _load_cp("_cp_quotes")
    if cp is None:
        return problems
    cases = [
        ("«Мифология науки: кричал ли Архимед «Эврика!»?»", True,
         "вторые ёлочки внутри ёлочек"),
        ("«Мифология науки: кричал ли Архимед „Эврика!“?»", False,
         "вложенные лапки — верно"),
        ("Мифология науки: кричал ли Архимед «Эврика!»?", False,
         "единственная пара без внешних ёлочек — верно"),
        ("«Ученые&nbsp;— детям» в&nbsp;рамках проекта", False,
         "одна пара — не вложенность"),
        ("<b>«Пираты Карибского моря»</b> и «Часть команды&nbsp;— часть "
         "корабля»", False, "две пары подряд, не вложенные"),
        ("<p>«Название «внутри» название»</p>", True,
         "вложенность внутри абзаца"),
        ("«Он сказал: „цикл «Ученые — детям» — мой“ цикл»", False,
         "третий уровень вложенности снова ёлочки — верно (2-й уровень в лапках)"),
    ]
    for text, want_hit, comment in cases:
        hit = bool(cp.p_nested_guillemets(cp.analyze(text)))
        if hit != want_hit:
            problems.append("проверка вложенных кавычек для %r дала "
                            "срабатывание=%s, ожидалось %s (%s)"
                            % (text, hit, want_hit, comment))
    src = "«Мифология науки: кричал ли Архимед «Эврика!»?»"
    want = "«Мифология науки: кричал ли Архимед „Эврика!“?»"
    fixed, _n = cp.apply_fixes(src, None)
    if fixed != want:
        problems.append("--fix не перевёл вложенные ёлочки в лапки: %r → %r"
                        % (src, fixed))
    fixed2, n2 = cp.apply_fixes(fixed, None)
    if n2:
        problems.append("--fix вложенных кавычек не идемпотентен: %r" % fixed2)
    return problems


def check_nested_b_head() -> list:
    """Один <b> на «автор + название» в шапке, без вложенных <b>.

    Ошибка 23.11.2026 (прототип TP-4318063 и ещё шесть ВДНХ):
    `<b><i>Имя</i> <b>«Название»</b></b>` вместо
    `<b><i>Имени</i> «Название»</b>`. Родительный падеж валидатор
    проверить не может, а вложенность — может.
    """
    cp, problems = _load_cp("_cp_bhead")
    if cp is None:
        return problems
    cases = [
        ({"desc_html": "<p class=\"small\">Дата.</p>\n\n"
                       "<p>Лекция <b><i>Марата Айрапетяна</i> «Космос как "
                       "бизнес»</b>.</p>\n\n<KLBLOCK eltclub_authors_about/>"},
         False, "один <b> на автора и название — верно"),
        ({"desc_html": "<p class=\"small\">Дата.</p>\n\n"
                       "<p>Лекция <b><i>Марат Айрапетян</i> <b>«Космос как "
                       "бизнес»</b></b>.</p>\n\n<KLBLOCK eltclub_authors_about/>"},
         True, "вложенные <b> — ошибка"),
        ({"desc_html": "<p class=\"small\">Дата.</p>\n\n"
                       "<p>Лекция <i>историка</i> <b><i>Андрея Шаповалова</i> "
                       "«Сибирские шаманы»</b>&nbsp;— седьмая лекция курса "
                       "<b>«Вселенная Сибири»</b>.</p>\n\n<KLBLOCK x/>"},
         False, "два последовательных <b>, не вложенных — верно"),
        ({"desc_html": ""}, False, "пустое описание"),
    ]
    for proto, want_hit, comment in cases:
        hit = bool(cp.p_nested_b_in_head(proto))
        if hit != want_hit:
            problems.append("проверка вложенных <b> в шапке дала "
                            "срабатывание=%s, ожидалось %s (%s)"
                            % (hit, want_hit, comment))
    return problems


def check_author_desc_capital() -> list:
    """Поле 7.4 «Описание автора» начинается с заглавной буквы.

    Ошибка 18.11.2026 (прототипы EXP-261122/EXP-261206/EXP-261213): во всех
    трёх 7.4 начиналось со строчной; в тексте аннотации после тире строчная
    при этом правильна, поэтому проверяем только поле 7.4.
    """
    cp, problems = _load_cp("_cp_a74")
    if cp is None:
        return problems
    cases = [
        ({"authors": [{"name": "X", "fields": [
            {"n": "7.4", "value": "<p>специалист в&nbsp;области…</p>"}]}]},
         True, "7.4 со строчной — ошибка"),
        ({"authors": [{"name": "X", "fields": [
            {"n": "7.4", "value": "<p>Специалист в&nbsp;области…</p>"}]}]},
         False, "7.4 с заглавной — верно"),
        ({"authors": [{"name": "X", "fields": [
            {"n": "7.2", "value": "специалист"}]}]},
         False, "не 7.4 — не проверяем"),
        ({"authors": []}, False, "авторов нет"),
    ]
    for proto, want_hit, comment in cases:
        hit = bool(cp.author_desc_lowercase(proto))
        if hit != want_hit:
            problems.append("проверка заглавной в 7.4 для %r дала "
                            "срабатывание=%s, ожидалось %s (%s)"
                            % (proto, hit, want_hit, comment))
    src = "<p>специалист в&nbsp;области</p>"
    want = "<p>Специалист в&nbsp;области</p>"
    fixed, _n = cp.fix_author_desc_capital(src)
    if fixed != want:
        problems.append("--fix не поднял первую букву 7.4: %r → %r"
                        % (src, fixed))
    fixed2, n2 = cp.fix_author_desc_capital(fixed)
    if n2:
        problems.append("--fix заглавной в 7.4 не идемпотентен: %r" % fixed2)
    return problems


def check_sweep_dedup() -> list:
    """Одно событие из двух источников распознаётся как одно (22.11.2026),
    а реестр с BOM читается и не перезаписывается пустым (урок CLI в тот же
    день, когда 124 события чуть не превратились в 7).
    """
    problems = []
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import sweep_lectories as S
    except Exception as exc:                        # noqa: BLE001
        return ["не удалось импортировать sweep_lectories: %s" % exc]
    base = {"date": "2026-12-05", "time": "17:00",
            "title": "От Бернейса до блогеров: сто лет управления общественным мнением",
            "author": "Фёдор Сердотецкий"}
    site = {"date": "2026-12-05", "time": "17:00",
            "title": "Лекция преподавателя РАНХиГС и РУДН Федора Сердотецкого "
                     "«От Бернейса до блогеров: сто лет управления общественным мнением»",
            "author": "Федор Сердотецкий"}
    other = {"date": "2026-12-05", "time": "19:00",
             "title": "Мария Кюри: радиоактивность, ответственность, свобода",
             "author": "Елизавета Губанова"}
    next_day = dict(base, date="2026-12-06")
    for a, b, want, label in [
        (base, site, True, "Timepad и сайт — одно событие"),
        (base, other, False, "две лекции в один день — разные события"),
        (base, next_day, False, "тот же заголовок в другой день"),
    ]:
        got = S.same_event(a, b)
        if got != want:
            problems.append("дедупликация: %s — результат %s, ожидалось %s"
                            % (label, got, want))
    reg = {"lectories": {"zil": {"events": [dict(base, key="ZIL-4307285")]}}}
    found = S.find_existing(reg, dict(site, key="SITE-1155"))
    if not found or found[1]["key"] != "ZIL-4307285":
        problems.append("find_existing не нашёл событие по отпечатку")
    # BOM: тот же JSON с \ufeff в начале должен читаться идентично
    import io
    import json
    import tempfile
    data = {"version": 1, "lectories": {"x": {"events": [{"key": "K"}]}}}
    fd, path = tempfile.mkstemp(suffix=".json")
    try:
        with io.open(path, "w", encoding="utf-8-sig") as f:
            json.dump(data, f, ensure_ascii=False)
        if S.load_json(path, None) != data:
            problems.append("load_json не читает JSON с BOM")
    finally:
        os.close(fd)
        os.remove(path)
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

    mech = check_yo_mertvec()
    print("%s механика: «мертвец» никогда не через «ё»"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_block_breaks()
    print("%s механика: пустая строка между абзацами описания"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_author_photo()
    print("%s механика: фото автора при on_elementy"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_nested_quotes()
    print("%s механика: вложенные кавычки (ёлочки → лапки)"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_nested_b_head()
    print("%s механика: вложенные <b> в шапке описания"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_author_desc_capital()
    print("%s механика: поле 7.4 с заглавной буквы"
          % ("OK  " if not mech else "FAIL"))
    for p in mech:
        print("     - %s" % p)
    ok = ok and not mech

    mech = check_sweep_dedup()
    print("%s механика: дедупликация источников и чтение BOM реестра"
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