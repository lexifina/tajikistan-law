"""Tajikistan: add FAOLEX (via ECOLEX) Tajik texts (secondary copies) to corpus.json. Run after parse_wipo.py.

Input: .cache/ecolex/records.json + .cache/ecolex/pdf/*.pdf (fetch_ecolex.py). Text layer only, no OCR.
Only Tajik texts are taken (most FAOLEX copies are Russian: listed in parsed.json, not built). Same rules as
parse_wipo.py: official versions win; nothing older than the latest version held; same day = duplicate.
Dated like the andoz.tj acts: the latest date the heading or amendment notes name (In-force-basis trailer).
"""
import hashlib, json, os, re, sys
from collections import Counter
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from parse_andoz import fix_encoding, page_lines, reflow, units_of, slugify, dates_in  # noqa: E402

HERE = Path(__file__).parent
D = HERE / '.cache' / 'ecolex'
TODAY = '2026-11-26'
PUB = {'name': 'FAOLEX (FAO), secondary copy of the Tajik text', 'email': 'publisher@faolex.invalid'}
TJ = re.compile(r'[ҷқҳӣӯғҶҚҲӢӮҒ]')


def title_of(lines):
    head = ' '.join(lines[:12])
    m = re.search(r'(Қонуни\s+(?:конститутсионии\s+)?Ҷумҳурии\s+Тоҷикистон)\s*["«]?\s*(Дар\s+бораи\s+[^"»]{3,200}?)["»]', head, re.I)
    if m:
        return f'{m.group(1)} "{m.group(2)}"'
    m = re.search(r'(Кодекси\s+\S+\s+Ҷумҳурии\s+Тоҷикистон)', head, re.I)
    return m.group(1) if m else None


