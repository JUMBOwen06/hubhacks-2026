// Results page: results.html?q=<text>&type=<a,b>&institution=<inst id>
// Asks the backend /search endpoint (or the local fallback, see data.js) and renders cards.
(function () {
  const { RESOURCE_TYPES, ACCESS_MODES, LOAD_ERROR_MESSAGE, searchRecords, el, marked, plural } = window.BHH;

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

  const listEl = document.getElementById('search-results-list');
  const countEl = document.getElementById('results-count');
  const summaryEl = document.getElementById('results-summary');
  const emptyEl = document.getElementById('results-empty');
  const emptyTitleEl = emptyEl.querySelector('.results-empty-title');
  const emptyTipsEl = emptyEl.querySelector('.results-empty-tips');
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

  function cardTags(card) {
    const tags = [];
    for (const type of TAG_TYPES) {
      for (const entity of (card.entities && card.entities[type]) || []) {
        tags.push(entity.name);
        if (tags.length === MAX_TAGS) return tags;
      }
    }
    return tags;
  }

  function holderLine(card) {
    if (card.holding_institution) {
      return el('span', { class: 'card-holder' }, 'Held by ', el('strong', null, card.holding_institution.name),
        card.holder_status === 'unconfirmed' ? ' (not confirmed)' : null);
    }
    const source = card.record_source;
    return el('span', { class: 'card-holder' }, 'Published by ', el('strong', null, source ? source.name : 'Unknown'));
  }

  function renderCard(card) {
    const tags = cardTags(card);
    const hl = card.highlight || {};
    const href = 'record.html?' + new URLSearchParams({ id: card.id }).toString();
    const why = card.why && card.why.summary;
    return el('article', { class: 'card horizontal-card' },
      typeIcon(card.resource_type),
      el('div', { class: 'card-content' },
        el('div', { class: 'card-top' },
          el('span', { class: 'card-title' }, RESOURCE_TYPES[card.resource_type] || card.resource_type),
          el('span', { class: 'card-category' }, ACCESS_MODES[card.access_mode] || card.access_mode)),
        el('div', { class: 'card-body' },
          el('h3', { class: 'card-heading' },
            el('a', { class: 'card-link', href }, hl.title ? marked(hl.title) : card.title)),
          card.date_display ? el('p', { class: 'card-date' }, card.date_display) : null,
          el('p', { class: 'card-snippet' }, hl.description ? marked(hl.description) : card.description),
          why ? el('p', { class: 'card-why' }, why) : null,
          tags.length ? el('ul', { class: 'card-tags', 'aria-label': 'People and places' },
            tags.map((name) => el('li', null,
              el('a', { class: 'card-tag', href: buildUrl({ q: name, types: [], institution: '' }) }, name)))) : null),
        el('div', { class: 'card-bottom' },
          holderLine(card),
          el('span', { class: 'card-action', 'aria-hidden': 'true' }, 'View record →'))));
  }

  function institutionName(response, id) {
    const facet = ((response.facets && response.facets.institution) || []).find((f) => f.value === id);
    return facet ? facet.label : id;
  }

  function renderSummary(state, response) {
    const parts = [];
    if (state.q) parts.push(['Showing results for ', el('span', { class: 'highlight-query' }, '"' + state.q + '"')]);
    else parts.push(['Showing all records']);
    const instName = state.institution ? institutionName(response, state.institution) : '';
    if (state.institution) {
      parts.push([' from ', el('strong', null, instName), ' ',
        el('a', { class: 'results-clear-filter', href: buildUrl({ ...state, institution: '' }), 'aria-label': 'Show records from all institutions' }, '✕')]);
    }
    if (state.types.length) {
      parts.push([' · ' + state.types.map((t) => RESOURCE_TYPES[t]).join(', ')]);
    }
    // Terminology bridge: e.g. "freedom seekers" also searched "self-emancipated", "fugitive slave".
    const related = (response.interpreted && response.interpreted.related_terms) || [];
    const alsoSearched = [...new Set(related.flatMap((r) => r.also_searched || []))];
    if (alsoSearched.length) {
      const notes = related.map((r) => r.note).filter(Boolean).join(' ');
      parts.push([el('span', { class: 'results-related', title: notes || null }, ' · also searched: ' + alsoSearched.join(', '))]);
    }
    if (response.source === 'local') {
      parts.push([el('span', { class: 'results-offline' }, ' · Offline mode: basic search of the bundled dataset')]);
    }
    summaryEl.replaceChildren(...parts.flat());

    const sources = new Set(response.results.map((r) => r.record_source && r.record_source.id));
    countEl.textContent = response.total
      ? plural(response.total, 'record') + ' from ' + plural(sources.size, 'institution')
      : 'No records';

    const label = (state.q ? '"' + state.q + '"' : 'All records') + (instName ? ' from ' + instName : '');
    headingEl.textContent = 'Search results for ' + label;
    document.title = label + ' — Black History Hub Search';
  }

  function renderEmpty(state, response) {
    emptyTitleEl.textContent = state.q ? 'No records found for "' + state.q + '"' : 'No records match these filters';
    // Remove anything we added last time, keep the static tips.
    emptyEl.querySelectorAll('.results-api-note').forEach((n) => n.remove());
    const extra = [];
    if (response.suggestions && response.suggestions.length) {
      extra.push(el('p', { class: 'results-api-note' }, 'Did you mean: ',
        response.suggestions.map((s, i) => [i ? ', ' : '',
          el('a', { href: buildUrl({ ...state, q: s }) }, s)])));
    }
    if (response.message) extra.push(el('p', { class: 'results-api-note' }, response.message));
    emptyTipsEl.before(...extra);
  }

  let requestId = 0;

  async function render(state) {
    const mine = ++requestId;
    countEl.textContent = 'Searching…';
    let response;
    try {
      response = await searchRecords({ q: state.q, resource_type: state.types, institution: state.institution });
    } catch (err) {
      console.error('Search failed:', err);
      countEl.textContent = '';
      summaryEl.textContent = LOAD_ERROR_MESSAGE;
      listEl.replaceChildren();
      return;
    }
    if (mine !== requestId) return; // a newer search started while this one was loading
    if (window.BHHTrack) window.BHHTrack.search(state.q, response.total);
    renderSummary(state, response);
    listEl.replaceChildren(...response.results.map(renderCard));
    emptyEl.hidden = response.results.length > 0;
    if (!response.results.length) renderEmpty(state, response);
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

  function init() {
    const state = readParams();
    syncControls(state);
    render(state);

    // Type checkboxes filter immediately on this page; the URL keeps the state shareable.
    checkboxes.forEach((cb) => cb.addEventListener('change', () => {
      const next = { ...readParams(), types: checkboxes.filter((c) => c.checked).map((c) => c.value) };
      history.replaceState(null, '', buildUrl(next));
      render(next);
    }));
  }

  init();
})();
