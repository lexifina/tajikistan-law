"""Tajikistan: add WIPO Lex Tajik texts (secondary copies) to corpus.json. Run after parse_andoz.py.

Input: .cache/wipo/records.json + .cache/wipo/pdf/*tg*.pdf (fetch_wipo.py). Text layer only, no OCR.
Rules: official andoz.tj / president.tj versions win; a WIPO version is added to an act already held only when it is
newer than every version held (an older one would need the published history rewritten: listed as held instead);
a version on a day already held is a duplicate and skipped. Amending laws are not acts of their own here.
Writes .cache/wipo/parsed.json (per-record status).
"""
import datetime as dt, hashlib, json, os, re, sys
from collections import Counter
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).parent))
from parse_andoz import fix_encoding, page_lines, reflow, units_of, slugify, dates_in  # noqa: E402

HERE = Path(__file__).parent
D = HERE / '.cache' / 'wipo'
TODAY = '2026-11-26'
PUB = {'name': 'WIPO Lex (secondary copy of the Tajik text)', 'email': 'publisher@wipolex.invalid'}
MON = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                                   'September', 'October', 'November', 'December'], 1)}
KNOWN = {  # WIPO English title -> slug already in the repo
    'Criminal Code': 'kodeksi-jinoyati', 'Criminal Code of the Republic of Tajikistan': 'kodeksi-jinoyati',
    'Criminal Procedure Code': 'kodeksi-murofiavii-jinoyatii',
    'Civil Procedure Code': 'kodeksi-murofiyavii-grazhdanii',
    'Economic Procedure Code': 'kodeksi-murofiyavii-iqtisodii',
    'Code of Administrative Offences': 'kodeksi-huquqvayronkunii-mamuri',
    'Customs Code': 'kodeksi-gumruki', 'Civil Code': 'kodeksi-madanii',
    'Civil Code of the Republic of Tajikistan (part I)': 'kodeksi-grazhdanii-qismi-i',
    'Civil Code of the Republic of Tajikistan (Part II)': 'kodeksi-grazhdanii-qismi-ii',
    'Civil Code of the Republic of Tajikistan (Part III)': 'kodeksi-grazhdanii-qismi-iii',
    'Constitution': 'konstitutsiya',
}


def day(s):
    if not s:
        return None
    m = re.fullmatch(r'([A-Z][a-z]+) (\d{1,2}), (\d{4})', s)
    return dt.date(int(m.group(3)), MON[m.group(1)], int(m.group(2))).isoformat() if m else None


HOMO = str.maketrans({'c': 'с', 'C': 'С', 'o': 'о', 'O': 'О', 'a': 'а', 'A': 'А', 'e': 'е', 'E': 'Е', 'p': 'р',
                      'P': 'Р', 'x': 'х', 'X': 'Х', 'H': 'Н', 'K': 'К', 'M': 'М', 'T': 'Т', 'B': 'В'})


def tg_title(r):
    m = re.search(r'Tajik (.*?)(?: Russian | English |$)', r.get('main_texts') or '')
    if not m:
        return None
    t = fix_encoding(' '.join(m.group(1).split()))[0]
    if re.search(r'[А-Яа-яӢӣӮӯ]', t):
        # Latin look-alike letters typed inside Tajik words
        t = re.sub(r'\b[\wӣӯҳқҷғ]+\b', lambda w: w.group(0).translate(HOMO) if re.search(r'[а-яА-Я]', w.group(0)) else w.group(0), t)
    t = re.sub(r'\s+аз\s+\d{1,2}\s+\S+\s+соли\s+\d{4}(?:\s*,?\s*№\s*\d+)?\s*$', '', t)
    return t


