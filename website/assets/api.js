// Shared client for the campaign API on Azure. Works from both the Azure-hosted site
// (same origin, cookie session) and GitHub Pages (cross-origin, bearer token).
(function () {
  'use strict';
  var AZURE = 'https://caren-act-server.calmpebble-c668572f.centralus.azurecontainerapps.io';
  var sameOrigin = /azurecontainerapps\.io$|^localhost$|^127\./.test(location.hostname);
  var BASE = sameOrigin ? '' : AZURE;
  var KEY = 'caren_token';

  // Pick up a session handed back after sign-in (#caren_token=...), then remove it from the address bar.
  var m = /[#&]caren_token=([a-f0-9]{64})/.exec(location.hash);
  if (m) {
    try { localStorage.setItem(KEY, m[1]); } catch (e) { /* storage blocked */ }
    history.replaceState(null, '', location.pathname + location.search);
  }
  function token() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }

  function api(path, opts) {
    opts = opts || {};
    var headers = Object.assign({}, opts.headers || {});
    if (opts.json !== undefined) { headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(opts.json); }
    var t = token();
    if (!sameOrigin && t) headers.Authorization = 'Bearer ' + t;
    return fetch(BASE + path, { method: opts.method || 'GET', headers: headers, body: opts.body, credentials: sameOrigin ? 'same-origin' : 'omit' })
      .then(function (r) {
        var ct = r.headers.get('content-type') || '';
        if (ct.indexOf('application/json') === -1) throw new Error('The campaign server is not available yet.');
        return r.json().then(function (j) {
          if (!r.ok) { var e = new Error(j.error || ('Request failed (' + r.status + ')')); e.status = r.status; throw e; }
          return j;
        });
      });
  }

  window.CarenAPI = {
    base: BASE,
    sameOrigin: sameOrigin,
    get: function (p) { return api(p); },
    post: function (p, body) { return api(p, { method: 'POST', json: body }); },
    patch: function (p, body) { return api(p, { method: 'PATCH', json: body }); },
    signInUrl: function (provider) { return BASE + '/auth/' + provider + '?next=' + encodeURIComponent(sameOrigin ? location.pathname : location.origin + location.pathname); },
    signOut: function () {
      return api('/auth/logout', { method: 'POST' }).catch(function () {}).then(function () { try { localStorage.removeItem(KEY); } catch (e) { /* ignore */ } });
    }
  };
})();
