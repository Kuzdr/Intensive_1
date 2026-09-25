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
4. YAML-файлы упомянутых путей читаются (нет поломанной структуры).

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

    print()
    if ok:
        print("РЕЗУЛЬТАТ: все скиллы валидны.")
        sys.exit(0)
    print("РЕЗУЛЬТАТ: найдены проблемы — исправить и прогнать заново.")
    sys.exit(1)


if __name__ == "__main__":
    main()