def main():
    recs = json.loads((D / 'records.json').read_text(encoding='utf-8'))
    cp = HERE / 'corpus.json'
    c = json.loads(cp.read_text(encoding='utf-8'))
    # idempotent: drop what an earlier run of this script added
    for a in c['acts']:
        a['versions'] = [v for v in a['versions'] if 'wipo.int' not in (v.get('source_url') or '')]
    c['acts'] = [a for a in c['acts'] if a['versions']]
    held = {a['slug']: a for a in c['acts']}
    status, new = [], {}
    for r in sorted(recs.values(), key=lambda r: r['wipo_no']):
        st = {'wipo_no': r['wipo_no'], 'title': r['title'], 'subtitle': r['subtitle']}
        status.append(st)
        tg = [u for u in r['pdfs'] if '/laws/tg/' in u]
        if not tg:
            st['status'] = 'skipped: no Tajik text (Russian/English only)'
            continue
        if re.match(r'Law on (Amendments|Additions)|Law of the Republic of Tajikistan No\. \d+ of .* on Amendments', r['title'] or '') \
                or r['relations'].get('Amends'):
            st['status'] = 'skipped: amending law (its changes are in the consolidated texts)'
            continue
        if 'Tajik Current text in this language is unavailable' in (r.get('main_texts') or ''):
            st['status'] = 'skipped: WIPO Lex gives only an earlier Tajik version for this record'
            continue
        m_am = re.search(r'\(as amended (?:up to|by) (?:the )?Law No\. \d+ of ([A-Z][a-z]+ \d{1,2}, \d{4})\)', r['title'] or '')
        if m_am and not r['amended_up_to']:
            r = dict(r, amended_up_to=m_am.group(1), subtitle=m_am.group(0).strip('()'))
        f = D / 'pdf' / tg[0].rsplit('/', 1)[1]
        if not f.exists():
            st['status'] = 'not fetched'
            continue
        raw = f.read_bytes()
        doc = pymupdf.open(stream=raw, filetype='pdf')
        lines = page_lines(doc)
        text = '\n'.join(lines)
        if len(text) < 500:
            st['status'] = 'held: no text layer (no OCR)'
            continue
        text, enc = fix_encoding(text)
        text = text.replace('\u0450', 'ё').replace('\u0400', 'Ё')  # PDF font: ѐ for ё
        lines = text.split('\n')
        units = units_of(reflow(lines))
        arts = [k for k in units if k.startswith('art-')]
        st.update(encoding=enc, units=len(units), articles=len(arts))
        upto, eif, adopted = day(r['amended_up_to']), day(r['entry_into_force']), day(r['adopted'])
        m = re.search(r'(?:Law|Decree|Resolution|Order)[^,]*? No\. ([\w-]+) of ([A-Z][a-z]+ \d{1,2}, \d{4})',
                      (r['subtitle'] or '') + ' ' + (r['title'] or ''))
        base = eif or adopted
        yrs = [int(y) for y in re.findall(r'соли\s+((?:19|20)\d\d)', text[:3000])]
        if not upto and base and yrs and max(yrs) > int(base[:4]):
            # a consolidated text (its Ахбори list names later amendments) that WIPO Lex gives no edition day for
            ds = dates_in(text[:4000]) + dates_in(' '.join(re.findall(
                r'\((?:Қонуни ҶТ|ҚҶТ|Қонуни Ҷумҳурии Тоҷикистон)\s+аз\s+[^,;)№]{6,30}', text)))
            if not ds or max(ds) <= base:
                st['status'] = 'held: consolidated text (amendments to ' + str(max(yrs)) + ') with no edition day'
                continue
            upto, r = max(ds), dict(r, subtitle=None, amended_up_to='the latest date its amendment notes name')
        if upto:
            d = upto
            basis = (f'date of the last amending law WIPO Lex names for this consolidated text '
                     f'({r["subtitle"] or "amended up to " + r["amended_up_to"]}); the day it took effect is not stated with the text')
        elif eif:
            d = eif
            basis = 'entry-into-force day WIPO Lex gives for this text'
        elif adopted:
            d = adopted
            basis = 'adoption day WIPO Lex gives for this text (no entry-into-force day stated)'
        elif m:
            d = day(m.group(2))
            basis = 'date of the act WIPO Lex names for this text (no entry-into-force day stated)'
        else:
            st['status'] = 'held: no date'
            continue
        title_tg = tg_title(r) or r['title']
        clean = re.sub(r'\s*\((?:Қонуни|бо\s|\d|ҚҶТ).*$', '', title_tg, flags=re.I).strip()
        clean = re.split(r'\s+(?:Бо|бо)\s+(?:Фармоиши|фармоиши|Қарори|қарори)\s', clean)[0].strip()
        clean = re.sub(r'\s+аз\s+\d{1,2}\s+\S+\s+соли\s+\d{4}.*$', '', clean)
        slug = KNOWN.get(r['title'])
        if not slug:
            t2 = re.sub(r'^Қонуни Ҷумҳурии Тоҷикистон\s*', 'Қонуни ҶТ ', clean, flags=re.I)
            t2 = re.sub(r'^Қонуни конститутсионии Ҷумҳурии Тоҷикистон\s*', 'Қонуни Конститутсионии ҶТ ', t2, flags=re.I)
            slug = slugify(t2).replace('-jt-', '-').removesuffix('-jt')
            slug = re.sub(r'^qonuni-dar-bora-', 'qonuni-dar-borai-', slug)
        if not arts and slug not in held:
            units = {'matn': {'label': 'Матн', 'kind': 'text', 'text': '\n'.join(reflow(lines)) + '\n'}}
        elif not arts:
            st['status'] = 'held: no articles found'
            continue
        v = {'from': d, 'source_url': f'https://www.wipo.int/wipolex/en/legislation/details/{r["id"]}',
             'sha256': hashlib.sha256(raw).hexdigest(), 'units': units, 'in_force_basis': basis,
             'source_status': f'secondary copy (WIPO Lex {r["wipo_no"]}, https://www.wipo.int/wipolex/en/legislation/details/{r["id"]})'}
        st['slug'], st['day'] = slug, d
        if slug in held:
            have = [x['from'] for x in held[slug]['versions']]
            if d in have:
                st['status'] = f'skipped: {slug} already holds a version on {d}'
                continue
            if d < max(have):
                st['status'] = f'held: older than the latest version held ({max(have)}); adding it needs a history rewrite'
                continue
            held[slug].setdefault('_new', []).append(dict(v, publisher=PUB))
            st['status'] = 'ok (newer version of a held act)'
            continue
        a = new.setdefault(slug, {'slug': slug, 'short': None, 'title': None,
                                  'url': f'https://www.wipo.int/wipolex/en/legislation/details/{r["id"]}',
                                  'first_law': None, 'earlier_laws': [], 'publisher': PUB, 'versions': []})
        full = re.sub(r'\bДар Бораи\b', 'Дар бораи', clean)
        short = re.sub(r'^Қонуни Ҷумҳурии Тоҷикистон\s*', 'Қонуни ҶТ ', full)
        short = re.sub(r'^Қонуни конститутсионии Ҷумҳурии Тоҷикистон\s*', 'Қонуни конститутсионии ҶТ ', short, flags=re.I)
        if short.count('"') % 2:
            short += '"'
        if len(short) > 70:
            short = short[:67].rstrip() + '...'
        a['short'], a['title'] = a['short'] or short, a['title'] or full
        if any(x['from'] == d for x in a['versions']):
            st['status'] = f'skipped: second WIPO text on {d}'
            continue
        a['versions'].append(v)
        st['status'] = 'ok (new act)'
    added = 0
    for a in held.values():
        for v in sorted(a.pop('_new', []), key=lambda v: v['from']):
            a['versions'].append(v)
            added += 1
    for a in new.values():
        a['versions'].sort(key=lambda v: v['from'])
        added += len(a['versions'])
    c['acts'] = sorted(list(held.values()) + list(new.values()), key=lambda a: (a['slug'] != 'konstitutsiya', a['slug']))
    c['sources'] = [s for s in c['sources'] if 'wipo.int' not in s['url']]
    c['sources'].append({'name': 'WIPO Lex (World Intellectual Property Organization), secondary copies',
                         'url': 'https://www.wipo.int/wipolex/en/members/profile/TJ', 'retrieved': TODAY,
                         'requests': len(recs) * 2 + 1,
                         'licence': 'Official texts (not objects of copyright, Law on Copyright of 13.11.1998, art. 7); WIPO Lex terms of use',
                         'notes': 'Tajik PDFs with a text layer: consolidated codes and laws; tagged Source-status: secondary copy'})
    dec = [x for x in c['decisions'] if 'WIPO Lex' not in x]
    dec += ['WIPO Lex Tajik PDFs (secondary copies, Source-status trailer): text layer only, read like the andoz.tj PDFs. '
            'A WIPO version is dated by the date of the last amending law WIPO Lex names for it (In-force-basis trailer), '
            'or by the entry-into-force / adoption day it gives for an unamended text. Official versions win; WIPO '
            'versions older than the latest version already published are held, since adding them would need a history rewrite.']
    c['decisions'] = dec
    (D / 'parsed.json').write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp = cp.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, cp)
    print(Counter(s.get('status', '?').split(':')[0].split(' (')[0] for s in status), 'versions added', added)
    for s in status:
        print(s['wipo_no'], s.get('status'), s.get('slug', ''), s.get('day', ''), s.get('articles', ''))


if __name__ == '__main__':
    main()
