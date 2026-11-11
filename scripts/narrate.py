#!/usr/bin/env python3
"""Generate narrated audio for Learn modules, with per-sentence timings for highlighting.

Uses Piper (offline, open-source text-to-speech; https://github.com/rhasspy/piper). Nothing is sent to an
outside service. Output, served with the site:
    website/audio/<lang>/<module>.mp3   one file per lesson (mono MP3)
    website/audio/<lang>/<module>.json  {"segments": [{"el": "s0", "text": "...", "start": 1.2, "end": 4.8}, ...]}

"el" names the element on module.html that holds the sentence: "title", "intro", "h<i>" (section heading)
or "s<i>" (section body). The page finds each sentence's text inside that element and highlights it.

Setup (once):
    python3 -m venv .venv && .venv/bin/pip install piper-tts lameenc
    # voice: en_US-ljspeech-high (public domain) from https://huggingface.co/rhasspy/piper-voices
Run:
    .venv/bin/python scripts/narrate.py --voice path/to/en_US-ljspeech-high.onnx before-race [more ids]
    .venv/bin/python scripts/narrate.py --voice ... --all
Re-run a module after editing its text in learn.json (or learn.<lang>.json).
"""
import argparse, html, json, re, sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'website'
BLOCK = {'p', 'li', 'ul', 'ol', 'div', 'br', 'h1', 'h2', 'h3', 'blockquote'}
ABBR = ['EE. UU.', 'p. ej.', 'n.º', 'Sra.', 'Dra.', 'U.S.', 'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'St.', 'Jr.', 'Sr.', 'v.', 'vs.', 'e.g.', 'i.e.', 'No.', 'Gen.', 'Rev.', 'Gov.', 'Sen.', 'Rep.', 'Lt.', 'Sgt.', 'Col.', 'Capt.', 'Mt.', 'Ft.', 'Co.', 'Inc.', 'a.m.', 'p.m.', 'D.C.', 'W.E.B.', 'C.J.', 'C.L.', 'J.B.', 'O.W.', 'B.', 'K.', 'L.', 'P.', 'T.', 'X.']
SAY = [(r'§\s*', 'section '), (r'(\d)–(\d)', r'\1 to \2'), (r'(\d0s)–(\d)', r'\1 to \2'), (r'\bv\. ', 'versus '), (r'\$(\d[\d,.]*) (million|billion)', r'\1 \2 dollars'), (r'&', ' and ')]
ONES = 'zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen'.split()
TENS = 'zero ten twenty thirty forty fifty sixty seventy eighty ninety'.split()


def two(n):
    return ONES[n] if n < 20 else TENS[n // 10] + ('-' + ONES[n % 10] if n % 10 else '')


def year(y, plural=False):
    """1492 -> fourteen ninety-two, 1905 -> nineteen oh five, 1900 -> nineteen hundred, 2005 -> two thousand five, 2023 -> twenty twenty-three."""
    hi, lo = divmod(y, 100)
    if 2000 <= y <= 2009:
        w = 'two thousand' + (' ' + ONES[lo] if lo else '')
    elif lo == 0:
        w = two(hi) + ' hundred'
    elif lo < 10:
        w = two(hi) + ' oh ' + ONES[lo]
    else:
        w = two(hi) + ' ' + two(lo)
    if plural:
        w = re.sub(r'y$', 'ie', w) + 's' if not w.endswith('hundred') else w + 's'
    return w


def years(t):
    # decades: 1830s, 1960s
    t = re.sub(r'(?<![\d,$.])(1[0-9]|20)(\d0)s\b', lambda m: year(int(m.group(1) + m.group(2)), True), t)
    # short decades after a range: 1960s–70s -> "to seventies"
    t = re.sub(r"\bto (\d0)s\b", lambda m: 'to ' + re.sub(r'y$', 'ies', TENS[int(m.group(1)) // 10]), t)
    # four-digit years 1000-2099 standing alone (not 1,256 or $1500 or 15000)
    return re.sub(r'(?<![\d,$.])(1[0-9]\d\d|20\d\d)(?![\d,]\d)', lambda m: year(int(m.group(1))), t)


class Blocks(HTMLParser):
    """Split HTML into block-level text runs (paragraphs, list items)."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = ['']
    def handle_starttag(self, tag, attrs):
        if tag in BLOCK: self.out.append('')
    def handle_endtag(self, tag):
        if tag in BLOCK: self.out.append('')
    def handle_data(self, d):
        self.out[-1] += d


def blocks(h):
    p = Blocks(); p.feed(h); p.close()
    return [re.sub(r'\s+', ' ', b).strip() for b in p.out if b.strip()]


def sentences(text):
    protected = text
    for i, a in enumerate(ABBR):
        protected = protected.replace(a, a.replace('.', '\x00'))
    parts = re.split(r'(?<=[.!?…])(?:["”’)\]]*)\s+(?=[“"(\[A-Z0-9¿¡])', protected)
    # re.split drops the closing quotes captured in the lookbehind group; recover them by re-scanning
    out, pos = [], 0
    for part in parts:
        start = protected.find(part, pos)
        end = start + len(part)
        while end < len(protected) and protected[end] in '"”’)]':
            end += 1
        out.append(protected[start:end].replace('\x00', '.').strip())
        pos = end
    return [s for s in out if s]


SAY_ES = [(r'EE\. ?UU\.', 'Estados Unidos'), (r'§\s*', 'sección '), (r'(\d)–(\d)', r'\1 a \2'), (r'n\.º', 'número'), (r'\bv\. ', 'contra '), (r'&', ' y ')]
LANG = 'en'


def say(text):
    t = text
    if LANG == 'es':
        # Spanish reads years as whole numbers (1492 = "mil cuatrocientos noventa y dos"), which espeak already does.
        for a, b in SAY_ES:
            t = re.sub(a, b, t)
        return t
    for a, b in SAY:
        t = re.sub(a, b, t)
    return years(t)


def segments(m):
    segs = [{'el': 'title', 'text': m['title'], 'pause': 0.8}]
    if m.get('intro'):
        segs += [{'el': 'intro', 'text': s, 'pause': 0.35} for s in sentences(m['intro'])]
    for i, s in enumerate(m.get('sections', [])):
        segs.append({'el': 'h%d' % i, 'text': s['h'], 'pause': 0.7})
        for b in blocks(s['body']):
            for x in sentences(b):
                segs.append({'el': 's%d' % i, 'text': x, 'pause': 0.35})
        segs[-1]['pause'] = 0.9
    return segs


def word_times(voice, text, audio, rate, t0):
    """Estimate when each whitespace-separated word of `text` is spoken in `audio` (int16 mono bytes).
    Piper's stock voices don't report timings, so the sentence's measured speech span is divided in
    proportion to each word's phoneme count, with extra time after commas and other pauses."""
    import array
    a = array.array('h'); a.frombytes(audio)
    win = int(rate * 0.01); thr = 500
    loud = [i for i in range(0, len(a), win) if max(abs(x) for x in a[i:i + win]) > thr]
    s0 = (loud[0] / rate) if loud else 0.0
    s1 = ((loud[-1] + win) / rate) if loud else len(a) / rate
    words = text.split()
    weights = []
    for w in words:
        ph = voice.phonemize(say(w))
        n = sum(1 for sent in ph for p in sent if p not in (' ', 'ˈ', 'ˌ', 'ː')) or 1
        pause = 3.5 if re.search(r'[,;:—–)]$', w) else (5 if re.search(r'[.!?]["”’)]*$', w) else 0)
        weights.append((n, pause))
    total = sum(n + p for n, p in weights) or 1
    span = max(s1 - s0, 0.1)
    out, t = [], s0
    for n, p in weights:
        d = span * n / total
        out.append([round(t0 + t, 2), round(t0 + t + d, 2)])
        t += d + span * p / total
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--lang', default='en')
    ap.add_argument('--voice', action='append', required=True,
                    help='name=path/to/voice.onnx[:speaker_id], e.g. female=en_US-kristin-medium.onnx; repeat for each voice')
    ap.add_argument('--label', action='append', default=[], help='name=Display label, e.g. "female=Female voice (Kristin)"')
    ap.add_argument('--kbps', type=int, default=48)
    a = ap.parse_args()
    from piper import PiperVoice, SynthesisConfig
    import lameenc
    cat = json.loads((ROOT / 'data' / 'learn.json').read_text(encoding='utf-8'))
    global LANG
    LANG = a.lang
    mods = {m['id']: m for m in cat['modules']}
    if a.lang != 'en':
        # Overlay the translated lesson text (same structure as learn.js) and narrate only fully translated modules.
        o = json.loads((ROOT / 'data' / ('learn.%s.json' % a.lang)).read_text(encoding='utf-8'))
        for mid, t in o.get('modules', {}).items():
            m = mods.get(mid)
            if not m or not t.get('sections'):
                continue
            for k in ('title', 'intro'):
                if t.get(k): m[k] = t[k]
            for i, sec in enumerate(t['sections']):
                if i < len(m['sections']):
                    m['sections'][i] = dict(m['sections'][i], **{k: sec[k] for k in ('h', 'body') if sec.get(k)})
            m['_translated'] = True
        missing = [i for i in (a.ids or []) if not mods.get(i, {}).get('_translated')]
        if missing:
            sys.exit('Not fully translated into %s yet: %s' % (a.lang, ', '.join(missing)))
    ids = [m['id'] for m in cat['modules'] if m.get('status') != 'outline' and (a.lang == 'en' or m.get('_translated'))] if a.all else a.ids
    labels = dict(x.split('=', 1) for x in a.label)
    out_dir = ROOT / 'audio' / a.lang
    out_dir.mkdir(parents=True, exist_ok=True)
    idx_path = out_dir / 'index.json'
    index = json.loads(idx_path.read_text(encoding='utf-8')) if idx_path.exists() else {'voices': {}, 'modules': {}}
    for spec in a.voice:
        name, path = spec.split('=', 1)
        speaker = None
        if re.search(r':\d+$', path):
            path, speaker = path.rsplit(':', 1); speaker = int(speaker)
        voice = PiperVoice.load(path)
        cfg = SynthesisConfig(length_scale=1.05, speaker_id=speaker)
        rate = voice.config.sample_rate
        index['voices'][name] = {'label': labels.get(name, name), 'model': Path(path).stem + ('#%d' % speaker if speaker is not None else '')}
        for mid in ids:
            m = mods[mid]
            pcm = bytearray(); t = 0.0; meta = []
            for sg in segments(m):
                audio = b''.join(c.audio_int16_bytes for c in voice.synthesize(say(sg['text']), syn_config=cfg))
                dur = len(audio) / 2 / rate
                meta.append({'el': sg['el'], 'text': sg['text'], 'start': round(t, 2), 'end': round(t + dur, 2),
                             'words': word_times(voice, sg['text'], audio, rate, t)})
                pcm += audio + b'\x00\x00' * int(rate * sg['pause'])
                t += dur + sg['pause']
            enc = lameenc.Encoder()
            enc.set_bit_rate(a.kbps); enc.set_in_sample_rate(rate); enc.set_channels(1); enc.set_quality(2)
            mp3 = enc.encode(bytes(pcm)) + enc.flush()
            (out_dir / ('%s.%s.mp3' % (mid, name))).write_bytes(mp3)
            (out_dir / ('%s.%s.json' % (mid, name))).write_text(json.dumps({'module': mid, 'voice': name, 'duration': round(t, 1), 'segments': meta}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
            vs = index['modules'].setdefault(mid, [])
            if name not in vs: vs.append(name)
            print('%s / %s: %d sentences, %.0f s, %d KB' % (mid, name, len(meta), t, len(mp3) // 1024))
    index['note'] = 'Generated by scripts/narrate.py with Piper TTS (offline). Voices and licenses: see README.'
    idx_path.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
