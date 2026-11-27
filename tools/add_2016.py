"""Tajikistan: add the 2016 edition of the Constitution (amendments of the referendum of 22 May 2016) to corpus.json.

Source: the President's site, https://president.tj/ (its API https://api.president.tj/api/constitution_special,
saved in .cache/pres/cs_tj.json). The page names the referendums of 26.09.1999, 22.06.2003 and 22.05.2016.
Reads only the cache; writes corpus.json atomically.
"""
import hashlib, html, json, os, re, sys
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / '.cache' / 'pres' / 'cs_tj.json'
API = 'https://api.president.tj/api/constitution_special'
PAGE = 'https://president.tj/constitution'

ORD = {'якум': 1, 'дуюм': 2, 'сеюм': 3, 'чорум': 4, 'чаҳорум': 4, 'панҷум': 5, 'шашум': 6, 'ҳафтум': 7,
       'ҳаштум': 8, 'нӯҳум': 9, 'нуҳум': 9, 'даҳум': 10}


def norm(s):
    s = s.replace('\xa0', ' ').replace('ў', 'ӯ').replace('Ў', 'Ӯ')
    s = re.sub(r'[ \t]+', ' ', s).strip()
    s = re.sub(r'\s+([,.;:])', r'\1', s)
    return s


def lines_of(raw_html):
    h = re.sub(r'(?i)<br\s*/?>|</p>|<p[^>]*>|</h\d>|<h\d[^>]*>|</div>|<div[^>]*>|</li>|<li[^>]*>', '\n', raw_html)
    h = re.sub(r'<[^>]+>', '', h)
    h = html.unescape(h)
    return [l for l in (norm(x) for x in h.split('\n')) if l]


def main():
    raw = SRC.read_bytes()
    d = json.loads(raw)['data']
    ls = lines_of(d['text'])
    start = next(i for i, l in enumerate(ls) if l.startswith('МО, ХАЛҚИ ТОҶИКИСТОН'))
    units, order, cur, key = {}, [], [], 'preamble'
    meta = {'preamble': ('Муқаддима', 'preamble')}

    def flush():
        if key in units:
            raise SystemExit(f'duplicate unit {key}')
        units[key] = cur[:]
        order.append(key)

    i = start
    while i < len(ls):
        l = ls[i]
        m_art = re.match(r'^Моддаи (\d+)\.?\s*(.*)$', l)
        m_bob = re.match(r'^Боби\s+(\S+)$', l)
        if m_art:
            flush()
            n = int(m_art.group(1))
            key, cur = f'art-{n:03d}', [f'Моддаи {n}.']
            meta[key] = (f'Моддаи {n}', 'art')
            if m_art.group(2):
                cur.append(m_art.group(2))
        elif m_bob:
            flush()
            n = ORD[m_bob.group(1).lower()]
            key, cur = f'bob-{n:02d}', [l]
            meta[key] = (l, 'chapter')
        elif l.startswith('Муқаррароти интиқолӣ'):
            flush()
            key, cur = 'muqarraroti-intiqoli', [l]
            meta[key] = ('Муқаррароти интиқолӣ', 'section')
        else:
            cur.append(l)
        i += 1
    flush()
    # The source breaks some words of chapter headings over lines (КОНСТИТУТСИОН / Ӣ): rejoin single letters
    # and word pieces into the heading lines, as the 2003 edition prints them.
    for k in [k for k in units if k.startswith('bob-')]:
        head, rest = units[k][0], units[k][1:]
        title = ' '.join(rest)
        title = re.sub(r'\s+(?=[ӢҒҲҚҶӮ]\b)', '', title)
        units[k] = [head, title]
    for k in [k for k in units if k.startswith('art-')]:
        if len(units[k]) < 2:
            raise SystemExit(f'empty {k}')
    pre = units['preamble']
    units['preamble'] = [pre[0], ' '.join(pre[1:-1]), pre[-1]]
    arts = [k for k in units if k.startswith('art-')]
    bobs = [k for k in units if k.startswith('bob-')]
    assert len(arts) == 100 and arts == [f'art-{n:03d}' for n in range(1, 101)], arts[:5]
    assert len(bobs) == 10, bobs
    out = {k: {'label': meta[k][0], 'kind': meta[k][1], 'text': '\n'.join(units[k]) + '\n'} for k in order}
    return out, hashlib.sha256(raw).hexdigest()


if __name__ == '__main__':
    units, sha = main()
    cp = HERE / 'corpus.json'
    c = json.loads(cp.read_text(encoding='utf-8'))
    c['laws']['raypursi-2003-06-22'] = c['laws'].get('raypursi-2003-06-22') or {
        'label': 'Раъйпурсии 22.06.2003', 'title': 'Constitutional amendments by national referendum', 'kind': 'referendum',
        'enacted': '2003-06-22', 'published': None, 'url': None, 'temporary_until': None, 'restores': None, 'note': None}
    c['laws']['raypursi-2016-05-22'] = {
        'label': 'Раъйпурсии 22.05.2016', 'title': 'Тағйиру иловаҳо ба Конститутсияи Ҷумҳурии Тоҷикистон: '
        'constitutional amendments adopted by national referendum on 22 May 2016', 'kind': 'referendum',
        'enacted': '2016-05-22', 'published': None, 'url': PAGE, 'temporary_until': None, 'restores': None,
        'note': 'Approved by a popular vote on 22 May 2016. Under the Transitional provisions the amendments take effect '
                'on their official publication after the result is announced; that day was not found at a source '
                'reachable from here, so this version is dated by the referendum day, the rule this repository '
                'already uses for the 2003 edition.'}
    act = c['acts'][0]
    act['versions'] = [v for v in act['versions'] if v['from'] != '2016-05-22']
    prev = act['versions'][-1]['units']
    # Where the two editions differ only in line breaks, spaces, punctuation or letter case, keep the earlier
    # text: the referendum did not change those words, and crediting it would be wrong.
    flat = lambda t: re.sub(r'[\s.,;:«»"]', '', t).lower()
    same = [k for k in units if k in prev and flat(prev[k]['text']) == flat(units[k]['text'])]
    for k in same:
        units[k] = prev[k]
    print('layout-only differences kept as 2003:', [k for k in same if True])
    credits = {k: ['raypursi-2016-05-22'] for k in sorted(set(prev) | set(units))
               if (prev.get(k) or {}).get('text') != (units.get(k) or {}).get('text')}
    act['versions'].append({'from': '2016-05-22', 'source_url': API, 'sha256': sha, 'units': units,
                            'credits': credits})
    print('changed', len(credits), sorted(credits))
    c['sources'] = [s for s in c['sources'] if 'president.tj' not in s['url']]
    c['sources'].append({'name': 'Президенти Ҷумҳурии Тоҷикистон (president.tj)', 'url': PAGE, 'retrieved': '2026-11-26',
                         'requests': 1, 'licence': 'Official text of the Constitution (an official act; not subject to copyright)',
                         'notes': 'current edition with the amendments of 26.09.1999, 22.06.2003 and 22.05.2016; Tajik; '
                                  'read live from the site API ' + API})
    tmp = cp.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, cp)
    print('units', len(units), 'sha', sha)
