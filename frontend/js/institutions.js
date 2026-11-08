// Institutions page: re-order the institution cards from the "Sort" menu.
// Record count = records held + records described (the numbers shown on each card).
document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('institution-grid');
  const menu = document.getElementById('institution-sort');
  if (!grid || !menu) return;

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
