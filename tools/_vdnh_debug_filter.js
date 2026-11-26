(async () => {
  const state = (tag) => ({tag: tag,
    filters: document.querySelectorAll('button.filters__filter').length,
    modal: document.querySelectorAll('.filters_modal__block').length,
    texts: [...document.querySelectorAll('button.filters__filter')].map(e => e.innerText.trim()).slice(0, 40),
    apply: [...document.querySelectorAll('button')].filter(e => e.innerText.trim() === 'Применить').length,
    cards: document.querySelectorAll('.events_items__card').length});
  const out = [state('initial')];
  const clickText = (t) => { const e = [...document.querySelectorAll('button')].find(x => x.innerText.trim() === t); if (e) { e.click(); return 'clicked'; } return 'not-found'; };
  out.push({click: 'Все фильтры #1', r: clickText('Все фильтры')});
  await new Promise(r => setTimeout(r, 3000));
  out.push(state('after1'));
  out.push({click: 'Все фильтры #2', r: clickText('Все фильтры')});
  await new Promise(r => setTimeout(r, 3000));
  out.push(state('after2'));
  out.push({click: 'Фильтры (mobile)', r: clickText('Фильтры')});
  await new Promise(r => setTimeout(r, 3000));
  out.push(state('after3'));
  return JSON.stringify(out);
})()
