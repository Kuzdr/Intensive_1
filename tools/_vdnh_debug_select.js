(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const txt = e => (e.innerText || '').trim();
  const btn = t => [...document.querySelectorAll('button')].find(e => txt(e) === t);
  const brief = tag => ({tag: tag, url: location.href,
    cards: document.querySelectorAll('.events_items__card').length,
    badges: [...document.querySelectorAll('.events_items__card .badge')].map(e => txt(e)).filter(x => x).slice(0, 12),
    headers: [...document.querySelectorAll('h1,h2,h3')].map(e => txt(e)).slice(0, 4),
    buttons: [...document.querySelectorAll('button')].map(e => txt(e)).filter(x => x).slice(-35),
    lecHtml: [...document.querySelectorAll('button.filters__filter')].filter(e => txt(e) === 'Лекции').map(e => e.outerHTML.slice(0, 300))});
  const out = [];
  for (let i = 0; i < 30 && (!btn('Все фильтры') || !document.querySelector('.events_items__card')); i++) await sleep(500);
  btn('Все фильтры').click();
  await sleep(2500);
  out.push(brief('form-open'));
  const lec = [...document.querySelectorAll('button.filters__filter')].filter(e => txt(e) === 'Лекции');
  lec[lec.length - 1].click();
  await sleep(1000);
  out.push(brief('after-select-1s'));
  await sleep(5000);
  out.push(brief('after-select-6s'));
  return JSON.stringify(out);
})()
