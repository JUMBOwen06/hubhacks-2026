// Anonymous usage counts for the Impact page (impact.html).
//
// What is sent: the kind of event (visit, page_view, search, source_click), the page name,
// the search words with the number of results, and a record id. Nothing else: no cookies,
// no visitor id, no IP address or location is stored by the backend (see backend/app/impact.py).
// A "visit" is counted once per browser tab session using a sessionStorage flag that never
// leaves the browser. If the backend isn't running, nothing happens.
(function () {
  const API_BASE = (typeof window.BHH_API_BASE === 'string')
    ? window.BHH_API_BASE
    : (window.location.pathname.startsWith('/app/') ? '' : 'http://127.0.0.1:8000');

  function send(event) {
    const body = JSON.stringify(event);
    try {
      // text/plain keeps this a "simple" request: no CORS preflight, works with sendBeacon.
      const blob = new Blob([body], { type: 'text/plain' });
      if (navigator.sendBeacon && navigator.sendBeacon(API_BASE + '/events', blob)) return;
      fetch(API_BASE + '/events', { method: 'POST', body, headers: { 'Content-Type': 'text/plain' }, keepalive: true })
        .catch(() => {});
    } catch (err) {
      // counting must never break the page
    }
  }

  const file = window.location.pathname.split('/').pop() || 'index.html';
  const page = file.replace(/\.html$/, '') || 'index';
  const recordId = page === 'record' ? new URLSearchParams(window.location.search).get('id') : null;

  try {
    if (!sessionStorage.getItem('bhh_visit_counted')) {
      sessionStorage.setItem('bhh_visit_counted', '1');
      send({ kind: 'visit' });
    }
  } catch (err) {
    // sessionStorage blocked: skip the visit count
  }
  if (page !== 'impact') send({ kind: 'page_view', page, record_id: recordId || undefined });

  // "Sent to the source": a click on an outside link from a record page.
  document.addEventListener('click', (e) => {
    const a = e.target.closest && e.target.closest('a[href]');
    if (!a || !recordId) return;
    let url;
    try { url = new URL(a.href, window.location.href); } catch (err) { return; }
    if (url.origin !== window.location.origin) send({ kind: 'source_click', record_id: recordId });
  });

  let lastSearch = null;
  window.BHHTrack = {
    // Called by results.js after each search; repeated renders of the same words count once.
    search(query, results) {
      const q = (query || '').trim();
      if (!q || q === lastSearch) return;
      lastSearch = q;
      send({ kind: 'search', query: q, results });
    },
  };
})();
