(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const state = (tag) => ({tag: tag,
    ids: [...document.querySelectorAll('[id]')].filter(e => /filter/i.test(e.id)).map(e => ({tag: e.tagName, id: e.id, cls: (e.className || '').slice(0, 100)})).slice(0, 30),
    modal: [...document.querySelectorAll('[class*=modal],[class*=offcanvas]')].map(e => ({tag: e.tagName, id: e.id, cls: (typeof e.className === 'string' ? e.className : '').slice(0, 120)})).slice(0, 30),
    filters: document.querySelectorAll('button.filters__filter').length,
    lectures: [...document.querySelectorAll('button.filters__filter')].filter(e => e.innerText.trim() === 'Лекции').length,
    cards: document.querySelectorAll('.events_items__card').length});
  const out = [state('initial')];
  const btn = () => [...document.querySelectorAll('button')].find(e => e.innerText.trim() === 'Фильтры');
  for (let i = 1; i <= 3; i++) {
    const b = btn();
    out.push({click: i, r: b ? b.outerHTML.slice(0, 220) : 'not-found'});
    if (b) b.click();
    await sleep(2500);
    out.push(state('after-click-' + i));
  }
  return JSON.stringify(out);
})()
