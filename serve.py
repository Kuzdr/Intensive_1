# -*- coding: utf-8 -*-
"""Локальный сервер проекта «Научный календарь».

Запуск:  python serve.py
После запуска откройте http://localhost:8000 — на главной странице появится
рабочая кнопка «Обновить данные» (сброс данных + сборка + git push).

Сервер раздаёт папку site/ и отвечает на:
  POST /api/update          — запустить обновление (одновременно в 2 раза нельзя)
  GET  /api/update/status   — текущий статус обновления (для прогресс-бара)
"""
import os, re, json, threading, subprocess, sys, webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

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

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SITE, **kwargs)

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path == '/api/update':
            if state['running']:
                self._json({'started': False, 'running': True}, 409)
                return
            threading.Thread(target=run_pipeline, daemon=True).start()
            self._json({'started': True})
            return
        self._json({'error': 'not found'}, 404)

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