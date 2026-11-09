// Federal CAREN Act server: serves the static site and a small API backed by Azure SQL.
const express = require('express');
const crypto = require('crypto');
const path = require('path');
const { sql, getPool, configured } = require('./db');

const app = express();
const PORT = parseInt(process.env.PORT || '8080', 10);
const ROOT = process.env.SITE_ROOT || path.join(__dirname, '..', '..');
const PUBLIC_BASE_URL = (process.env.PUBLIC_BASE_URL || '').replace(/\/$/, '');
const ADMIN_EMAILS = (process.env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
const CORS_ORIGINS = (process.env.CORS_ORIGINS || 'https://prodataman.github.io').split(',').map(s => s.trim()).filter(Boolean);
const SESSION_DAYS = 30;
const STATES = new Set('AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split(' '));
const ROLES = new Set(['law-verifier', 'case-verifier', 'cdc-exporter', 'local-deliverer', 'legal-reviewer', 'researcher']);

app.disable('x-powered-by');
app.set('trust proxy', true);
app.use(express.json({ limit: '32kb' }));

// ---------------------------------------------------------------- helpers
function cookies(req) {
  const out = {};
  (req.headers.cookie || '').split(';').forEach(p => {
    const i = p.indexOf('=');
    if (i > 0) out[p.slice(0, i).trim()] = decodeURIComponent(p.slice(i + 1).trim());
  });
  return out;
}
function setCookie(res, name, value, maxAgeSec) {
  const parts = [`${name}=${encodeURIComponent(value)}`, 'Path=/', 'HttpOnly', 'SameSite=Lax', `Max-Age=${maxAgeSec}`];
  if (process.env.NODE_ENV === 'production') parts.push('Secure');
  res.append('Set-Cookie', parts.join('; '));
}
function baseUrl(req) { return PUBLIC_BASE_URL || `${req.protocol}://${req.get('host')}`; }
const str = (v, max) => (typeof v === 'string' ? v.trim().slice(0, max) : '');
const isEmail = e => /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/.test(e);

// Simple per-IP rate limiter (per container instance)
const hits = new Map();
function rateLimit(max, windowMs) {
  return (req, res, next) => {
    const key = req.ip + req.path, now = Date.now();
    const arr = (hits.get(key) || []).filter(t => now - t < windowMs);
    if (arr.length >= max) return res.status(429).json({ error: 'Too many requests. Please try again later.' });
    arr.push(now); hits.set(key, arr); next();
  };
}
setInterval(() => { const now = Date.now(); for (const [k, v] of hits) if (!v.some(t => now - t < 3600e3)) hits.delete(k); }, 600e3).unref();

// CORS for the GitHub Pages copy of the site (public endpoints only, no cookies)
function cors(req, res, next) {
  const o = req.headers.origin;
  if (o && CORS_ORIGINS.includes(o)) {
    res.set('Access-Control-Allow-Origin', o);
    res.set('Vary', 'Origin');
    res.set('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS');
    res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
    res.set('Access-Control-Max-Age', '600');
  }
  if (req.method === 'OPTIONS') return res.sendStatus(204);
  next();
}

// Session id comes from the first-party cookie (Azure-hosted pages) or an
// "Authorization: Bearer <id>" header (GitHub Pages, where cross-site cookies are blocked).
function sessionId(req) {
  const m = /^Bearer ([a-f0-9]{64})$/.exec(req.headers.authorization || '');
  return m ? m[1] : cookies(req).caren_sid;
}
// Where to send the browser after sign-in: a path on this site, or a page on an allowed origin (GitHub Pages).
function safeReturn(v) {
  const s = str(v, 500);
  if (s.startsWith('/') && !s.startsWith('//')) return s;
  try { const u = new URL(s); if (CORS_ORIGINS.includes(u.origin)) return u.origin + u.pathname + u.search; } catch (e) { /* not a URL */ }
  return '/website/volunteer.html';
}

async function currentUser(req) {
  const sid = sessionId(req);
  if (!sid || !/^[a-f0-9]{64}$/.test(sid) || !configured()) return null;
  const pool = await getPool();
  const r = await pool.request().input('id', sql.Char(64), sid)
    .query('SELECT u.id, u.email, u.name, u.picture, u.provider FROM dbo.sessions s JOIN dbo.users u ON u.id = s.user_id WHERE s.id = @id AND s.expires_at > SYSUTCDATETIME()');
  const u = r.recordset[0];
  if (!u) return null;
  u.isAdmin = !!u.email && ADMIN_EMAILS.includes(u.email.toLowerCase());
  return u;
}
function requireAdmin(req, res, next) {
  currentUser(req).then(u => {
    if (!u) return res.status(401).json({ error: 'Sign in required' });
    if (!u.isAdmin) return res.status(403).json({ error: 'Admins only' });
    req.user = u; next();
  }).catch(next);
}

// ---------------------------------------------------------------- OAuth (Google, Facebook)
const PROVIDERS = {
  google: {
    enabled: () => !!(process.env.GOOGLE_OAUTH_CLIENT_ID && process.env.GOOGLE_OAUTH_CLIENT_SECRET),
    authorize: (redirect, state) => 'https://accounts.google.com/o/oauth2/v2/auth?' + new URLSearchParams({
      client_id: process.env.GOOGLE_OAUTH_CLIENT_ID, redirect_uri: redirect, response_type: 'code',
      scope: 'openid email profile', state, prompt: 'select_account'
    }),
    async profile(code, redirect) {
      const t = await fetch('https://oauth2.googleapis.com/token', {
        method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ code, client_id: process.env.GOOGLE_OAUTH_CLIENT_ID, client_secret: process.env.GOOGLE_OAUTH_CLIENT_SECRET, redirect_uri: redirect, grant_type: 'authorization_code' })
      }).then(r => r.json());
      if (!t.access_token) throw new Error('Google token exchange failed');
      const p = await fetch('https://openidconnect.googleapis.com/v1/userinfo', { headers: { Authorization: 'Bearer ' + t.access_token } }).then(r => r.json());
      if (!p.sub) throw new Error('Google profile lookup failed');
      return { id: p.sub, email: p.email_verified ? p.email : null, name: p.name, picture: p.picture };
    }
  },
  facebook: {
    enabled: () => !!(process.env.FACEBOOK_OAUTH_APP_ID && process.env.FACEBOOK_OAUTH_APP_SECRET),
    authorize: (redirect, state) => 'https://www.facebook.com/v19.0/dialog/oauth?' + new URLSearchParams({
      client_id: process.env.FACEBOOK_OAUTH_APP_ID, redirect_uri: redirect, state, scope: 'public_profile,email'
    }),
    async profile(code, redirect) {
      const t = await fetch('https://graph.facebook.com/v19.0/oauth/access_token?' + new URLSearchParams({
        client_id: process.env.FACEBOOK_OAUTH_APP_ID, client_secret: process.env.FACEBOOK_OAUTH_APP_SECRET, redirect_uri: redirect, code
      })).then(r => r.json());
      if (!t.access_token) throw new Error('Facebook token exchange failed');
      const p = await fetch('https://graph.facebook.com/me?' + new URLSearchParams({ fields: 'id,name,email,picture.type(large)', access_token: t.access_token })).then(r => r.json());
      if (!p.id) throw new Error('Facebook profile lookup failed');
      return { id: p.id, email: p.email || null, name: p.name, picture: p.picture && p.picture.data && p.picture.data.url };
    }
  }
};

