// Results page: results.html?q=<text>&type=<a,b>&institution=<inst id>
// Searches the seed dataset in the browser and renders result cards.
(function () {
  const { RESOURCE_TYPES, ACCESS_MODES, LOAD_ERROR_MESSAGE, loadDataset, el, normalize } = window.BHH;

  const SVG_NS = 'http://www.w3.org/2000/svg';
  // Inner SVG for each resource type's card icon (24x24, stroked by CSS).
  const TYPE_ICONS = {
    archival_document: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
    book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5M19 19v2H6"/>',
    correspondence: '<path d="M4 6h16v12H4z"/><path d="M4 7l8 6 8-6"/>',
    journal_article: '<path d="M5 4h14v16H5z"/><path d="M8 8h8M8 12h8M8 16h5"/>',
    map: '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z"/><path d="M9 3v15M15 6v15"/>',
    person_profile: '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    photograph: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    register: '<path d="M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01"/>',
    research_guide: '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>',
    other: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>',
  };
  // Entity types shown as chips on a card, in this order of preference.
  const TAG_TYPES = ['person', 'community', 'place'];
  const MAX_TAGS = 3;

  // How much a term hit counts for, by field.
  const WEIGHTS = { title: 6, entity: 4, institution: 3, container: 2, description: 1, other: 1 };

  const listEl = document.getElementById('search-results-list');
  const countEl = document.getElementById('results-count');
  const summaryEl = document.getElementById('results-summary');
  const emptyEl = document.getElementById('results-empty');
  const emptyTitleEl = emptyEl.querySelector('.results-empty-title');
  const headingEl = document.getElementById('results-heading');
  const searchInput = document.getElementById('search-input');
  const searchForm = document.getElementById('search-form');
  const checkboxes = Array.from(document.querySelectorAll('.tag-checkbox'));
  const tagLabel = document.getElementById('tag-dropdown-label');

  // ---- URL state --------------------------------------------------------
  function readParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      q: (params.get('q') || '').trim(),
      types: (params.get('type') || '').split(',').map((t) => t.trim()).filter((t) => RESOURCE_TYPES[t]),
      institution: (params.get('institution') || '').trim(),
    };
  }

  function buildUrl(state) {
    const params = new URLSearchParams();
    params.set('q', state.q);
    if (state.types.length) params.set('type', state.types.join(','));
    if (state.institution) params.set('institution', state.institution);
    return 'results.html?' + params.toString();
  }

  // ---- search index -----------------------------------------------------
  // One entry per record with normalized text per field.
  function buildIndex(data) {
    const entityNamesByRecord = new Map();
    for (const link of data.record_entity) {
      const entity = data.entitiesById.get(link.entity_id);
      if (!entity) continue;
      const names = entityNamesByRecord.get(link.record_id) || [];
      names.push(entity.name_preferred);
      if (link.name_as_written) names.push(link.name_as_written);
      entityNamesByRecord.set(link.record_id, names);
    }
    return data.record.map((record) => {
      const source = data.institutionsById.get(record.record_source_id);
      const holder = data.institutionsById.get(record.holding_institution_id);
      return {
        record,
        fields: {
          title: normalize(record.title_original),
          entity: normalize((entityNamesByRecord.get(record.id) || []).join(' | ')),
          institution: normalize([source && source.name, holder && holder.name].join(' | ')),
          container: normalize(record.container_title),
          description: normalize(record.description),
          other: normalize([record.date_display, record.source_reference, RESOURCE_TYPES[record.resource_type]].join(' | ')),
        },
      };
    });
  }

  // Every term must appear somewhere (AND). Score by where it appears; bonus for the whole phrase.
  function scoreEntry(entry, terms, phrase) {
    let score = 0;
    for (const term of terms) {
      let termScore = 0;
      for (const [field, text] of Object.entries(entry.fields)) {
        if (text.includes(term)) termScore = Math.max(termScore, WEIGHTS[field]);
      }
      if (!termScore) return 0;
      score += termScore;
    }
    if (terms.length > 1) {
      if (entry.fields.title.includes(phrase)) score += 6;
      else if (entry.fields.entity.includes(phrase)) score += 4;
      else if (entry.fields.description.includes(phrase)) score += 2;
    }
    return score;
  }

  function search(index, state) {
    const phrase = normalize(state.q).replace(/\s+/g, ' ').trim();
    const terms = phrase.split(' ').filter(Boolean);
    const results = [];
    for (const entry of index) {
      const r = entry.record;
      if (state.types.length && !state.types.includes(r.resource_type)) continue;
      if (state.institution && r.record_source_id !== state.institution && r.holding_institution_id !== state.institution) continue;
      const score = terms.length ? scoreEntry(entry, terms, phrase) : 1;
      if (score) results.push({ record: r, score });
    }
    // Best score first; ties keep dataset order (stable sort).
    results.sort((a, b) => b.score - a.score);
    return results.map((r) => r.record);
  }

  // ---- rendering --------------------------------------------------------
  function typeIcon(type) {
    const svg = document.createElementNS(SVG_NS, 'svg');
    svg.setAttribute('class', 'card-type-icon');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    // Static markup from TYPE_ICONS above, never from data.
    svg.innerHTML = TYPE_ICONS[type] || TYPE_ICONS.other;
    return svg;
  }

  function cardTags(data, record) {
    const links = data.record_entity.filter((l) => l.record_id === record.id);
    const seen = new Set();
    const tags = [];
    for (const type of TAG_TYPES) {
      for (const link of links) {
        const entity = data.entitiesById.get(link.entity_id);
        if (!entity || entity.entity_type !== type || seen.has(entity.id)) continue;
        seen.add(entity.id);
        tags.push(entity.name_preferred);
        if (tags.length === MAX_TAGS) return tags;
      }
    }
    return tags;
  }

  function holderLine(data, record) {
    const holder = data.institutionsById.get(record.holding_institution_id);
    if (holder) {
      return el('span', { class: 'card-holder' }, 'Held by ', el('strong', null, holder.name),
        record.holder_status === 'unconfirmed' ? ' (not confirmed)' : null);
    }
    const source = data.institutionsById.get(record.record_source_id);
    return el('span', { class: 'card-holder' }, 'Published by ', el('strong', null, source ? source.name : 'Unknown'));
  }

  function renderCard(data, record) {
    const tags = cardTags(data, record);
    return el('article', { class: 'card horizontal-card' },
      typeIcon(record.resource_type),
      el('div', { class: 'card-content' },
        el('div', { class: 'card-top' },
          el('span', { class: 'card-title' }, RESOURCE_TYPES[record.resource_type] || record.resource_type),
          el('span', { class: 'card-category' }, ACCESS_MODES[record.access_mode] || record.access_mode)),
        el('div', { class: 'card-body' },
          el('h3', { class: 'card-heading' },
            el('a', { class: 'card-link', href: 'record.html?' + new URLSearchParams({ id: record.id }).toString() }, record.title_original)),
          record.date_display ? el('p', { class: 'card-date' }, record.date_display) : null,
          el('p', { class: 'card-snippet' }, record.description),
          tags.length ? el('ul', { class: 'card-tags', 'aria-label': 'People and places' },
            tags.map((name) => el('li', null,
              el('a', { class: 'card-tag', href: buildUrl({ q: name, types: [], institution: '' }) }, name)))) : null),
        el('div', { class: 'card-bottom' },
          holderLine(data, record),
          el('span', { class: 'card-action', 'aria-hidden': 'true' }, 'View record →'))));
  }

  function plural(n, word) {
    return n + ' ' + word + (n === 1 ? '' : 's');
  }

  function renderSummary(data, state, results) {
    const parts = [];
    if (state.q) parts.push(['Showing results for ', el('span', { class: 'highlight-query' }, '"' + state.q + '"')]);
    else parts.push(['Showing all records']);
    const inst = state.institution && data.institutionsById.get(state.institution);
    if (state.institution) {
      parts.push([' from ', el('strong', null, inst ? inst.name : state.institution), ' ',
        el('a', { class: 'results-clear-filter', href: buildUrl({ ...state, institution: '' }), 'aria-label': 'Show records from all institutions' }, '✕')]);
    }
    if (state.types.length) {
      parts.push([' · ' + state.types.map((t) => RESOURCE_TYPES[t]).join(', ')]);
    }
    summaryEl.replaceChildren(...parts.flat());

    const institutions = new Set(results.map((r) => r.record_source_id));
    countEl.textContent = results.length
      ? plural(results.length, 'record') + ' from ' + plural(institutions.size, 'institution')
      : 'No records';

    const label = (state.q ? '"' + state.q + '"' : 'All records') + (inst ? ' from ' + inst.name : '');
    headingEl.textContent = 'Search results for ' + label;
    document.title = label + ' — Black History Hub Search';
  }

  function render(data, index, state) {
    const results = search(index, state);
    renderSummary(data, state, results);
    listEl.replaceChildren(...results.map((r) => renderCard(data, r)));
    emptyEl.hidden = results.length > 0;
    if (!results.length) {
      emptyTitleEl.textContent = state.q ? 'No records found for "' + state.q + '"' : 'No records match these filters';
    }
  }

  // ---- controls ---------------------------------------------------------
  function syncControls(state) {
    searchInput.value = state.q;
    checkboxes.forEach((cb) => { cb.checked = state.types.includes(cb.value); });
    if (tagLabel) {
      tagLabel.textContent = state.types.length ? `Type (${state.types.length} selected)` : 'Filter by Type';
    }
    // script.js reads this when the form is submitted, so a new search keeps the institution filter.
    if (state.institution) searchForm.dataset.institution = state.institution;
    else delete searchForm.dataset.institution;
  }

  async function init() {
    const state = readParams();
    syncControls(state);
    let data;
    try {
      data = await loadDataset();
    } catch (err) {
      console.error('Failed to load dataset:', err);
      countEl.textContent = '';
      summaryEl.textContent = LOAD_ERROR_MESSAGE;
      listEl.replaceChildren();
      return;
    }
    const index = buildIndex(data);
    render(data, index, state);

    // Type checkboxes filter immediately on this page; the URL keeps the state shareable.
    checkboxes.forEach((cb) => cb.addEventListener('change', () => {
      const next = {
        ...readParams(),
        types: checkboxes.filter((c) => c.checked).map((c) => c.value),
      };
      history.replaceState(null, '', buildUrl(next));
      render(data, index, next);
    }));
  }

  init();
})();
