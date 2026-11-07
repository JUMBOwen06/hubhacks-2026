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

  // Carousel elements
  const slides = document.querySelectorAll('.carousel-slide');
  let currentSlide = 0;
  const slideInterval = 6000;

  // Modal elements
  const modalBackdrop = document.getElementById('modal-backdrop');
  const modalCloseBtn = document.getElementById('modal-close-btn');
  const modalThumbnail = document.getElementById('modal-thumbnail');
  const modalTitle = document.getElementById('modal-title');
  const modalIndex = document.getElementById('modal-index');
  const modalCategory = document.getElementById('modal-category');
  const modalTagsContainer = document.getElementById('modal-tags');
  const modalSourceBtn = document.getElementById('modal-source-btn');

  // Placeholder website URL variable (to be replaced by backend endpoint)
  let placeholderWebsiteUrl = 'https://archives.novascotia.ca/african-heritage/archival/';

  // Sidebar visibility handlers
  function openNav() {
    sideNav.classList.add('open');
    backdrop.classList.add('open');
  }

  function closeNav() {
    sideNav.classList.remove('open');
    backdrop.classList.remove('open');
  }

  if (toggleBtn) toggleBtn.addEventListener('click', openNav);
  if (closeBtn) closeBtn.addEventListener('click', closeNav);
  if (backdrop) backdrop.addEventListener('click', closeNav);

  // Dynamic tag selection counter
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

  // Carousel auto-rotation controller
  if (slides.length > 0) {
    setInterval(() => {
      slides[currentSlide].classList.remove('active');
      currentSlide = (currentSlide + 1) % slides.length;
      slides[currentSlide].classList.add('active');
    }, slideInterval);
  }

  // Search form submit handler
  if (searchForm) {
    searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const query = searchInput ? searchInput.value.trim() : '';
      const selectedTags = Array.from(document.querySelectorAll('.tag-checkbox:checked')).map(
        (cb) => cb.value
      );
      console.log('Search dispatched:', { query, selectedTags });
    });
  }

  // Modal display handlers
  function openModal(cardElement) {
    if (!modalBackdrop) return;

    // Extract content from clicked card
    const cardImg = cardElement.querySelector('.card-thumb');
    const cardTitleEl = cardElement.querySelector('.card-heading');
    const cardIndexEl = cardElement.querySelector('.card-title');
    const cardCatEl = cardElement.querySelector('.card-category');
    const cardTags = cardElement.querySelectorAll('.card-tag');

    // Populate modal components
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

    modalBackdrop.classList.add('open');
    modalBackdrop.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
  }

  function closeModal() {
    if (!modalBackdrop) return;
    modalBackdrop.classList.remove('open');
    modalBackdrop.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
  }

  // Attach click listener to all cards on the page (excluding the rec card inside modal)
  document.querySelectorAll('.card-stack .card').forEach((card) => {
    card.addEventListener('click', () => openModal(card));
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        openModal(card);
      }
    });
  });

  if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeModal);

  // Close modal when clicking on the blurred backdrop outside the card
  if (modalBackdrop) {
    modalBackdrop.addEventListener('click', (e) => {
      if (e.target === modalBackdrop) closeModal();
    });
  }

  // Close modal on Escape key press
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalBackdrop && modalBackdrop.classList.contains('open')) {
      closeModal();
    }
  });
});