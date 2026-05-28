/* ============================================
   ASTRONOMY PORTFOLIO - MAIN JAVASCRIPT
   Interactive features and animations
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  initThemeToggle();
  initMobileNav();
  initSmoothScroll();
  initScrollAnimations();
  initGallery();
  initLazyLoading();
  initProgressBar();
  initWritingsFilter();
});

/* --- Reading Progress Bar --- */
function initProgressBar() {
  const bar = document.getElementById('progress-bar');
  if (!bar) return;
  const update = () => {
    const scrollTop = window.scrollY;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = docHeight > 0 ? (scrollTop / docHeight * 100) + '%' : '0%';
  };
  window.addEventListener('scroll', update, { passive: true });
  update();
}

/* --- Meanderings Filter --- */
function initWritingsFilter() {
  const buttons = document.querySelectorAll('.filter-btn');
  if (!buttons.length) return;
  const cards = document.querySelectorAll('.writing-card');

  const stampMap = document.getElementById('stamp-map-section');

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;
      cards.forEach(card => {
        const match = filter === 'all' || card.classList.contains('writing-card--' + filter);
        card.classList.toggle('hidden', !match);
      });
      if (stampMap) stampMap.style.display = filter === 'all' ? '' : 'none';
    });
  });
}

/* --- Theme Toggle (Dark/Light Mode) --- */
function initThemeToggle() {
  const toggle = document.querySelector('.theme-toggle');
  if (!toggle) return;

  // Check for saved preference or system preference
  const savedTheme = localStorage.getItem('theme');
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  
  if (savedTheme) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  } else if (systemPrefersDark) {
    document.documentElement.setAttribute('data-theme', 'dark');
  }

  toggle.addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Announce theme change for screen readers
    const announcement = document.createElement('div');
    announcement.setAttribute('role', 'status');
    announcement.setAttribute('aria-live', 'polite');
    announcement.className = 'sr-only';
    announcement.textContent = `Theme changed to ${newTheme} mode`;
    document.body.appendChild(announcement);
    setTimeout(() => announcement.remove(), 1000);
  });

  // Listen for system preference changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
      document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
    }
  });
}

/* --- Mobile Navigation --- */
function initMobileNav() {
  const toggle = document.querySelector('.nav__toggle');
  const navList = document.querySelector('.nav__list');
  
  if (!toggle || !navList) return;

  toggle.addEventListener('click', () => {
    const isOpen = navList.classList.contains('active');
    navList.classList.toggle('active');
    toggle.setAttribute('aria-expanded', !isOpen);
    
    // Toggle body scroll
    document.body.style.overflow = isOpen ? '' : 'hidden';
    
    // Animate hamburger
    const spans = toggle.querySelectorAll('span');
    if (!isOpen) {
      spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
      spans[1].style.opacity = '0';
      spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
    } else {
      spans[0].style.transform = '';
      spans[1].style.opacity = '';
      spans[2].style.transform = '';
    }
  });

  // Close nav on link click
  navList.querySelectorAll('a').forEach(link => {
    link.addEventListener('click', () => {
      navList.classList.remove('active');
      document.body.style.overflow = '';
      toggle.setAttribute('aria-expanded', 'false');
      
      const spans = toggle.querySelectorAll('span');
      spans.forEach(span => {
        span.style.transform = '';
        span.style.opacity = '';
      });
    });
  });

  // Close on escape
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && navList.classList.contains('active')) {
      navList.classList.remove('active');
      document.body.style.overflow = '';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.focus();
    }
  });
}

/* --- Smooth Scrolling --- */
function initSmoothScroll() {
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', (e) => {
      const href = anchor.getAttribute('href');
      if (href === '#') return;
      
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const headerOffset = 100;
        const elementPosition = target.getBoundingClientRect().top;
        const offsetPosition = elementPosition + window.pageYOffset - headerOffset;

        window.scrollTo({
          top: offsetPosition,
          behavior: 'smooth'
        });
        
        // Update focus for accessibility
        target.setAttribute('tabindex', '-1');
        target.focus({ preventScroll: true });
      }
    });
  });
}

