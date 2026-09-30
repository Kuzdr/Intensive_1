# -*- coding: utf-8 -*-
"""Локальный сервер проекта «Научный календарь».

Запуск:  python serve.py
После запуска откройте http://localhost:8000 — на главной странице появится
рабочая кнопка «Обновить данные» (сброс данных + сборка + git push).

Сервер раздаёт папку site/ и отвечает на:
  POST /api/update          — запустить обновление (одновременно в 2 раза нельзя)
  GET  /api/update/status   — текущий статус обновления (для прогресс-бара)
  POST /api/proto           — действие с прототипом: скрыть/показать, комментарий,
                              обратная связь, удаление, правка HTML-поля. Каждое
                              действие пересобирает сайт (build.py).
Автопересборка: сервер следит за папкой data/prototypes (prototype.json,
   _state.json) и пересобирает сайт, если прототип изменился извне (редактор,
   агент). Конфликты не создаёт: пересборку пропускает, пока идёт обновление
   данных или только что была пересборка после действия с прототипом.
"""
import os, re, json, threading, subprocess, sys, webbrowser, hashlib, time as _time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import protolib

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, 'site')
PY = sys.executable
PORT = int(os.environ.get('PORT', 8000))

# Когда загружен этот код. Если файл сервера меняли ПОСЛЕ запуска, работающий
# сервер — старый, и предупреждение показывается и в консоли, и в панели кнопки.
# Сравниваем СОДЕРЖИМОЕ (хэш), а не время изменения: если файл переписан без
# изменений (например, git-операцией), перезапуск не нужен, чтобы не было
# ложных предупреждений. В набор входят только файлы, загруженные в ЭТОТ
# процесс: serve.py (сам сервер) и protolib.py (импортируется). build.py сюда
# НЕ входит — он запускается отдельным процессом при каждом обновлении
# (run_step), поэтому его правки применяются при следующем нажатии «Обновить»
# без перезапуска сервера (правило 02.10.2026).
CODE_FILES = ('serve.py', 'protolib.py')

def _code_sha(fn):
    try:
        with open(os.path.join(ROOT, fn), 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return None

BASE_SHA = {fn: _code_sha(fn) for fn in CODE_FILES}

def stale_files():
    """Файлы кода, изменившиеся ПОСЛЕ запуска этого процесса."""
    out = []
    for fn in CODE_FILES:
        if BASE_SHA[fn] and _code_sha(fn) != BASE_SHA[fn]:
            out.append(fn)
    return out

state = {
    'running': False,
    'stage': '',          # scrape | protos | build | git | done | error
    'percent': 0,
    'message': '',
    'report': None,       # данные из data/update_report.json
    'proto_report': None, # сводка прохода по прототипам (total/shown/hidden/items)
    'error': None,
    'commit': None,       # короткий hash последнего коммита
    'counts': None,       # {'events': N, 'protos': M, …} — счётчик для панели
    'counts_line': '',    # готовая строка «События: … · Прототипы: …»
}

def set_counts(events=None, protos=None, ev=None, pr=None):
    """Счётчик «сколько событий / сколько прототипов» — виден с самого начала.

    Числа берутся из файлов проекта (data/events.json и папок прототипов),
    поэтому появляются мгновенно, ещё до сбора данных с сайта. По ходу
    обновления дополняются итогами: сколько событий и прототипов изменилось.
    """
    c = dict(state.get('counts') or {})
    if events is not None:
        c['events'] = events
    if protos is not None:
        c['protos'] = protos
    if ev:
        c.update(ev)
    if pr:
        c['changed_protos'] = len(pr.get('changed') or [])
    state['counts'] = c
    parts = ['События: %d' % c.get('events', 0)]
    if 'added' in c:
        parts[0] += ' (новых %d, изменено %d, удалено %d)' % (
            c.get('added', 0), c.get('changed', 0), c.get('removed', 0))
    parts.append('Прототипы: %d' % c.get('protos', 0))
    if 'changed_protos' in c:
        parts[1] += ' (изменено %d)' % c['changed_protos']
    state['counts_line'] = ' · '.join(parts)
    return state['counts_line']

def load_report():
    fp = os.path.join(ROOT, 'data', 'update_report.json')
    if os.path.exists(fp):
        try:
            return json.load(open(fp, encoding='utf-8'))
        except Exception:
            pass
    return None

def run_step(name, cmd, p0, p1):
    """Запускает дочерний процесс и читает его строки PROGRESS:pct:msg."""
    state['stage'] = name
    pr = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          encoding='utf-8', errors='replace', bufsize=1, text=True)
    tail = []
    for line in iter(pr.stdout.readline, ''):
        line = line.rstrip('\n')
        tail.append(line)
        m = re.match(r'PROGRESS:(\d+):(.*)', line)
        if m:
            pct = int(m.group(1))
            state['percent'] = p0 + (p1 - p0) * pct // 100
            state['message'] = m.group(2)
    pr.stdout.close()
    err = (pr.stderr or '')
    stderr_txt = err.read() if hasattr(err, 'read') else str(err)
    rc = pr.wait()
    if rc != 0:
        state['error'] = ('\n'.join(tail[-8:]) + '\n' + stderr_txt[-600:]).strip()
    return rc