def main():
    recs = json.loads((D / 'records.json').read_text(encoding='utf-8'))
    cp = HERE / 'corpus.json'
    c = json.loads(cp.read_text(encoding='utf-8'))
    for a in c['acts']:
        a['versions'] = [v for v in a['versions'] if 'faolex' not in (v.get('source_url') or '')]
    c['acts'] = [a for a in c['acts'] if a['versions']]
    held = {a['slug']: a for a in c['acts']}
    status, new, added = [], {}, 0
    for r in recs:
        for u in r['pdfs']:
            st = {'title': r['title'], 'pdf': u}
            status.append(st)
            f = D / 'pdf' / u.rsplit('/', 1)[1]
            if not f.exists():
                st['status'] = 'not fetched'
                continue
            raw = f.read_bytes()
            try:
                doc = pymupdf.open(stream=raw, filetype='pdf')
            except Exception:
                st['status'] = 'held: not a readable PDF'
                continue
            lines = page_lines(doc)
            text = '\n'.join(lines)
            if len(text) < 500:
                st['status'] = 'held: no text layer (no OCR)'
                continue
            text, enc = fix_encoding(text)
            text = text.replace('\u0450', 'ё').replace('\u0400', 'Ё')  # PDF font: ѐ for ё
            if len(TJ.findall(text[:20000])) < 30:
                st['status'] = 'not built: Russian/English text'
                continue
            if re.search(r'(?i)ворид намудани тағйир|ворид намудани илова', ' '.join(text.split('\n')[:8])):
                st['status'] = 'skipped: amending law'
                continue
            lines = text.split('\n')
            t = title_of(lines)
            if not t:
                st['status'] = 'held: no Tajik title found'
                continue
            units = units_of(reflow(lines))
            arts = [k for k in units if k.startswith('art-')]
            ds = dates_in(text[:4000])
            ds += dates_in(' '.join(re.findall(r'\((?:Қонуни ҶТ|ҚҶТ|Қонуни Ҷумҳурии Тоҷикистон)\s+аз\s+[^,;)№]{6,30}', text)))
            if not ds:
                st['status'] = 'held: no date in the text'
                continue
            d = max(ds)
            short_t = re.sub(r'^Қонуни Ҷумҳурии Тоҷикистон', 'Қонуни ҶТ', t)
            short_t = re.sub(r'^Қонуни конститутсионии Ҷумҳурии Тоҷикистон', 'Қонуни Конститутсионии ҶТ', short_t, flags=re.I)
            slug = slugify(short_t).replace('-jt-', '-').removesuffix('-jt')
            if t.startswith('Кодекси'):
                slug = slugify(re.sub(r'\s+Ҷумҳурии\s+Тоҷикистон', '', t))
            st.update(slug=slug, day=d, articles=len(arts), encoding=enc)
            if not arts:
                st['status'] = 'held: no articles found'
                continue
            v = {'from': d, 'source_url': u, 'sha256': hashlib.sha256(raw).hexdigest(), 'units': units,
                 'in_force_basis': ('latest date the text names in its heading or amendment notes (FAOLEX gives no '
                                    'in-force day for this text)'),
                 'source_status': f'secondary copy (FAOLEX via ECOLEX, {u})'}
            if slug in held:
                have = [x['from'] for x in held[slug]['versions']]
                if d in have:
                    st['status'] = f'skipped: already holds {d}'
                elif d < max(have):
                    st['status'] = f'held: older than the latest version held ({max(have)}); needs a history rewrite'
                else:
                    held[slug].setdefault('_new', []).append(dict(v, publisher=PUB))
                    st['status'] = 'ok (newer version of a held act)'
                continue
            short = re.sub(r'^Қонуни Ҷумҳурии Тоҷикистон "Дар бораи ', 'Қонун "', t)
            short = short.replace('Қонуни конститутсионии Ҷумҳурии Тоҷикистон ', 'Қонуни конститутсионӣ ')
            short = re.sub(r'\s+Ҷумҳурии\s+Тоҷикистон$', '', short)
            if len(short) > 70:
                short = short[:67].rstrip() + '...'
            a = new.setdefault(slug, {'slug': slug, 'short': short, 'title': t, 'url': f'https://www.ecolex.org/details/legislation/{r["slug"]}/',
                                      'first_law': None, 'earlier_laws': [], 'publisher': PUB, 'versions': []})
            if any(x['from'] == d for x in a['versions']):
                st['status'] = f'skipped: second copy on {d}'
                continue
            a['versions'].append(v)
            st['status'] = 'ok (new act)'
    for a in held.values():
        for v in sorted(a.pop('_new', []), key=lambda v: v['from']):
            if v['from'] > max(x['from'] for x in a['versions']):
                a['versions'].append(v)
                added += 1
    for a in new.values():
        a['versions'].sort(key=lambda v: v['from'])
        added += len(a['versions'])
    c['acts'] = sorted(list(held.values()) + list(new.values()), key=lambda a: (a['slug'] != 'konstitutsiya', a['slug']))
    c['sources'] = [s for s in c['sources'] if 'ecolex' not in s['url']]
    c['sources'].append({'name': 'FAOLEX (FAO), via ECOLEX, secondary copies', 'url': 'https://www.ecolex.org/result/?type=legislation&xcountry=Tajikistan',
                         'retrieved': TODAY, 'requests': 2 * len(recs) + 25,
                         'licence': 'Official texts (not objects of copyright, Law on Copyright of 13.11.1998, art. 7); FAO terms: non-commercial reuse with credit',
                         'notes': 'Tajik-language PDFs with a text layer only; Russian copies not built'})
    dec = [x for x in c['decisions'] if 'FAOLEX' not in x]
    dec.append('FAOLEX PDFs (via ECOLEX; secondary copies, Source-status trailer): Tajik texts only, read like the andoz.tj '
               'PDFs and dated the same way; Russian copies are not built.')
    c['decisions'] = dec
    (D / 'parsed.json').write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp = cp.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, cp)
    print(Counter(s['status'].split(':')[0].split(' (')[0] for s in status), 'versions added', added)
    for s in status:
        if not s['status'].startswith('not built'):
            print(s['status'], '|', s.get('slug', ''), s.get('day', ''), s.get('articles', ''), '|', (s['title'] or '')[:60])


if __name__ == '__main__':
    main()
