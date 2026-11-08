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