app.get('/auth/:provider', (req, res) => {
  const p = PROVIDERS[req.params.provider];
  if (!p || !p.enabled()) return res.status(404).send('Sign-in with this provider is not configured.');
  const state = crypto.randomBytes(24).toString('hex');
  setCookie(res, 'caren_oauth', JSON.stringify({ state, next: safeReturn(req.query.next) }), 600);
  res.redirect(p.authorize(`${baseUrl(req)}/auth/${req.params.provider}/callback`, state));
});

app.get('/auth/:provider/callback', async (req, res, next) => {
  try {
    const p = PROVIDERS[req.params.provider];
    if (!p || !p.enabled()) return res.status(404).send('Not configured');
    let saved = {};
    try { saved = JSON.parse(cookies(req).caren_oauth || '{}'); } catch (e) { /* ignore */ }
    setCookie(res, 'caren_oauth', '', 0);
    if (!saved.state || saved.state !== req.query.state || !req.query.code) return res.status(400).send('Sign-in expired or was tampered with. Please try again.');
    const prof = await p.profile(String(req.query.code), `${baseUrl(req)}/auth/${req.params.provider}/callback`);
    const pool = await getPool();
    const u = await pool.request()
      .input('provider', sql.NVarChar(20), req.params.provider).input('pid', sql.NVarChar(200), String(prof.id))
      .input('email', sql.NVarChar(320), prof.email).input('name', sql.NVarChar(200), prof.name || null).input('pic', sql.NVarChar(1000), prof.picture || null)
      .query(`MERGE dbo.users WITH (HOLDLOCK) AS t USING (SELECT @provider AS provider, @pid AS provider_id) AS s
              ON t.provider = s.provider AND t.provider_id = s.provider_id
              WHEN MATCHED THEN UPDATE SET email = COALESCE(@email, t.email), name = COALESCE(@name, t.name), picture = @pic, last_login_at = SYSUTCDATETIME()
              WHEN NOT MATCHED THEN INSERT (provider, provider_id, email, name, picture) VALUES (@provider, @pid, @email, @name, @pic)
              OUTPUT inserted.id;`);
    const sid = crypto.randomBytes(32).toString('hex');
    await pool.request().input('id', sql.Char(64), sid).input('uid', sql.Int, u.recordset[0].id).input('days', sql.Int, SESSION_DAYS)
      .query('INSERT INTO dbo.sessions (id, user_id, expires_at) VALUES (@id, @uid, DATEADD(day, @days, SYSUTCDATETIME()))');
    setCookie(res, 'caren_sid', sid, SESSION_DAYS * 86400);
    const dest = safeReturn(saved.next);
    // Cross-site return (GitHub Pages): hand the session over in the URL fragment, which is never sent to any server.
    res.redirect(dest.startsWith('/') ? dest : dest + '#caren_token=' + sid);
  } catch (e) { next(e); }
});

