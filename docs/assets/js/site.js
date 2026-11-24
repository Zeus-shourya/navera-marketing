/* Navera Marketing - site behaviour (no dependencies) */
(function () {
  'use strict';
  var doc = document.documentElement;
  var header = document.querySelector('.site-header');

  /* header glass on scroll */
  function onScroll() { if (header) header.classList.toggle('is-scrolled', window.scrollY > 24); }
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* mobile menu */
  var burger = document.querySelector('.burger');
  function setNav(open) {
    doc.classList.toggle('nav-open', open);
    if (burger) {
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
      burger.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    }
    document.body.style.overflow = open ? 'hidden' : '';
  }
  if (burger) burger.addEventListener('click', function () { setNav(!doc.classList.contains('nav-open')); });
  document.querySelectorAll('.menu a').forEach(function (a) {
    a.addEventListener('click', function () { setNav(false); });
  });

  /* services dropdown (click / keyboard / touch) */
  document.querySelectorAll('.has-drop').forEach(function (li) {
    var btn = li.querySelector('button.top');
    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = !li.classList.contains('open');
      li.classList.toggle('open', open);
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  });
  document.addEventListener('click', function (e) {
    document.querySelectorAll('.has-drop.open').forEach(function (li) {
      if (!li.contains(e.target)) { li.classList.remove('open'); li.querySelector('button.top').setAttribute('aria-expanded', 'false'); }
    });
  });

  /* WhatsApp chooser */
  var fab = document.getElementById('fab');
  var fabBtn = fab && fab.querySelector('.fab-btn');
  function setFab(open) {
    if (!fab) return;
    fab.classList.toggle('open', open);
    fabBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (fabBtn) fabBtn.addEventListener('click', function (e) { e.stopPropagation(); setFab(!fab.classList.contains('open')); });
  document.querySelectorAll('[data-wa]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      if (!fab) return;
      e.preventDefault(); e.stopPropagation();
      setNav(false);
      setFab(true);
      var first = fab.querySelector('.fab-panel a');
      if (first) setTimeout(function () { first.focus({ preventScroll: true }); }, 60);
    });
  });
  document.addEventListener('click', function (e) { if (fab && fab.classList.contains('open') && !fab.contains(e.target)) setFab(false); });
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    setFab(false); setNav(false);
    document.querySelectorAll('.has-drop.open').forEach(function (li) { li.classList.remove('open'); });
  });

  /* reveal on scroll */
  var rv = document.querySelectorAll('.rv');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
    rv.forEach(function (el) { io.observe(el); });
  } else {
    rv.forEach(function (el) { el.classList.add('in'); });
  }

  /* portfolio filters (/work/) */
  var grid = document.getElementById('work-grid');
  if (grid) {
    var btns = document.querySelectorAll('[data-filter]');
    var status = document.getElementById('work-status');
    btns.forEach(function (b) {
      b.addEventListener('click', function () {
        var f = b.getAttribute('data-filter'), n = 0;
        btns.forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        grid.querySelectorAll('.work-card').forEach(function (c) {
          var cats = c.getAttribute('data-cats');
          var show = f === 'all' || cats === '*' || (' ' + cats + ' ').indexOf(' ' + f + ' ') > -1;
          c.hidden = !show;
          if (show) { c.classList.add('in'); if (cats !== '*') n++; }
        });
        if (status) status.textContent = n + (n === 1 ? ' project' : ' projects') + ' shown';
      });
    });
  }

  /* footer year */
  document.querySelectorAll('[data-year]').forEach(function (el) { el.textContent = new Date().getFullYear(); });

  /* contact form -> WhatsApp message */
  var form = document.getElementById('wa-form');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var f = form.elements;
      var lines = ['Hi Navera Marketing! I came from your website.'];
      function add(label, v) { v = (v || '').trim(); if (v) lines.push(label + ': ' + v); }
      add('Name', f.name.value);
      add('Business', f.business.value);
      add('Phone', f.phone.value);
      add('Interested in', f.service.value);
      add('Area', f.area.value);
      add('Message', f.message.value);
      var to = (f.to && f.to.value) || form.getAttribute('data-default');
      window.open('https://wa.me/' + to + '?text=' + encodeURIComponent(lines.join('\n')), '_blank', 'noopener');
    });
  }
})();
