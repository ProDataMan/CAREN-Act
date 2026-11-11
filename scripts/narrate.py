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
ABBR = ['U.S.', 'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'St.', 'Jr.', 'Sr.', 'v.', 'vs.', 'e.g.', 'i.e.', 'No.', 'Gen.', 'Rev.', 'Gov.', 'Sen.', 'Rep.', 'Lt.', 'Sgt.', 'Col.', 'Capt.', 'Mt.', 'Ft.', 'Co.', 'Inc.', 'a.m.', 'p.m.', 'D.C.', 'W.E.B.', 'C.J.', 'C.L.', 'J.B.', 'O.W.', 'B.', 'K.', 'L.', 'P.', 'T.', 'X.']
SAY = [(r'§\s*', 'section '), (r'\bU\.S\.', 'U.S.'), (r'(\d{4})–(\d{2,4})', r'\1 to \2'), (r'(\d)–(\d)', r'\1 to \2'), (r'\bv\. ', 'versus '), (r'\$(\d[\d,]*) (million|billion)', r'\1 \2 dollars'), (r'&', ' and ')]


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


def say(text):
    t = text
    for a, b in SAY:
        t = re.sub(a, b, t)
    return t


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ids', nargs='*')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--lang', default='en')
    ap.add_argument('--voice', required=True, help='Piper .onnx voice file')
    ap.add_argument('--kbps', type=int, default=48)
    a = ap.parse_args()
    from piper import PiperVoice, SynthesisConfig
    import lameenc
    cat = json.loads((ROOT / 'data' / 'learn.json').read_text(encoding='utf-8'))
    if a.lang != 'en':
        sys.exit('Non-English narration: overlay learn.%s.json first (not implemented yet)' % a.lang)
    mods = {m['id']: m for m in cat['modules']}
    ids = [m['id'] for m in cat['modules'] if m.get('status') != 'outline'] if a.all else a.ids
    voice = PiperVoice.load(a.voice)
    cfg = SynthesisConfig(length_scale=1.05)
    rate = voice.config.sample_rate
    out_dir = ROOT / 'audio' / a.lang
    out_dir.mkdir(parents=True, exist_ok=True)
    for mid in ids:
        m = mods[mid]
        segs = segments(m)
        pcm = bytearray(); t = 0.0; meta = []
        for sg in segs:
            audio = b''.join(c.audio_int16_bytes for c in voice.synthesize(say(sg['text']), syn_config=cfg))
            dur = len(audio) / 2 / rate
            meta.append({'el': sg['el'], 'text': sg['text'], 'start': round(t, 2), 'end': round(t + dur, 2)})
            pcm += audio + b'\x00\x00' * int(rate * sg['pause'])
            t += dur + sg['pause']
        enc = lameenc.Encoder()
        enc.set_bit_rate(a.kbps); enc.set_in_sample_rate(rate); enc.set_channels(1); enc.set_quality(2)
        mp3 = enc.encode(bytes(pcm)) + enc.flush()
        (out_dir / (mid + '.mp3')).write_bytes(mp3)
        (out_dir / (mid + '.json')).write_text(json.dumps({'module': mid, 'lang': a.lang, 'voice': Path(a.voice).stem, 'license': 'Voice: LJSpeech (public domain) via Piper TTS', 'duration': round(t, 1), 'segments': meta}, ensure_ascii=False, indent=0), encoding='utf-8')
        print('%s: %d sentences, %.0f s, %d KB' % (mid, len(meta), t, len(mp3) // 1024))


if __name__ == '__main__':
    main()
