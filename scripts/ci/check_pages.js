// Loads every page in headless Chrome at desktop and phone width and fails on JavaScript errors,
// horizontal overflow, or axe-core accessibility violations (WCAG 2.0/2.1/2.2 A and AA, best practices).
//   node scripts/ci/check_pages.js http://localhost:8765/website/
// Needs Chrome (google-chrome or CHROME env) and axe-core (npm install axe-core@4.10.2 in scripts/ci).
const { spawn } = require('child_process');
const fs = require('fs'), path = require('path');
const BASE = (process.argv[2] || 'http://localhost:8765/website/').replace(/\/?$/, '/');
const AXE = fs.readFileSync(require.resolve('axe-core/axe.min.js', { paths: [__dirname, process.cwd()] }), 'utf8');
const PAGES = ['index.html', 'act.html', 'county.html?f=40143', 'bill.html', 'deaths.html', 'laws.html', 'history.html', 'learn.html', 'learn.html?lang=es',
  'module.html?m=before-race', 'module.html?m=movements&lang=es', 'teach.html', 'teach.html?m=rights', 'data.html', 'volunteer.html', 'stories.html', 'toolkit.html',
  'brief.html', 'press.html', 'review.html', 'class.html', 'record.html', 'search.html?q=tulsa', 'voices.html', 'privacy.html', 'admin.html', 'embed.html'];
const WIDTHS = [1280, 390];
const sleep = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const port = 9400 + Math.floor(Math.random() * 400);
  const ch = spawn(process.env.CHROME || 'google-chrome', ['--headless=new', '--disable-gpu', '--no-sandbox', '--remote-debugging-port=' + port, '--user-data-dir=' + path.join(require('os').tmpdir(), 'caren-ci-' + port), 'about:blank'], { stdio: 'ignore' });
  let tabs; for (let i = 0; i < 80; i++) { try { tabs = await (await fetch('http://127.0.0.1:' + port + '/json')).json(); if (tabs.length) break; } catch (e) {} await sleep(250); }
  const ws = new WebSocket(tabs.find(t => t.type === 'page').webSocketDebuggerUrl);
  let id = 0; const pend = {}; let pageErrors = [];
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pend[d.id]) { pend[d.id](d); delete pend[d.id]; } else if (d.method === 'Runtime.exceptionThrown') pageErrors.push((d.params.exceptionDetails.exception || {}).description || d.params.exceptionDetails.text); };
  await new Promise(r => ws.onopen = r);
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pend[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  await send('Runtime.enable');
  const failures = [];
  for (const w of WIDTHS) {
    await send('Emulation.setDeviceMetricsOverride', { width: w, height: 900, deviceScaleFactor: 1, mobile: w < 600 });
    for (const p of PAGES) {
      pageErrors = [];
      await send('Page.navigate', { url: BASE + p }); await sleep(4500);
      const ov = (await send('Runtime.evaluate', { expression: 'document.documentElement.scrollWidth > innerWidth + 1', returnByValue: true })).result.result.value;
      let axe = [];
      if (w === 1280 || /module|learn|index/.test(p)) {
        await send('Runtime.evaluate', { expression: AXE });
        const r = await send('Runtime.evaluate', { awaitPromise: true, returnByValue: true, expression: "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}}).then(r=>r.violations.map(v=>v.id+' ('+v.nodes.length+'): '+v.nodes[0].target.join(' ')))" });
        axe = r.result.result.value || [];
      }
      const problems = [].concat(pageErrors.map(e => 'JS error: ' + String(e).split('\n')[0]), ov ? ['horizontal overflow'] : [], axe.map(a => 'axe ' + a));
      console.log((problems.length ? 'FAIL ' : 'ok   ') + w + ' ' + p + (problems.length ? '\n       ' + problems.join('\n       ') : ''));
      if (problems.length) failures.push(p);
    }
  }
  ch.kill();
  console.log(failures.length ? failures.length + ' page checks failed' : 'All page checks passed');
  process.exit(failures.length ? 1 : 0);
})();
