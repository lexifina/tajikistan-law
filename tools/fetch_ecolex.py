"""Fetch ECOLEX's Tajikistan legislation records (FAOLEX data) and their FAOLEX PDFs.

.cache/ecolex/list-<n>.html, details/<slug>.html, records.json, pdf/<file>.pdf. One request in flight per host,
~1 s apart; stops a host at the first 403/429/challenge.
"""
import html, json, re, time, urllib.parse
from pathlib import Path

import requests

HERE = Path(__file__).parent
D = HERE / '.cache' / 'ecolex'
(D / 'details').mkdir(parents=True, exist_ok=True)
(D / 'pdf').mkdir(parents=True, exist_ok=True)
S = requests.Session()
S.headers['User-Agent'] = 'Mozilla/5.0 (Lexifina legal record)'
LOG = D / 'progress.log'
STOPPED = set()


def log(m):
    with LOG.open('a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + m + '\n')


def get(url, binary=False):
    import subprocess, tempfile
    host = urllib.parse.urlsplit(url).netloc
    if host in STOPPED:
        return None
    for i in range(4):
        time.sleep(1.0)
        out = Path(tempfile.mktemp(dir=D, suffix='.part'))
        r = subprocess.run([r'C:\Windows\System32\curl.exe', '-s', '-L', '-m', '300', '-A', 'Mozilla/5.0 (Lexifina legal record)',
                            '-o', str(out), '-w', '%{http_code}', url], capture_output=True, text=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        code = r.stdout.strip()
        b = out.read_bytes() if out.exists() else b''
        out.unlink(missing_ok=True)
        if code in ('403', '429') or b'challenge-platform' in b[:20000]:
            log(f'STOP host {host}: {code} {url}')
            STOPPED.add(host)
            return None
        if code == '200':
            return b if binary else b.decode('utf-8', 'replace')
        if code == '404':
            log(f'404 {url}')
            return None
        log(f'retry {code} {url}')
        time.sleep(10 * 2 ** i)
    return None


def txt(s):
    s = re.sub(r'<script.*?</script>', ' ', s, flags=re.S)
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', s)).split())


def main():
    links, n = [], 1
    while True:
        f = D / f'list-{n}.html'
        if not f.exists():
            s = get(f'https://www.ecolex.org/result/?q=&type=legislation&xcountry=Tajikistan&page={n}')
            if not s:
                break
            f.write_text(s, encoding='utf-8')
        s = f.read_text(encoding='utf-8')
        new = [h for h in re.findall(r'href="/details/legislation/([^/"]+)/', s) if h not in links]
        if not new:
            break
        links += new
        n += 1
    log(f'{len(links)} records listed')
    recs = []
    for slug in links:
        f = D / 'details' / f'{slug[:150]}.html'
        if not f.exists():
            s = get(f'https://www.ecolex.org/details/legislation/{slug}/')
            if not s:
                continue
            f.write_text(s, encoding='utf-8')
        s = f.read_text(encoding='utf-8')
        t = txt(s)
        rec = {'slug': slug, 'pdfs': sorted(set(re.findall(r'https://faolex\.fao\.org/docs/pdf/[^"\s]+\.pdf', s)))}
        m = re.search(r'Search results » Legislation (.*?) Country/Territory', t)
        rec['title'] = m.group(1) if m else None
        for k in ('Date', 'Document type', 'Source', 'Original title', 'Language', 'Entry into force notes',
                  'Repealed', 'Amended by', 'Implemented by', 'Consolidated version'):
            m = re.search(r'(?<![A-Za-z])' + re.escape(k) + r' (.{1,300}?) (?:Country/Territory|Document type|Source|Subject|Keyword|Geographical area|Entry into force notes|Abstract|Full text|Website|Date|Original title|Language|Reference|$)', t)
            if m:
                rec[k.lower().replace(' ', '_')] = m.group(1)
        rec['text'] = t[:6000]
        recs.append(rec)
    (D / 'records.json').write_text(json.dumps(recs, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f'records {len(recs)}')
    import concurrent.futures as cf

    def one(u):
        out = D / 'pdf' / u.rsplit('/', 1)[1]
        if out.exists() and out.stat().st_size > 1000:
            return
        b = get(u, binary=True)
        if b:
            out.write_bytes(b)
            log(f'pdf {out.name} {len(b)}')

    with cf.ThreadPoolExecutor(3) as ex:
        list(ex.map(one, [u for r in recs for u in r['pdfs']]))
    log('DONE')


if __name__ == '__main__':
    main()
