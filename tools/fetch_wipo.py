"""Fetch WIPO Lex Tajikistan records (latest + every superseded/historical version) and their PDFs.

Writes .cache/wipo/records.json: {details_id: {wipo_no, title, amended_up_to, entry_into_force, adopted,
texts: [{lang, title, url}], links: [details ids]}} and PDFs to .cache/wipo/pdf/<file>.
One request in flight, ~1 s apart; stops at the first 403/429 or challenge page.
"""
import html, json, re, sys, time
from pathlib import Path

import requests

HERE = Path(__file__).parent
D = HERE / '.cache' / 'wipo'
PDF = D / 'pdf'
PDF.mkdir(parents=True, exist_ok=True)
BASE = 'https://www.wipo.int'
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0 (Lexifina legal record)'
LOG = D / 'progress.log'


def log(m):
    with LOG.open('a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + m + '\n')


def get(url, binary=False):
    import subprocess, tempfile
    for i in range(4):
        time.sleep(1.0)
        out = Path(tempfile.mktemp(dir=D, suffix='.part'))
        r = subprocess.run([r'C:\Windows\System32\curl.exe', '-s', '-L', '-m', '300', '-A', 'Mozilla/5.0 (Lexifina legal record)',
                            '-o', str(out), '-w', '%{http_code}', url], capture_output=True, text=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        code = r.stdout.strip()
        b = out.read_bytes() if out.exists() else b''
        out.unlink(missing_ok=True)
        if code in ('403', '429') or b'cf-chl' in b[:5000]:
            log(f'STOP {code} {url}')
            raise SystemExit(f'stopped: {code} {url}')
        if code == '200':
            return b if binary else b.decode('utf-8', 'replace')
        log(f'retry {code} {url}')
        time.sleep(10 * 2 ** i)
    return None


def txt(s):
    s = re.sub(r'<script.*?</script>', ' ', s, flags=re.S)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', s)).split())


def details(i):
    cache = D / f'details-{i}.html'
    if cache.exists():
        s = cache.read_text(encoding='utf-8')
    else:
        s = get(f'{BASE}/wipolex/en/legislation/details/{i}')
        if s is None:
            return None
        cache.write_text(s, encoding='utf-8')
    t = txt(s)
    rec = {'id': i}
    m = re.search(r'WIPO Lex No\.\s*(TJ\d+)', t)
    rec['wipo_no'] = m.group(1) if m else None
    m = re.search(r'Browse By Jurisdiction (.*?), Tajikistan(?: \((.*?)\))? Back', t)
    rec['title'] = m.group(1) if m else None
    rec['subtitle'] = m.group(2) if m and m.group(2) else None
    for k, lab in (('amended_up_to', 'Amended up to:'), ('entry_into_force', 'Entry into force:'),
                   ('adopted', 'Adopted:'), ('year', 'Year of Version')):
        m = re.search(re.escape(lab) + r'\s*([A-Z][a-z]+ \d{1,2}, \d{4}|\d{4})', t)
        rec[k] = m.group(1) if m else None
    # main texts: language label then title, then PDF links in the same order
    pdfs = []
    for u in re.findall(r'href="(https://wipolex-res\.wipo\.int/edocs/lexdocs/laws/[^"?]+\.pdf)', s):
        if u not in pdfs:
            pdfs.append(u)
    rec['pdfs'] = pdfs
    m = re.search(r'Main text\(s\) Main text\(s\) (.*?) Open PDF', t)
    rec['main_texts'] = m.group(1) if m else None
    rec['links'] = sorted(set(re.findall(r'/wipolex/en/legislation/details/(\d+)', s)) - {str(i)})
    m = re.search(r'(Supersedes|Historical Versions|Superseded by|Repeals|Amends|Amended by)', t)
    rel = {}
    for blk in re.finditer(r'(Supersedes|Superseded by|Repeals|Repealed by|Amends|Amended by|Historical Versions|Implements|Implemented by|Related Legislation)\s*\((\d+) text', t):
        rel[blk.group(1)] = int(blk.group(2))
    rec['relations'] = rel
    return rec


def main():
    prof = D / 'profile.html'
    if not prof.exists():
        prof.write_text(get(f'{BASE}/wipolex/en/members/profile/TJ'), encoding='utf-8')
    seeds = sorted(set(re.findall(r'/wipolex/en/legislation/details/(\d+)', prof.read_text(encoding='utf-8'))))
    recs, todo, seen = {}, list(seeds), set()
    rp = D / 'records.json'
    while todo:
        i = todo.pop(0)
        if i in seen:
            continue
        seen.add(i)
        r = details(i)
        if not r:
            continue
        if r['wipo_no'] is None or not r['wipo_no'].startswith('TJ'):
            continue
        recs[i] = r
        todo += [x for x in r['links'] if x not in seen]
        log(f'{i} {r["wipo_no"]} {r["title"]} | {r["subtitle"]}')
    rp.write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f'records {len(recs)}')
    if '--no-pdf' in sys.argv:
        return
    # PDF links are signed and expire within minutes: read each record's page afresh, then fetch its Tajik PDF
    order = sorted(recs.values(), key=lambda r: (not re.search(r'Code|Constitution', r['title'] or ''),
                                                  bool(re.match(r'Law on (Amendments|Additions)', r['title'] or '')), r['wipo_no']), reverse=False)
    for r in order:
        if re.match(r'Law on (Amendments|Additions)', r['title'] or '') or r['relations'].get('Amends'):
            continue
        want = [u for u in r['pdfs'] if '/laws/tg/' in u]
        want = [u for u in want if not ((PDF / u.rsplit('/', 1)[1]).exists() and (PDF / u.rsplit('/', 1)[1]).stat().st_size > 1000)]
        if not want:
            continue
        s = get(f"{BASE}/wipolex/en/legislation/details/{r['id']}")
        if not s:
            continue
        signed = {}
        for h in re.findall(r'href="(https://wipolex-res\.wipo\.int/edocs/lexdocs/laws/[^"]+\.pdf\?[^"]+)"', s):
            h = html.unescape(h)
            signed.setdefault(h.split('?')[0], h)
        for u in want:
            out = PDF / u.rsplit('/', 1)[1]
            if u not in signed:
                log(f'no signed link {u}')
                continue
            b = get(signed[u], binary=True)
            if b and b[:5] == b'%PDF-':
                out.write_bytes(b)
                log(f'pdf {out.name} {len(b)}')
            else:
                log(f'not a PDF {u}')
    log('DONE')


if __name__ == '__main__':
    main()
