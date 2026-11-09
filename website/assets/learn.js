// Learn: progress, XP, levels and badges. Needs assets/api.js loaded first.
// Progress is kept in this browser under a random device ID and synced to the campaign server,
// so it survives reloads. Signing in links the device's progress to a profile that follows you.
(function () {
  'use strict';
  var STORE = 'caren-learn', DEV = 'caren-device';
  var catalogP = null;

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE)) || { events: {} }; } catch (e) { return { events: {} }; }
  }
  function save(s) { try { localStorage.setItem(STORE, JSON.stringify(s)); } catch (e) { /* storage blocked */ } }
  function deviceId() {
    var id = null;
    try { id = localStorage.getItem(DEV); } catch (e) { /* ignore */ }
    if (!id || !/^[a-f0-9]{32}$/.test(id)) {
      var b = new Uint8Array(16); crypto.getRandomValues(b);
      id = Array.prototype.map.call(b, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
      try { localStorage.setItem(DEV, id); } catch (e) { /* ignore */ }
    }
    return id;
  }

  function catalog() {
    if (!catalogP) catalogP = fetch('data/learn.json').then(function (r) { return r.json(); });
    return catalogP;
  }

  // XP for an event key, from the catalog (the server uses the same rules).
  function xpFor(cat, key) {
    var p = key.split(':'), kind = p[0], id = p[1];
    if (kind === 'read') { var m = cat.modules.find(function (x) { return x.id === id; }); return m && m.status !== 'outline' ? cat.xp.read : 0; }
    if (kind === 'quiz') { var q = cat.modules.find(function (x) { return x.id === id; }); return q && q.quiz && q.quiz.length ? cat.xp.quiz : 0; }
    if (kind === 'quest') { var t = cat.quests.find(function (x) { return x.id === id; }); return t ? t.xp : 0; }
    return 0;
  }
  function total(s) { return Object.keys(s.events).reduce(function (a, k) { return a + (s.events[k].xp || 0); }, 0); }
  function level(cat, xp) {
    var cur = cat.levels[0], next = null;
    cat.levels.forEach(function (l, i) { if (xp >= l.xp) { cur = l; next = cat.levels[i + 1] || null; } });
    return { name: cur.name, xp: cur.xp, num: cat.levels.indexOf(cur) + 1, next: next };
  }
  function badges(cat, s) {
    var keys = Object.keys(s.events);
    return cat.badges.map(function (b) {
      var r = b.rule, got = false;
      if (r.any) got = r.any.some(function (k) { return keys.indexOf(k) !== -1; });
      if (r.prefix) got = keys.filter(function (k) { return k.indexOf(r.prefix) === 0; }).length >= r.n;
      return Object.assign({ earned: got }, b);
    });
  }

  var listeners = [];
  function changed() { var s = load(); listeners.forEach(function (fn) { try { fn(s); } catch (e) { console.error(e); } }); }

  // Send local events the server doesn't have, and take back anything it has (e.g. from another device).
  var syncing = null;
  function sync() {
    if (!window.CarenAPI) return Promise.resolve(null);
    if (syncing) return syncing;
    var s = load();
    syncing = window.CarenAPI.post('/api/learn/sync', { device: deviceId(), state: s.state || null, keys: Object.keys(s.events) })
      .then(function (r) {
        var cur = load();
        (r.events || []).forEach(function (e) { if (!cur.events[e.key]) cur.events[e.key] = { xp: e.xp, at: e.at }; });
        cur.profile = r.signedIn ? { name: r.name, picture: r.picture } : null;
        cur.synced = new Date().toISOString();
        save(cur); changed();
        return r;
      })
      .catch(function (e) { return { error: e.message }; })
      .then(function (r) { syncing = null; return r; });
    return syncing;
  }

  function record(key) {
    return catalog().then(function (cat) {
      var s = load();
      if (s.events[key]) return { already: true, xp: 0 };
      var xp = xpFor(cat, key);
      if (!xp) return { already: false, xp: 0 };
      s.events[key] = { xp: xp, at: new Date().toISOString() };
      save(s); changed(); sync();
      return { already: false, xp: xp };
    });
  }

  function setState(st) { var s = load(); s.state = st || null; save(s); changed(); sync(); }

  window.CarenLearn = {
    catalog: catalog, deviceId: deviceId, state: load, record: record, sync: sync, setState: setState,
    has: function (key) { return !!load().events[key]; },
    total: function () { return total(load()); },
    level: level, badges: badges, xpFor: xpFor,
    onChange: function (fn) { listeners.push(fn); },
    reset: function () { try { localStorage.removeItem(STORE); localStorage.removeItem(DEV); } catch (e) { /* ignore */ } changed(); }
  };
})();

