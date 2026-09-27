# -*- coding: utf-8 -*-
"""Прототипы лекций: хранение, состояние, поиск дублей, правка полей.

Прототип — это описание события, которого ещё нет на «Элементах», но которое
уже подготовлено агентом и выложено на сайт. Данные каждого прототипа лежат
в папке data/prototypes/<ID>/prototype.json, состояние пользователя (скрыт,
комментарий, обратная связь) — в общем файле data/prototypes/_state.json.

Модуль используют build.py (сборка сайта) и serve.py (правка с сайта).
"""
import os, io, re, json, shutil, datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
PROTO_DIR = os.path.join(ROOT, 'data', 'prototypes')
ARCHIVE_DIR = os.path.join(PROTO_DIR, '_archive')
STATE_FILE = os.path.join(PROTO_DIR, '_state.json')

# Порядок и названия формальных полей (схема event-description, раздел 2).
# Поля без значения не выводятся и не хранятся.
FIELD_ORDER = [
    ('0', 'ID события'),
    ('1', 'Привязка'),
    ('2', 'Дата события'),
    ('2.1', 'Начало события'),
    ('2.2', 'Время начала'),
    ('2.3', 'Поставить'),
    ('2.4', 'Снять'),
    ('3', 'Полный заголовок с подзаголовком'),
    ('4', 'Полный заголовок без подзаголовка'),
    ('5', 'Название лекции'),
    ('6', 'Подзаголовок'),
    ('6.1', 'Тип'),
    ('6.2', 'Место (из списка)'),
    ('6.3', 'Лекторий'),
    ('6.4', 'Тематики'),
    ('7', 'Дата и время'),
    ('8', 'Место'),
    ('9', 'Источники'),
    ('10', 'URL регистрации/покупки билета'),
    ('11', 'Стоимость'),
    ('12', 'Возрастные ограничения'),
    ('13', 'Адрес'),
    ('14', 'Аудитория'),
]

# У этих полей кнопок правки нет — они выводятся только для справки.
NO_EDIT = {'2.1', '2.3', '2.4'}

FIELD_NAMES = dict(FIELD_ORDER)
FIELD_NUMBERS = [n for n, _ in FIELD_ORDER]


def field(p, n):
    """Значение формального поля прототипа по номеру (None, если нет)."""
    for f in p.get('fields') or []:
        if f.get('n') == n:
            return f.get('value') or ''
    return None


def fields(p):
    return p.get('fields') or []


