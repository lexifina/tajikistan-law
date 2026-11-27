"""Fetch andoz.tj legislation listings and their PDFs into .cache/andoz/ (3 in flight, back off on 429/5xx).

Writes .cache/andoz/index.json: [{page, href, url, title, file}] and progress to .cache/andoz/progress.log.
Stops the host at the first 403 or challenge page.
"""
import concurrent.futures as cf, hashlib, html, json, re, subprocess, sys, time, urllib.parse
from pathlib import Path

HERE = Path(__file__).parent
D = HERE / '.cache' / 'andoz'
PDF = D / 'pdf'
PDF.mkdir(parents=True, exist_ok=True)
CURL = r'C:\Windows\System32\curl.exe'
BASE = 'https://andoz.tj/Legislation/'
PAGES = sys.argv[1:] or ['TaxCode', 'OtherCodes', 'Laws', 'Constitution', 'Decrees', 'Resolutions']
LOG = D / 'progress.log'
STOP = False


def log(m):
    with LOG.open('a', encoding='utf-8') as f:
        f.write(time.strftime('%H:%M:%S ') + m + '\n')


def get(url, out, tries=5):
    global STOP
    for i in range(tries):
        if STOP:
            return None
        r = subprocess.run([CURL, '-s', '-m', '600', '-A', 'Mozilla/5.0 (Lexifina legal record)', '-o', str(out),
                            '-w', '%{http_code}', url], capture_output=True, text=True,
                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        code = r.stdout.strip()
        if code == '200':
            return code
        if code == '403':
            STOP = True
            log(f'STOP 403 {url}')
            return code
        if code == '404':
            return code
        log(f'retry {code} {url}')
        time.sleep(10 * 2 ** i)
    return code


def listing(page):
    out = D / f'{page}.html'
    if not out.exists() or out.stat().st_size < 1000:
        get(BASE + page, out)
    s = out.read_text(encoding='utf-8', errors='replace')
    items = []
    for h, t in re.findall(r'href="([^"]+\.pdf)"[^>]*>(.{0,400}?)</a>', s, re.S | re.I):
        h = html.unescape(h).replace('\\', '/')
        t = ' '.join(re.sub(r'<[^>]+>', ' ', html.unescape(t)).split())
        url = urllib.parse.urljoin(BASE + page, urllib.parse.quote(h, safe='/:.%-_()'))
        items.append({'page': page, 'href': h, 'url': url, 'title': t})
    return items


def main():
    allitems, seen = [], set()
    for p in PAGES:
        for it in listing(p):
            if it['url'] in seen or '/doljniki/' in it['href'] or '/savolho/' in it['href']:
                continue
            seen.add(it['url'])
            it['file'] = hashlib.sha256(it['url'].encode()).hexdigest()[:20] + '.pdf'
            allitems.append(it)
    (D / 'index.json').write_text(json.dumps(allitems, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f'{len(allitems)} PDFs listed on {PAGES}')

    def one(it):
        out = PDF / it['file']
        if out.exists() and out.stat().st_size > 1000:
            return 'cached'
        tmp = out.with_suffix('.part')
        code = get(it['url'], tmp)
        if code == '200':
            tmp.replace(out)
        it['status'] = code
        log(f'{code} {it["title"][:80]}')
        return code

    with cf.ThreadPoolExecutor(3) as ex:
        res = list(ex.map(one, allitems))
    (D / 'index.json').write_text(json.dumps(allitems, ensure_ascii=False, indent=1), encoding='utf-8')
    log(f'DONE {sum(r in ("200", "cached") for r in res)}/{len(res)}')


if __name__ == '__main__':
    main()
