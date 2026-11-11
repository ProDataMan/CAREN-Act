// Shared header/navigation and footer. Include with <script src="assets/site.js" defer></script>
// and put <header class="site-header" id="siteHeader"></header> at the top of <body>.
(function () {
  'use strict';
  var NAV = [
    { href: 'index.html', label: 'Map' },
    { href: 'county.html', label: 'Your county' },
    { href: 'bill.html', label: 'Draft bill' },
    { href: 'deaths.html', label: 'Contested deaths' },
    { href: 'laws.html', label: 'Old laws tracker' },
    { href: 'history.html', label: 'History' },
    { href: 'learn.html', label: 'Learn' },
    { href: 'stories.html', label: 'Stories' },
    { href: 'data.html', label: 'Data' },
    { href: 'volunteer.html', label: 'Volunteer' },
    { href: 'act.html', label: 'Take action', cta: true }
  ];
  var page = (location.pathname.split('/').pop() || 'index.html');

  var header = document.getElementById('siteHeader');
  if (header) {
    header.className = 'site-header';
    var links = NAV.map(function (n) {
      var current = (n.href === page || (page === 'module.html' && n.href === 'learn.html')) ? ' aria-current="page"' : '';
      return '<a href="' + n.href + '"' + current + (n.cta ? ' class="cta"' : '') + '>' + n.label + '</a>';
    }).join('');
    header.innerHTML =
      '<div class="bar">' +
      '<a class="site-brand" href="index.html" aria-label="Federal CAREN Act home"><span class="mark" aria-hidden="true">CA</span><span>Federal CAREN Act</span></a>' +
      '<button class="nav-toggle" type="button" aria-expanded="false" aria-controls="siteNav">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M3 6h18M3 12h18M3 18h18"/></svg>Menu</button>' +
      '<nav class="site-nav" id="siteNav" aria-label="Main">' + links + '</nav></div>';
    var toggle = header.querySelector('.nav-toggle');
    var nav = header.querySelector('.site-nav');
    function setOpen(open) {
      nav.classList.toggle('open', open);
      document.body.classList.toggle('nav-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.lastChild.textContent = open ? 'Close' : 'Menu';
    }
    toggle.addEventListener('click', function () { setOpen(!nav.classList.contains('open')); });
    // Collapse to the menu button whenever the links don't fit (e.g. longer translated labels).
    var bar = header.querySelector('.bar');
    window.CarenFitHeader = function () {
      header.classList.remove('compact');
      if (bar.scrollWidth > bar.clientWidth + 1) header.classList.add('compact');
    };
    window.addEventListener('resize', window.CarenFitHeader);
    setTimeout(window.CarenFitHeader, 0);
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) setOpen(false); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && nav.classList.contains('open')) { setOpen(false); toggle.focus(); } });
  }

  // "63% people of color (Asian 35%, Hispanic 16%)": list groups largest first, and stop once the groups
  // shown add up to at least half of all people of color, or once both Black and Hispanic have been shown.
  function pct(v) { return (v >= 9.95 || v === 0 ? Math.round(v) : Math.round(v * 10) / 10) + '%'; }
  window.CarenRace = {
    pct: pct,
    // groups: { Black: 4.7, Hispanic: 16.2, Asian: 34.9, ... } as percentages of the whole population
    describe: function (minority, groups) {
      var list = Object.keys(groups).map(function (k) { return [k, Number(groups[k]) || 0]; })
        .filter(function (g) { return g[1] > 0; }).sort(function (a, b) { return b[1] - a[1]; });
      var shown = [], sum = 0, sawB = false, sawH = false;
      for (var i = 0; i < list.length; i++) {
        shown.push(list[i][0] + ' ' + pct(list[i][1]));
        sum += list[i][1];
        if (list[i][0] === 'Black') sawB = true;
        if (list[i][0] === 'Hispanic') sawH = true;
        if (sum >= minority / 2 || (sawB && sawH)) break;
      }
      return pct(minority) + ' people of color' + (shown.length ? ' (' + shown.join(', ') + ')' : '');
    },
    // counties.json row -> groups
    fromCounty: function (r) { return { Black: r[7], Hispanic: r[8], Asian: r[15], 'Native American': r[16], 'Pacific Islander': r[17], 'Other or multiracial': r[18] }; },
    // districts.json entry -> groups
    fromDistrict: function (d) { return { Black: d[2], Hispanic: d[3], Asian: d[4], 'Native American': d[5], 'Pacific Islander': d[6], 'Other or multiracial': d[7] }; }
  };

  var footer = document.getElementById('siteFooter');
  if (footer) {
    footer.className = 'site-footer';
    footer.innerHTML =
      '<div><a href="https://github.com/ProDataMan/CAREN-Act">GitHub</a>·<a href="../docs/SF-CAREN-Act.pdf" download>Original SF ordinance (PDF)</a>·<a href="data.html">Data &amp; methodology</a>·<a href="privacy.html">Privacy</a></div>' +
      '<div style="margin-top:6px">Public data from EJI, Mapping Police Violence, FBI, CDC, U.S. Census Bureau and Mapping Inequality. Verify with primary sources.</div>';
  }
})();