app.options('/auth/logout', cors);
app.post('/auth/logout', cors, async (req, res, next) => {
  try {
    const sid = sessionId(req);
    if (sid && /^[a-f0-9]{64}$/.test(sid) && configured()) {
      const pool = await getPool();
      await pool.request().input('id', sql.Char(64), sid).query('DELETE FROM dbo.sessions WHERE id = @id');
    }
    setCookie(res, 'caren_sid', '', 0);
    res.json({ ok: true });
  } catch (e) { next(e); }
});

// ---------------------------------------------------------------- API
app.use('/api', cors);

app.get('/api/health', async (req, res) => {
  const out = { ok: true, db: configured() ? 'unknown' : 'not-configured', comments: Boolean(process.env.GITHUB_TOKEN), auth: { google: PROVIDERS.google.enabled(), facebook: PROVIDERS.facebook.enabled() } };
  if (configured()) {
    try {
      const pool = await Promise.race([getPool(), new Promise((_, rej) => setTimeout(() => rej(new Error('waking')), 4000))]);
      await pool.request().query('SELECT 1 AS ok');
      out.db = 'ok';
    } catch (e) { out.db = e.message === 'waking' ? 'waking' : 'error'; }
  }
  res.json(out);
});

app.get('/api/me', async (req, res, next) => {
  try {
    const u = await currentUser(req);
    res.json(u ? { signedIn: true, name: u.name, email: u.email, picture: u.picture, provider: u.provider, isAdmin: u.isAdmin } : { signedIn: false });
  } catch (e) { next(e); }
});