/* --- Scroll-triggered Animations --- */
function initScrollAnimations() {
  const animatedElements = document.querySelectorAll('.animate-on-scroll');
  
  if (!animatedElements.length) return;

  const observerOptions = {
    root: null,
    rootMargin: '0px 0px -50px 0px',
    threshold: 0.1
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        
        // Stagger children if present
        const children = entry.target.querySelectorAll('.stagger-item');
        children.forEach((child, index) => {
          child.style.animationDelay = `${index * 0.1}s`;
          child.classList.add('is-visible');
        });
        
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  animatedElements.forEach(el => observer.observe(el));
}

/* --- Photo Gallery --- */
function initGallery() {
  const gallery = document.querySelector('.gallery__grid');
  if (!gallery) return;

  // Create lightbox if it doesn't exist
  let lightbox = document.querySelector('.lightbox');
  if (!lightbox) {
    lightbox = document.createElement('div');
    lightbox.className = 'lightbox';
    lightbox.innerHTML = `
      <button class="lightbox__close" aria-label="Close lightbox">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
      <div class="lightbox__content">
        <img class="lightbox__img" src="" alt="">
        <div class="lightbox__caption"></div>
      </div>
    `;
    document.body.appendChild(lightbox);
  }

  const lightboxImg = lightbox.querySelector('.lightbox__img');
  const lightboxCaption = lightbox.querySelector('.lightbox__caption');
  const closeBtn = lightbox.querySelector('.lightbox__close');

  // Gallery item click handler
  gallery.addEventListener('click', (e) => {
    const item = e.target.closest('.gallery__item');
    if (!item) return;

    const img = item.querySelector('img');
    const caption = item.querySelector('.gallery__caption-text');
    const location = item.querySelector('.gallery__caption-location');
    
    lightboxImg.src = img.dataset.fullSrc || img.src;
    lightboxImg.alt = img.alt;
    
    if (caption || location) {
      lightboxCaption.innerHTML = `
        ${caption ? `<p>${caption.textContent}</p>` : ''}
        ${location ? `<span style="font-size: 0.75rem; opacity: 0.7;">${location.textContent}</span>` : ''}
      `;
    } else {
      lightboxCaption.innerHTML = '';
    }
    
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
    closeBtn.focus();
  });

  // Close lightbox
  const closeLightbox = () => {
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
  };

  closeBtn.addEventListener('click', closeLightbox);
  lightbox.addEventListener('click', (e) => {
    if (e.target === lightbox) closeLightbox();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && lightbox.classList.contains('active')) {
      closeLightbox();
    }
  });

  // Touch support for captions on mobile
  if ('ontouchstart' in window) {
    gallery.querySelectorAll('.gallery__item').forEach(item => {
      item.addEventListener('touchstart', () => {
        item.classList.toggle('touch-active');
      });
    });
  }
}

/* --- Lazy Loading Images --- */
function initLazyLoading() {
  const lazyImages = document.querySelectorAll('img[data-src]');
  
  if (!lazyImages.length) return;

  if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          img.src = img.dataset.src;
          img.removeAttribute('data-src');
          img.classList.add('loaded');
          imageObserver.unobserve(img);
        }
      });
    }, {
      rootMargin: '100px 0px'
    });

    lazyImages.forEach(img => imageObserver.observe(img));
  } else {
    // Fallback for older browsers
    lazyImages.forEach(img => {
      img.src = img.dataset.src;
      img.removeAttribute('data-src');
    });
  }
}

/* --- Utility Functions --- */

