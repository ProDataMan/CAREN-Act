#!/usr/bin/env python3
"""Print a Markdown summary of what needs fact-checking or review (used by the quarterly reminder issue)."""
import json, sys
from datetime import date, timedelta
from pathlib import Path

cat = json.loads((Path(__file__).resolve().parent.parent.parent / 'website' / 'data' / 'learn.json').read_text(encoding='utf-8'))
mods = {m['id']: m for m in cat['modules']}
soon = (date.today() + timedelta(days=30)).isoformat()
site = 'https://prodataman.github.io/CAREN-Act/website/'
fcs = cat.get('factChecks', [])
open_ = [f for f in fcs if f['status'] == 'open']
due = [f for f in fcs if f['status'] != 'open' and f.get('recheck') and f['recheck'] <= soon]
unreviewed = [m for m in cat['modules'] if m.get('status') != 'outline' and not (m.get('reviewed') or {}).get('date')]
out = ['Quarterly review reminder. The queue is at %sreview.html.' % site, '',
       'Update `factChecks` (status, checked date, note, sources, next recheck date) and each lesson\'s `reviewed` field in `website/data/learn.json`. If a lesson\'s text changes, re-run `scripts/narrate.py` and `scripts/sync_audio.py` (CI will fail until the narration matches).', '']
def item(f):
    m = mods.get(f['module'], {})
    return '- [ ] **%s** (%s): %s _%s_' % (f['id'], m.get('title', f['module']).split(':')[0], f['claim'], f.get('note', ''))
out += ['## Open fact checks (%d)' % len(open_)] + [item(f) for f in open_] + ['']
out += ['## Rechecks due by %s (%d)' % (soon, len(due))] + [item(f) + ' (recheck by %s)' % f['recheck'] for f in due] + ['']
out += ['## Lessons not yet reviewed by an expert (%d of %d)' % (len(unreviewed), len(cat['modules'])), ', '.join('%d. %s' % (m['num'], m['title'].split(':')[0]) for m in unreviewed), '']
print('\n'.join(out))