// Shared UI pieces for learn.html and module.html
(function () {
  'use strict';
  var L = window.CarenLearn;
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function chip(cat, label) { var l = cat.labels[label]; return l ? '<span class="ev ' + label + '" title="' + esc(l.desc) + '">' + esc(l.name) + '</span>' : ''; }
  function toast(msg) {
    var t = document.createElement('div'); t.className = 'toast'; t.setAttribute('role', 'status'); t.textContent = msg;
    document.body.appendChild(t); setTimeout(function () { t.remove(); }, 3200);
  }
  function award(key, label) {
    return L.record(key).then(function (r) {
      if (r.xp) toast('+' + r.xp + ' XP' + (label ? ': ' + label : ''));
      return r;
    });
  }
  // questions: [{q, options, a, why}] with numeric answers, or detective style with a = label key
  function quiz(el, questions, opts) {
    var answered = 0, right = 0;
    el.classList.add('quiz');
    el.innerHTML = questions.map(function (q, i) {
      var options = q.options || opts.choices.map(function (c) { return c.name; });
      return '<div class="qq" data-i="' + i + '"><p>' + (i + 1) + '. ' + esc(q.q) + '</p><div class="opts">' +
        options.map(function (o, j) { return '<button type="button" data-j="' + j + '">' + esc(o) + '</button>'; }).join('') +
        '</div><div class="why" hidden></div></div>';
    }).join('') + '<p class="score" aria-live="polite"></p>';
    if (el._quizHandler) el.removeEventListener('click', el._quizHandler);
    el._quizHandler = function (e) {
      var b = e.target.closest('.opts button'); if (!b) return;
      var box = b.closest('.qq'); if (box.dataset.done) return;
      var q = questions[+box.dataset.i], j = +b.dataset.j;
      var correct = q.options ? q.a : opts.choices.map(function (c) { return c.id; }).indexOf(q.a);
      box.dataset.done = '1'; answered++;
      box.querySelectorAll('button').forEach(function (x, k) { x.disabled = true; if (k === correct) x.classList.add('right'); });
      if (j === correct) right++; else b.classList.add('wrong');
      var w = box.querySelector('.why'); w.hidden = false; w.textContent = (j === correct ? 'Correct. ' : 'Not quite. ') + (q.why || '');
      if (answered === questions.length) {
        var pass = right / questions.length >= opts.pass;
        el.querySelector('.score').innerHTML = '<b>' + right + ' of ' + questions.length + ' correct.</b> ' + (pass ? 'You passed!' : 'Read the explanations and try again.') +
          (pass ? '' : ' <button type="button" class="btn secondary retry">Try again</button>');
        if (pass && opts.onPass) opts.onPass(right);
        var r = el.querySelector('.retry'); if (r) r.addEventListener('click', function () { quiz(el, questions, opts); });
      }
    };
    el.addEventListener('click', el._quizHandler);
  }
  function timeline(cat, items, showModule) {
    return '<ol class="tl">' + items.map(function (t) {
      return '<li><span class="y">' + t.y + '</span> ' + esc(t.t) + ' ' + chip(cat, t.label) +
        (showModule && t.mod ? ' <a class="m" href="module.html?m=' + t.mod.id + '">Module ' + t.mod.num + '</a>' : '') + '</li>';
    }).join('') + '</ol>';
  }
  L.ui = { esc: esc, chip: chip, toast: toast, award: award, quiz: quiz, timeline: timeline };
})();
