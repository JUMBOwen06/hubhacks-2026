// Record detail page: record.html?id=<record id>
// Reads /records/{id} from the API (or the local fallback) and renders one record with its dates, people/places,
// where to find it, rights, related records and provenance.
(function () {
  const { RESOURCE_TYPES, el, extLink, getRecord, LOAD_ERROR_MESSAGE } = window.BHH;

  const DATE_KINDS = {
    document: 'Document date',
    event: 'Event',
    publication: 'Published',
    designation: 'Designated',
    life: 'Lifetime',
    period_discussed: 'Period covered',
  };
  const ACCESS_MODES = { online: 'Online', mixed: 'Online & in person', unknown: 'Unknown' };
  const DIGITIZED = { yes: 'Yes', partial: 'Partly', not_applicable: 'Not applicable (born digital or published)', unknown: 'Unknown' };
  const LANGUAGES = { en: 'English', fr: 'French' };
  const ENTITY_GROUPS = [
    ['person', 'People'],
    ['community', 'Communities'],
    ['place', 'Places'],
    ['organization', 'Organizations'],
    ['event', 'Events'],
    ['subject', 'Subjects'],
  ];
  // Roles worth calling out next to a name; subject/location/mentioned are implied by the group.
  const ROLE_LABELS = { author: 'author', creator: 'creator', recipient: 'recipient', contributor: 'contributor' };
  const RELATION_TYPES = {
    describes_same_resource: 'Describes the same resource',
    related_context: 'Related context',
  };

  function section(id, title, ...content) {
    return el('section', { class: 'column-section about-section record-section', 'aria-labelledby': id },
      el('h2', { id, class: 'column-title' }, title),
      ...content);
  }

  function factList(rows) {
    const items = rows.filter(([, value]) => value !== null && value !== undefined && value !== '');
    if (!items.length) return null;
    return el('dl', { class: 'record-facts' },
      items.map(([term, value]) => el('div', null, el('dt', null, term), el('dd', null, value))));
  }

  function formatDate(iso) {
    if (!iso) return null;
    const d = new Date(iso + 'T00:00:00');
    return isNaN(d) ? iso : d.toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  function searchUrl(q) {
    return 'results.html?' + new URLSearchParams({ q }).toString();
  }

  // ---- page states ------------------------------------------------------
  const body = document.getElementById('record-body');
  const titleEl = document.getElementById('page-title');

  function showMessage(title, message, extra) {
    titleEl.textContent = title;
    document.title = title + ' — Black History Hub';
    body.replaceChildren(
      el('section', { class: 'column-section about-section' },
        el('p', null, message),
        extra || el('p', null, el('a', { href: 'index.html' }, 'Go to search'))));
  }

  function setBackLink() {
    const back = document.getElementById('back-link');
    try {
      const last = sessionStorage.getItem('lastResults');
      if (last && new URL(last).origin === window.location.origin) {
        back.href = last;
        back.textContent = new URL(last).pathname.endsWith('/results.html') ? '← Back to results' : '← Back';
      }
    } catch (err) {
      // sessionStorage unavailable; keep "Back to search"
    }
  }

  // ---- render -----------------------------------------------------------
  // rec is the /records/{id} response (or the same shape from the local fallback).
  function render(rec) {
    const source = rec.record_source;
    const holder = rec.holding_institution;
    const access = rec.access || {};
    const rights = rec.rights || {};
    const prov = rec.provenance || {};
    const typeLabel = RESOURCE_TYPES[rec.resource_type] || rec.resource_type;

    // Hero
    document.title = rec.title + ' — Black History Hub';
    document.getElementById('record-type').textContent = typeLabel;
    titleEl.textContent = rec.title;
    document.getElementById('record-date').textContent = rec.date_display || '';
    if (rec.content_note) {
      const note = document.getElementById('record-content-note');
      note.replaceChildren(el('strong', null, 'Content note: '), rec.content_note);
      note.hidden = false;
    }
    const actions = document.getElementById('record-actions');
    if (access.source_url) {
      actions.append(extLink(access.source_url, 'View at ' + (source ? source.name : 'source'), 'record-btn record-btn-primary'));
    }
    if (access.digital_url && access.digital_url !== access.source_url) {
      actions.append(extLink(access.digital_url, 'View digitized copy', 'record-btn'));
    }

    const parts = [];

    // 1. Description
    const dates = rec.dates || [];
    parts.push(section('rec-about', 'About this record',
      el('p', { class: 'record-description' }, rec.description),
      factList([
        ['Type', typeLabel],
        ['Part of', rec.container_title],
        ['Language', LANGUAGES[rec.language] || rec.language],
        ['Reference', access.source_reference],
      ]),
      dates.length ? el('div', null,
        el('h3', { class: 'record-subhead' }, 'Dates'),
        el('ul', { class: 'record-dates' },
          dates.map((d) => el('li', null,
            el('span', { class: 'record-date-kind' }, DATE_KINDS[d.kind] || d.kind),
            d.label,
            d.approximate ? el('span', { class: 'record-muted' }, ' (approximate)') : null)))) : null));

    // 2. People, places & subjects (API groups them by type: { person: [{id, name, roles}] })
    const entities = rec.entities || {};
    const groups = ENTITY_GROUPS.map(([type, label]) => {
      const items = entities[type] || [];
      if (!items.length) return null;
      return el('div', { class: 'record-entity-group' },
        el('h3', { class: 'record-subhead' }, label),
        el('ul', { class: 'card-tags record-tags' },
          items.map((entity) => {
            const role = (entity.roles || []).map((r) => ROLE_LABELS[r]).find(Boolean);
            return el('li', null,
              el('a', { class: 'card-tag', href: searchUrl(entity.name) },
                entity.name,
                role ? el('span', { class: 'record-role' }, ' · ' + role) : null));
          })));
    }).filter(Boolean);
    if (groups.length) parts.push(section('rec-entities', 'People, places & subjects', groups));

    // 3. Where to find it
    const where = [];
    if (source) {
      where.push(institutionBlock('Described by', source,
        'This institution wrote the description and hosts the page this record links to.'));
    }
    if (holder) {
      const status = rec.holder_status === 'unconfirmed' ? ' (not confirmed)' : '';
      const block = institutionBlock('Original held by' + status, holder, null);
      if (rec.holder_note) {
        block.append(el('details', { class: 'record-details' },
          el('summary', null, 'How we know this'),
          el('p', { class: 'record-muted' }, rec.holder_note)));
      }
      where.push(block);
    } else if (rec.holder_status === 'not_applicable') {
      where.push(el('p', { class: 'record-muted' }, 'There is no separate original to locate: the resource is the published or online item itself.'));
    } else {
      where.push(el('p', { class: 'record-muted' }, 'Where the original is held is not known yet.'));
    }
    where.push(factList([
      ['Access', ACCESS_MODES[access.access_mode] || access.access_mode],
      ['Digitized', DIGITIZED[access.digitized] || access.digitized],
    ]));
    if (access.access_instructions) {
      where.push(el('div', null, el('h3', { class: 'record-subhead' }, 'How to access it'), el('p', null, access.access_instructions)));
    }
    if (access.access_restrictions) {
      where.push(el('div', { class: 'record-callout' }, el('strong', null, 'Restrictions: '), access.access_restrictions));
    }
    const also = rec.also_available_from || [];
    if (also.length) {
      where.push(el('div', null,
        el('h3', { class: 'record-subhead' }, 'Also available from'),
        el('ul', { class: 'institution-links' }, also.map((a) => el('li', null,
          el('a', { href: 'record.html?' + new URLSearchParams({ id: a.record_id }).toString() },
            (a.institution && a.institution.name) || a.institution || a.record_id))))));
    }
    parts.push(section('rec-where', 'Where to find it', where));

    // 4. Rights
    if (rights.rights_statement || rights.rights_url) {
      parts.push(section('rec-rights', 'Rights & reuse',
        rights.rights_statement ? el('p', null, rights.rights_statement) : null,
        rights.rights_url ? el('ul', { class: 'institution-links' }, el('li', null, extLink(rights.rights_url, 'Rights policy'))) : null,
        el('p', { class: 'record-muted' }, 'Black History Hub stores only this description and a link. The content belongs to the institution above.')));
    }

    // 5. Related records: curated relations, then records the API found through shared
    //    people, places and subjects ("connected").
    const relations = rec.relations || [];
    const connected = rec.connected || [];
    if (relations.length || connected.length) {
      const relatedItem = (other, label, note) => el('li', null,
        el('span', { class: 'record-date-kind' }, label),
        el('a', { href: 'record.html?' + new URLSearchParams({ id: other.id }).toString() }, other.title),
        other.record_source ? el('span', { class: 'record-muted' }, ' — ' + other.record_source.name) : null,
        note ? el('p', { class: 'record-muted record-related-note' }, note) : null);
      parts.push(section('rec-related', 'Related records',
        relations.length ? el('ul', { class: 'record-related' },
          relations.map((rel) => relatedItem(rel.record, RELATION_TYPES[rel.relation_type] || rel.relation_type, rel.evidence_note))) : null,
        connected.length ? el('div', null,
          el('h3', { class: 'record-subhead' }, 'Connected through shared people, places and subjects'),
          el('ul', { class: 'record-related' },
            connected.map((c) => relatedItem(c, 'Connected', c.summary)))) : null));
    }

    // 6. Provenance
    const verified = prov.verification_status === 'verified';
    parts.push(section('rec-provenance', 'Provenance',
      factList([
        ['Status', el('span', { class: 'record-status ' + (verified ? 'is-verified' : 'needs-review') },
          verified ? 'Verified' : 'Needs review')],
        ['Last verified', formatDate(prov.last_verified_at)],
        ['Link last checked', formatDate(prov.link_last_checked)],
        ['Added', [formatDate(prov.imported_at), prov.added_by ? 'by ' + prov.added_by : null].filter(Boolean).join(' ')],
        ['Collected', prov.collection_method === 'manual' ? 'By hand from the source page' : prov.collection_method],
        ['Record ID', rec.id],
      ]),
      rec.notes ? el('details', { class: 'record-details' }, el('summary', null, 'Curator notes'), el('p', null, rec.notes)) : null,
      prov.change_notes ? el('details', { class: 'record-details' }, el('summary', null, 'Change history'), el('p', null, prov.change_notes)) : null));

    body.replaceChildren(...parts);
  }

  function institutionBlock(label, inst, note) {
    const links = [];
    if (inst.website_url) links.push(el('li', null, extLink(inst.website_url, 'Visit website')));
    if (inst.catalogue_url) links.push(el('li', null, extLink(inst.catalogue_url, 'Search their catalogue')));
    return el('div', { class: 'record-institution' },
      el('h3', { class: 'record-subhead' }, label),
      el('p', { class: 'record-institution-name' }, inst.name),
      note ? el('p', { class: 'record-muted' }, note) : null,
      links.length ? el('ul', { class: 'institution-links' }, links) : null);
  }

  // ---- load -------------------------------------------------------------
  async function init() {
    setBackLink();
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id) {
      showMessage('No record selected', 'This page shows one record. Search for something and pick a result.');
      return;
    }

    let record;
    try {
      record = await getRecord(id);
    } catch (err) {
      showMessage('Could not load the record', LOAD_ERROR_MESSAGE);
      console.error('Failed to load record:', err);
      return;
    }

    if (!record) {
      showMessage('Record not found', 'There is no record with the ID "' + id + '". It may have been removed or the link may be wrong.');
      return;
    }
    render(record);
  }

  init();
})();
