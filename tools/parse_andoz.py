"""Tajikistan: read the andoz.tj PDFs (text layer only, no OCR) and add their acts to corpus.json.

Input: .cache/andoz/index.json + .cache/andoz/pdf/*.pdf (fetch_andoz.py). Output: corpus.json (atomic), and
.cache/andoz/parsed.json (per-PDF status) for review.
Two legacy Tajik font encodings occur in these PDFs; each document's encoding is detected from how it spells
ҶУМҲУРИИ and mapped back to standard Tajik letters (an encoding fix, not a change of words).
"""
import datetime as dt, hashlib, json, os, re, sys, unicodedata
from collections import Counter
from pathlib import Path

import pymupdf

HERE = Path(__file__).parent
D = HERE / '.cache' / 'andoz'
TODAY = '2026-11-26'
PUB = {'name': 'Кумитаи андози назди Ҳукумати Ҷумҳурии Тоҷикистон (andoz.tj)', 'email': 'publisher@andoz.invalid'}

# A: ЉУМЊУРИИ (Љ=Ҷ Њ=Ҳ Ќ=Қ Ї=Ӣ Ѓ=Ғ Ў=Ӯ);  B: ЇУМІУРИИ (Ї=Ҷ І=Ҳ Ѕ=Қ Њ=Ӣ Љ=Ғ Ў=Ӯ)
MAP_A = str.maketrans({'Љ': 'Ҷ', 'љ': 'ҷ', 'Њ': 'Ҳ', 'њ': 'ҳ', 'Ќ': 'Қ', 'ќ': 'қ', 'Ї': 'Ӣ', 'ї': 'ӣ',
                       'Ѓ': 'Ғ', 'ѓ': 'ғ', 'Ў': 'Ӯ', 'ў': 'ӯ'})
MAP_B = str.maketrans({'Ї': 'Ҷ', 'ї': 'ҷ', 'І': 'Ҳ', 'і': 'ҳ', 'Ѕ': 'Қ', 'ѕ': 'қ', 'Њ': 'Ӣ', 'њ': 'ӣ',
                       'Љ': 'Ғ', 'љ': 'ғ', 'Ў': 'Ӯ', 'ў': 'ӯ'})
MAP_STD = str.maketrans({'Ў': 'Ӯ', 'ў': 'ӯ'})

LAT = str.maketrans({'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'ғ': 'gh', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
                     'з': 'z', 'и': 'i', 'ӣ': 'i', 'й': 'y', 'к': 'k', 'қ': 'q', 'л': 'l', 'м': 'm', 'н': 'n',
                     'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ӯ': 'u', 'ф': 'f', 'х': 'kh',
                     'ҳ': 'h', 'ц': 'ts', 'ч': 'ch', 'ҷ': 'j', 'ш': 'sh', 'щ': 'sh', 'ъ': '', 'ы': 'y', 'ь': '',
                     'э': 'e', 'ю': 'yu', 'я': 'ya'})
MONTHS = {'январи': 1, 'феврали': 2, 'марти': 3, 'апрели': 4, 'майи': 5, 'июни': 6, 'июли': 7, 'августи': 8,
          'сентябри': 9, 'октябри': 10, 'ноябри': 11, 'декабри': 12}


def fix_encoding(t):
    if re.search(r'[ЇI]УМ[ІI]УР|[Її]ум[іi]ур', t[:20000]) or t[:20000].count('Ѕ') + t[:20000].count('ѕ') > 5:
        return t.translate(MAP_B), 'B'
    if re.search(r'ЉУМЊУР|Љумњур', t[:20000]) or t[:20000].count('Ќ') + t[:20000].count('ќ') > 5:
        return t.translate(MAP_A), 'A'
    return t.translate(MAP_STD), 'std'


def page_lines(doc):
    pages = [[l.strip() for l in p.get_text().split('\n')] for p in doc]
    # running headers/footers: a line that repeats on more than a third of the pages (and is short)
    cnt = Counter(l for ls in pages for l in set(ls) if l and len(l) < 120)
    rep = {l for l, n in cnt.items() if len(pages) >= 6 and n > len(pages) / 3 and not l.startswith('Моддаи')}
    out = []
    for ls in pages:
        for l in ls:
            if not l or l in rep or re.fullmatch(r'[-–—\s]*\d{1,4}[-–—\s]*', l):
                continue
            out.append(l)
    return out


