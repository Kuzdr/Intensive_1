# -*- coding: utf-8 -*-
r"""Интерактивный обход афиши vdnh.ru через обычный Edge (CDP).

Режимы:
    python -X utf8 tools\cdp_vdnh_collect.py probe
    python -X utf8 tools\cdp_vdnh_collect.py evalfile tools\my_js.txt
    python -X utf8 tools\cdp_vdnh_collect.py collect --clicks 12

Снимки DOM сохраняются в data/raw/cdp/vdnh_events_<tag>.html.
"""
import argparse
import io
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cdp_read import WS, wait_target, edge_path, PORT, PROFILE, OUTDIR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://vdnh.ru/events/"


class Browser(object):
    def __init__(self, url=URL, needle="vdnh.ru", wait=15):
        os.makedirs(OUTDIR, exist_ok=True)
        # Свежий профиль на каждый запуск: прошлые открытые панели фильтров
        # и куки не должны влиять на состояние страницы.
        profile = os.path.join(OUTDIR, "edge_profile_vdnh_%d" % int(time.time()))
        self.proc = subprocess.Popen([
            edge_path(),
            "--remote-debugging-port=%d" % PORT,
            "--user-data-dir=" + profile,
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-features=Translate,EdgeWallet",
            "--new-window",
            url,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.ws = WS(wait_target(needle)["webSocketDebuggerUrl"])
        self.n = 10
        for _ in range(wait):
            if self.evaljs("document.readyState") == "complete" and len(
                    self.evaljs("document.body.innerText")) > 300:
                break
            time.sleep(1)
        time.sleep(3)

    def evaljs(self, expr):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({"id": mid, "method": "Runtime.evaluate", "params": {
            "expression": expr, "returnByValue": True,
            "awaitPromise": True}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                res = msg.get("result", {})
                if "exceptionDetails" in res:
                    raise RuntimeError(str(res["exceptionDetails"])[:500])
                return res.get("result", {}).get("value", "")

    def save(self, tag):
        html = self.evaljs("document.documentElement.outerHTML")
        path = os.path.join(OUTDIR, "vdnh_events_%s.html" % tag)
        with io.open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        return path

    def cards(self):
        js = """JSON.stringify([...document.querySelectorAll('.events_items__card')].map(e=>{
          const a=e.querySelector('a[href*="/events/"]');
          return {href:a?a.getAttribute('href'):'',
                  title:(e.querySelector('.card-text')||{innerText:''}).innerText.trim(),
                  date:(e.querySelector('.card-date')||{innerText:''}).innerText.trim(),
                  badges:[...e.querySelectorAll('.badge')].map(b=>b.innerText.trim()).filter(Boolean)};
        }))"""
        return json.loads(self.evaljs(js))

    def close(self):
        try:
            self.ws.close()
        finally:
            self.proc.terminate()


PROBE_JS = r"""JSON.stringify({
  url: location.href,
  title: document.title,
  visible: document.body.innerText.slice(0, 4000),
  buttons: [...document.querySelectorAll('button')].map((b,i)=>({i,
    t:(b.innerText||'').trim().slice(0,70), c:(b.className||'').slice(0,110)})).filter(x=>x.t).slice(0,100),
  labels: [...document.querySelectorAll('label')].map((b,i)=>({i,
    t:(b.innerText||'').trim().slice(0,70), c:(b.className||'').slice(0,90)})).filter(x=>x.t).slice(0,100),
  inputs: [...document.querySelectorAll('input,select')].map((b,i)=>({i, tag:b.tagName,
    type:b.type||'', value:(b.value||'').slice(0,50), c:(b.className||'').slice(0,90)})).slice(0,60),
  leafs: [...document.querySelectorAll('*')].filter(e=>e.children.length===0 &&
    /Лекц|Показать|Все фильтры|Фильтры/.test(e.textContent)).map(e=>({
    tag:e.tagName, t:e.textContent.trim().slice(0,60), c:(e.className||'').slice(0,90)})).slice(0,60),
  cards: document.querySelectorAll('.events_items__card').length,
  loadMore: [...document.querySelectorAll('button,a')].filter(e=>/Показать/i.test(e.textContent)).map(e=>({
    tag:e.tagName, t:e.textContent.trim().slice(0,60), c:(e.className||'').slice(0,110)}))
})"""

APPLY_LECTURE_FILTER_JS = r"""(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const txt = e => (e.innerText || '').trim();
  const btn = t => [...document.querySelectorAll('button')].find(e => txt(e) === t);
  const state = tag => ({tag: tag,
    filters: document.querySelectorAll('button.filters__filter').length,
    Lectures: [...document.querySelectorAll('button.filters__filter')].filter(e => txt(e) === 'Лекции').length,
    apply: [...document.querySelectorAll('button')].filter(e => /^Применить/.test(txt(e))).length,
    cards: document.querySelectorAll('.events_items__card').length});
  const log = [];
  // Ждём гидрацию Nuxt: кнопка «Все фильтры» и карточки афиши.
  for (let i = 0; i < 40 && (!btn('Все фильтры') || !document.querySelector('.events_items__card')); i++) await sleep(500);
  log.push(state('hydrated'));
  // Кнопка «Все фильтры» открывает форму выбора типов событий.
  let ok = false;
  for (let i = 0; i < 5; i++) {
    const b = btn('Все фильтры');
    if (!b) { log.push('Все фильтры: not-found'); await sleep(1500); continue; }
    b.click();
    log.push('click Все фильтры #' + (i + 1));
    await sleep(2500);
    const s = state('after-click-' + (i + 1));
    log.push(s);
    if (s.Lectures && s.apply) { ok = true; break; }
  }
  if (!ok) return JSON.stringify({status: 'form-not-found', log: log});
  // Выбираем тип «Лекции» в открывшейся форме.
  const lec = [...document.querySelectorAll('button.filters__filter')].filter(e => txt(e) === 'Лекции');
  lec[lec.length - 1].click();
  await sleep(1000);
  log.push(state('after-select-Лекции'));
  // Применяем фильтр.
  const apply = [...document.querySelectorAll('button')].find(e => /^Применить/.test(txt(e)));
  if (!apply) return JSON.stringify({status: 'apply-not-found', log: log});
  apply.click();
  await sleep(5000);
  const badges = [...document.querySelectorAll('.events_items__card .badge')]
    .map(e => txt(e)).filter(x => x);
  return JSON.stringify({status: 'applied', url: location.href, log: log,
    cards: document.querySelectorAll('.events_items__card').length,
    header: [...document.querySelectorAll('h1,h2,h3')].map(e => txt(e)).slice(0, 6),
    badges: badges.slice(0, 40)});
})()"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=["probe", "evalfile", "collect"])
    ap.add_argument("jsfile", nargs="?", help="файл с JS для режима evalfile")
    ap.add_argument("--url", default=URL)
    ap.add_argument("--clicks", type=int, default=12)
    ap.add_argument("--wait", type=int, default=15)
    ap.add_argument("--tag", default="lectures", help="префикс для файлов снимков")
    a = ap.parse_args()

    b = Browser(a.url, wait=a.wait)
    try:
        if a.mode == "probe":
            print(b.evaljs(PROBE_JS))
            path = b.save("probe")
            print("DOM:", os.path.relpath(path, ROOT))
        elif a.mode == "evalfile":
            js = io.open(a.jsfile, encoding="utf-8").read()
            print(b.evaljs(js))
        else:
            path = b.save("%s_before_filter" % a.tag)
            print("DOM до фильтра:", os.path.relpath(path, ROOT), "карточек:", len(b.cards()))
            if "/events/" in a.url and "/lektorij/" not in a.url:
                # Полная афиша: ждём гидрацию, открываем панель фильтров,
                # выбираем тип «Лекции» и нажимаем «Применить» — всё внутри JS,
                # чтобы не ловить состояние страницы между отдельными CDP-вызовами.
                result = b.evaljs(APPLY_LECTURE_FILTER_JS)
                print("Фильтр:", result)
                if "applied" not in str(result):
                    print("ВНИМАНИЕ: фильтр не подтверждён — проверьте снимок вручную")
            else:
                # Страница Лектория: отдельного фильтра нет, все карточки — лекторий.
                print("Лекторий: фильтр не требуется, собираем все карточки страницы")
            time.sleep(4)
            path = b.save("%s_step0" % a.tag)
            cards = b.cards()
            print("После фильтра:", os.path.relpath(path, ROOT), "карточек:", len(cards))
            out = os.path.join(OUTDIR, "vdnh_events_%s_cards.json" % a.tag)
            best = list(cards)

            def dump():
                with io.open(out, "w", encoding="utf-8", newline="\n") as f:
                    json.dump({"url": a.url, "cards": best, "count": len(best)}, f,
                              ensure_ascii=False, indent=2)

            dump()
            for i in range(1, a.clicks + 1):
                before = len(cards)
                clicked = b.evaljs("""(()=>{const b=[...document.querySelectorAll('button,a')]
                  .find(e=>/Показать\\s*еще/i.test(e.innerText));
                  if(!b) return 'not-found'; b.click(); return 'clicked';})()""")
                if clicked == "not-found":
                    print("Шаг %d: кнопка «Показать еще» не найдена — стоп" % i)
                    break
                time.sleep(3)
                cards = b.cards()
                path = b.save("%s_step%d" % (a.tag, i))
                print("Шаг %d: %s, карточек %d → %d, DOM %s" % (
                    i, clicked, before, len(cards), os.path.relpath(path, ROOT)))
                if len(cards) > len(best):
                    best = list(cards)
                    dump()
                if len(cards) <= before:
                    print("Новых карточек нет — стоп")
                    break
            cards = best
            print("Карточки:", os.path.relpath(out, ROOT), len(cards))
            for c in cards:
                print("  %s | %s | %s" % (c["href"], c["date"], c["title"][:80]))
    finally:
        b.close()


if __name__ == "__main__":
    main()
