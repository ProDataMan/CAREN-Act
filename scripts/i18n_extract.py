#!/usr/bin/env python3
"""Hub-and-spoke translation helper.

Extracts the English UI strings (the hub) from website/*.html and website/assets/*.js, and reports which
strings each spoke (website/i18n/<lang>.json) is missing. Lesson content is translated separately in
website/data/learn.<lang>.json.

    python3 scripts/i18n_extract.py            # counts per language
    python3 scripts/i18n_extract.py es --missing > /tmp/missing.txt
"""
import html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'website'
PAGES = sorted(ROOT.glob('*.html'))
SCRIPTS = [ROOT / 'assets' / n for n in ('site.js', 'reps.js', 'learn.js', 'api.js')]
ATTRS = {'placeholder', 'title', 'aria-label', 'alt', 'content'}
norm = lambda s: re.sub(r'\s+', ' ', s).strip()

def useful(s):
    s = norm(s)
    if len(s) < 2 or not re.search(r'[A-Za-z]{2}', s): return False
    if re.search(r'=>|\bfunction\b|\.json|https?:|[{};]|\$\(|^#|^\.|px\b|rgba?\(', s): return False
    if re.fullmatch(r'[a-z0-9_-]+', s): return False   # identifiers, ids, classes
    return True

class P(HTMLParser):
    def __init__(self):
        super().__init__(); self.out = []; self.skip = 0; self.scripts = []; self.inscript = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1; self.inscript = tag == 'script'; self.buf = ''
        a = dict(attrs)
        if tag == 'meta' and a.get('name') not in ('description',) and a.get('property') not in ('og:title', 'og:description'): return
        for k, v in attrs:
            if k in ATTRS and v and useful(v): self.out.append(norm(v))
    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1
            if tag == 'script' and self.buf: self.scripts.append(self.buf)
            self.inscript = False
    def handle_data(self, d):
        if self.skip:
            if self.inscript: self.buf += d
            return
        if useful(d): self.out.append(norm(d))

LIT = re.compile(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"|`((?:[^`\\]|\\.)*)`")
def from_js(src):
    out = []
    for m in LIT.finditer(src):
        s = next(g for g in m.groups() if g is not None)
        s = s.replace("\\'", "'").replace('\\"', '"').replace('\\n', ' ')
        if '${' in s: s = re.sub(r'\$\{[^}]*\}', '\x00', s)
        for frag in re.split(r'<[^>]*>|\x00', s):
            frag = html.unescape(frag)
            if useful(frag) and ' ' in norm(frag) or (useful(frag) and re.fullmatch(r"[A-Z][A-Za-z’'.]+[:.!?]?", norm(frag))):
                out.append(norm(frag))
    return out

def hub():
    seen = {}
    for p in PAGES:
        parser = P(); parser.feed(p.read_text(encoding='utf-8'))
        for s in parser.out + [x for sc in parser.scripts for x in from_js(sc)]: seen.setdefault(s, p.name)
    for js in SCRIPTS:
        for s in from_js(js.read_text(encoding='utf-8')): seen.setdefault(s, js.name)
    return seen

if __name__ == '__main__':
    h = hub()
    langs = [a for a in sys.argv[1:] if not a.startswith('-')] or [p.stem for p in (ROOT / 'i18n').glob('*.json')]
    for lang in langs:
        f = ROOT / 'i18n' / (lang + '.json')
        have = json.loads(f.read_text(encoding='utf-8')).get('strings', {}) if f.exists() else {}
        missing = [s for s in h if s not in have]
        if '--missing' in sys.argv:
            for s in missing: print(json.dumps(s, ensure_ascii=False) + '\t' + h[s])
        else:
            print(f'{lang}: {len(h) - len(missing)} of {len(h)} strings translated ({len(missing)} missing)')
