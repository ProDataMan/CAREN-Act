#!/usr/bin/env python3
"""Consistency checks for the site's data, translations and narration. Exits non-zero on any error.

    python3 scripts/ci/check_data.py
"""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
W = ROOT / 'website'
sys.path.insert(0, str(ROOT / 'scripts'))
errors, warnings = [], []
err = errors.append
warn = warnings.append

# 1. Every JSON file parses
for p in sorted(list((W / 'data').glob('*.json')) + list((W / 'i18n').glob('*.json')) + list((W / 'audio').rglob('*.json')) + [W / 'bill.json']):
    try:
        json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:
        err('%s: invalid JSON (%s)' % (p.relative_to(ROOT), e))

cat = json.loads((W / 'data' / 'learn.json').read_text(encoding='utf-8'))
mods = cat['modules']
ids = [m['id'] for m in mods]

# 2. Learn catalog structure
if len(set(ids)) != len(ids): err('learn.json: duplicate module ids')
if [m['num'] for m in mods] != list(range(1, len(mods) + 1)): err('learn.json: module "num" values are not 1..N in order')
labels = set(cat['labels'])
qids = [q['id'] for q in cat['quests']]
if len(set(qids)) != len(qids): err('learn.json: duplicate quest ids')
for m in mods:
    for i, s in enumerate(m.get('sections', [])):
        if s.get('label') not in labels: err('%s section %d: unknown label %r' % (m['id'], i, s.get('label')))
        for k in s.get('sources', []):
            if k not in m.get('sourcesList', {}): err('%s section %d: source %r not in sourcesList' % (m['id'], i, k))
    for t in m.get('timeline', []):
        if t.get('label') not in labels: err('%s timeline %r: unknown label' % (m['id'], t.get('t')))
    for i, q in enumerate(m.get('quiz', [])):
        if not (0 <= q['a'] < len(q['options'])): err('%s quiz %d: answer index out of range' % (m['id'], i))
    if m.get('quest') and m['quest'] not in qids: err('%s: quest %r does not exist' % (m['id'], m['quest']))
    if m.get('status') != 'outline' and not m.get('sections'): err('%s: written module has no sections' % m['id'])
for b in cat['badges']:
    r = b['rule']
    for k in r.get('any', []) + r.get('all', []):
        kind, _, x = k.partition(':')
        if kind == 'quest' and x not in qids: err('badge %s: unknown quest %s' % (b['id'], x))
        if kind in ('read', 'quiz') and x not in ids: err('badge %s: unknown module %s' % (b['id'], x))
for p in cat.get('paths', []):
    for x in p['modules']:
        if x not in ids: err('path %s: unknown module %s' % (p['id'], x))
for d in cat.get('detective', []):
    if d['a'] not in labels: err('detective: unknown answer label %r' % d['a'])

# 2b. Fact-check queue
DATE = re.compile(r'^\d{4}-\d{2}-\d{2}$')
fids = set()
for f in cat.get('factChecks', []):
    if f.get('id') in fids: err('factChecks: duplicate id %s' % f.get('id'))
    fids.add(f.get('id'))
    if f.get('module') not in ids: err('factChecks %s: unknown module %s' % (f.get('id'), f.get('module')))
    if f.get('status') not in ('open', 'verified', 'corrected'): err('factChecks %s: status must be open, verified or corrected' % f.get('id'))
    if f.get('status') != 'open' and not (f.get('checked') and DATE.match(f['checked']) and f.get('sources')): err('factChecks %s: checked items need a date and at least one source' % f.get('id'))
    if f.get('recheck') and not DATE.match(f['recheck']): err('factChecks %s: bad recheck date' % f.get('id'))
for m in mods:
    r = m.get('reviewed')
    if r and not (r.get('date') and DATE.match(r['date'])): err('%s: "reviewed" needs a YYYY-MM-DD date' % m['id'])

# 3. Spanish overlay matches the English structure
es = json.loads((W / 'data' / 'learn.es.json').read_text(encoding='utf-8'))
for mid, t in es.get('modules', {}).items():
    if mid not in ids: err('learn.es.json: unknown module %s' % mid); continue
    m = mods[ids.index(mid)]
    for k in ('sections', 'timeline', 'quiz'):
        if k in t and len(t[k]) != len(m.get(k, [])): err('learn.es.json %s: %d %s, English has %d' % (mid, len(t[k]), k, len(m.get(k, []))))
    for i, q in enumerate(t.get('quiz', [])):
        if i < len(m.get('quiz', [])) and 'options' in q and len(q['options']) != len(m['quiz'][i]['options']):
            err('learn.es.json %s quiz %d: option count differs from English' % (mid, i))
for k in es.get('quests', {}):
    if k not in qids: err('learn.es.json: unknown quest %s' % k)
for k in es.get('badges', {}):
    if k not in {b['id'] for b in cat['badges']}: err('learn.es.json: unknown badge %s' % k)

# 4. Narration matches the current lesson text, and every narration has stored audio in the manifest
try:
    import narrate
except Exception as e:
    err('cannot import scripts/narrate.py: %s' % e); narrate = None
manifest = json.loads((W / 'audio' / 'manifest.json').read_text(encoding='utf-8')) if (W / 'audio' / 'manifest.json').exists() else {'narrations': []}
in_manifest = {(r['lang'], r['module'], r['voice']) for r in manifest['narrations']}
for lang_dir in sorted(p for p in (W / 'audio').iterdir() if p.is_dir() and len(p.name) == 2):
    lang = lang_dir.name
    idx = json.loads((lang_dir / 'index.json').read_text(encoding='utf-8'))
    if narrate:
        narrate.LANG = lang
    for mid, voices in idx['modules'].items():
        if mid not in ids: err('audio/%s/index.json: unknown module %s' % (lang, mid)); continue
        m = json.loads(json.dumps(mods[ids.index(mid)]))
        if lang != 'en':
            t = es['modules'].get(mid, {})
            if not t.get('sections'): err('audio/%s: %s is narrated but not fully translated' % (lang, mid)); continue
            m['title'] = t.get('title', m['title']); m['intro'] = t.get('intro', m.get('intro'))
            m['sections'] = [dict(s, **{k: x[k] for k in ('h', 'body') if x.get(k)}) for s, x in zip(m['sections'], t['sections'])]
        expected = [s['text'] for s in narrate.segments(m)] if narrate else None
        for v in voices:
            f = lang_dir / ('%s.%s.json' % (mid, v))
            if not f.exists(): err('audio/%s: missing timing file %s' % (lang, f.name)); continue
            meta = json.loads(f.read_text(encoding='utf-8'))
            if not meta.get('audio', '').startswith('https://'): err('audio/%s/%s: no stored audio URL (run scripts/sync_audio.py)' % (lang, f.name))
            if (lang, mid, v) not in in_manifest: err('audio/%s/%s: not in audio/manifest.json (run scripts/sync_audio.py)' % (lang, f.name))
            got = [s['text'] for s in meta['segments']]
            if expected is not None and got != expected:
                diff = next((i for i, (a, b) in enumerate(zip(got, expected)) if a != b), min(len(got), len(expected)))
                (warn if meta.get('human') else err)('audio/%s/%s: narration no longer matches the lesson text (first difference at sentence %d). Re-run scripts/narrate.py%s.' % (lang, f.name, diff + 1, '' if lang == 'en' else ' --lang ' + lang))

for w in warnings: print('warning:', w)
for e in errors: print('ERROR:', e)
print('%d errors, %d warnings' % (len(errors), len(warnings)))
sys.exit(1 if errors else 0)