app.get('/api/volunteers/coverage', async (req, res, next) => {
  try {
    const pool = await getPool();
    const r = await pool.request().query("SELECT state, COUNT(*) AS n FROM dbo.volunteers WHERE status <> 'withdrawn' GROUP BY state");
    res.set('Cache-Control', 'public, max-age=60');
    res.json(Object.fromEntries(r.recordset.map(x => [x.state, x.n])));
  } catch (e) { next(e); }
});

app.post('/api/volunteers', rateLimit(5, 3600e3), async (req, res, next) => {
  try {
    const b = req.body || {};
    if (b.website) return res.json({ ok: true }); // honeypot: bots fill hidden fields
    const user = await currentUser(req).catch(() => null);
    const v = {
      name: str(b.name, 200) || (user && user.name) || '',
      email: (str(b.email, 320) || (user && user.email) || '').toLowerCase(),
      phone: str(b.phone, 50) || null,
      state: str(b.state, 2).toUpperCase(),
      area: str(b.area, 200) || null,
      roles: (Array.isArray(b.roles) ? b.roles : []).filter(r => ROLES.has(r)),
      background: str(b.background, 100) || null,
      hours: str(b.hours, 50) || null,
      experience: str(b.experience, 2000) || null
    };
    const errors = [];
    if (!v.name) errors.push('Name is required.');
    if (!isEmail(v.email)) errors.push('A valid email is required.');
    if (!STATES.has(v.state)) errors.push('Choose a state.');
    if (!v.roles.length) errors.push('Choose at least one role.');
    if (b.agree !== true) errors.push('Please accept the verification commitments.');
    if (errors.length) return res.status(400).json({ error: errors.join(' ') });
    const pool = await getPool();
    await pool.request()
      .input('uid', sql.Int, user ? user.id : null).input('name', sql.NVarChar(200), v.name).input('email', sql.NVarChar(320), v.email)
      .input('phone', sql.NVarChar(50), v.phone).input('state', sql.Char(2), v.state).input('area', sql.NVarChar(200), v.area)
      .input('roles', sql.NVarChar(400), v.roles.join(',')).input('bg', sql.NVarChar(100), v.background).input('hours', sql.NVarChar(50), v.hours)
      .input('exp', sql.NVarChar(2000), v.experience).input('src', sql.NVarChar(40), req.headers.origin && CORS_ORIGINS.includes(req.headers.origin) ? 'github-pages' : 'web')
      .query(`INSERT INTO dbo.volunteers (user_id, name, email, phone, state, area, roles, background, hours, experience, source)
              VALUES (@uid, @name, @email, @phone, @state, @area, @roles, @bg, @hours, @exp, @src)`);
    res.status(201).json({ ok: true });
  } catch (e) { next(e); }
});

