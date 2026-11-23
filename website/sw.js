// Service worker: lets saved Learn lessons (text, quizzes and narration) work without an internet connection.
// Pages, scripts and data: network first (so updates arrive), falling back to the cache when offline.
// Narration audio: only what the visitor saved (CarenOffline.saveLesson in assets/learn.js), served from the
// cache with byte-range support so seeking works offline. Nothing is cached from other sites except saved audio.
'use strict';
const VERSION = 'v1';
const SHELL = 'caren-shell-' + VERSION;
const RUNTIME = 'caren-runtime-' + VERSION;
const SAVED = 'caren-saved';            // lessons the visitor chose to keep (not versioned: survives updates)
const AUDIO_HOST = 'carenactmedia.blob.core.windows.net';
const CORE = ['learn.html', 'module.html', 'offline.html', 'assets/site.css', 'assets/site.js', 'assets/api.js', 'assets/learn.js',
  'data/learn.json', 'data/learn.es.json', 'i18n/es.json', 'audio/en/index.json', 'audio/es/index.json', 'manifest.webmanifest', 'icons/icon-192.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== SHELL && k !== RUNTIME && k !== SAVED).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Serve part of a cached file for media Range requests (needed for seeking in <audio>).
async function ranged(req, res) {
  const range = req.headers.get('range');
  if (!range || !res) return res;
  const buf = await res.arrayBuffer(), m = /bytes=(\d*)-(\d*)/.exec(range);
  const size = buf.byteLength, start = m && m[1] ? +m[1] : 0, end = m && m[2] ? Math.min(+m[2], size - 1) : size - 1;
  return new Response(buf.slice(start, end + 1), { status: 206, statusText: 'Partial Content', headers: {
    'Content-Type': res.headers.get('Content-Type') || 'audio/mpeg', 'Content-Range': 'bytes ' + start + '-' + end + '/' + size,
    'Content-Length': String(end - start + 1), 'Accept-Ranges': 'bytes' } });
}

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET') return;
  // Saved narration audio: cache first (file names are content hashes, so they never change).
  if (url.hostname === AUDIO_HOST) {
    e.respondWith(caches.open(SAVED).then(c => c.match(req.url)).then(hit => hit ? ranged(req, hit) : fetch(req)));
    return;
  }
  if (url.origin !== location.origin || url.pathname.indexOf('/api/') >= 0 || url.pathname.indexOf('/auth/') >= 0) return;
  // module.html?m=… and learn.html?… all share one cached page; the content comes from data/learn.json.
  const ignoreSearch = /\/(module|learn|teach|offline)\.html$/.test(url.pathname);
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok && res.type === 'basic') { const copy = res.clone(); caches.open(RUNTIME).then(c => c.put(ignoreSearch ? url.origin + url.pathname : req, copy)); }
      return res;
    }).catch(() => caches.match(ignoreSearch ? url.origin + url.pathname : req, { ignoreSearch })
      .then(hit => hit || caches.match(req, { ignoreSearch: true }))
      .then(hit => hit || (req.mode === 'navigate' ? caches.match('offline.html', { ignoreSearch: true }) : Response.error())))
  );
});
