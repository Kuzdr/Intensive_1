# -*- coding: utf-8 -*-
"""Полный список «ё» и неразбиваемых пробелов готового прототипа для аудита.

Нужен для обязательного письменного артефакта корректуры (скилл `proofreading`,
п. 0): все «ё» и все `&nbsp;` выписываются в порядке появления, с контекстом,
и получают вердикт в `audit.md`. Дословные вставки `verbatim_fragments` не
проверяются по правилам проекта, поэтому из вывода исключаются.

    python -X utf8 tools\\audit_proto_dump.py data\\prototypes\\TP-4324715\\prototype.json
"""
import argparse
import json
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def items(proto):
    """Все проверяемые тексты прототипа в порядке полей."""
    for key in ("title", "annot", "lecturer", "price_short"):
        if proto.get(key):
            yield key, str(proto[key])
    for f in proto.get("fields") or []:
        yield "поле " + str(f.get("n") or "?"), str(f.get("value") or "")
    if proto.get("desc_html"):
        yield "desc_html", str(proto["desc_html"])
    for i, e in enumerate(proto.get("extra_html") or []):
        yield "extra[%d]" % i, str(e)
    for a in proto.get("authors") or []:
        name = "автор " + str(a.get("name") or "?")
        if a.get("block_html"):
            yield name, str(a["block_html"])
        for f in a.get("fields") or []:
            yield name + " / " + str(f.get("n") or "?"), str(f.get("value") or "")


def mask_fragments(s, fragments):
    """Заменить дословные вставки пробелами — по ним правила не работают."""
    for frag in fragments:
        if frag:
            s = s.replace(frag, " " * len(frag))
    return s


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("prototype", help="путь к prototype.json")
    a = ap.parse_args()
    path = a.prototype if os.path.isabs(a.prototype) else os.path.join(ROOT, a.prototype)
    with open(path, encoding="utf-8") as f:
        proto = json.load(f)
    fragments = proto.get("verbatim_fragments") or []
    n_nbsp = n_yo = 0
    for label, raw in items(proto):
        s = mask_fragments(raw, fragments)
        for m in re.finditer("&nbsp;", s):
            n_nbsp += 1
            ctx = s[max(0, m.start() - 12):m.end() + 12].replace("\n", " ")
            print("%-38s nbsp ...%s..." % (label, ctx))
        for m in re.finditer("[ёЁ]", s):
            n_yo += 1
            ctx = s[max(0, m.start() - 12):m.end() + 12].replace("\n", " ")
            print("%-38s Ё   ...%s..." % (label, ctx))
    print("ИТОГО: nbsp %d, «ё» %d (verbatim_fragments исключены)" % (n_nbsp, n_yo))


if __name__ == "__main__":
    main()
