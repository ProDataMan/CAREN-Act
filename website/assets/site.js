// Shared header/navigation and footer. Include with <script src="assets/site.js" defer></script>
// and put <header class="site-header" id="siteHeader"></header> at the top of <body>.
(function () {
  'use strict';
  var NAV = [
    { href: 'index.html', label: 'Map' },
    { href: 'bill.html', label: 'Draft bill' },
    { href: 'deaths.html', label: 'Contested deaths' },
    { href: 'laws.html', label: 'Old laws tracker' },
    { href: 'history.html', label: 'History' },
    { href: 'data.html', label: 'Data' },
    { href: 'volunteer.html', label: 'Volunteer' },
    { href: 'index.html#contact', label: 'Contact Congress', cta: true }
  ];
  var page = (location.pathname.split('/').pop() || 'index.html');

  var header = document.getElementById('siteHeader');
  if (header) {
    header.className = 'site-header';
    var links = NAV.map(function (n) {
      var current = !n.cta && n.href === page ? ' aria-current="page"' : '';
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

  var footer = document.getElementById('siteFooter');
  if (footer) {
    footer.className = 'site-footer';
    footer.innerHTML =
      '<div><a href="https://github.com/ProDataMan/CAREN-Act">GitHub</a>·<a href="../docs/SF-CAREN-Act.pdf" download>Original SF ordinance (PDF)</a>·<a href="data.html">Data &amp; methodology</a></div>' +
      '<div style="margin-top:6px">Public data from EJI, Mapping Police Violence, FBI, CDC, U.S. Census Bureau and Mapping Inequality. Verify with primary sources.</div>';
  }
})();
