document.addEventListener('DOMContentLoaded', () => {
  // Navigation elements
  const sideNav = document.getElementById('side-nav');
  const backdrop = document.getElementById('backdrop');
  const toggleBtn = document.getElementById('sidebar-toggle-btn');
  const closeBtn = document.getElementById('sidebar-close-btn');

  // Search & Filter elements
  const searchForm = document.getElementById('search-form');
  const searchInput = document.getElementById('search-input');
  const tagDropdownLabel = document.getElementById('tag-dropdown-label');
  const checkboxes = document.querySelectorAll('.tag-checkbox');

  // Carousel elements (only runs if slides exist on page)
  const slides = document.querySelectorAll('.carousel-slide');
  const carouselToggle = document.getElementById('carousel-toggle');
  let currentSlide = 0;
  const slideInterval = 6000;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // 1. Sidebar (mobile menu)
  function openNav() {
    if (!sideNav) return;
    sideNav.classList.add('open');
    sideNav.inert = false;
    if (backdrop) backdrop.classList.add('open');
    if (toggleBtn) toggleBtn.setAttribute('aria-expanded', 'true');
    const firstLink = sideNav.querySelector('a');
    if (firstLink) firstLink.focus();
  }

  function closeNav() {
    if (!sideNav || !sideNav.classList.contains('open')) return;
    sideNav.classList.remove('open');
    sideNav.inert = true;
    if (backdrop) backdrop.classList.remove('open');
    if (toggleBtn) {
      toggleBtn.setAttribute('aria-expanded', 'false');
      toggleBtn.focus();
    }
  }

  if (toggleBtn) toggleBtn.addEventListener('click', openNav);
  if (closeBtn) closeBtn.addEventListener('click', closeNav);
  if (backdrop) backdrop.addEventListener('click', closeNav);

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeNav();
  });

  // 2. Dynamic tag selection counter
  checkboxes.forEach((cb) => {
    cb.addEventListener('change', () => {
      const checkedCount = document.querySelectorAll('.tag-checkbox:checked').length;
      if (tagDropdownLabel) {
        tagDropdownLabel.textContent = checkedCount === 0
          ? 'Filter by Type'
          : `Type (${checkedCount} selected)`;
      }
    });
  });

  // 3. Carousel: auto-rotates unless the user prefers reduced motion; pause/play button
  let carouselTimer = null;

  function nextSlide() {
    slides[currentSlide].classList.remove('active');
    currentSlide = (currentSlide + 1) % slides.length;
    slides[currentSlide].classList.add('active');
  }

  function setCarouselPlaying(playing) {
    clearInterval(carouselTimer);
    carouselTimer = playing ? setInterval(nextSlide, slideInterval) : null;
    if (carouselToggle) {
      carouselToggle.textContent = playing ? '❚❚' : '▶';
      carouselToggle.setAttribute('aria-label', playing ? 'Pause slideshow' : 'Play slideshow');
      carouselToggle.setAttribute('aria-pressed', playing ? 'false' : 'true');
    }
  }

  if (slides.length > 1) {
    setCarouselPlaying(!reduceMotion);
    if (carouselToggle) {
      carouselToggle.addEventListener('click', () => setCarouselPlaying(carouselTimer === null));
    }
  } else if (carouselToggle) {
    carouselToggle.hidden = true;
  }

  // 3b. "About these photos" toggle (only visible on mobile; shows the image credits)
  const citationToggle = document.getElementById('hero-citation-toggle');
  const citationBar = document.getElementById('hero-citation-bar');
  if (citationToggle && citationBar) {
    const setCitationOpen = (open) => {
      citationBar.classList.toggle('is-open', open);
      citationToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    citationToggle.addEventListener('click', () => {
      setCitationOpen(!citationBar.classList.contains('is-open'));
    });
    document.addEventListener('click', (e) => {
      if (!citationBar.classList.contains('is-open')) return;
      if (e.target.closest('#hero-citation-bar, #hero-citation-toggle')) return;
      setCitationOpen(false);
    });
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && citationBar.classList.contains('is-open')) {
        setCitationOpen(false);
        citationToggle.focus();
      }
    });
  }

  // 3c. Featured columns (Recently Searched / Recommended / Popular): when the columns stack
  //     (narrow screens, see .card-stack.is-collapsed in styles.css) show the first
  //     COLUMN_PREVIEW cards and a "Show N more" button. On wide screens CSS hides the button
  //     and shows every card.
  const COLUMN_PREVIEW = 2;
  document.querySelectorAll('.column-section .card-stack').forEach((stack, i) => {
    const extra = stack.querySelectorAll(':scope > .card').length - COLUMN_PREVIEW;
    if (extra <= 0) return;
    const section = stack.closest('.column-section');
    const title = section.querySelector('.column-title');
    const name = title ? title.textContent.trim() : 'records';
    if (!stack.id) stack.id = `card-stack-${i + 1}`;

    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'column-more';
    btn.setAttribute('aria-controls', stack.id);

    const setOpen = (open) => {
      stack.classList.toggle('is-collapsed', !open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      btn.innerHTML = '';
      btn.append(open ? 'Show fewer' : `Show ${extra} more`);
      const hidden = document.createElement('span');
      hidden.className = 'visually-hidden';
      hidden.textContent = ` ${name}`;
      btn.append(hidden);
    };

    btn.addEventListener('click', () => {
      const opening = stack.classList.contains('is-collapsed');
      setOpen(opening);
      if (opening) {
        // Move focus to the first newly shown card so keyboard users land on it
        const firstNew = stack.querySelectorAll(':scope > .card')[COLUMN_PREVIEW];
        const link = firstNew && firstNew.querySelector('a');
        if (link) link.focus({ preventScroll: true });
      } else {
        // Cards above the button disappear; bring the column back into view
        section.scrollIntoView({ block: 'start', behavior: reduceMotion ? 'auto' : 'smooth' });
      }
    });

    setOpen(false);
    stack.after(btn);
  });

  // 4. Search form submit -> results.html?q=…&type=… (type values match record.resource_type)
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = searchInput ? searchInput.value.trim() : '';
      const selectedTypes = Array.from(document.querySelectorAll('.tag-checkbox:checked')).map(
        (cb) => cb.value
      );

      const params = new URLSearchParams();
      params.set('q', query);
      if (selectedTypes.length > 0) params.set('type', selectedTypes.join(','));
      // Set by results.js when the results are limited to one institution
      if (searchForm.dataset.institution) params.set('institution', searchForm.dataset.institution);
      window.location.href = `results.html?${params.toString()}`;
    });
  }

  // 5. Remember the page a record was opened from so record.html can link back to it.
  //    Delegated, because results.js renders the cards after this runs.
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.card-link')) return;
    try {
      sessionStorage.setItem('lastResults', window.location.href);
    } catch (err) {
      // sessionStorage unavailable (private mode etc.); back link falls back to index.html
    }
  });
});
