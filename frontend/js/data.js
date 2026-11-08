// Shared data layer for results.html, record.html and institutions.html. Exposes window.BHH.
//
// The pages call BHH.searchRecords / getRecord / listInstitutions. Each one asks the backend
// API first. If the API can't be reached, it falls back to searching the seed JSON in the
// browser (the team's agreed fallback) and returns the same shapes as the API, so the
// pages only have one format to render. Fallback results have no "why matched", no
// terminology bridge and no connected records.
(function () {
  // Where the API lives.
  // - Served by the backend at http://127.0.0.1:8000/app/ (the normal way): same origin, ''.
  // - Opened from another local server (e.g. VS Code Live Server): the default uvicorn
  //   address. Override by setting window.BHH_API_BASE before this script loads.
  const API_BASE = (typeof window.BHH_API_BASE === 'string')
    ? window.BHH_API_BASE
    : (window.location.pathname.startsWith('/app/') ? '' : 'http://127.0.0.1:8000');

  // Relative to the frontend/ pages. Works at /app/ (the API serves data/ at /data/) and
  // when the repo root is served with any static server.
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

  // ---- API ----------------------------------------------------------------
  // GET an API path. Array params repeat the key (resource_type=book&resource_type=map),
  // which is what FastAPI expects. Resolves to parsed JSON, or null for a 404 when
  // notFoundIsNull is set (only /records/{id}: "no such record").
  // Throws ApiUnavailable if the server can't be reached, errors, or doesn't answer with
  // JSON (e.g. a plain static server such as `python -m http.server` returns an HTML 404).
  class ApiUnavailable extends Error {}

  async function api(path, params, notFoundIsNull) {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params || {})) {
      if (value === null || value === undefined || value === '') continue;
      if (Array.isArray(value)) value.forEach((v) => qs.append(key, v));
      else qs.append(key, value);
    }
    const query = qs.toString();
    let res;
    try {
      res = await fetch(API_BASE + path + (query ? '?' + query : ''), { headers: { Accept: 'application/json' } });
    } catch (err) {
      throw new ApiUnavailable(err.message);
    }
    const isJson = (res.headers.get('Content-Type') || '').includes('application/json');
    if (!isJson) throw new ApiUnavailable('HTTP ' + res.status + ' non-JSON response from ' + path);
    if (res.status === 404 && notFoundIsNull) return null;
    if (!res.ok) throw new ApiUnavailable('HTTP ' + res.status + ' from ' + path);
    try {
      return await res.json();
    } catch (err) {
      throw new ApiUnavailable('Invalid JSON from ' + path);
    }
  }

  // Try the API; on ApiUnavailable run the local fallback. Tags the result with .source.
  async function withFallback(apiCall, localCall) {
    try {
      const result = await apiCall();
      if (result) result.source = 'api';
      return result;
    } catch (err) {
      if (!(err instanceof ApiUnavailable)) throw err;
      console.warn('API unavailable, using the local dataset:', err.message);
      const result = await localCall();
      if (result) result.source = 'local';
      return result;
    }
  }

  // ---- local fallback: load the seed JSON ----------------------------------
  let datasetPromise = null;

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
          data.linksByRecord = new Map();
          for (const link of data.record_entity) {
            const list = data.linksByRecord.get(link.record_id) || [];
            list.push(link);
            data.linksByRecord.set(link.record_id, list);
          }
          return data;
        });
      datasetPromise.catch(() => { datasetPromise = null; });
    }
    return datasetPromise;
  }

  // Lowercase and strip accents so "Quebec" matches "Québec".
  function normalize(text) {
    return String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  function instRef(data, id) {
    const inst = id && data.institutionsById.get(id);
    return inst ? { id: inst.id, name: inst.name } : null;
  }

  function instFull(data, id) {
    const inst = id && data.institutionsById.get(id);
    return inst ? { ...inst } : null;
  }

  // entities grouped by type, like the API: { person: [{id, name, roles}], ... }
  function groupedEntities(data, recordId) {
    const groups = {};
    const byId = new Map();
    for (const link of data.linksByRecord.get(recordId) || []) {
      const entity = data.entitiesById.get(link.entity_id);
      if (!entity) continue;
      let item = byId.get(entity.id);
      if (!item) {
        item = { id: entity.id, name: entity.name_preferred, roles: [] };
        byId.set(entity.id, item);
        (groups[entity.entity_type] = groups[entity.entity_type] || []).push(item);
      }
      if (link.role && !item.roles.includes(link.role)) item.roles.push(link.role);
    }
    return groups;
  }

  function localCard(data, r) {
    return {
      id: r.id,
      title: r.title_original,
      resource_type: r.resource_type,
      date_display: r.date_display || null,
      description: r.description,
      content_note: r.content_note || null,
      record_source: instRef(data, r.record_source_id),
      holding_institution: instRef(data, r.holding_institution_id),
      holder_status: r.holder_status,
      digitized: r.digitized,
      access_mode: r.access_mode,
      source_url: r.source_url,
      collection_method: r.collection_method,
      verification_status: r.verification_status,
      last_verified_at: r.last_verified_at,
      entities: groupedEntities(data, r.id),
      why: null,
      highlight: null,
    };
  }

  // Simple weighted keyword search: every term must appear somewhere.
  const WEIGHTS = { title: 6, entity: 4, institution: 3, container: 2, description: 1, other: 1 };

  function recordFields(data, r) {
    const names = [];
    for (const link of data.linksByRecord.get(r.id) || []) {
      const e = data.entitiesById.get(link.entity_id);
      if (e) names.push(e.name_preferred);
      if (link.name_as_written) names.push(link.name_as_written);
    }
    const source = data.institutionsById.get(r.record_source_id);
    const holder = data.institutionsById.get(r.holding_institution_id);
    return {
      title: normalize(r.title_original),
      entity: normalize(names.join(' | ')),
      institution: normalize([source && source.name, holder && holder.name].join(' | ')),
      container: normalize(r.container_title),
      description: normalize(r.description),
      other: normalize([r.date_display, r.source_reference, RESOURCE_TYPES[r.resource_type]].join(' | ')),
    };
  }

  function scoreFields(fields, terms, phrase) {
    let score = 0;
    for (const term of terms) {
      let best = 0;
      for (const [field, text] of Object.entries(fields)) {
        if (text.includes(term)) best = Math.max(best, WEIGHTS[field]);
      }
      if (!best) return 0;
      score += best;
    }
    if (terms.length > 1) {
      if (fields.title.includes(phrase)) score += 6;
      else if (fields.entity.includes(phrase)) score += 4;
      else if (fields.description.includes(phrase)) score += 2;
    }
    return score;
  }

  async function searchLocal({ q, resource_type, institution, limit }) {
    const data = await loadDataset();
    const phrase = normalize(q).replace(/\s+/g, ' ').trim();
    const terms = phrase.split(' ').filter(Boolean);
    const types = resource_type || [];
    const hits = [];
    for (const r of data.record) {
      if (types.length && !types.includes(r.resource_type)) continue;
      if (institution && r.record_source_id !== institution && r.holding_institution_id !== institution) continue;
      const score = terms.length ? scoreFields(recordFields(data, r), terms, phrase) : 1;
      if (score) hits.push({ r, score });
    }
    hits.sort((a, b) => b.score - a.score);
    const instCounts = new Map();
    for (const { r } of hits) {
      for (const id of new Set([r.record_source_id, r.holding_institution_id].filter(Boolean))) {
        instCounts.set(id, (instCounts.get(id) || 0) + 1);
      }
    }
    return {
      query: q,
      total: hits.length,
      results: hits.slice(0, limit || 100).map(({ r }) => localCard(data, r)),
      facets: {
        institution: Array.from(instCounts, ([value, count]) => ({
          value, count, label: (data.institutionsById.get(value) || {}).name || value,
        })),
      },
      suggestions: [],
      message: null,
    };
  }

  async function getRecordLocal(id) {
    const data = await loadDataset();
    const r = data.recordsById.get(id);
    if (!r) return null;
    const card = localCard(data, r);
    const relations = data.record_relation
      .filter((rel) => (rel.record_a_id === id || rel.record_b_id === id) && rel.status !== 'rejected')
      .map((rel) => {
        const other = data.recordsById.get(rel.record_a_id === id ? rel.record_b_id : rel.record_a_id);
        return other && {
          relation_type: rel.relation_type,
          evidence_note: rel.evidence_note,
          record: { id: other.id, title: other.title_original, record_source: instRef(data, other.record_source_id) },
        };
      })
      .filter(Boolean);
    return {
      ...card,
      record_source: instFull(data, r.record_source_id),
      holding_institution: instFull(data, r.holding_institution_id),
      language: r.language,
      container_title: r.container_title,
      notes: r.notes,
      holder_note: r.holder_note,
      dates: data.record_date.filter((d) => d.record_id === id),
      access: {
        source_url: r.source_url, source_reference: r.source_reference, digital_url: r.digital_url,
        digitized: r.digitized, access_mode: r.access_mode,
        access_instructions: r.access_instructions, access_restrictions: r.access_restrictions,
      },
      rights: { rights_statement: r.rights_statement, rights_url: r.rights_url },
      provenance: {
        collection_method: r.collection_method, imported_at: r.imported_at, added_by: r.added_by,
        last_verified_at: r.last_verified_at, verification_status: r.verification_status,
        link_last_checked: r.link_last_checked, change_notes: r.change_notes,
      },
      relations,
      connected: [],
    };
  }

  async function listInstitutionsLocal() {
    const data = await loadDataset();
    return data.institution.map((inst) => ({
      ...inst,
      records_supplied: data.record.filter((r) => r.record_source_id === inst.id).length,
      records_held: data.record.filter((r) => r.holding_institution_id === inst.id).length,
    }));
  }

  // ---- public data calls ------------------------------------------------------
  // params: { q, resource_type: [..], institution, sort, limit }
  function searchRecords(params) {
    return withFallback(
      () => api('/search', { limit: 100, ...params, institution: params.institution ? [params.institution] : null }),
      () => searchLocal(params));
  }

  function getRecord(id) {
    return withFallback(() => api('/records/' + encodeURIComponent(id), null, true), () => getRecordLocal(id));
  }

  async function listInstitutions() {
    // The API returns a plain array; wrap it so the source tag can be attached.
    return withFallback(
      async () => ({ institutions: await api('/institutions') }),
      async () => ({ institutions: await listInstitutionsLocal() }));
  }

  // ---- DOM helpers -------------------------------------------------------------
  // el('a', { href, class, text }, ...children). Never uses innerHTML.
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
    for (const child of children.flat(Infinity)) {
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

  // The API returns highlights as escaped HTML with <mark> around matched words.
  // Rebuild them as DOM nodes keeping only text and <mark>, so nothing else can be injected.
  function marked(html) {
    const doc = new DOMParser().parseFromString('<body>' + (html || '') + '</body>', 'text/html');
    return Array.from(doc.body.childNodes, (n) => (n.nodeName === 'MARK'
      ? el('mark', null, n.textContent)
      : document.createTextNode(n.textContent)));
  }

  function plural(n, word) {
    return n + ' ' + word + (n === 1 ? '' : 's');
  }

  const LOAD_ERROR_MESSAGE = 'The record data could not be loaded. Start the backend '
    + '(cd backend, then: uvicorn app.main:app --reload) and open http://127.0.0.1:8000/app/';

  window.BHH = {
    API_BASE, RESOURCE_TYPES, ACCESS_MODES, LOAD_ERROR_MESSAGE,
    searchRecords, getRecord, listInstitutions, el, extLink, marked, plural,
  };
})();
