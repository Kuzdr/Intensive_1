(async () => {
  const state = (tag) => ({tag: tag,
    modal: document.querySelectorAll('.filters_modal__block').length,
    filters: document.querySelectorAll('.filters_modal__block button.filters__filter').length,
    selected: [...document.querySelectorAll('.filters_modal__block button.filters__filter')].filter(e => e.className.includes('active') || e.getAttribute('aria-pressed') === 'true').map(e => e.innerText.trim()),
    apply: [...document.querySelectorAll('button')].filter(e => e.innerText.trim() === 'Применить').map(e => e.outerHTML.slice(0, 200)),
    header: (document.querySelector('.page_content__title') || {innerText: ''}).innerText.slice(0, 200),
    cards: document.querySelectorAll('.events_items__card').length,
    badges: [...document.querySelectorAll('.events_items__card .badge')].map(e => e.innerText.trim()).filter(x => x).slice(0, 30),
    title: (document.title || '')});
  const out = [state('initial')];
  const click = (t, sel) => { const e = [...document.querySelectorAll(sel || 'button')].find(x => x.innerText.trim() === t); if (e) { e.click(); return e.outerHTML.slice(0, 250); } return 'not-found'; };
  out.push({click: 'open', r: click('Фильтры')});
  await new Promise(r => setTimeout(r, 3000));
  out.push(state('modal-open'));
  out.push({click: 'Лекции', r: click('Лекции', '.filters_modal__block button.filters__filter')});
  await new Promise(r => setTimeout(r, 3000));
  out.push(state('after-lectures'));
  return JSON.stringify(out);
})()