def has_uncommitted():
    """Есть ли незакоммиченные изменения (события, прототипы, правки)."""
    p = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    return bool((p.stdout or '').strip())


# ------------------------------------------------- проход по прототипам

PROTO_DIR = os.path.join(ROOT, 'data', 'prototypes')
PROTO_STAMP = os.path.join(ROOT, 'data', 'proto_stamp.json')
PROTO_FILES = ('prototype.json', '_state.json')

def proto_fingerprint():
    """{id прототипа: подпись его файлов} — подпись меняется при правке.

    Прототипом считаем папку с `prototype.json` (так же, как build.py и
    protolib): папки только с `passport.txt` прототипами не являются.
    Подпись — по РАЗМЕРУ и хэшу содержимого, а не по времени изменения:
    время не переносится между машинами, а при `git add`/`checkout`
    меняется у всех файлов разом.
    """
    import hashlib
    out = {}
    if not os.path.isdir(PROTO_DIR):
        return out
    for name in sorted(os.listdir(PROTO_DIR)):
        if name.startswith(('_', '.')) or not os.path.isdir(os.path.join(PROTO_DIR, name)):
            continue
        if not os.path.exists(os.path.join(PROTO_DIR, name, 'prototype.json')):
            continue
        marks = []
        for fn in PROTO_FILES:
            fp = os.path.join(PROTO_DIR, name, fn)
            try:
                with open(fp, 'rb') as f:
                    data = f.read()
                # Переносы строк НЕ считаем правкой: один и тот же файл на
                # Windows (CRLF) и на сервере GitHub Pages (LF) отличается
                # только ими, а содержательно он тот же.
                data = data.replace(b'\r\n', b'\n')
                marks.append('%s:%d:%s' % (fn, len(data),
                                           hashlib.sha1(data).hexdigest()[:12]))
            except OSError:
                marks.append('%s:-' % fn)
        out[name] = '|'.join(marks)
    return out

def load_proto_stamp():
    """Подпись прототипов на момент ПОСЛЕДНЕГО обновления (пусто — если нет)."""
    if not os.path.exists(PROTO_STAMP):
        return {}
    try:
        with open(PROTO_STAMP, encoding='utf-8') as f:
            return json.load(f).get('protos') or {}
    except Exception:
        return {}

def save_proto_stamp(fps):
    """Запоминаем подпись прототипов, которые ПУБЛИКУЕМ.

    Файл `data/proto_stamp.json` — часть проекта (в Git): после клона он
    есть и соответствует уже закоммиченным прототипам, поэтому проход
    сразу показывает «0 изменённых», а не «все изменились».

    Записывается ДО `git add`: тогда подпись в коммите соответствует
    состоянию, которое мы только что отправили, и рабочая копия остаётся
    чистой (иначе появился бы вечный «есть изменения»).
    """
    try:
        if load_proto_stamp() == fps:
            return                      # ничего не поменялось — файл не трогаем
        tmp = PROTO_STAMP + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump({'date': _time.strftime('%Y-%m-%d %H:%M:%S'), 'protos': fps},
                      f, ensure_ascii=False, indent=2)
        os.replace(tmp, PROTO_STAMP)
    except Exception as e:
        print('Не удалось сохранить подпись прототипов: %s' % e)

