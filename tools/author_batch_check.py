# -*- coding: utf-8 -*-
"""Пакетная проверка авторов на elementy.ru (ускоряет массовый сбор).

Использование:
  python -X utf8 tools\author_batch_check.py "Руслан Ильницкий" "Георгий Носов"
  python -X utf8 tools\author_batch_check.py --names _tmp\authors.txt
  python -X utf8 tools\author_batch_check.py --names list.txt --json out.json --refresh
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources"))
import elementy  # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    refresh = "--refresh" in sys.argv
    json_out = None
    for i, a in enumerate(sys.argv):
        if a == "--json" and i + 1 < len(sys.argv):
            json_out = sys.argv[i + 1]
    names_list = list(args)
    for i, a in enumerate(sys.argv):
        if a == "--names" and i + 1 < len(sys.argv):
            path = sys.argv[i + 1]
            try:
                with io.open(path, encoding="utf-8") as f:
                    for s in f:
                        s = s.strip()
                        if s:
                            names_list.append(s)
            except Exception as e:
                print("ERR read names:", e, file=sys.stderr)
            break
    if not names_list:
        print(__doc__)
        return 1
    res = {}
    for n in names_list:
        r = elementy.search(n, refresh=refresh)
        res[n] = r
        found = r.get("found")
        if found:
            print("✓ %s" % n)
            print("  %s" % r.get("event_url"))
            print("  ФИО: %s" % r.get("full_name"))
            print("  Фото: %s" % r.get("photo"))
            blk = r.get("block_html") or ""
            print("  Блок: %s" % (blk[:160].replace("\n", " ")))
        else:
            print("✗ %s — НЕ НАЙДЕН на «Элементах»" % n)
        print()
    if json_out:
        with io.open(json_out, "w", encoding="utf-8", newline="\n") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        print("Сохранено: %s" % json_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