HEAD = re.compile(r'^(?:ҚИСМИ|ФАСЛИ|БОБИ|Боби|Фасли|ЗЕРФАСЛИ|ЗЕРБОБИ)\s+[\dIVXLC]+(?:\(\d+\))?\.?(?:\s|$)')
ART = re.compile(r'^Моддаи\s+(\d+)(?:\s*\((\d+)\)|[.\-](\d+)(?=\.))?\s*\.?\s*(.*)$')


def reflow(lines):
    """Join PDF lines into paragraphs: a line continues the one before unless that one ended a sentence or this
    one opens an article, a heading or a numbered item."""
    paras = []
    for l in lines:
        l = re.sub(r'\s+', ' ', l.replace('\xa0', ' ').replace('­', '')).strip()
        new = (not paras or ART.match(l) or HEAD.match(l)
               or re.match(r'^(\d+(\.\d+)*[.)]|[а-яӣӯғқҳҷ]\)|[-–—•])\s', l)
               or re.search(r'[.:;!?»"]$', paras[-1]) or HEAD.match(paras[-1]) or ART.match(paras[-1]))
        if new:
            paras.append(l)
        elif paras[-1].endswith('-') and not paras[-1].endswith(' -'):
            paras[-1] = paras[-1][:-1] + l
        else:
            paras[-1] += ' ' + l
    return paras


def units_of(paras):
    units, order, pending = {}, [], []
    key, cur = 'preamble', []
    labels = {'preamble': ('Муқаддима', 'preamble')}

    def flush():
        if cur:
            if key in units:
                units[key] += cur
            else:
                units[key] = cur[:]
                order.append(key)

    for p in paras:
        m = ART.match(p)
        if m:
            n, sub = int(m.group(1)), m.group(2) or m.group(3)
            k = f'art-{n:03d}' + (f'-{int(sub)}' if sub else '')
            if k not in units and k != key:
                flush()
                key = k
                cur = pending + [p]
                pending = []
                labels[k] = (f'Моддаи {n}' + (f'({sub})' if sub else ''), 'art')
                continue
        if HEAD.match(p) and len(p) < 200 and key != 'preamble':
            pending.append(p)
            continue
        if pending:
            cur += pending
            pending = []
        cur.append(p)
    cur += pending
    flush()
    return {k: {'label': labels[k][0], 'kind': labels[k][1], 'text': '\n'.join(units[k]) + '\n'} for k in order}


def dates_in(t):
    out = []
    for d, m, y in re.findall(r'(?<!\d)(\d{1,2})\.(\d{1,2})\.((?:19|20)\d\d)(?!\d)', t):
        try:
            out.append(dt.date(int(y), int(m), int(d)).isoformat())
        except ValueError:
            pass
    for d, mn, y in re.findall(r'(?<!\d)(\d{1,2})\s+([а-яӣӯ]+)\s+(?:соли\s+)?((?:19|20)\d\d)', t):
        if mn.lower() in MONTHS:
            try:
                out.append(dt.date(int(y), MONTHS[mn.lower()], int(d)).isoformat())
            except ValueError:
                pass
    return [x for x in out if '1991-01-01' <= x <= TODAY]


def slugify(title):
    t = title.lower().replace('ҷт', 'jt')
    t = re.sub(r'["«»“”„]', '', t)
    t = t.translate(LAT)
    t = re.sub(r'[^a-z0-9]+', '-', t).strip('-')
    return t[:80].rstrip('-')


TAX_LAW = re.compile(r'аз (\d\d)\.(\d\d)\.(\d{4}), №\s*([\d\s\-–]+)')
TAX_DAY = re.compile(r'\((\d\d)\.(\d\d)\.(\d{4})\)')