def load_events():
    """События «Элементов» — нужны, чтобы отличить дубль (лекция уже стоит
    на «Элементах») от обычного прототипа."""
    fp = os.path.join(ROOT, 'data', 'events.json')
    try:
        with open(fp, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def hidden_snapshot():
    """Список прототипов, скрытых пользователем (из _state.json)."""
    try:
        return set(protolib.hidden_ids())
    except Exception:
        return set()


def guard_hidden(before):
    """Проверка: скрытые пользователем прототипы НЕ «восстановились».

    Вызывается после сборки, до публикации. Скрытие хранится в
    `data/prototypes/_state.json`; если файл не читается, все скрытые
    прототипы молча вернулись бы в список на сайте. Такую публикацию
    останавливаем, а не отправляем.

    Возвращает (ok, сообщение об ошибке).
    """
    ok, msg = protolib.state_health()
    if not ok:
        return False, ('Остановлено: ' + msg
                       + ' Публиковать нельзя — скрытые прототипы вернутся в список.')
    lost = sorted(set(before) - hidden_snapshot())
    if lost:
        return False, ('Остановлено: во время обновления исчезло скрытие прототипов: %s.'
                       ' Публикация отменена, чтобы скрытые прототипы не восстановились.'
                       % ', '.join(lost))
    # Файл состояния обязан попадать в Git: без него публичная версия сайта
    # (GitHub Pages) соберётся без скрытых прототипов.
    p = subprocess.run(['git', 'check-ignore', '-q', 'data/prototypes/_state.json'],
                       cwd=ROOT, capture_output=True, text=True)
    if p.returncode == 0:
        return False, ('Остановлено: data/prototypes/_state.json попал в .gitignore —'
                       ' скрытые прототипы не доедут до публичной версии сайта.')
    return True, msg


def proto_pass(evs=None, p0=62, p1=68, live=True):
    """ЯВНЫЙ проход по прототипам.

    Идём по каждому прототипу и для каждого печатаем ДВА факта:
      1) изменился ли он с прошлого обновления (сравнение с подписью);
      2) что с ним сейчас: в списке / скрыт вами / скрыт, потому что такая
         же лекция уже стоит на «Элементах» (дубль) / перенесён в архив.

    Отчёт возвращается целиком: он идёт в панель кнопки, в статистику
    обновления и в сообщение коммита.
    """
    cur = proto_fingerprint()
    prev = load_proto_stamp()
    if evs is None:
        evs = load_events()
    st = protolib.load_state()
    health_ok, health_msg = protolib.state_health()
    ids = sorted(cur) or protolib.list_ids()
    items, changed = [], []
    shown, hid_user, hid_dup, archived = [], [], [], []
    for i, pid in enumerate(ids, 1):
        mark = 'ИЗМЕНЁН' if prev.get(pid) != cur.get(pid) else 'без изменений'
        if prev.get(pid) != cur.get(pid):
            changed.append(pid)
        try:
            p = protolib.load(pid)
        except Exception as e:
            status = 'НЕ ЧИТАЕТСЯ (%s)' % e
        else:
            if protolib.is_past(p.get('date_iso')):
                status = 'перенесён в архив (лекция уже прошла)'
                archived.append(pid)
            else:
                hits, dup = protolib.find_duplicate(p, evs)
                own = protolib.state_of(st, pid)['hidden']
                if own:
                    hid_user.append(pid)
                if hits:
                    status = ('скрыт: такая же лекция уже стоит на «Элементах»'
                              ' (ID %s: %s)' % (dup['id'], ', '.join(hits)))
                    hid_dup.append(pid)
                elif own:
                    status = 'скрыт вами'
                else:
                    status = 'в списке на сайте'
                    shown.append(pid)
        items.append({'id': pid, 'mark': mark, 'status': status})
        line = '  ПРОТОТИП %s — %s; %s' % (pid, mark, status)
        print(line)
        if live:
            state['percent'] = p0 + (p1 - p0) * i // max(1, len(ids))
            state['message'] = 'Проход по прототипам (%d из %d): %s — %s' % (i, len(ids), pid, status)
            _time.sleep(0.12)          # чтобы проход был виден глазами
    hidden_total = len(set(hid_user) | set(hid_dup))
    print('ПРОТОТИПЫ: всего %d, изменено с прошлого обновления: %d; показано %d, '
          'скрыто %d (вами %d, дублей «Элементов» %d), в архиве %d'
          % (len(ids), len(changed), len(shown), hidden_total, len(set(hid_user)),
             len(set(hid_dup)), len(archived)))
    if not health_ok:
        print('ВНИМАНИЕ: ' + health_msg)
    return {
        'total': len(ids), 'checked': len(ids), 'changed': changed,
        'shown': len(shown), 'hidden': hidden_total,
        'hidden_user': sorted(set(hid_user)), 'hidden_dup': sorted(set(hid_dup)),
        'archived': sorted(archived), 'items': items,
        'state_ok': health_ok, 'state_msg': health_msg,
    }

def git_publish(report, proto_report=None, kind='pipeline'):
    state['stage'] = 'git'
    state['message'] = 'Отправка изменений на GitHub…'
    report = report or {}
    added, changed, removed = (len(report.get('added', [])), len(report.get('changed', [])),
                               len(report.get('removed', [])))
    pch = (proto_report or {}).get('changed') or []
    if kind == 'reload':
        # Кнопка «Перезагрузить с «Элементов»»: публикуем ТО, что скачали.
        ids = ', '.join(str(x.get('id', '?')) for x in (report.get('changed') or [])[:10])
        msg = 'Перезагрузка с «Элементов»: обновлено событий: %d' % changed
        if ids:
            msg += ' (%s)' % ids
    else:
        msg = ('Автообновление данных: +%d новых, %d изменено, %d удалено'
               % (added, changed, removed))
    # Прототипы в статистике коммита: сколько проверено, сколько изменилось,
    # сколько скрыто (вами / как дубли «Элементов»).
    if proto_report:
        msg += '; прототипов: %d' % proto_report.get('total', 0)
        if pch:
            msg += ', изменено: %d (%s)' % (len(pch), ', '.join(pch))
        else:
            msg += ', не изменились'
        if proto_report.get('hidden'):
            msg += '; скрыто %d (вами %d, дублей «Элементов» %d)' % (
                proto_report['hidden'], len(proto_report.get('hidden_user') or []),
                len(proto_report.get('hidden_dup') or []))
        if proto_report.get('archived'):
            msg += '; в архиве %d' % len(proto_report['archived'])
    # Подпись прототипов пишем ДО `git add`: она описывает то состояние,
    # которое мы сейчас отправляем, поэтому рабочая копия остаётся чистой,
    # а в коммите подпись соответствует опубликованным прототипам.
    save_proto_stamp(proto_fingerprint())
    for cmd in (['git', 'add', '-A'], ['git', 'commit', '-m', msg], ['git', 'push']):
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        out = (p.stdout or '') + (p.stderr or '')
        if p.returncode != 0 and not re.search(r'nothing to commit|Everything up-to-date', out):
            state['error'] = out[-800:]
            return False
    p = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    state['commit'] = (p.stdout or '').strip()
    return True

def save_report_stats(report, proto_report):
    """Дописывает в отчёт обновления сводку по прототипам.

    `data/update_report.json` — тот же отчёт, который показывает панель
    кнопки; кладём туда и прототипы, чтобы статистика обновления была в
    одном месте (и переживала перезагрузку страницы).
    """
    if not isinstance(report, dict) or not proto_report:
        return
    try:
        rep = dict(report)
        rep['protos'] = {k: v for k, v in proto_report.items() if k != 'items'}
        rep['protos_pass'] = proto_report.get('items') or []
        fp = os.path.join(ROOT, 'data', 'update_report.json')
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(rep, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print('Не удалось записать статистику прототипов в отчёт: %s' % e)


def run_pipeline():
    state['running'] = True
    try:
        state.update({'stage': 'protos', 'percent': 0,
                      'message': 'Начинаем обновление…',
                      'error': None, 'commit': None, 'report': None,
                      'proto_report': None, 'counts': None, 'counts_line': '',
                      'stale': stale_files()})
        # Счётчик появляется ПЕРВЫМ: сколько событий в календаре и сколько
        # прототипов — до того, как что-либо скачивается.
        line = set_counts(events=len(load_events()), protos=len(proto_fingerprint()))
        state['message'] = line + ' — начинаем обновление: сначала прототипы'
        if state['stale']:
            state['message'] += ' (ВНИМАНИЕ: сервер старый, нужен перезапуск — %s)' \
                                % ', '.join(state['stale'])
        # Снимок ДО обновления: после сборки проверим, что скрытые вами
        # прототипы не «восстановились» (см. guard_hidden).
        hidden_before = hidden_snapshot()

        # --- ШАГ 1. ПРОТОТИПЫ (с самого начала обновления) ----------------
        proto_report = proto_pass(load_events(), 2, 14)
        state['proto_report'] = proto_report
        set_counts(pr=proto_report)
        save_report_stats(load_report(), proto_report)
        state['percent'] = 15
        state['message'] = line + ' — прототипы проверены, переходим к событиям'

        # --- ШАГ 2. СОБЫТИЯ «ЭЛЕМЕНТЫ» ------------------------------------
        state['stage'] = 'scrape'
        if run_step('scrape', [PY, os.path.join('scrape.py')], 16, 70) != 0:
            state['stage'] = 'error'
            state['message'] = 'Ошибка при сборе данных'
            return
        report = load_report()
        state['report'] = report
        total = len((report or {}).get('added', [])) + len((report or {}).get('changed', [])) \
            + len((report or {}).get('removed', []))
        # Числа по событиям подставляем сразу после сбора.
        line = set_counts(events=(report or {}).get('total') or len(load_events()),
                          ev={'added': len((report or {}).get('added', [])),
                              'changed': len((report or {}).get('changed', [])),
                              'removed': len((report or {}).get('removed', []))})
        state['percent'] = 71
        state['message'] = line + ' — события собраны, собираем сайт'

        # Изменилось ли что-то вообще: события ИЛИ прототипы (или есть
        # незакоммиченные правки других файлов).
        protos_dirty = bool(proto_report['changed']) or has_uncommitted()
        if total == 0 and not protos_dirty:
            state.update({'stage': 'done', 'percent': 100,
                          'message': 'Изменений нет — ни события, ни прототипы '
                                     'не менялись с прошлого обновления.'})
            return
        if run_step('build', [PY, os.path.join('build.py')], 70, 86) != 0:
            state['stage'] = 'error'
            state['message'] = 'Ошибка при сборке сайта'
            return
        # Сборка могла перенести прошедшие прототипы в архив — пересчитываем
        # видимость, иначе в статистике останутся устаревшие числа.
        proto_report = proto_pass(load_events(), 86, 86, live=False)
        state['proto_report'] = proto_report
        set_counts(pr=proto_report)
        save_report_stats(report, proto_report)
        ok, why = guard_hidden(hidden_before)
        if not ok:
            state.update({'stage': 'error', 'error': why,
                          'message': 'Обновление остановлено: скрытые прототипы могли вернуться в список.'})
            return
        if not git_publish(report, proto_report):
            state['stage'] = 'error'
            state['message'] = 'Не удалось опубликовать изменения'
            return
        state.update({'stage': 'done', 'percent': 100,
                      'message': 'Готово. Сайт обновлён и опубликован.'})
    finally:
        state['running'] = False

def rebuild_site():
    """Пересборка сайта после действия с прототипом."""
    p = subprocess.run([PY, os.path.join('build.py')], cwd=ROOT, capture_output=True,
                       text=True, encoding='utf-8', errors='replace')
    if p.returncode != 0:
        return False, ((p.stdout or '') + (p.stderr or ''))[-900:]
    watch['last_rebuild'] = _time.time()
    return True, p.stdout or ''


# ------------------------------------------------------------ автопересборка

WATCH_DIR = os.path.join(ROOT, 'data', 'prototypes')
WATCH_POLL = 0.5          # период опроса файлов, сек
WATCH_DEBOUNCE = 1.0      # ждём столько без изменений, потом пересобираем
WATCH_FILES = ('prototype.json', '_state.json')
watch = {
    'snap': [],
    'changed_at': 0.0,
    'lock': threading.Lock(),
    'last_rebuild': 0.0,
    'busy': False,        # идёт пересборка (кнопка/действие) — вотчер ждёт
}

def watch_snapshot():
    """(путь, mtime_ns, размер) всех файлов прототипов — для сравнения."""
    out = []
    if not os.path.isdir(WATCH_DIR):
        return out
    for name in sorted(os.listdir(WATCH_DIR)):
        if name.startswith('_') or name.startswith('.'):
            continue
        folder = os.path.join(WATCH_DIR, name)
        for fn in WATCH_FILES:
            fp = os.path.join(folder, fn)
            try:
                st = os.stat(fp)
                out.append((fp, st.st_mtime_ns, st.st_size))
            except OSError:
                pass
    return out

def watch_loop():
    """Фоновый поток: заметили изменение прототипа — пересобираем сайт."""
    watch['snap'] = watch_snapshot()
    while True:
        _time.sleep(WATCH_POLL)
        cur = watch_snapshot()
        if cur != watch['snap']:
            watch['snap'] = cur
            watch['changed_at'] = _time.time()
            continue
        if not watch['changed_at']:
            continue
        if _time.time() - watch['changed_at'] < WATCH_DEBOUNCE:
            continue
        watch['changed_at'] = 0.0
        if state['running']:
            # идёт полное обновление данных — сборку и так сделает scrape/pipeline
            continue
        if watch['busy']:
            # сейчас пересобирает само действие с прототипом
            continue
        if _time.time() - watch['last_rebuild'] < WATCH_DEBOUNCE:
            # это наша же пересборка после действия с прототипом (build.py
            # прототипы не трогает, но _state.json мог измениться)
            continue
        threading.Thread(target=watch_rebuild, daemon=True).start()

def watch_rebuild():
    ok, out = rebuild_site()
    watch['last_rebuild'] = _time.time()
    if not ok:
        print('Автопересборка после правки прототипа: ОШИБКА\n%s' % out)
    else:
        print('Автопересборка после правки прототипа: готово')


def reload_event(eid):
    """Перезагрузить одно событие с elementy.ru.

    Кнопка «Перезагрузить с «Элементов»» на странице события: подходит, когда
    на «Элементах» что-то исправили, а ждать полного обновления не хочется.
    Возвращает (ok, сообщение, изменилось ли).
    """
    fp = os.path.join(ROOT, 'data', 'events.json')
    try:
        evs = json.load(open(fp, encoding='utf-8'))
    except Exception as e:
        return False, 'не прочитался data/events.json: %s' % e, False
    ev = next((x for x in evs if str(x.get('id')) == str(eid)), None)
    if ev is None:
        return False, 'событие %s не найдено в data/events.json' % eid, False
    p = subprocess.run([PY, os.path.join(ROOT, 'scrape.py'), '--ids', str(eid)],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if p.returncode != 0:
        return False, 'не удалось скачать событие: %s' % ((p.stderr or '')[-300:]), False
    try:
        rep = json.load(open(os.path.join(ROOT, 'data', 'update_report.json'),
                             encoding='utf-8'))
    except Exception:
        rep = {}
    changed = rep.get('changed') or []
    if not changed:
        return True, 'Изменений нет — данные на «Элементах» такие же.', False
    fields = ', '.join(changed[0].get('fields') or [])
    return True, 'Обновлено (%s).' % (fields or 'данные'), True


def proto_action(data):
    """Действие с прототипом из prototypes.js. Возвращает (ok, сообщение)."""
    pid = (data.get('id') or '').strip()
    action = (data.get('action') or '').strip()
    if not pid or '/' in pid or '\\' in pid or pid.startswith('.'):
        return False, 'неверный ID'
    if action == 'reload':
        hidden_before = hidden_snapshot()
        ok, msg, changed = reload_event(pid)
        if not ok:
            return False, msg
        if not changed:
            # Данные на «Элементах» те же — публиковать нечего.
            return True, msg
        # Пересобираем сайт и ПУБЛИКУЕМ на GitHub: кнопка «Обновить данные»
        # это делает, а перезагрузка одного события раньше только
        # пересобирала сайт локально — на GitHub лекция не обновлялась.
        watch['busy'] = True
        try:
            ok2, out = rebuild_site()
        finally:
            watch['busy'] = False
        if not ok2:
            return False, 'сайт не пересобрался: %s' % out
        # Пересборка не имеет права «восстановить» скрытые прототипы.
        hidden_ok, why = guard_hidden(hidden_before)
        if not hidden_ok:
            return False, why
        if not git_publish(load_report(), proto_pass(load_events(), live=False), kind='reload'):
            return False, 'не удалось отправить изменения на GitHub%s' % (
                ': ' + state['error'] if state.get('error') else '')
        return True, msg + ' Изменение опубликовано на GitHub (коммит %s).' % (state['commit'] or '?')
    if pid not in protolib.list_ids():
        return False, 'прототип %s не найден' % pid
    try:
        if action == 'hide':
            protolib.set_state(pid, hidden=bool(data.get('hidden')))
        elif action == 'comment':
            protolib.set_state(pid, comment=(data.get('value') or '').strip())
        elif action == 'feedback':
            protolib.set_state(pid, feedback=(data.get('value') or '').strip(),
                              rebuild=bool(data.get('rebuild')))
        elif action == 'field':
            # area: fields | desc | extra | author_fields | author_block | source
            protolib.set_value(pid, data.get('area') or '', str(data.get('key') or ''),
                               data.get('value') or '')
        elif action == 'delete':
            if not protolib.archive(pid, 'удалён с сайта'):
                return False, 'не удалось убрать прототип в архив'
        else:
            return False, 'неизвестное действие %s' % action
    except KeyError as e:
        return False, str(e).strip("'")
    except Exception as e:
        return False, 'ошибка: %s' % e
    watch['busy'] = True
    try:
        ok, out = rebuild_site()
    finally:
        watch['busy'] = False
    if not ok:
        return False, 'сайт не пересобрался: %s' % out
    return True, 'готово'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SITE, **kwargs)

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == '/api/update':
            if state['running']:
                self._json({'started': False, 'running': True}, 409)
                return
            threading.Thread(target=run_pipeline, daemon=True).start()
            self._json({'started': True})
            return
        if path == '/api/proto':
            n = int(self.headers.get('Content-Length') or 0)
            if n > 4 * 1024 * 1024:
                self._json({'ok': False, 'error': 'слишком большой запрос'}, 413)
                return
            try:
                data = json.loads(self.rfile.read(n).decode('utf-8') or '{}')
            except Exception as e:
                self._json({'ok': False, 'error': 'не разобрался запрос: %s' % e}, 400)
                return
            ok, msg = proto_action(data)
            body = {'ok': ok, 'message': msg}
            if not ok:
                body['error'] = msg
            self._json(body, 200 if ok else 400)
            return
        self._json({'error': 'not found'}, 404)

    def end_headers(self):
        # Локальный сервер отдаёт файлы без кэша: иначе браузер после
        # пересборки сайта продолжает показывать старые HTML/JS/CSS
        # («кнопки не работают», «страница выглядит по-старому»).
        self.send_header('Cache-Control', 'no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/update/status':
            self._json(dict(state))
            return
        super().do_GET()

if __name__ == '__main__':
    print('Сайт «Научный календарь»: http://localhost:%d' % PORT)
    print('Чтобы остановить сервер, закройте это окно (или нажмите Ctrl+C).')
    for f in stale_files():
        print('ВНИМАНИЕ: файл %s изменён ПОСЛЕ запуска этого сервера.' % f)
        print('          Значит сервер работает на старом коде — новое (например,')
        print('          проход по прототипам при обновлении) не появится.')
        print('          Перезапустите: Ctrl+C в этом окне, затем снова python serve.py')
    threading.Thread(target=watch_loop, daemon=True).start()
    threading.Timer(1.0, lambda: webbrowser.open('http://localhost:%d' % PORT)).start()
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()