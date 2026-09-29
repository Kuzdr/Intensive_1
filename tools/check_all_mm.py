# -*- coding: utf-8 -*-
"""Прогон обоих валидаторов по всем прототипам Medio Modo (папки MM-*).

Запуск:  python -X utf8 tools\\check_all_mm.py [папка ...]
По умолчанию проверяются все data/prototypes/MM-*.
"""
import glob
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROTO_DIR = os.path.join(ROOT, "data", "prototypes")

RES = re.compile(r"(?:ошибок|ошибки)\s+(\d+)[^\d]*?(\d+)")


def run(script, args):
    p = subprocess.run([sys.executable, "-X", "utf8", script] + args,
                       cwd=ROOT, capture_output=True)
    return (p.stdout or b"").decode("utf-8", "replace") + \
           (p.stderr or b"").decode("utf-8", "replace")


def counts(text):
    m = RES.search(text)
    if m:
        return int(m.group(1)), int(m.group(2))
    if "ошибок нет" in text:
        return 0, text.count("НАВОДКА")
    return -1, -1


def problem_lines(text):
    out = []
    for i, line in enumerate(text.splitlines()):
        if line.startswith(("ОШИБКА", "НАВОДКА")):
            out.append(line.strip())
            if i + 1 < len(text.splitlines()) and "фрагмент" in text.splitlines()[i + 1]:
                out.append("    " + text.splitlines()[i + 1].strip())
    return out


def main():
    targets = sys.argv[1:] or sorted(
        os.path.basename(p) for p in glob.glob(os.path.join(PROTO_DIR, "MM-*"))
        if os.path.isdir(p))
    bad = 0
    for name in targets:
        j = os.path.join("data", "prototypes", name, "prototype.json")
        t1 = run(os.path.join("tools", "check_prototype.py"), ["--json", j])
        t2 = run(os.path.join("tools", "check_proto_json.py"), [j])
        e1, w1 = counts(t1)
        e2, w2 = counts(t2)
        flag = "OK " if e1 == 0 and e2 == 0 else "FAIL"
        if flag == "FAIL":
            bad += 1
        print("%s %-45s check_prototype: e=%s w=%s | check_proto_json: e=%s w=%s"
              % (flag, name, e1, w1, e2, w2))
        if flag == "FAIL":
            for line in problem_lines(t2) or problem_lines(t1):
                print("      " + line)
    print("---- всего: %d, с ошибками: %d" % (len(targets), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