// Debounce function for scroll/resize events
function debounce(func, wait = 100) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Copy email to clipboard
function copyEmail(email) {
  const formattedEmail = email.replace(' [at] ', '@').replace(' [dot] ', '.');
  navigator.clipboard.writeText(formattedEmail).then(() => {
    // Show confirmation
    const confirmation = document.createElement('div');
    confirmation.className = 'copy-confirmation';
    confirmation.textContent = 'Email copied!';
    confirmation.style.cssText = `
      position: fixed;
      bottom: 2rem;
      left: 50%;
      transform: translateX(-50%);
      background: var(--color-text);
      color: var(--color-paper);
      padding: 0.75rem 1.5rem;
      border-radius: 4px;
      font-size: 0.875rem;
      z-index: 3000;
      animation: fadeInUp 0.3s ease;
    `;
    document.body.appendChild(confirmation);
    setTimeout(() => confirmation.remove(), 2000);
  });
}

// Header scroll behavior
let lastScroll = 0;
const header = document.querySelector('.header');

if (header) {
  window.addEventListener('scroll', debounce(() => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 100) {
      header.style.boxShadow = 'var(--shadow-subtle)';
    } else {
      header.style.boxShadow = '';
    }
    
    lastScroll = currentScroll;
  }, 10));
}

/* --- Expandable Content --- */
document.querySelectorAll('[data-expandable]').forEach(trigger => {
  trigger.addEventListener('click', () => {
    const targetId = trigger.getAttribute('data-expandable');
    const target = document.getElementById(targetId);
    
    if (target) {
      const isExpanded = target.classList.contains('expanded');
      target.classList.toggle('expanded');
      trigger.setAttribute('aria-expanded', !isExpanded);
      
      if (!isExpanded) {
        target.style.maxHeight = target.scrollHeight + 'px';
      } else {
        target.style.maxHeight = '0';
      }
    }
  });
});

/* --- Form Handling --- */
const contactForm = document.querySelector('.contact-form form');
if (contactForm) {
  contactForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    // Get form data
    const formData = new FormData(contactForm);
    const data = Object.fromEntries(formData);
    
    // Here you would typically send the data to a server
    // For now, we'll just show a confirmation
    
    const submitBtn = contactForm.querySelector('.form-submit');
    const originalText = submitBtn.textContent;
    
    submitBtn.textContent = 'Sending...';
    submitBtn.disabled = true;
    
    // Simulate sending (replace with actual API call)
    setTimeout(() => {
      submitBtn.textContent = 'Message Sent!';
      submitBtn.style.background = 'var(--color-accent)';
      
      // Reset form
      contactForm.reset();
      
      setTimeout(() => {
        submitBtn.textContent = originalText;
        submitBtn.style.background = '';
        submitBtn.disabled = false;
      }, 2000);
    }, 1000);
  });
}

/* --- Constellation Background Effect --- */
function createConstellationEffect(container) {
  if (!container) return;
  
  const canvas = document.createElement('canvas');
  canvas.className = 'constellation-canvas';
  canvas.style.cssText = `
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    opacity: 0.3;
  `;
  container.appendChild(canvas);
  
  const ctx = canvas.getContext('2d');
  let stars = [];
  
  function resize() {
    canvas.width = container.offsetWidth;
    canvas.height = container.offsetHeight;
    initStars();
  }
  
  function initStars() {
    stars = [];
    const numStars = Math.floor((canvas.width * canvas.height) / 15000);
    
    for (let i = 0; i < numStars; i++) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        radius: Math.random() * 1.5 + 0.5,
        opacity: Math.random() * 0.5 + 0.3,
        twinkleSpeed: Math.random() * 0.02 + 0.01
      });
    }
  }
  
  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    stars.forEach(star => {
      star.opacity += Math.sin(Date.now() * star.twinkleSpeed) * 0.01;
      star.opacity = Math.max(0.1, Math.min(0.8, star.opacity));
      
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(200, 168, 124, ${star.opacity})`;
      ctx.fill();
    });
    
    requestAnimationFrame(draw);
  }
  
  resize();
  draw();
  window.addEventListener('resize', debounce(resize, 200));
}

// Initialize constellation effect on hero if present
const heroSection = document.querySelector('.hero');
if (heroSection && window.innerWidth > 768) {
  // createConstellationEffect(heroSection); // Uncomment to enable
}
