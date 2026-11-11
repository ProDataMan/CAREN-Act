#!/usr/bin/env python3
"""Build podcast RSS feeds from the narrated Learn lessons.

    python3 scripts/podcast.py            # writes website/podcast/<lang>-<voice>.xml for every language and voice
Run after scripts/narrate.py. Feeds point at the GitHub Pages copy of the audio.
"""
import email.utils, html, json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / 'website'
SITE = 'https://prodataman.github.io/CAREN-Act/website/'
TEXT = {
    'en': {'title': 'How We Got Here: Lessons on Systemic Racism', 'author': 'Federal CAREN Act campaign',
           'desc': 'Short, sourced lessons on how systemic racism was built in America, from the first slave laws to the weaponized 911 call, and what has worked to undo it. Every claim is labeled documented, debated, or belief or myth. Narrated by computer voices; full text, sources and quizzes at the link for each episode.',
           'voice': {'female': 'female voice', 'male': 'male voice'}},
    'es': {'title': 'Cómo llegamos aquí: lecciones sobre el racismo sistémico', 'author': 'Campaña por la Ley CAREN federal',
           'desc': 'Lecciones breves y con fuentes sobre cómo se construyó el racismo sistémico en Estados Unidos y qué ha funcionado para deshacerlo. Cada afirmación está etiquetada como documentada, debatida o creencia o mito. Narradas con voces de computadora; texto completo, fuentes y cuestionarios en el enlace de cada episodio.',
           'voice': {'female': 'voz femenina', 'male': 'voz masculina'}},
}


def esc(s):
    return html.escape(s, quote=True)


def main():
    cat = json.loads((ROOT / 'data' / 'learn.json').read_text(encoding='utf-8'))
    out = ROOT / 'podcast'
    out.mkdir(exist_ok=True)
    feeds = []
    for lang in ('en', 'es'):
        idx_p = ROOT / 'audio' / lang / 'index.json'
        if not idx_p.exists():
            continue
        idx = json.loads(idx_p.read_text(encoding='utf-8'))
        o = json.loads((ROOT / 'data' / 'learn.es.json').read_text(encoding='utf-8')) if lang == 'es' else {'modules': {}}
        t = TEXT[lang]
        for voice in idx['voices']:
            items = []
            base = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)  # stable dates keep episodes in lesson order
            for n, m in enumerate(cat['modules']):
                if voice not in idx['modules'].get(m['id'], []):
                    continue
                mp3 = ROOT / 'audio' / lang / ('%s.%s.mp3' % (m['id'], voice))
                meta = json.loads((ROOT / 'audio' / lang / ('%s.%s.json' % (m['id'], voice))).read_text(encoding='utf-8'))
                tr = o['modules'].get(m['id'], {})
                title, short = tr.get('title', m['title']), tr.get('short', m['short'])
                link = SITE + 'module.html?m=%s&lang=%s' % (m['id'], lang)
                d = int(meta['duration'])
                items.append(
                    '<item><title>%s</title><description>%s</description><link>%s</link><guid isPermaLink="false">caren-%s-%s-%s</guid>'
                    '<pubDate>%s</pubDate><enclosure url="%s" length="%d" type="audio/mpeg"/><itunes:duration>%d:%02d</itunes:duration>'
                    '<itunes:episode>%d</itunes:episode><itunes:explicit>false</itunes:explicit></item>' % (
                        esc('%d. %s' % (m['num'], title)), esc(short + ' ' + link), esc(link), lang, voice, m['id'],
                        email.utils.format_datetime(datetime.fromtimestamp(base.timestamp() + m['num'] * 3600, timezone.utc)),
                        esc(SITE + 'audio/%s/%s.%s.mp3' % (lang, m['id'], voice)), mp3.stat().st_size, d // 60, d % 60, m['num']))
            if not items:
                continue
            name = '%s-%s.xml' % (lang, voice)
            feed_title = '%s (%s)' % (t['title'], t['voice'][voice])
            xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom"><channel>'
                   '<title>%s</title><link>%s</link><language>%s</language><description>%s</description>'
                   '<atom:link href="%s" rel="self" type="application/rss+xml"/><itunes:author>%s</itunes:author><itunes:summary>%s</itunes:summary>'
                   '<itunes:image href="%s"/><image><url>%s</url><title>%s</title><link>%s</link></image>'
                   '<itunes:category text="History"/><itunes:category text="Education"/><itunes:explicit>false</itunes:explicit><itunes:type>serial</itunes:type>'
                   '%s</channel></rss>\n') % (
                esc(feed_title), esc(SITE + 'learn.html'), lang, esc(t['desc']), esc(SITE + 'podcast/' + name), esc(t['author']), esc(t['desc']),
                esc(SITE + 'podcast/cover.png'), esc(SITE + 'podcast/cover.png'), esc(feed_title), esc(SITE + 'learn.html'), ''.join(items))
            (out / name).write_text(xml, encoding='utf-8')
            feeds.append({'lang': lang, 'voice': voice, 'file': 'podcast/' + name, 'title': feed_title, 'episodes': len(items)})
            print(name, len(items), 'episodes')
    (out / 'feeds.json').write_text(json.dumps(feeds, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
