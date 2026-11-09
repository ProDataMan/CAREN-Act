// Representative lookup shared by index.html, act.html and embed.html.
// Looks for #repForm, #repStatus and #reps on the page. Fields: fName, fStreet, fCity, fState, fZip, fStory (optional).
// No API keys: Census Geocoder (JSONP) + @unitedstates/congress-legislators + ZIP fallback file.
(function () {
  'use strict';
  var form = document.getElementById('repForm');
  if (!form) return;
  var repStatus = document.getElementById('repStatus');
  var repsDiv = document.getElementById('reps');
  var BASE = (document.currentScript && document.currentScript.src) ? document.currentScript.src.replace(/assets\/reps\.js.*$/, '') : '';
  var LEGISLATORS = 'https://unitedstates.github.io/congress-legislators/legislators-current.json';
  var COMMITTEES = 'https://unitedstates.github.io/congress-legislators/committee-membership-current.json';
  var SITE = 'https://prodataman.github.io/CAREN-Act/website/';
  var BILL_URL = SITE + 'bill.html';
  var STATE_FIPS = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY","60":"AS","66":"GU","69":"MP","72":"PR","78":"VI"};
  var STATE_NAMES = {AL:'Alabama',AK:'Alaska',AZ:'Arizona',AR:'Arkansas',CA:'California',CO:'Colorado',CT:'Connecticut',DE:'Delaware',DC:'the District of Columbia',FL:'Florida',GA:'Georgia',HI:'Hawaii',ID:'Idaho',IL:'Illinois',IN:'Indiana',IA:'Iowa',KS:'Kansas',KY:'Kentucky',LA:'Louisiana',ME:'Maine',MD:'Maryland',MA:'Massachusetts',MI:'Michigan',MN:'Minnesota',MS:'Mississippi',MO:'Missouri',MT:'Montana',NE:'Nebraska',NV:'Nevada',NH:'New Hampshire',NJ:'New Jersey',NM:'New Mexico',NY:'New York',NC:'North Carolina',ND:'North Dakota',OH:'Ohio',OK:'Oklahoma',OR:'Oregon',PA:'Pennsylvania',RI:'Rhode Island',SC:'South Carolina',SD:'South Dakota',TN:'Tennessee',TX:'Texas',UT:'Utah',VT:'Vermont',VA:'Virginia',WA:'Washington',WV:'West Virginia',WI:'Wisconsin',WY:'Wyoming',PR:'Puerto Rico',GU:'Guam',VI:'the U.S. Virgin Islands',AS:'American Samoa',MP:'the Northern Mariana Islands'};
  // States that already have a related law (see history.html). Letters there ask to strengthen it.
  // Places that already have a local CAREN ordinance (Census place or county GEOID).
  var LOCAL_LAWS = { '0667000': 'San Francisco', '06075': 'San Francisco' };
  var STATE_LAWS = {
    OR: 'Oregon’s 2019 law lets people sue someone who calls police on them out of racial bias, but damages are capped at $250',
    CA: 'California’s AB 1775 (2020) strengthened penalties for false reports made because of a protected characteristic, but it gives the person targeted no civil remedy of their own'
  };

  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var getJSON = function (url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }); };
  var cache = {};
  var once = function (key, fn) { return cache[key] || (cache[key] = fn()); };
  var legislators = function () { return once('leg', function () { return getJSON(LEGISLATORS); }); };
  var committees = function () { return once('com', function () { return getJSON(COMMITTEES); }); };

  function jsonp(url) {
    return new Promise(function (resolve, reject) {
      var cb = 'censusCb' + Date.now() + Math.floor(Math.random() * 1e6);
      var s = document.createElement('script');
      var timer = setTimeout(function () { cleanup(); reject(new Error('Census geocoder timed out')); }, 20000);
      function cleanup() { clearTimeout(timer); delete window[cb]; s.remove(); }
      window[cb] = function (data) { cleanup(); resolve(data); };
      s.onerror = function () { cleanup(); reject(new Error('Census geocoder unavailable')); };
      s.src = url + '&format=jsonp&callback=' + cb;
      document.head.appendChild(s);
    });
  }

  function first(g, re) { var k = Object.keys(g).find(function (x) { return re.test(x); }); return k && g[k][0]; }

  // Returns { exact, matched, list:[{state, district}], upper, lower, county, place }
  async function findDistricts(street, city, state, zip) {
    if (street) {
      var addr = [street, city, state, zip].filter(Boolean).join(', ');
      var url = 'https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress?benchmark=Public_AR_Current&vintage=ACS2025_Current&layers=all&address=' + encodeURIComponent(addr);
      try {
        var d = await jsonp(url);
        var m = d.result && d.result.addressMatches && d.result.addressMatches[0];
        if (m) {
          var g = m.geographies;
          var cd = first(g, /119th Congressional/) || first(g, /Congressional/);
          if (cd) {
            var up = first(g, /State Legislative Districts - Upper/), lo = first(g, /State Legislative Districts - Lower/);
            var co = first(g, /^Counties$/), pl = first(g, /Incorporated Places/);
            return {
              exact: true, matched: m.matchedAddress,
              list: [{ state: STATE_FIPS[cd.STATE], district: (parseInt(cd.GEOID.slice(2), 10) % 98), geoid: cd.GEOID }],
              upper: up && up.NAME, lower: lo && lo.NAME, upperId: up && up.GEOID, lowerId: lo && lo.GEOID,
              county: co && co.NAME, countyFips: co && co.GEOID, place: pl && pl.BASENAME, placeId: pl && pl.GEOID
            };
          }
        }
      } catch (e) { console.warn(e); }
    }
    var zips = await once('zips', function () { return getJSON(BASE + 'data/zip_districts.json'); });
    var list = (zips[zip] || []).map(function (g) { return { state: STATE_FIPS[g.slice(0, 2)], district: parseInt(g.slice(2), 10), geoid: g }; });
    return { exact: false, list: list };
  }

  // District demographics (ACS 5-year, built by scripts/build_data.py). Optional: cards work without it.
  var districts = function () { return once('dist', function () { return getJSON(BASE + 'data/districts.json').catch(function () { return {}; }); }); };
  function demo(d) {
    if (!d) return '';
    var R = window.CarenRace;
    return (R ? R.describe(d[1], R.fromDistrict(d)) : Math.round(d[1]) + '% people of color') + ', population ' + d[0].toLocaleString();
  }

  function storyPara(me) {
    var s = (me.story || '').trim();
    return s ? 'This matters to me personally. ' + s + '\n\n' : '';
  }
  function where(me) { return [me.city, me.state, me.zip].filter(Boolean).join(', '); }
  function signoff(me) { return 'Sincerely,\n' + (me.name || '[Your name]') + (me.street ? '\n' + me.street : '') + (where(me) ? '\n' + where(me) : ''); }

  function letter(p, t, me) {
    var title = t.type === 'sen' ? 'Senator' : 'Representative';
    return 'Dear ' + title + ' ' + p.name.last + ',\n\n' +
      'My name is ' + (me.name || '[Your name]') + ', and I am your constituent' + (where(me) ? ' in ' + where(me) : '') + '. I am writing to ask you to sponsor or cosponsor a federal version of San Francisco’s CAREN Act (Caution Against Racial and Exploitative Non-Emergencies).\n\n' +
      storyPara(me) +
      'Calls to police made with the specific intent to harass or discriminate against people because of their race or other protected characteristics put innocent people at risk of detention, humiliation, financial harm, and violence. San Francisco unanimously passed the CAREN Act in 2020 (Police Code §637), and states such as Oregon have enacted similar protections, but most Americans have no remedy at all.\n\n' +
      'The draft federal bill would:\n' +
      '• Prohibit knowingly causing law enforcement to contact a person with the specific intent to discriminate;\n' +
      '• Provide minimum statutory damages of $1,000 ($500 from the caller and $500 from the responding agency), plus attorneys’ fees;\n' +
      '• Protect good-faith reports of real emergencies and crimes; and\n' +
      '• Preserve stronger state and local laws.\n\n' +
      'You can read the draft and public comments here: ' + BILL_URL + '\n\n' +
      'Will you introduce or cosponsor this legislation' + (p._judiciary ? ', and support it in the ' + p._judiciary : '') + '? I would appreciate a response.\n\n' +
      signoff(me);
  }

  function callScript(p, t, me) {
    var title = t.type === 'sen' ? 'Senator' : 'Representative';
    return 'Hi, my name is ' + (me.name || '[your name]') + ' and I’m a constituent' + (me.zip ? ' from ZIP code ' + me.zip : '') + '. ' +
      'I’m calling to ask ' + title + ' ' + p.name.last + ' to sponsor or cosponsor a federal CAREN Act, which would make it illegal to call the police on someone to harass or discriminate against them because of their race. ' +
      ((me.story || '').trim() ? 'This matters to me because ' + me.story.trim().replace(/^[A-Z]/, function (c) { return c.toLowerCase(); }) + ' ' : '') +
      'Can you tell me where the ' + title + ' stands on this? Thank you.';
  }

  function stateLetter(me, res) {
    var st = (res.list[0] || {}).state, name = STATE_NAMES[st] || 'our state';
    var dist = [res.upper, res.lower].filter(Boolean).join(' and ');
    return 'Dear [Senator or Representative name],\n\n' +
      'My name is ' + (me.name || '[Your name]') + ', and I live in your district' + (dist ? ' (' + dist + ')' : '') + (where(me) ? ' in ' + where(me) : '') + '. I am asking you to introduce or support a bill that makes it unlawful to call the police on someone with the intent to discriminate against them because of their race, religion, or other protected characteristic, and that gives the person targeted the right to sue.\n\n' +
      storyPara(me) +
      (STATE_LAWS[st] ? STATE_LAWS[st] + '. I am asking you to strengthen it so people in ' + name + ' have a meaningful remedy.\n\n'
        : name + ' does not have a law like this yet. San Francisco passed one unanimously in 2020 (the CAREN Act, Police Code §637), and Oregon and California have passed related laws.\n\n') +
      'A model bill and the original San Francisco ordinance are here: ' + SITE + 'laws.html and ' + BILL_URL + '\n\n' +
      'Will you sponsor this legislation in the next session? I would appreciate a response.\n\n' + signoff(me);
  }

  function localLetter(me, res) {
    if (LOCAL_LAWS[res.placeId] || LOCAL_LAWS[res.countyFips]) {
      return 'Dear Supervisor [name],\n\n' +
        'My name is ' + (me.name || '[Your name]') + ', and I live in your district in ' + (res.place || res.county) + '. Thank you for our city’s CAREN Act (Police Code §637). I am asking you to support a resolution urging Congress to pass a federal version, so people everywhere have the same protection we do, and to publicize the law so residents know they can use it.\n\n' +
        storyPara(me) + 'The draft federal bill is here: ' + BILL_URL + '\n\n' + signoff(me);
    }
    var body = res.place ? 'the ' + res.place + ' City Council' : (res.county ? 'the ' + res.county + ' Board' : 'our city council or county board');
    return 'Dear Members of ' + body + ',\n\n' +
      'My name is ' + (me.name || '[Your name]') + ', and I live in ' + (res.place || res.county || '[your city or county]') + '. I am asking you to adopt a local ordinance modeled on San Francisco’s CAREN Act (Police Code §637), which makes it unlawful to call the police on someone to harass or discriminate against them because of their race or another protected characteristic, and lets the person targeted sue for damages.\n\n' +
      storyPara(me) +
      'San Francisco’s Board of Supervisors passed the CAREN Act 11–0 in October 2020. The ordinance text is here: https://prodataman.github.io/CAREN-Act/docs/SF-CAREN-Act.pdf, and its history is here: ' + SITE + 'history.html\n\n' +
      'Please place this on a future agenda. I would be glad to speak during public comment.\n\n' + signoff(me);
  }

  function copyBtn(ta, label) {
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'secondary'; b.textContent = label;
    b.addEventListener('click', function () {
      (navigator.clipboard ? navigator.clipboard.writeText(ta.value) : Promise.reject()).then(function () { b.textContent = 'Copied ✓'; })
        .catch(function () { ta.select(); document.execCommand('copy'); b.textContent = 'Copied ✓'; });
      setTimeout(function () { b.textContent = label; }, 2000);
    });
    return b;
  }

  // Each card registers a generator so letters refresh when the story changes (unless edited by hand).
  var generated = [];
  function bindText(ta, gen) {
    var entry = { ta: ta, gen: gen, last: gen() };
    ta.value = entry.last;
    generated.push(entry);
  }

  function card(p, me, note, dist) {
    var t = p.terms[p.terms.length - 1];
    var dline = t.type === 'rep' ? demo(dist && dist.cd && dist.cd[p._geoid]) : '';
    var id = p.id.bioguide;
    var title = t.type === 'sen' ? 'U.S. Senator, ' + t.state + (t.state_rank ? ' (' + t.state_rank + ')' : '') : 'U.S. Representative, ' + t.state + (t.district === 0 ? ' at-large' : '-' + t.district);
    var div = document.createElement('div');
    div.className = 'rep';
    div.innerHTML =
      '<div class="head"><img alt="" src="https://unitedstates.github.io/images/congress/225x275/' + esc(id) + '.jpg" onerror="this.style.visibility=\'hidden\'">' +
      '<div><h4>' + esc(p.name.official_full || (p.name.first + ' ' + p.name.last)) + '</h4><div class="sub">' + esc(title) + ' · ' + esc(t.party) + '</div>' +
      (p._judiciary ? '<span class="badge">' + esc(p._judiciary) + (p._jtitle ? ' — ' + esc(p._jtitle) : '') + '</span>' : '') +
      (note ? '<div class="sub">' + esc(note) + '</div>' : '') + (dline ? '<div class="sub">District: ' + esc(dline) + '</div>' : '') + '</div></div>' +
      (t.phone ? '<a class="call-now" href="tel:' + esc(t.phone.replace(/[^0-9+]/g, '')) + '">📞 Call ' + esc(t.phone) + '</a>' : '') +
      '<details class="script"><summary>Call script (30 seconds)</summary><p data-script></p><p class="note">Calls are tallied by staff, usually by ZIP code. If you reach voicemail, leave your name, ZIP code and the same message.</p></details>' +
      '<dl>' + (t.address ? '<dt>Office</dt><dd>' + esc(t.address) + '</dd>' : '') +
      (t.url ? '<dt>Website</dt><dd><a href="' + esc(t.url) + '" target="_blank" rel="noopener">' + esc(t.url.replace(/^https?:\/\//, '')) + '</a></dd>' : '') + '</dl>' +
      '<textarea aria-label="Letter to ' + esc(p.name.last) + '"></textarea>' +
      '<div class="actions">' +
      (t.contact_form ? '<a class="secondary" href="' + esc(t.contact_form) + '" target="_blank" rel="noopener">Open official contact form ↗</a>' : '') +
      '<a class="secondary" data-mail href="#">Email draft to myself</a></div>';
    var ta = div.querySelector('textarea');
    bindText(ta, function () { return letter(p, t, me); });
    var sp = div.querySelector('[data-script]');
    generated.push({ el: sp, gen: function () { return callScript(p, t, me); } });
    sp.textContent = callScript(p, t, me);
    div.querySelector('.actions').prepend(copyBtn(ta, 'Copy letter'));
    div.querySelector('[data-mail]').addEventListener('click', function (e) {
      e.currentTarget.href = 'mailto:?subject=' + encodeURIComponent('Letter to ' + (t.type === 'sen' ? 'Senator ' : 'Rep. ') + p.name.last + ' — Federal CAREN Act') + '&body=' + encodeURIComponent(ta.value);
    });
    return div;
  }

  function extraCard(kind, me, res, dd) {
    var st = (res.list[0] || {}).state;
    var div = document.createElement('div');
    div.className = 'rep rep-local';
    var head, links;
    if (kind === 'state') {
      var dist = [res.upper, res.lower].filter(Boolean);
      head = '<h4>Your state lawmakers' + (STATE_NAMES[st] ? ' in ' + esc(STATE_NAMES[st].replace(/^the /, '')) : '') + '</h4>' +
        '<div class="sub">' + (dist.length ? esc(dist.join(' · ')) : 'Add your street address to see your exact state districts.') + '</div>' +
        [[res.upper, 'sldu', res.upperId], [res.lower, 'sldl', res.lowerId]].map(function (x) { var d = dd && dd[x[1]] && dd[x[1]][x[2]]; return d ? '<div class="sub">' + esc(x[0]) + ': ' + esc(demo(d)) + '</div>' : ''; }).join('') +
        '<div class="sub">State and city laws are where CAREN-style protections have actually passed so far.</div>';
      links = '<a class="secondary" href="https://openstates.org/find_your_legislator/" target="_blank" rel="noopener">Find their names &amp; emails (Open States) ↗</a>';
    } else if (LOCAL_LAWS[res.placeId] || LOCAL_LAWS[res.countyFips]) {
      head = '<h4>Your ' + esc(res.place || 'local') + ' supervisor</h4><div class="sub">' + esc(res.place || 'Your city') + ' already has a CAREN Act. Thank your supervisor and ask them to urge Congress to pass a federal one.</div>';
      links = '<a class="secondary" href="https://sfbos.org/" target="_blank" rel="noopener">Find your supervisor ↗</a>';
    } else {
      head = '<h4>Your ' + (res.place ? esc(res.place) + ' city council' : 'city council or county board') + '</h4>' +
        '<div class="sub">' + (res.county ? esc(res.county) : 'Local governments can pass a CAREN ordinance on their own, as San Francisco did.') + '</div>';
      links = '<a class="secondary" href="https://www.usa.gov/local-governments" target="_blank" rel="noopener">Find your local government (USA.gov) ↗</a>';
    }
    div.innerHTML = '<div>' + head + '</div><textarea aria-label="' + (kind === 'state' ? 'Letter to state lawmakers' : 'Letter to local officials') + '"></textarea><div class="actions">' + links + '</div>';
    var ta = div.querySelector('textarea');
    bindText(ta, function () { return kind === 'state' ? stateLetter(me, res) : localLetter(me, res); });
    div.querySelector('.actions').prepend(copyBtn(ta, 'Copy letter'));
    return div;
  }

  function shareBar(res) {
    var div = document.createElement('div');
    div.className = 'share-bar';
    var countyLink = res.countyFips ? SITE + 'county.html?f=' + res.countyFips : null;
    div.innerHTML = '<strong>Done? Ask two friends to do the same.</strong> ' +
      '<button type="button" class="secondary" data-share>Share this page</button>' +
      (countyLink ? ' <a class="secondary" href="' + esc(countyLink) + '">See &amp; share your county’s numbers</a>' : '') +
      ' <a class="secondary" href="' + SITE + 'volunteer.html">Volunteer in your state</a>';
    div.querySelector('[data-share]').addEventListener('click', function (e) {
      var b = e.currentTarget, data = { title: 'Make discriminatory 911 calls illegal', text: 'I just asked my lawmakers to back a federal CAREN Act. It takes 2 minutes:', url: SITE + 'act.html' };
      if (navigator.share) navigator.share(data).catch(function () {});
      else (navigator.clipboard ? navigator.clipboard.writeText(data.text + ' ' + data.url) : Promise.reject()).then(function () { b.textContent = 'Link copied ✓'; }).catch(function () {});
    });
    return div;
  }

  var story = document.getElementById('fStory');
  var current = null;
  if (story) story.addEventListener('input', function () {
    if (!current) return;
    current.story = story.value;
    generated.forEach(function (g) {
      if (g.el) { g.el.textContent = g.gen(); return; }
      if (g.ta.value === g.last) { g.last = g.gen(); g.ta.value = g.last; } // keep hand edits
    });
  });

  form.addEventListener('submit', async function (e) {
    e.preventDefault();
    var v = function (id) { var el = document.getElementById(id); return el ? el.value.trim() : ''; };
    var me = current = { name: v('fName'), street: v('fStreet'), city: v('fCity'), state: v('fState'), zip: v('fZip').slice(0, 5), story: v('fStory') };
    generated = [];
    repsDiv.innerHTML = '';
    repStatus.textContent = 'Looking up your district…';
    try {
      var all = await Promise.all([findDistricts(me.street, me.city, me.state, me.zip), legislators(), committees(), districts()]);
      var res = all[0], leg = all[1], com = all[2], dd = all[3];
      if (!res.list.length) { repStatus.textContent = 'We could not find that ZIP code. Please check it, or add your street address.'; return; }
      var jud = {};
      (com.HSJU || []).forEach(function (m) { jud[m.bioguide] = ['House Judiciary Committee', m.title]; });
      (com.SSJU || []).forEach(function (m) { jud[m.bioguide] = ['Senate Judiciary Committee', m.title]; });
      leg.forEach(function (p) { var j = jud[p.id.bioguide]; if (j) { p._judiciary = j[0]; p._jtitle = j[1]; } });
      if (!me.city && res.place) me.city = res.place;
      var st = res.list[0].state;
      var cur = function (p) { return p.terms[p.terms.length - 1]; };
      var senators = leg.filter(function (p) { return cur(p).type === 'sen' && cur(p).state === st; });
      var reps = [];
      res.list.forEach(function (c) { leg.filter(function (p) { return cur(p).type === 'rep' && cur(p).state === c.state && cur(p).district === c.district; }).forEach(function (p) { p._geoid = c.geoid; reps.push(p); }); });
      var msg = res.exact ? 'Matched address: ' + res.matched + '. ' : '';
      if (!res.exact && res.list.length > 1) msg += 'ZIP ' + me.zip + ' spans ' + res.list.length + ' congressional districts. All possible representatives are shown; add your street address to narrow it to one. ';
      else if (!res.exact) msg += 'Based on ZIP ' + me.zip + '. ';
      if (!reps.length) msg += 'No voting U.S. Representative was found for this location (the seat may be vacant or a non-voting delegate). ';
      repStatus.textContent = msg + 'A phone call counts most; a personal letter is next. Edit anything before sending.';
      senators.concat(reps).forEach(function (p) { repsDiv.appendChild(card(p, me, !res.exact && res.list.length > 1 && cur(p).type === 'rep' ? 'Possible representative for your ZIP' : '', dd)); });
      repsDiv.appendChild(extraCard('state', me, res, dd));
      repsDiv.appendChild(extraCard('local', me, res));
      repsDiv.appendChild(shareBar(res));
      if (!me.name) repStatus.textContent += ' Tip: add your name so the letters are signed.';
    } catch (err) {
      console.error(err);
      repStatus.textContent = 'Lookup failed: ' + err.message + '. Please try again.';
    }
  });
})();
