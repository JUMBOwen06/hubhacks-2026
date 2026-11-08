// Record detail page: record.html?id=<record id>
// Reads the seed dataset and renders one record with its dates, people/places,
// where to find it, rights, related records and provenance.
(function () {
  const { RESOURCE_TYPES, el, extLink, loadDataset, LOAD_ERROR_MESSAGE } = window.BHH;

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
  function render(data, record) {
    const institutions = data.institutionsById;
    const entities = data.entitiesById;
    const records = data.recordsById;
    const source = institutions.get(record.record_source_id);
    const holder = institutions.get(record.holding_institution_id);
    const typeLabel = RESOURCE_TYPES[record.resource_type] || record.resource_type;

    // Hero
    document.title = record.title_original + ' — Black History Hub';
    document.getElementById('record-type').textContent = typeLabel;
    titleEl.textContent = record.title_original;
    document.getElementById('record-date').textContent = record.date_display || '';
    if (record.content_note) {
      const note = document.getElementById('record-content-note');
      note.replaceChildren(el('strong', null, 'Content note: '), record.content_note);
      note.hidden = false;
    }
    const actions = document.getElementById('record-actions');
    if (record.source_url) {
      actions.append(extLink(record.source_url, 'View at ' + (source ? source.name : 'source'), 'record-btn record-btn-primary'));
    }
    if (record.digital_url && record.digital_url !== record.source_url) {
      actions.append(extLink(record.digital_url, 'View digitized copy', 'record-btn'));
    }

    const parts = [];

    // 1. Description
    const dates = data.record_date.filter((d) => d.record_id === record.id);
    parts.push(section('rec-about', 'About this record',
      el('p', { class: 'record-description' }, record.description),
      factList([
        ['Type', typeLabel],
        ['Part of', record.container_title],
        ['Language', LANGUAGES[record.language] || record.language],
        ['Reference', record.source_reference],
      ]),
      dates.length ? el('div', null,
        el('h3', { class: 'record-subhead' }, 'Dates'),
        el('ul', { class: 'record-dates' },
          dates.map((d) => el('li', null,
            el('span', { class: 'record-date-kind' }, DATE_KINDS[d.kind] || d.kind),
            d.label,
            d.approximate ? el('span', { class: 'record-muted' }, ' (approximate)') : null)))) : null));

    // 2. People, places & subjects
    const links = data.record_entity.filter((l) => l.record_id === record.id);
    if (links.length) {
      const groups = ENTITY_GROUPS.map(([type, label]) => {
        const seen = new Set();
        const items = links
          .map((l) => ({ link: l, entity: entities.get(l.entity_id) }))
          .filter(({ entity }) => entity && entity.entity_type === type)
          .filter(({ link }) => !seen.has(link.entity_id) && seen.add(link.entity_id));
        if (!items.length) return null;
        return el('div', { class: 'record-entity-group' },
          el('h3', { class: 'record-subhead' }, label),
          el('ul', { class: 'card-tags record-tags' },
            items.map(({ link, entity }) => {
              const role = ROLE_LABELS[link.role];
              const tip = [entity.disambiguator, entity.description].filter(Boolean).join(' — ');
              return el('li', null,
                el('a', { class: 'card-tag', href: searchUrl(entity.name_preferred), title: tip || null },
                  entity.name_preferred,
                  role ? el('span', { class: 'record-role' }, ' · ' + role) : null));
            })));
      }).filter(Boolean);
      parts.push(section('rec-entities', 'People, places & subjects', groups));
    }

    // 3. Where to find it
    const where = [];
    if (source) {
      where.push(institutionBlock('Described by', source,
        'This institution wrote the description and hosts the page this record links to.'));
    }
    if (holder) {
      const status = record.holder_status === 'unconfirmed' ? ' (not confirmed)' : '';
      const block = institutionBlock('Original held by' + status, holder, null);
      if (record.holder_note) {
        block.append(el('details', { class: 'record-details' },
          el('summary', null, 'How we know this'),
          el('p', { class: 'record-muted' }, record.holder_note)));
      }
      where.push(block);
    } else if (record.holder_status === 'not_applicable') {
      where.push(el('p', { class: 'record-muted' }, 'There is no separate original to locate: the resource is the published or online item itself.'));
    } else {
      where.push(el('p', { class: 'record-muted' }, 'Where the original is held is not known yet.'));
    }
    where.push(factList([
      ['Access', ACCESS_MODES[record.access_mode] || record.access_mode],
      ['Digitized', DIGITIZED[record.digitized] || record.digitized],
    ]));
    if (record.access_instructions) {
      where.push(el('div', null, el('h3', { class: 'record-subhead' }, 'How to access it'), el('p', null, record.access_instructions)));
    }
    if (record.access_restrictions) {
      where.push(el('div', { class: 'record-callout' }, el('strong', null, 'Restrictions: '), record.access_restrictions));
    }
    parts.push(section('rec-where', 'Where to find it', where));

    // 4. Rights
    if (record.rights_statement || record.rights_url) {
      parts.push(section('rec-rights', 'Rights & reuse',
        record.rights_statement ? el('p', null, record.rights_statement) : null,
        record.rights_url ? el('ul', { class: 'institution-links' }, el('li', null, extLink(record.rights_url, 'Rights policy'))) : null,
        el('p', { class: 'record-muted' }, 'Black History Hub stores only this description and a link. The content belongs to the institution above.')));
    }

    // 5. Related records (relations are stored once, so check both sides)
    const related = data.record_relation
      .filter((rel) => rel.record_a_id === record.id || rel.record_b_id === record.id)
      .map((rel) => ({ rel, other: records.get(rel.record_a_id === record.id ? rel.record_b_id : rel.record_a_id) }))
      .filter(({ other }) => other);
    if (related.length) {
      parts.push(section('rec-related', 'Related records',
        el('ul', { class: 'record-related' },
          related.map(({ rel, other }) => {
            const otherSource = institutions.get(other.record_source_id);
            return el('li', null,
              el('span', { class: 'record-date-kind' }, RELATION_TYPES[rel.relation_type] || rel.relation_type),
              el('a', { href: 'record.html?' + new URLSearchParams({ id: other.id }).toString() }, other.title_original),
              otherSource ? el('span', { class: 'record-muted' }, ' — ' + otherSource.name) : null,
              rel.evidence_note ? el('p', { class: 'record-muted record-related-note' }, rel.evidence_note) : null);
          }))));
    }

    // 6. Provenance
    const verified = record.verification_status === 'verified';
    parts.push(section('rec-provenance', 'Provenance',
      factList([
        ['Status', el('span', { class: 'record-status ' + (verified ? 'is-verified' : 'needs-review') },
          verified ? 'Verified' : 'Needs review')],
        ['Last verified', formatDate(record.last_verified_at)],
        ['Link last checked', formatDate(record.link_last_checked)],
        ['Added', [formatDate(record.imported_at), record.added_by ? 'by ' + record.added_by : null].filter(Boolean).join(' ')],
        ['Collected', record.collection_method === 'manual' ? 'By hand from the source page' : record.collection_method],
        ['Record ID', record.id],
      ]),
      record.notes ? el('details', { class: 'record-details' }, el('summary', null, 'Curator notes'), el('p', null, record.notes)) : null,
      record.change_notes ? el('details', { class: 'record-details' }, el('summary', null, 'Change history'), el('p', null, record.change_notes)) : null));

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

    let data;
    try {
      data = await loadDataset();
    } catch (err) {
      showMessage('Could not load the record', LOAD_ERROR_MESSAGE);
      console.error('Failed to load dataset:', err);
      return;
    }

    const record = data.recordsById.get(id);
    if (!record) {
      showMessage('Record not found', 'There is no record with the ID "' + id + '". It may have been removed or the link may be wrong.');
      return;
    }
    render(data, record);
  }

  init();
})();