// ---------- Bill comments posted from the website (no GitHub account needed) ----------
// The server creates a labeled GitHub issue in the same format the bill page builds, so the
// existing pipeline (display, editor approval, gold stars) works unchanged.
// Needs GITHUB_TOKEN: a fine-grained token with Issues read/write on this repository only.
const GH_REPO = process.env.GITHUB_REPO || 'ProDataMan/CAREN-Act';
const COMMENT_MARKER = '<!-- caren-bill-comment -->';
app.post('/api/comments', rateLimit(10, 3600e3), async (req, res, next) => {
  try {
    if (!process.env.GITHUB_TOKEN) return res.status(503).json({ error: 'Posting from the website is not set up yet.' });
    const b = req.body || {};
    if (b.website) return res.json({ ok: true }); // honeypot
    const title = String(b.title || '').trim();
    let body = String(b.body || '');
    const name = String(b.name || '').replace(/[<>@\[\]`*_#]/g, '').trim().slice(0, 60);
    const m = body.match(/```json\n(\{.*\})\n```/);
    let data = null;
    try { data = m && JSON.parse(m[1]); } catch (e) { data = null; }
    if (!/^\[Bill (comment|edit)\] .{1,180}$/.test(title) || !body.startsWith(COMMENT_MARKER) || body.length > 12000 ||
        !data || !/^[\w.-]{1,40}$/.test(String(data.para || '')) || !/^[a-z0-9]{6,40}$/i.test(String(data.token || ''))) {
      return res.status(400).json({ error: 'That comment could not be read. Please reload the page and try again.' });
    }
    const user = await currentUser(req).catch(() => null);
    const by = (user && user.name) || name || 'Anonymous';
    // Break @mentions so a comment can't notify arbitrary GitHub users.
    body = body.replace(/@(?=[\w-])/g, '@​');
    body = body.replace(COMMENT_MARKER + '\n', COMMENT_MARKER + '\n**Posted from the website by:** ' + by + (user ? ' (signed in)' : '') + '\n');
    const r = await fetch('https://api.github.com/repos/' + GH_REPO + '/issues', {
      method: 'POST',
      headers: { Authorization: 'Bearer ' + process.env.GITHUB_TOKEN, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'caren-act-server', 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, body, labels: ['bill-comment'] })
    });
    if (!r.ok) {
      console.error('GitHub issue create failed', r.status, (await r.text()).slice(0, 300));
      return res.status(502).json({ error: 'GitHub did not accept the comment. Please try again later.' });
    }
    const j = await r.json();
    res.json({ ok: true, number: j.number, url: j.html_url, author: by });
  } catch (e) { next(e); }
});

app.get('/api/admin/volunteers', requireAdmin, async (req, res, next) => {
  try {
    const pool = await getPool();
    const r = await pool.request().query('SELECT TOP 2000 id, created_at, name, email, phone, state, area, roles, background, hours, experience, status, source FROM dbo.volunteers ORDER BY created_at DESC');
    res.json(r.recordset);
  } catch (e) { next(e); }
});

app.patch('/api/admin/volunteers/:id', requireAdmin, async (req, res, next) => {
  try {
    const status = str((req.body || {}).status, 20);
    if (!['new', 'active', 'inactive', 'withdrawn'].includes(status)) return res.status(400).json({ error: 'Invalid status' });
    const pool = await getPool();
    await pool.request().input('id', sql.Int, parseInt(req.params.id, 10)).input('s', sql.NVarChar(20), status).query('UPDATE dbo.volunteers SET status = @s WHERE id = @id');
    res.json({ ok: true });
  } catch (e) { next(e); }
});

// ---------------------------------------------------------------- static site
app.get('/', (req, res) => res.redirect('/website/'));
app.use('/website', express.static(path.join(ROOT, 'website'), { extensions: ['html'], maxAge: '5m' }));
app.use('/docs', express.static(path.join(ROOT, 'docs'), { maxAge: '1d' }));
app.get('/healthz', (req, res) => res.send('ok'));

app.use('/api', (req, res) => res.status(404).json({ error: 'Not found' }));
app.use((err, req, res, next) => { // eslint-disable-line no-unused-vars
  console.error('[error]', err);
  if (res.headersSent) return;
  const dbDown = /not configured|connect|Login failed|ETIMEOUT|ESOCKET|40613/i.test(String(err.message));
  res.status(dbDown ? 503 : 500).json({ error: dbDown ? 'The database is waking up or unavailable. Please try again in a minute.' : 'Something went wrong.' });
});

if (require.main === module) {
  app.listen(PORT, () => {
    console.log(`CAREN Act server on :${PORT} (db ${configured() ? process.env.DB_NAME || 'connection string' : 'not configured'})`);
    if (configured()) getPool().then(() => console.log('[db] ready')).catch(e => console.error('[db] not ready:', e.message));
  });
  setInterval(() => { if (configured()) getPool().then(p => p.request().query('DELETE FROM dbo.sessions WHERE expires_at < SYSUTCDATETIME()')).catch(() => {}); }, 6 * 3600e3).unref();
}

module.exports = app;