// ---------------------------------------------------------------- Languages (hub and spoke)
// English text in the pages is the hub. Each other language is a spoke file, i18n/<lang>.json, that maps
// English strings to translations ("strings"), plus regex "patterns" for text with numbers. Anything missing
// stays in English. The language comes from ?lang=, then the visitor's saved choice, then the browser locale.
(function () {
  'use strict';
  var LANGS = { en: 'English', es: 'Español' };
  var KEY = 'caren-lang';
  function saved() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function save(l) { try { localStorage.setItem(KEY, l); } catch (e) { /* ignore */ } }
  var q = /[?&]lang=([a-z]{2})/.exec(location.search);
  var lang = q && LANGS[q[1]] ? q[1] : saved();
  if (q && LANGS[q[1]]) save(q[1]);
  if (!lang || !LANGS[lang]) {
    var nav = (navigator.languages && navigator.languages[0]) || navigator.language || 'en';
    lang = /^es\b/i.test(nav) ? 'es' : 'en';
  }
  document.documentElement.lang = lang;
  var api = window.CarenI18n = { lang: lang, langs: LANGS, t: function (s) { return s; }, ready: Promise.resolve(), set: function (l) { save(l); var u = new URL(location.href); u.searchParams.delete('lang'); location.href = u.toString(); } };

  // Language selector in the header (every page that has the shared header).
  var bar = document.querySelector('#siteHeader .bar');
  if (bar) {
    var sel = document.createElement('select');
    sel.className = 'lang-select'; sel.setAttribute('aria-label', lang === 'es' ? 'Idioma' : 'Language'); sel.setAttribute('translate', 'no');
    Object.keys(LANGS).forEach(function (k) { var o = document.createElement('option'); o.value = k; o.textContent = LANGS[k]; if (k === lang) o.selected = true; sel.appendChild(o); });
    sel.addEventListener('change', function () { api.set(sel.value); });
    var toggle = bar.querySelector('.nav-toggle');
    bar.insertBefore(sel, toggle);
    if (window.CarenFitHeader) window.CarenFitHeader();
  }
  if (lang === 'en') return;

  var SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, CODE: 1, PRE: 1, NOSCRIPT: 1 };
  var ATTRS = ['placeholder', 'title', 'aria-label', 'alt'];
  var dict = {}, patterns = [];
  var norm = function (s) { return s.replace(/\s+/g, ' ').trim(); };
  function tr(s) {
    var k = norm(s);
    if (!k) return null;
    if (Object.prototype.hasOwnProperty.call(dict, k)) return dict[k];
    for (var i = 0; i < patterns.length; i++) if (patterns[i][0].test(k)) return k.replace(patterns[i][0], patterns[i][1]);
    return null;
  }
  api.t = function (s) { var r = tr(String(s)); return r == null ? s : r; };
  function skip(el) {
    for (var e = el; e && e.nodeType === 1; e = e.parentNode) {
      if (SKIP[e.tagName] || e.getAttribute('translate') === 'no' || e.classList.contains('notranslate')) return true;
    }
    return false;
  }
  function doText(n) {
    if (!n.nodeValue || !/[A-Za-z]/.test(n.nodeValue) || skip(n.parentNode)) return;
    var r = tr(n.nodeValue);
    // Only write when the text changes: writing fires the observer again, and an unchanged write would loop forever.
    if (r != null && r !== norm(n.nodeValue)) { var m = /^(\s*)[\s\S]*?(\s*)$/.exec(n.nodeValue); n.nodeValue = m[1] + r + m[2]; }
  }
  function doEl(el) {
    if (el.nodeType !== 1 || skip(el)) return;
    ATTRS.forEach(function (a) { var v = el.getAttribute(a); if (v) { var r = tr(v); if (r != null && r !== v) el.setAttribute(a, r); } });
    if (el.tagName === 'INPUT' && /^(button|submit)$/i.test(el.type) && el.value) { var r = tr(el.value); if (r != null) el.value = r; }
    var w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
    var n;
    while ((n = w.nextNode())) {
      if (n.nodeType === 3) doText(n);
      else if (n !== el) ATTRS.forEach(function (a) { var v = n.getAttribute(a); if (v && !skip(n)) { var r = tr(v); if (r != null && r !== v) n.setAttribute(a, r); } });
    }
  }
  function run() {
    var t = tr(document.title); if (t != null) document.title = t;
    var md = document.querySelector('meta[name="description"]'); if (md) { var d = tr(md.content); if (d != null) md.content = d; }
    doEl(document.body);
    if (window.CarenFitHeader) window.CarenFitHeader();
    new MutationObserver(function (list) {
      list.forEach(function (m) {
        if (m.type === 'characterData') doText(m.target);
        else m.addedNodes.forEach(function (n) { if (n.nodeType === 3) doText(n); else doEl(n); });
      });
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  document.documentElement.classList.add('i18n-pending');
  var reveal = function () { document.documentElement.classList.remove('i18n-pending'); };
  setTimeout(reveal, 1500);
  api.ready = fetch('i18n/' + lang + '.json').then(function (r) { return r.json(); }).then(function (j) {
    dict = j.strings || {};
    patterns = (j.patterns || []).map(function (p) { return [new RegExp(p[0]), p[1]]; });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run); else run();
  }).catch(function (e) { console.warn('[i18n]', e); }).then(reveal);
})();
