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
"""
import os, re, json, threading, subprocess, sys, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import protolib

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, 'site')
PY = sys.executable
PORT = int(os.environ.get('PORT', 8000))

state = {
    'running': False,
    'stage': '',          # scrape | build | git | done | error
    'percent': 0,
    'message': '',
    'report': None,       # данные из data/update_report.json
    'error': None,
    'commit': None,       # короткий hash последнего коммита
}

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

def git_publish(report):
    state['stage'] = 'git'
    state['message'] = 'Отправка изменений на GitHub…'
    msg = 'Автообновление данных: +%d новых, %d изменено, %d удалено' % (
        len(report.get('added', [])), len(report.get('changed', [])), len(report.get('removed', [])))
    for cmd in (['git', 'add', '-A'], ['git', 'commit', '-m', msg], ['git', 'push']):
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        out = (p.stdout or '') + (p.stderr or '')
        if p.returncode != 0 and not re.search(r'nothing to commit|Everything up-to-date', out):
            state['error'] = out[-800:]
            return False
    p = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
                       capture_output=True, text=True, encoding='utf-8')
    state['commit'] = (p.stdout or '').strip()
    return True

def run_pipeline():
    state['running'] = True
    try:
        state.update({'stage': 'scrape', 'percent': 0, 'message': 'Начинаем обновление…',
                      'error': None, 'commit': None, 'report': None})
        if run_step('scrape', [PY, os.path.join('scrape.py')], 2, 68) != 0:
            state['stage'] = 'error'
            state['message'] = 'Ошибка при сборе данных'
            return
        report = load_report()
        state['report'] = report
        total = len((report or {}).get('added', [])) + len((report or {}).get('changed', [])) \
            + len((report or {}).get('removed', []))
        if total == 0:
            state.update({'stage': 'done', 'percent': 100, 'message': 'Изменений нет — данные уже актуальны.'})
            return
        if run_step('build', [PY, os.path.join('build.py')], 70, 84) != 0:
            state['stage'] = 'error'
            state['message'] = 'Ошибка при сборке сайта'
            return
        if not git_publish(report):
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
    return True, p.stdout or ''


def reload_event(eid):
    """Перезагрузить одно событие с elementy.ru и пересобрать сайт.

    Кнопка «Перезагрузить с «Элементов»» на странице события: подходит, когда
    на «Элементах» что-то исправили, а ждать полного обновления не хочется.
    """
    fp = os.path.join(ROOT, 'data', 'events.json')
    try:
        evs = json.load(open(fp, encoding='utf-8'))
    except Exception as e:
        return False, 'не прочитался data/events.json: %s' % e
    ev = next((x for x in evs if str(x.get('id')) == str(eid)), None)
    if ev is None:
        return False, 'событие %s не найдено в data/events.json' % eid
    p = subprocess.run([PY, os.path.join(ROOT, 'scrape.py'), '--ids', str(eid)],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if p.returncode != 0:
        return False, 'не удалось скачать событие: %s' % ((p.stderr or '')[-300:])
    try:
        rep = json.load(open(os.path.join(ROOT, 'data', 'update_report.json'),
                             encoding='utf-8'))
    except Exception:
        rep = {}
    changed = rep.get('changed') or []
    if not changed:
        return True, 'Изменений нет — данные на «Элементах» такие же.'
    fields = ', '.join(changed[0].get('fields') or [])
    return True, 'Обновлено (%s).' % (fields or 'данные')


def proto_action(data):
    """Действие с прототипом из prototypes.js. Возвращает (ok, сообщение)."""
    pid = (data.get('id') or '').strip()
    action = (data.get('action') or '').strip()
    if not pid or '/' in pid or '\\' in pid or pid.startswith('.'):
        return False, 'неверный ID'
    if action == 'reload':
        ok, msg = reload_event(pid)
        if not ok:
            return False, msg
        ok2, out = rebuild_site()
        if not ok2:
            return False, 'сайт не пересобрался: %s' % out
        return True, msg
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
    ok, out = rebuild_site()
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
    threading.Timer(1.0, lambda: webbrowser.open('http://localhost:%d' % PORT)).start()
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()