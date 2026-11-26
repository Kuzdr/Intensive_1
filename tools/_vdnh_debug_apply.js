(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const btn = t => [...document.querySelectorAll('button')].find(e => e.innerText.trim() === t);
  const info = tag => ({tag: tag, url: location.href,
    offcanvas: document.querySelectorAll('.offcanvas.show').length,
    filters: document.querySelectorAll('button.filters__filter').length,
    lectures: [...document.querySelectorAll('button.filters__filter')].filter(e => e.innerText.trim() === 'Лекции').map(e => e.className),
    apply: [...document.querySelectorAll('button')].filter(e => e.innerText.trim() === 'Применить').length,
    header: [...document.querySelectorAll('h1,h2,h3')].map(e => e.innerText.trim()).slice(0, 6),
    cards: document.querySelectorAll('.events_items__card').length,
    badges: [...document.querySelectorAll('.events_items__card .badge')].map(e => e.innerText.trim()).filter(x => x).slice(0, 20)});
  const out = [];
  for (let i = 0; i < 4 && !document.querySelector('.offcanvas.show'); i++) {
    const b = btn('Фильтры'); if (b) b.click(); await sleep(2000);
  }
  out.push(info('offcanvas-open'));
  const lec = [...document.querySelectorAll('button.filters__filter')].filter(e => e.innerText.trim() === 'Лекции');
  out.push({clickLectures: lec.length ? (lec[lec.length - 1].click(), 'clicked') : 'not-found'});
  await sleep(1500);
  out.push(info('after-lectures'));
  const apply = btn('Применить');
  out.push({clickApply: apply ? (apply.click(), 'clicked') : 'not-found'});
  await sleep(5000);
  out.push(info('after-apply'));
  return JSON.stringify(out);
})()
