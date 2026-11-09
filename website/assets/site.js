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
