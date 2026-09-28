# -*- coding: utf-8 -*-
"""Разовая миграция прототипов: неразбиваемый пробел → запись `&nbsp;`.

    python -X utf8 tools\\fix_nbsp_entities.py [--dry]

Правило (пользователь, 28.09.2026): в данных проекта неразбиваемый пробел
всегда записан текстом `&nbsp;` — и в формальных полях, и в HTML, и в обычном
тексте. Настоящий U+00A0 не храним.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import protolib as PL  # noqa: E402


def main():
    dry = '--dry' in sys.argv
    base = PL.PROTO_DIR
    for pid in PL.list_ids():
        p = PL.load(pid)
        raw = io.open(PL.proto_path(pid), encoding='utf-8').read()
        cnt = sum(raw.count(s) for s in PL.NBSP_SYMS if s != PL.NBSP_ENTITY)
        fixed = PL.nb_deep(p)
        new = json.dumps(fixed, ensure_ascii=False, indent=1)
        if new == raw:
            continue
        print('%s: заменено вхождений — %d%s' % (pid, cnt, ' (пробный режим)' if dry else ''))
        if not dry:
            with io.open(PL.proto_path(pid), 'w', encoding='utf-8') as f:
                f.write(new + ('' if raw.endswith('\n') else '\n'))
    print('готово')


if __name__ == '__main__':
    main()
