// Shared helpers for pages that read the seed dataset (results.html, record.html).
// Exposes window.BHH. Load this before results.js / record.js.
(function () {
  // Relative to the frontend/ pages; the site must be served from the repo root.
  const DATASET_URL = '../data/seed/black_history_dataset_v2_2026-11-06.json';

  const RESOURCE_TYPES = {
    archival_document: 'Archival document',
    book: 'Book',
    correspondence: 'Correspondence',
    journal_article: 'Journal article',
    map: 'Map',
    person_profile: 'Person profile',
    photograph: 'Photograph',
    register: 'Register',
    research_guide: 'Research guide',
    other: 'Other',
  };

  const ACCESS_MODES = { online: 'Online', mixed: 'Online & in person', unknown: 'Access unknown' };

  let datasetPromise = null;

  // Fetches the dataset once and adds lookup maps.
  function loadDataset() {
    if (!datasetPromise) {
      datasetPromise = fetch(DATASET_URL)
        .then((res) => {
          if (!res.ok) throw new Error('HTTP ' + res.status);
          return res.json();
        })
        .then((data) => {
          data.institutionsById = new Map(data.institution.map((i) => [i.id, i]));
          data.entitiesById = new Map(data.entity.map((e) => [e.id, e]));
          data.recordsById = new Map(data.record.map((r) => [r.id, r]));
          return data;
        });
      datasetPromise.catch(() => { datasetPromise = null; });
    }
    return datasetPromise;
  }

  // Small DOM builder: el('a', { href, class, text }, ...children). Never uses innerHTML.
  function el(tag, attrs, ...children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [key, value] of Object.entries(attrs)) {
        if (value === null || value === undefined || value === false) continue;
        if (key === 'class') node.className = value;
        else if (key === 'text') node.textContent = value;
        else node.setAttribute(key, value);
      }
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  function extLink(href, label, className) {
    return el('a', { href, class: className, target: '_blank', rel: 'noopener noreferrer' },
      label,
      el('span', { class: 'ext-icon', 'aria-hidden': 'true' }, ' ↗'),
      el('span', { class: 'visually-hidden' }, ' (opens in a new tab)'));
  }

  // Lowercase and strip accents so "Quebec" matches "Québec".
  function normalize(text) {
    return String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  const LOAD_ERROR_MESSAGE = 'The record data could not be loaded. If you opened this file directly from disk, '
    + 'serve the project folder with a local web server instead (for example: python -m http.server).';

  window.BHH = { DATASET_URL, RESOURCE_TYPES, ACCESS_MODES, LOAD_ERROR_MESSAGE, loadDataset, el, extLink, normalize };
})();