def norm(s):
    """Нормализация строки для сравнения: без регистра, ё=е, без знаков."""
    s = (s or '').lower().replace('ё', 'е')
    s = re.sub(r'[^0-9a-zа-я]+', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def person_keys(s):
    """Ключи для сравнения имён: «Имя Фамилия» и «Фамилия Имя» + по фамилии
    и имени отдельно (порядок на «Элементах» и в источниках разный)."""
    s = re.sub(r'\s+', ' ', (s or '').replace('ё', 'е').replace('Ё', 'Е')).strip()
    out = set()
    for part in re.split(r',\s*|;|\s+и\s+', s):
        part = part.strip()
        if not part or len(part.split()) < 2:
            continue
        w = part.split()
        low = norm(part)
        if low:
            out.add(low)
            out.add(' '.join(reversed(w)))
            out.add(norm(w[-1]) + ' ' + norm(w[0]))
    return out


def slugify(pid):
    """Имя файла страницы прототипа: proto-tp-4207848, proto-0-261006-budanov."""
    return 'proto-' + re.sub(r'[^0-9a-zA-Z]+', '-', str(pid)).strip('-').lower()


def field_list(values):
    """Собирает список полей из dict {номер: значение} в порядке FIELD_ORDER,
    пропуская пустые значения."""
    out = []
    for n, name in FIELD_ORDER:
        v = (values.get(n) or '').strip()
        if v:
            out.append({'n': n, 'name': name, 'value': v})
    return out


# ---------------------------------------------------------------- состояние
# Комментарии и обратная связь лежат в data/prototypes/_state.json и должны
# переживать пересборку сайта, архивирование прототипа и сбой при записи.
# Поэтому запись атомарная (через временный файл) + резервная копия,
# а при архивировании запись НЕ удаляется — иначе комментарий пропадёт
# после возврата папки из архива.

STATE_BAK = STATE_FILE + '.bak'


def _read_json(path):
    with io.open(path, encoding='utf-8') as f:
        st = json.load(f)
    if not (isinstance(st, dict) and isinstance(st.get('items'), dict)):
        raise ValueError('не похоже на состояние прототипов')
    return st


def load_state():
    """Читает состояние; при битом основном файле берёт резервную копию."""
    for path in (STATE_FILE, STATE_BAK):
        if not os.path.exists(path):
            continue
        try:
            return _read_json(path)
        except Exception:
            # битый файл не выбрасываем, а переименовываем — чтобы его можно
            # было посмотреть и вручную вытащить комментарии
            broken = path + '.broken'
            try:
                os.replace(path, broken)
            except Exception:
                pass
    return {'version': 1, 'items': {}}


def save_state(st):
    """Атомарная запись состояния + резервная копия предыдущей версии."""
    os.makedirs(PROTO_DIR, exist_ok=True)
    if os.path.exists(STATE_FILE):
        try:
            shutil.copyfile(STATE_FILE, STATE_BAK)
        except Exception:
            pass
    tmp = STATE_FILE + '.tmp'
    with io.open(tmp, 'w', encoding='utf-8') as f:
        json.dump(st, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_FILE)


def state_of(st, pid):
    it = (st.get('items') or {}).get(pid) or {}
    return {
        'hidden': bool(it.get('hidden')),
        'comment': it.get('comment') or '',
        'feedback': it.get('feedback') or '',
        'rebuild': bool(it.get('rebuild')),
    }


def set_state(pid, **kw):
    st = load_state()
    st.setdefault('version', 1)
    items = st.setdefault('items', {})
    it = dict(items.get(pid) or {})
    it.update(kw)
    if not (it.get('hidden') or it.get('comment') or it.get('feedback') or it.get('rebuild')):
        items.pop(pid, None)
    else:
        items[pid] = it
    save_state(st)
    return it


# ---------------------------------------------------------------- прототипы

def proto_path(pid):
    return os.path.join(PROTO_DIR, pid, 'prototype.json')


def list_ids():
    if not os.path.isdir(PROTO_DIR):
        return []
    out = []
    for name in sorted(os.listdir(PROTO_DIR)):
        if name.startswith('_') or name.startswith('.'):
            continue
        if os.path.isfile(proto_path(name)):
            out.append(name)
    return out


def load(pid):
    with io.open(proto_path(pid), encoding='utf-8') as f:
        return json.load(f)


def save(pid, data):
    with io.open(proto_path(pid), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
        f.write('\n')


def archive(pid, reason=''):
    """Переносит папку прототипа в data/prototypes/_archive/<ID>.

    Комментарий и обратная связь в _state.json сохраняются: если папку вернут
    из архива на место (то есть восстановят предыдущую версию прототипа),
    комментарий должен остаться.
    """
    src = os.path.join(PROTO_DIR, pid)
    if not os.path.isdir(src):
        return None
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    dst = os.path.join(ARCHIVE_DIR, pid)
    if os.path.exists(dst):
        stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        dst = os.path.join(ARCHIVE_DIR, '%s_%s' % (pid, stamp))
    shutil.move(src, dst)
    st = load_state()
    it = dict((st.get('items') or {}).get(pid) or {})
    if it:
        it['archived'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        st.setdefault('items', {})[pid] = it
        save_state(st)
    return dst


def is_past(date_iso):
    try:
        d = datetime.date(*map(int, str(date_iso).split('-')))
    except Exception:
        return False
    return d < datetime.date.today()


# ---------------------------------------------------------------- дубли

def titles_match(a, b):
    """Одинаковые названия (после нормализации). Допускаем вхождение длинного
    названия в короткое: на «Элементах» бывает «Название. Подзаголовок»."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 15 and short in long_


def find_duplicate(p, evs):
    """Ищет то же самое событие среди событий «Элементов».

    Совпадение = та же дата + хотя бы ДВА признака из трёх: название, автор,
    ссылка на источник. Возвращает (список совпавших признаков, событие)
    или (None, None).
    """
    pdate = (p.get('date_iso') or '')[:10]
    if not pdate:
        return None, None
    ppeople = person_keys(p.get('lecturer'))
    psrc = [u for u in (norm_url(x) for x in
                        (p.get('sources') or ([p.get('url')] if p.get('url') else []))) if u]
    for e in evs:
        if (e.get('date_iso') or '')[:10] != pdate:
            continue
        hits = []
        if titles_match(p.get('title'), e.get('title')):
            hits.append('название')
        epeople = person_keys(e.get('lecturer'))
        if ppeople and epeople and (ppeople & epeople):
            hits.append('автор')
        raw = ('%s %s' % ((e.get('detail_html') or ''), (e.get('url') or ''))).replace('\\', '/').lower()
        loose = norm(raw)
        for u in psrc:
            # ищем и точную ссылку (festivalnauki.ru/program/x/), и её «мягкую»
            # форму без знаков (festivalnauki ru program x) — HTML полон ссылок
            if u in raw or norm(u) in loose:
                hits.append('ссылка на источник')
                break
        if len(hits) >= 2:
            return hits, e
    return None, None


def norm_url(u):
    u = (u or '').strip().lower()
    if not u:
        return ''
    u = re.sub(r'^https?://', '', u)
    u = re.sub(r'^(www\.)?', '', u)
    return u.rstrip('/')


# ---------------------------------------------------------------- правка

def authors_list(p):
    """Список авторов прототипа. Старые прототипы: один автор в ключе author;
    новые (встреча с двумя лекторами): список authors."""
    lst = p.get('authors')
    if isinstance(lst, list) and lst:
        return [a for a in lst if isinstance(a, dict)]
    a = p.get('author')
    return [a] if isinstance(a, dict) else []


def set_authors_list(p, aus):
    """Кладём список авторов обратно, не размножая ключи: один автор —
    в author (как раньше), несколько — в authors."""
    if len(aus) == 1:
        p['author'] = aus[0]
        p.pop('authors', None)
    else:
        p['authors'] = aus
        p.pop('author', None)


def parse_author_key(key):
    """Ключ правки описания автора: 'i:номер поля' (i — индекс автора,
    начиная с 0) или просто 'номер поля' — для одиночного автора."""
    s = str(key)
    if ':' in s:
        i, _, sub = s.partition(':')
        try:
            return int(i), sub
        except ValueError:
            return 0, s
    return 0, s


def set_value(pid, area, key, value):
    """Меняет одно значение в prototype.json.

    area: 'fields' | 'desc' | 'extra' | 'author_fields' | 'author_block' | 'source'
    key:  номер формального поля / индекс абзаца доп. информации /
          номер поля описания автора
    """
    p = load(pid)
    if area == 'fields':
        hit = [f for f in p.get('fields') or [] if f.get('n') == key]
        if not hit:
            raise KeyError('нет поля %s' % key)
        hit[0]['value'] = value
    elif area == 'desc':
        p['desc_html'] = value
    elif area == 'extra':
        lst = p.get('extra_html') or []
        i = int(key)
        if not (0 <= i < len(lst)):
            raise KeyError('нет абзаца %s' % key)
        lst[i] = value
    elif area == 'source':
        # key — индекс источника; key == len(sources) добавляет новый в конец.
        # Пустая строка удаляет источник.
        lst = list(p.get('sources') or [])
        i = int(key)
        value = (value or '').strip()
        if i == len(lst):
            if not value:
                raise KeyError('нечего добавлять')
            lst.append(value)
        elif not (0 <= i < len(lst)):
            raise KeyError('нет источника %s' % key)
        elif not value:
            lst.pop(i)
        else:
            lst[i] = value
        # поле 9 «Источники» хранит тот же список — синхронизируем
        if p.get('fields'):
            for f in p['fields']:
                if f.get('n') == '9':
                    f['value'] = '<br>'.join(lst)
                    break
        p['sources'] = lst
    elif area in ('author_fields', 'author_block'):
        aus = authors_list(p)
        i, sub = parse_author_key(key)
        if not (0 <= i < len(aus)):
            raise KeyError('нет автора %s' % i)
        a = aus[i]
        if area == 'author_block':
            a['block_html'] = value
        else:
            hit = [f for f in a.get('fields') or [] if f.get('n') == sub]
            if not hit:
                raise KeyError('нет поля автора %s' % sub)
            hit[0]['value'] = value
        set_authors_list(p, aus)
    else:
        raise KeyError('неизвестный раздел %s' % area)
    save(pid, p)
    return p
