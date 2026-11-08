// Institutions page: builds the institution cards from /institutions (or the local
// fallback, see data.js), then lets the "Sort" menu re-order them.
// The cards written in institutions.html stay as the fallback if nothing can load.
// Record count = records held + records described (the numbers shown on each card).
const INSTITUTION_TYPES = {
  archive: 'Archive', library: 'Library', museum: 'Museum', university: 'University',
  government: 'Government', publisher: 'Publisher', community: 'Community organization', other: 'Other',
};
const INSTITUTION_ICON = '<path d="M3 21h18"/><path d="M5 21V10l7-5 7 5v11"/><path d="M9 21v-6h6v6"/>';

function renderInstitutionCard(inst) {
  const { el, extLink, plural } = window.BHH;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'card-type-icon');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  svg.innerHTML = INSTITUTION_ICON; // static markup, never from data

  const held = inst.records_held || 0;
  const supplied = inst.records_supplied || 0;
  const links = [];
  if (inst.website_url) links.push(el('li', null, extLink(inst.website_url, 'Visit website')));
  if (inst.catalogue_url) links.push(el('li', null, extLink(inst.catalogue_url, 'Search their catalogue')));
  if (inst.rights_policy_url) links.push(el('li', null, extLink(inst.rights_policy_url, 'Rights policy')));

  const bottom = (held + supplied)
    ? el('a', { class: 'card-action', href: 'results.html?' + new URLSearchParams({ institution: inst.id }).toString() },
      'View records', el('span', { class: 'visually-hidden' }, ' from ' + inst.name), ' →')
    : el('span', { class: 'card-holder' }, 'No records of its own yet');

  return el('article', { class: 'card institution-card' },
    svg,
    el('div', { class: 'card-content' },
      el('div', { class: 'card-top' }, el('span', { class: 'card-title' }, INSTITUTION_TYPES[inst.type] || inst.type)),
      el('div', { class: 'card-body' },
        el('h2', { class: 'card-heading' }, inst.name),
        inst.description ? el('p', { class: 'card-snippet institution-desc' }, inst.description) : null,
        el('p', { class: 'institution-counts' },
          el('span', null, 'Holds ', el('strong', null, plural(held, 'record'))),
          el('span', null, 'Describes ', el('strong', null, plural(supplied, 'record')))),
        links.length ? el('ul', { class: 'institution-links' }, links) : null),
      el('div', { class: 'card-bottom' }, bottom)));
}

async function loadInstitutionCards(grid) {
  if (!window.BHH) return;
  try {
    const { institutions } = await window.BHH.listInstitutions();
    if (!institutions || !institutions.length) return;
    grid.replaceChildren(...institutions.map(renderInstitutionCard));
    const countText = document.querySelector('.results-count-text');
    if (countText) {
      const records = institutions.reduce((n, i) => n + (i.records_supplied || 0), 0);
      countText.textContent = window.BHH.plural(institutions.length, 'institution') + ' · ' + window.BHH.plural(records, 'record');
    }
  } catch (err) {
    console.error('Could not load institutions; showing the cards in the page instead.', err);
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  const grid = document.getElementById('institution-grid');
  const menu = document.getElementById('institution-sort');
  if (!grid || !menu) return;

  await loadInstitutionCards(grid);

  const item = menu.querySelector('.item');
  const sortLabel = document.getElementById('sort-label');
  const radios = Array.from(menu.querySelectorAll('input[name="institution-sort"]'));

  const cards = Array.from(grid.querySelectorAll('.institution-card')).map((el, index) => {
    const name = (el.querySelector('.card-heading')?.textContent || '').trim();
    const total = Array.from(el.querySelectorAll('.institution-counts strong'))
      .reduce((sum, s) => sum + (parseInt(s.textContent, 10) || 0), 0);
    return { el, name, total, index };
  });

  const byName = (a, b) => a.name.localeCompare(b.name, 'en', { sensitivity: 'base' });

  const sorters = {
    'records-desc': (a, b) => b.total - a.total || a.index - b.index,
    'records-asc': (a, b) => a.total - b.total || byName(a, b),
    'name-asc': byName,
    'name-desc': (a, b) => byName(b, a),
  };

  function applySort(radio) {
    const sorted = cards.slice().sort(sorters[radio.value] || sorters['records-desc']);
    sorted.forEach((c) => grid.appendChild(c.el));
    if (sortLabel) sortLabel.textContent = radio.closest('label').textContent.trim();
  }

  radios.forEach((radio) => {
    radio.addEventListener('change', () => applySort(radio));
  });

  // The menu opens on hover/focus like the Filter by Type menu. After a mouse or tap pick,
  // close it (single choice); keyboard arrow-key changes leave it open.
  menu.addEventListener('click', (e) => {
    if (!e.target.closest('.tag-label') || e.detail === 0) return;
    item.classList.add('is-closed');
    if (document.activeElement) document.activeElement.blur();
  });
  item.addEventListener('mouseleave', () => item.classList.remove('is-closed'));
  item.addEventListener('focusin', (e) => {
    if (e.target.closest('.link')) item.classList.remove('is-closed');
  });
  item.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      item.querySelector('.link').focus();
      item.classList.add('is-closed');
    } else if (e.key === 'Enter' || e.key === ' ') {
      item.classList.remove('is-closed');
    }
  });

  const checked = radios.find((r) => r.checked) || radios[0];
  if (checked) applySort(checked);
});
