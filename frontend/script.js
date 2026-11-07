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
  let currentSlide = 0;
  const slideInterval = 6000;

  // Modal elements
  const modalBackdrop = document.getElementById('modal-backdrop');
  const modalCard = document.getElementById('article-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalThumbnail = document.getElementById('modal-thumbnail');
  const modalTitle = document.getElementById('modal-title');
  const modalIndex = document.getElementById('modal-index');
  const modalCategory = document.getElementById('modal-category');
  const modalTagsContainer = document.getElementById('modal-tags');
  const modalSourceBtn = document.getElementById('modal-source-btn');
  const modalRecCard = document.querySelector('.modal-rec-card');

  // Placeholder website URL variable
  let placeholderWebsiteUrl = 'https://archives.novascotia.ca/african-heritage/archival/';

  // 1. Sidebar visibility handlers
  function openNav() {
    if (sideNav) sideNav.classList.add('open');
    if (backdrop) backdrop.classList.add('open');
  }

  function closeNav() {
    if (sideNav) sideNav.classList.remove('open');
    if (backdrop) backdrop.classList.remove('open');
  }

  if (toggleBtn) toggleBtn.addEventListener('click', openNav);
  if (closeBtn) closeBtn.addEventListener('click', closeNav);
  if (backdrop) backdrop.addEventListener('click', closeNav);

  // 2. Dynamic tag selection counter
  if (checkboxes.length > 0) {
    checkboxes.forEach((cb) => {
      cb.addEventListener('change', () => {
        const checkedCount = document.querySelectorAll('.tag-checkbox:checked').length;
        if (tagDropdownLabel) {
          tagDropdownLabel.textContent = checkedCount === 0 
            ? 'Filter by Tags' 
            : `Tags (${checkedCount} selected)`;
        }
      });
    });
  }

  // 3. Carousel auto-rotation controller
  if (slides && slides.length > 0) {
    setInterval(() => {
      slides[currentSlide].classList.remove('active');
      currentSlide = (currentSlide + 1) % slides.length;
      slides[currentSlide].classList.add('active');
    }, slideInterval);
  }

  // 4. Search form submit handler
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = searchInput ? searchInput.value.trim() : '';
      const selectedTags = Array.from(document.querySelectorAll('.tag-checkbox:checked')).map(
        (cb) => cb.value
      );
      
      console.log('Search dispatched:', { query, selectedTags });
      window.location.href = `results.html?q=${encodeURIComponent(query)}&tags=${encodeURIComponent(selectedTags.join(','))}`;
    });
  }

  // 5. Helper function: Populates modal contents from any card DOM element
  function fillModalFromCard(cardElement) {
    if (!cardElement) return;

    const cardImg = cardElement.querySelector('.card-thumb');
    const cardTitleEl = cardElement.querySelector('.card-heading');
    const cardIndexEl = cardElement.querySelector('.card-title');
    const cardCatEl = cardElement.querySelector('.card-category');
    const cardTags = cardElement.querySelectorAll('.card-tag');

    if (modalThumbnail && cardImg) modalThumbnail.src = cardImg.src;
    if (modalTitle && cardTitleEl) modalTitle.textContent = cardTitleEl.textContent;
    if (modalIndex && cardIndexEl) modalIndex.textContent = cardIndexEl.textContent;
    if (modalCategory && cardCatEl) modalCategory.textContent = cardCatEl.textContent;

    if (modalTagsContainer) {
      modalTagsContainer.innerHTML = '';
      cardTags.forEach((tag) => {
        const span = document.createElement('span');
        span.className = 'card-tag';
        span.textContent = tag.textContent;
        modalTagsContainer.appendChild(span);
      });
    }

    if (modalSourceBtn) {
      modalSourceBtn.href = placeholderWebsiteUrl;
    }

    // Reset scroll position to top of modal card
    if (modalCard) {
      modalCard.scrollTop = 0;
    }
  }

  // 6. Modal Open / Close handlers
  function openModal(cardElement) {
    if (!modalBackdrop) return;
    fillModalFromCard(cardElement);

    modalBackdrop.classList.add('open');
    modalBackdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    if (!modalBackdrop) return;
    modalBackdrop.classList.remove('open');
    modalBackdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  // 7. Attach click listener ONLY to outer cards (ignoring the inner modal-rec-card)
  const outerCards = document.querySelectorAll(
    '.column-section .card, .horizontal-results-list .card'
  );

  outerCards.forEach((card) => {
    // Ensure we never attach this listener to the modal's internal recommended card
    if (card.classList.contains('modal-rec-card')) return;

    card.addEventListener('click', () => openModal(card));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openModal(card);
      }
    });
  });

  // 8. Recommended Article inside Modal: Click Transition Handler
  if (modalRecCard) {
    function handleRecCardClick(e) {
      if (e) e.stopPropagation();

      // Read current recommended details
      const recTitleEl = modalRecCard.querySelector('.card-heading');
      const recIndexEl = modalRecCard.querySelector('.card-title');
      const recTags = modalRecCard.querySelectorAll('.card-tag');
      const previousModalTitle = modalTitle ? modalTitle.textContent : 'Related Archive';

      // 1. Transition modal to the recommended article
      if (modalTitle && recTitleEl) modalTitle.textContent = recTitleEl.textContent;
      if (modalIndex && recIndexEl) modalIndex.textContent = recIndexEl.textContent;
      if (modalCategory) modalCategory.textContent = 'Recommended Selection';

      if (modalTagsContainer) {
        modalTagsContainer.innerHTML = '';
        recTags.forEach((tag) => {
          const span = document.createElement('span');
          span.className = 'card-tag';
          span.textContent = tag.textContent;
          modalTagsContainer.appendChild(span);
        });
      }

      // Smoothly scroll modal back to top
      if (modalCard) {
        modalCard.scrollTo({ top: 0, behavior: 'smooth' });
      }

      // 2. Rotate the recommended card slot with a new recommendation
      if (recTitleEl) {
        recTitleEl.textContent = `Exploration: ${previousModalTitle}`;
      }
    }

    modalRecCard.addEventListener('click', handleRecCardClick);
    modalRecCard.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleRecCardClick(e);
      }
    });
  }

  // 9. Close buttons and backdrop listeners
  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);

  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) closeModal();
    });
  }

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalBackdrop && modalBackdrop.classList.contains('open')) {
      closeModal();
    }
  });
});