# -*- coding: utf-8 -*-
"""Проверка прототипа описания события по самому prototype.json.

    python -X utf8 tools\\check_proto_json.py data\\prototypes\\<ID>\\prototype.json

Скрипт собирает текст из всех блоков, которые видит пользователь
(формальные поля, заголовок, аннотация, описание, доп. информация, блок
авторов) и прогоняет по нему механику из скиллов `proofreading` и
`post-check`: неразбиваемые пробелы, «ё», тире, кавычки, сущности.

Он НЕ заменяет два человеческих прохода (по скиллу `proofreading` и по
`post-check`) — он ловит только то, что можно проверить механически.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKER = os.path.join(HERE, "check_prototype.py")


def list_protos():
    base = os.path.join(os.path.dirname(HERE), "data", "prototypes")
    if not os.path.isdir(base):
        return []
    out = []
    for name in sorted(os.listdir(base)):
        if name.startswith("_") or name.startswith("."):
            continue
        p = os.path.join(base, name, "prototype.json")
        if os.path.isfile(p):
            out.append(p)
    return out


def main():
    targets = sys.argv[1:]
    if not targets:
        targets = list_protos()
        if not targets:
            print("Прототипов нет: data/prototypes пуста.")
            return 0
        print("Прототипов не указано — проверяю все: %d" % len(targets))
    rc = 0
    for p in targets:
        print("=" * 70)
        print("ФАЙЛ: %s" % p)
        r = subprocess.run([sys.executable, "-X", "utf8", CHECKER, "--json", p])
        if r.returncode:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
