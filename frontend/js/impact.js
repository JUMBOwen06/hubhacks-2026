// Impact page: reads the anonymous counts from GET /impact and draws them.
(function () {
  const API_BASE = (typeof window.BHH_API_BASE === 'string')
    ? window.BHH_API_BASE
    : (window.location.pathname.startsWith('/app/') ? '' : 'http://127.0.0.1:8000');
  const $ = (id) => document.getElementById(id);
  const fmt = (n) => Number(n || 0).toLocaleString('en-CA');

  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
    children.forEach((c) => node.append(c));
    return node;
  }

  function fillList(id, items, render, emptyText) {
    const list = $(id);
    list.replaceChildren(...(items.length ? items.map(render) : [el('li', { class: 'impact-empty' }, emptyText)]));
  }

  function row(label, value, href) {
    const name = href ? el('a', { href }, label) : el('span', null, label);
    return el('li', null, name, el('span', { class: 'impact-count' }, value));
  }

  // Draw at the container's real width so the axis labels stay readable on phones
  // (a fixed 700-wide viewBox scaled down to a phone shrinks 12px text to about 5px).
  let lastDaily = null;
  function chart(daily) {
    lastDaily = daily;
    const box = $('impact-chart');
    const w = Math.round(Math.min(700, Math.max(280, box.clientWidth || 700)));
    const h = w < 480 ? 160 : 200, pad = 28, n = daily.length;
    const max = Math.max(1, ...daily.map((d) => Math.max(d.searches, d.source_clicks)));
    const slot = (w - pad) / n, bar = Math.max(4, slot / 3);
    const ns = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('viewBox', `0 0 ${w} ${h + 24}`);
    svg.setAttribute('role', 'img');
    const total = daily.reduce((a, d) => a + d.searches, 0);
    const clicks = daily.reduce((a, d) => a + d.source_clicks, 0);
    svg.setAttribute('aria-label', `Bar chart: ${total} searches and ${clicks} visits to sources over the last ${n} days.`);
    const add = (tag, attrs, text) => {
      const e = document.createElementNS(ns, tag);
      for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
      if (text !== undefined) e.textContent = text;
      svg.append(e);
      return e;
    };
    add('line', { x1: pad, y1: h, x2: w, y2: h, class: 'impact-axis' });
    add('text', { x: pad - 6, y: 12, class: 'impact-tick', 'text-anchor': 'end' }, String(max));
    add('text', { x: pad - 6, y: h, class: 'impact-tick', 'text-anchor': 'end' }, '0');
    daily.forEach((d, i) => {
      const x = pad + i * slot + slot / 2;
      const hs = (d.searches / max) * (h - 16), hc = (d.source_clicks / max) * (h - 16);
      const s = add('rect', { x: x - bar - 1, y: h - hs, width: bar, height: hs, rx: 2, class: 'impact-bar-searches' });
      s.append(Object.assign(document.createElementNS(ns, 'title'), { textContent: `${d.day}: ${d.searches} searches` }));
      const c = add('rect', { x: x + 1, y: h - hc, width: bar, height: hc, rx: 2, class: 'impact-bar-clicks' });
      c.append(Object.assign(document.createElementNS(ns, 'title'), { textContent: `${d.day}: ${d.source_clicks} sent to the source` }));
      if (i % 2 === (n - 1) % 2) {
        add('text', { x, y: h + 18, class: 'impact-tick', 'text-anchor': 'middle' },
          new Date(d.day + 'T12:00:00').toLocaleDateString('en-CA', { month: 'short', day: 'numeric' }));
      }
    });
    $('impact-chart').replaceChildren(svg);
  }

  function render(s) {
    $('t-visits').textContent = fmt(s.totals.visits);
    $('t-searches').textContent = fmt(s.totals.searches);
    $('t-clicks').textContent = fmt(s.totals.source_clicks);
    $('t-insts').textContent = fmt(s.totals.institutions_reached);
    $('impact-since').textContent = s.since
      ? `Counting since ${new Date(s.since + 'T12:00:00').toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' })}. `
        + `${fmt(s.totals.searches_no_results)} of ${fmt(s.totals.searches)} searches found nothing.`
      : 'Nothing counted yet. Use the search and this page fills in.';
    fillList('impact-sent-list', s.sent_to_institutions, (x) => row(x.name, fmt(x.count)), 'No one has opened a source yet.');
    fillList('impact-gaps-list', s.searches_no_results, (x) => row(x.query, fmt(x.count), 'results.html?q=' + encodeURIComponent(x.query)), 'Every search so far found something.');
    fillList('impact-top-list', s.top_searches, (x) => row(x.query, fmt(x.count), 'results.html?q=' + encodeURIComponent(x.query)), 'No searches yet.');
    fillList('impact-viewed-list', s.most_viewed_records, (x) => row(x.title, fmt(x.count), 'record.html?id=' + encodeURIComponent(x.id)), 'No record pages viewed yet.');
    $('impact-status').hidden = true;
    $('impact-body').hidden = false;
    chart(s.daily); // after unhiding, so the chart can measure its width
  }

  async function load(key) {
    const status = $('impact-status');
    status.hidden = false;
    status.textContent = 'Loading…';
    let res;
    try {
      res = await fetch(API_BASE + '/impact?days=7' + (key ? '&key=' + encodeURIComponent(key) : ''), { headers: { Accept: 'application/json' } });
    } catch (err) {
      status.textContent = 'The Impact page needs the backend running (start.bat, then open /app/impact.html).';
      return;
    }
    if (res.status === 401) {
      status.hidden = true;
      $('impact-key-form').hidden = false;
      return;
    }
    if (!res.ok) {
      status.textContent = 'Could not load the counts (HTTP ' + res.status + ').';
      return;
    }
    $('impact-key-form').hidden = true;
    render(await res.json());
  }

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (lastDaily) chart(lastDaily); }, 150);
  });

  $('impact-key-form').addEventListener('submit', (e) => {
    e.preventDefault();
    load($('impact-key').value);
  });
  load();
})();
