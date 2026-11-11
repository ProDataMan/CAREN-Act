#!/usr/bin/env python3
"""Turn a volunteer's recording of a Learn lesson into narration the site can play, with word highlighting.

    .venv/bin/python scripts/align_narration.py rights recording.m4a --name maya --label "Narrated by Maya" [--lang en]

What it does:
1. Decodes the recording (mp3, m4a, wav, webm, ogg: anything FFmpeg can read, via PyAV).
2. Transcribes it offline with faster-whisper (word timestamps). Nothing leaves this machine.
3. Lines the recognized words up with the lesson text (the same sentences scripts/narrate.py uses) and fills
   in any words that weren't recognized by interpolation.
4. Writes website/audio/<lang>/<module>.<name>.mp3 and .json, and adds the voice to audio/<lang>/index.json,
   so the lesson page offers it in the voice menu.

It prints how much of the text it matched. Below about 85%, the reader probably skipped or added
passages: listen to the result before publishing.

Setup: .venv/bin/pip install faster-whisper lameenc  (the Whisper model downloads once, ~150 MB)
"""
import argparse, difflib, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import narrate  # noqa: E402  (shares the lesson text and sentence splitting)

ROOT = narrate.ROOT


def norm(w):
    return re.sub(r'[^0-9a-záéíóúüñ]', '', w.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('module')
    ap.add_argument('audio')
    ap.add_argument('--name', required=True, help='voice key, e.g. maya (letters, digits, dashes)')
    ap.add_argument('--label', required=True, help='shown in the voice menu, e.g. "Narrated by Maya"')
    ap.add_argument('--lang', default='en')
    ap.add_argument('--model', default=None, help='Whisper model (default: base.en for English, base otherwise)')
    ap.add_argument('--kbps', type=int, default=48)
    a = ap.parse_args()
    if not re.fullmatch(r'[a-z0-9-]{2,30}', a.name) or a.name in ('female', 'male'):
        sys.exit('--name must be 2-30 lowercase letters, digits or dashes, and not "female" or "male"')

    import av, lameenc, numpy as np
    from faster_whisper import WhisperModel, decode_audio

    # Lesson text and segments, exactly as the page and narrate.py see them
    cat = json.loads((ROOT / 'data' / 'learn.json').read_text(encoding='utf-8'))
    mods = {m['id']: m for m in cat['modules']}
    m = mods.get(a.module) or sys.exit('No module %s' % a.module)
    if a.lang != 'en':
        o = json.loads((ROOT / 'data' / ('learn.%s.json' % a.lang)).read_text(encoding='utf-8'))['modules'].get(a.module, {})
        if not o.get('sections'):
            sys.exit('Module %s is not fully translated into %s' % (a.module, a.lang))
        m = dict(m, title=o.get('title', m['title']), intro=o.get('intro', m.get('intro')),
                 sections=[dict(s, **{k: t[k] for k in ('h', 'body') if t.get(k)}) for s, t in zip(m['sections'], o['sections'])])
    segs = narrate.segments(m)
    tokens = []  # (segment index, token index, normalized)
    for si, s in enumerate(segs):
        for ti, w in enumerate(s['text'].split()):
            tokens.append((si, ti, norm(w)))

    # 1. Transcribe with word timestamps
    model = WhisperModel(a.model or ('base.en' if a.lang == 'en' else 'base'), device='cpu', compute_type='int8')
    audio16 = decode_audio(a.audio, sampling_rate=16000)
    result, _ = model.transcribe(audio16, language=a.lang, word_timestamps=True, condition_on_previous_text=False, beam_size=5)
    asr = [(norm(w.word), w.start, w.end) for seg in result for w in seg.words if norm(w.word)]
    duration = len(audio16) / 16000.0

    # 2. Align recognized words to the lesson text
    sm = difflib.SequenceMatcher(None, [t[2] for t in tokens], [x[0] for x in asr], autojunk=False)
    times = [None] * len(tokens)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = [asr[blk.b + k][1], asr[blk.b + k][2]]
    matched = sum(1 for t in times if t)
    # 3. Interpolate unmatched words between their matched neighbours, weighted by length
    i = 0
    while i < len(times):
        if times[i]:
            i += 1; continue
        j = i
        while j < len(times) and not times[j]:
            j += 1
        t0 = times[i - 1][1] if i > 0 else 0.0
        t1 = times[j][0] if j < len(times) else duration
        lens = [max(len(tokens[k][2]), 1) for k in range(i, j)]
        tot, t = sum(lens), t0
        for k, n in zip(range(i, j), lens):
            d = (t1 - t0) * n / tot
            times[k] = [t, t + d]; t += d
        i = j

    out_segs = []
    for si, s in enumerate(segs):
        ws = [[round(times[k][0], 2), round(times[k][1], 2)] for k, tk in enumerate(tokens) if tk[0] == si]
        if not ws:
            continue
        out_segs.append({'el': s['el'], 'text': s['text'], 'start': ws[0][0], 'end': ws[-1][1], 'words': ws})

    # 4. Re-encode the recording as mono MP3 for the site
    rate = 24000
    pcm = bytearray()
    with av.open(a.audio) as f:
        rs = av.AudioResampler(format='s16', layout='mono', rate=rate)
        for frame in f.decode(audio=0):
            for fr in rs.resample(frame):
                pcm += fr.to_ndarray().tobytes()
        for fr in rs.resample(None):
            pcm += fr.to_ndarray().tobytes()
    enc = lameenc.Encoder()
    enc.set_bit_rate(a.kbps); enc.set_in_sample_rate(rate); enc.set_channels(1); enc.set_quality(2)
    mp3 = enc.encode(bytes(pcm)) + enc.flush()

    out_dir = ROOT / 'audio' / a.lang
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / ('%s.%s.mp3' % (a.module, a.name))).write_bytes(mp3)
    (out_dir / ('%s.%s.json' % (a.module, a.name))).write_text(json.dumps({'module': a.module, 'voice': a.name, 'human': True, 'duration': round(duration, 1), 'matched': round(matched / max(len(tokens), 1), 3), 'segments': out_segs}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    idx_p = out_dir / 'index.json'
    idx = json.loads(idx_p.read_text(encoding='utf-8')) if idx_p.exists() else {'voices': {}, 'modules': {}}
    idx['voices'][a.name] = {'label': a.label, 'model': 'human recording'}
    vs = idx['modules'].setdefault(a.module, [])
    if a.name not in vs:
        vs.insert(0, a.name)  # human narration first in the voice menu
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1), encoding='utf-8')
    pct = 100.0 * matched / max(len(tokens), 1)
    print('%s / %s: %.0f s, %d KB, %.0f%% of words matched%s' % (a.module, a.name, duration, len(mp3) // 1024, pct,
          '' if pct >= 85 else '  <-- low: check that the reader followed the script'))


if __name__ == '__main__':
    main()
