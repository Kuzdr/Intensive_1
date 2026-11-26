(async () => {
  const b = [...document.querySelectorAll('button')].find(e => e.innerText.trim() === 'Все фильтры');
  const clicked = b ? (b.click(), 'clicked') : 'not-found';
  await new Promise(r => setTimeout(r, 4000));
  return JSON.stringify({
    clicked: clicked,
    url: location.href,
    visible: document.body.innerText.slice(0, 7000),
    buttons: [...document.querySelectorAll('button')].map((x, i) => ({i, t: (x.innerText || '').trim().slice(0, 70), c: (x.className || '').slice(0, 100)})).filter(x => x.t).slice(0, 100),
    labels: [...document.querySelectorAll('label')].map((x, i) => ({i, t: (x.innerText || '').trim().slice(0, 70)})).filter(x => x.t).slice(0, 100),
    inputs: [...document.querySelectorAll('input,select')].map((x, i) => ({i, tag: x.tagName, type: x.type || '', value: (x.value || '').slice(0, 50), c: (x.className || '').slice(0, 80)})).slice(0, 80),
    cards: document.querySelectorAll('.events_items__card').length
  });
})()
