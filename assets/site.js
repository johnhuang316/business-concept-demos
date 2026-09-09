(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const revealItems = document.querySelectorAll('.reveal');

  if (reducedMotion || !('IntersectionObserver' in window)) {
    revealItems.forEach((item) => item.classList.add('visible'));
  } else {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealItems.forEach((item) => observer.observe(item));
  }

  document.querySelectorAll('[data-demo-form]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const result = form.querySelector('.form-result');
      if (!result) return;
      result.textContent = form.dataset.resultLang === 'en'
        ? 'This is a concept interaction. Your information was not sent or stored. A production version could connect to the business’s preferred email, WhatsApp or booking flow.'
        : '這是概念頁互動示意，資料沒有送出或保存。正式版本可串接品牌指定的 LINE、Email 或預約系統。';
      result.classList.add('show');
      result.setAttribute('role', 'status');
      result.focus?.();
    });
  });

  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', () => {
      const target = document.querySelector(link.getAttribute('href'));
      if (target) target.setAttribute('tabindex', '-1');
    });
  });
})();