def main():
    idx = json.loads((D / 'index.json').read_text(encoding='utf-8'))
    status, acts = [], {}
    laws = {}
    for it in idx:
        f = D / 'pdf' / it['file']
        title = it['title']
        st = {'title': title, 'page': it['page'], 'file': it['file']}
        status.append(st)
        if not f.exists():
            st['status'] = 'not fetched'
            continue
        if it['page'] == 'TaxCode' and not title.startswith('Кодекси андози') or 'англисӣ' in title:
            st['status'] = 'skipped (not a Tajik code text)'
            continue
        if it['page'] in ('Constitution', 'Decrees') or title.startswith(('Фарҳанг', 'Замимаи', 'Аз рӯйхати', 'Андозсупорандагони')):
            st['status'] = 'skipped (not an act, or Constitution already held)'
            continue
        raw = f.read_bytes()
        doc = pymupdf.open(stream=raw, filetype='pdf')
        lines = page_lines(doc)
        text = '\n'.join(lines)
        if len(text) < 500:
            st['status'] = 'no text layer (held: no OCR)'
            continue
        text, enc = fix_encoding(text)
        lines = text.split('\n')
        units = units_of(reflow(lines))
        arts = [k for k in units if k.startswith('art-')]
        st.update(encoding=enc, units=len(units), articles=len(arts))
        basis = None
        law_key = None
        if it['page'] == 'TaxCode':
            m = TAX_LAW.search(title)
            m2 = TAX_DAY.search(title)
            if m:
                day = f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
                no = re.sub(r'\s+', '', m.group(4))
                law_key = f'qonun-{day}-{no}'
                laws[law_key] = {'label': f'Қонуни ҶТ аз {m.group(1)}.{m.group(2)}.{m.group(3)} №{no}',
                                 'title': 'Дар бораи ворид намудани тағйиру иловаҳо ба Кодекси андози Ҷумҳурии Тоҷикистон',
                                 'kind': 'law', 'enacted': day, 'published': None, 'url': None, 'temporary_until': None,
                                 'restores': None, 'note': None}
                basis = (f'date of the amending law the publisher names for this edition (№{no} of {day}); '
                         'the day it took effect is not stated with the text')
            elif m2:
                day = f'{m2.group(3)}-{m2.group(2)}-{m2.group(1)}'
                basis = f'the date the publisher gives for this edition ({m2.group(1)}.{m2.group(2)}.{m2.group(3)})'
            else:
                st['status'] = 'held: no date'
                continue
            head = text[:3000]
            if day >= '2022-01-01':
                slug, short, full = 'kodeksi-andoz', 'Кодекси андоз', 'Кодекси андози Ҷумҳурии Тоҷикистон'
            elif day >= '2012-09-01':
                slug, short, full = 'kodeksi-andoz-2012', 'Кодекси андоз (2012)', 'Кодекси андози Ҷумҳурии Тоҷикистон (2012)'
            else:
                slug, short, full = 'kodeksi-andoz-2004', 'Кодекси андоз (2004)', 'Кодекси андози Ҷумҳурии Тоҷикистон (2004)'
        else:
            ds = dates_in(title) if it['page'] == 'Resolutions' else []
            ds = ds or dates_in(text[:4000])
            # amendment notes anywhere in the text ("Қонуни ҶТ аз 23.11.2015 № 1223", "ҚҶТ аз ...") name the laws
            # the publisher consolidated; the latest of them is the edition's date
            ds += [x for x in dates_in(' '.join(re.findall(r'\((?:Қонуни ҶТ|ҚҶТ|Қонуни Ҷумҳурии Тоҷикистон)\s+аз\s+[^,;)№]{6,30}', text)))]
            if not ds:
                st['status'] = 'held: no date in the text'
                continue
            day = max(ds)
            basis = ('latest date the text names in its heading or amendment list (the last amending law the '
                     'publisher consolidated); the publisher gives no in-force day for this edition')
            full = re.sub(r'^Қонуни ҶТ', 'Қонуни Ҷумҳурии Тоҷикистон', title)
            full = re.sub(r'^Қонуни Конститутсионии ҶТ', 'Қонуни конститутсионии Ҷумҳурии Тоҷикистон', full)
            full = re.sub(r' ҶТ\b', ' Ҷумҳурии Тоҷикистон', full)
            short = title.replace('Қонуни ҶТ ', 'Қонун ').replace('Қонуни Конститутсионии ҶТ ', 'Қонуни конститутсионӣ ')
            short = short.replace('"Дар бораи ', '"')
            if len(short) > 70:
                short = short[:67].rstrip() + '...'
            slug = slugify(title).replace('-jt-', '-').removesuffix('-jt')
            if 'кодекси ҷиноятии' in title.lower() and len(arts) > 200:
                # The two "amending law" PDFs (№1661, №1662) carry the whole Criminal Code as amended to 2.01.2020
                slug, short, full = 'kodeksi-jinoyati', 'Кодекси ҷиноятӣ', 'Кодекси ҷиноятии Ҷумҳурии Тоҷикистон'
            elif 'кодекси ҳуқуқвайронкунии маъмури' in title.lower():
                slug, short, full = ('kodeksi-huquqvayronkunii-mamuri', 'Кодекси ҳуқуқвайронкунии маъмурӣ',
                                     'Кодекси ҳуқуқвайронкунии маъмурии Ҷумҳурии Тоҷикистон')
            elif title.startswith('Кодекси'):
                short = re.sub(r' ҶТ.*$', '', title)
            if it['page'] == 'Resolutions':
                slug = 'qarori-hukumat-' + slugify(title.replace('Қарори', ''))
        if len(arts) < 1:
            if it['page'] != 'Resolutions':
                st['status'] = 'held: no articles found'
                continue
            # a government resolution has numbered points, not articles: the whole text is one file
            units = {'matn': {'label': 'Матн', 'kind': 'text', 'text': chr(10).join(reflow(lines)) + chr(10)}}
        st['status'] = 'ok'
        st['slug'], st['day'] = slug, day
        v = {'from': day, 'source_url': it['url'], 'sha256': hashlib.sha256(raw).hexdigest(), 'units': units,
             'in_force_basis': basis}
        if law_key:
            v['_law'] = law_key
        a = acts.setdefault(slug, {'slug': slug, 'short': short, 'title': full, 'url': f'https://andoz.tj/Legislation/{it["page"]}',
                                   'first_law': None, 'earlier_laws': [], 'publisher': PUB, 'versions': []})
        if any(x['from'] == day for x in a['versions']):
            st['status'] = f'held: second edition on {day}'
            continue
        a['versions'].append(v)
    # order versions, credit word changes to the amending law where the publisher names one
    for a in acts.values():
        a['versions'].sort(key=lambda v: v['from'])
        for i, v in enumerate(a['versions']):
            lk = v.pop('_law', None)
            if i and lk:
                prev = a['versions'][i - 1]['units']
                v['credits'] = {k: [lk] for k in sorted(set(prev) | set(v['units']))
                                if (prev.get(k) or {}).get('text') != (v['units'].get(k) or {}).get('text')}
    (D / 'parsed.json').write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding='utf-8')
    cp = HERE / 'corpus.json'
    c = json.loads(cp.read_text(encoding='utf-8'))
    c['acts'] = [x for x in c['acts'] if x['slug'] == 'konstitutsiya'] + sorted(acts.values(), key=lambda x: x['slug'])
    used = {l for a in acts.values() for v in a['versions'] for ls in v.get('credits', {}).values() for l in ls}
    for k in list(c['laws']):
        if k.startswith('qonun-'):
            del c['laws'][k]
    for k in used:
        c['laws'][k] = laws[k]
    c['sources'] = [s for s in c['sources'] if 'andoz.tj' not in s['url']]
    c['sources'].append({'name': 'Кумитаи андози назди Ҳукумати Ҷумҳурии Тоҷикистон (andoz.tj)',
                         'url': 'https://andoz.tj/Legislation/', 'retrieved': TODAY,
                         'requests': len(idx) + 6, 'licence': 'Official texts (not objects of copyright, Law on Copyright of 13.11.1998, art. 7)',
                         'notes': 'PDFs with a text layer: Tax Code editions 2010-2025, other codes, laws, government resolutions; Tajik'})
    dec = [d for d in c['decisions'] if 'andoz.tj' not in d]
    dec += ['andoz.tj PDFs: text layer only (no OCR). Two legacy Tajik font encodings are mapped back to standard letters per document; running headers and page numbers are dropped; PDF lines are joined into paragraphs. Chapter and section headings go into the file of the article that follows them.',
            'andoz.tj acts other than the Tax Code are single consolidated editions, dated by the latest date their heading or amendment list names (In-force-basis trailer); they are "oldest version available" commits credited to the publisher.',
            'andoz.tj Tax Code: three acts (2004 code, 2012 code, 2021 code in force from 2022-01-01); each listed edition is a version, dated by the date the publisher gives; editions named after an amending law are credited to that law, the rest to the publisher.']
    c['decisions'] = dec
    tmp = cp.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, cp)
    print(Counter(s['status'].split(':')[0] for s in status))
    for s in status:
        if s['status'] == 'ok':
            print(s['day'], s['slug'][:60], s['articles'], s['encoding'])
        else:
            print('  --', s['status'], '|', s['title'][:70])


if __name__ == '__main__':
    main()
