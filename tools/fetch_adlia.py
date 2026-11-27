"""Tajikistan: fetch every record of the Ministry of Justice public register (portali-huquqi.tj/publicadliya).

usage: python fetch_adlia.py [tj|ru] [first_id] [last_id] [--only ids.txt]
Each record page (view_qonunhoview.php?asosi_id=N&language=..) holds the current edition's text, the reference card
(number, adoption day, status, start of action, current edition and the act that made it, publication) and links.
Saved as .cache/adlia/<lang>/<N>.html.gz (only the record's tab content). Pace: starts with 1 request in flight about
1 s apart, steps up by one (max 5) after 10 clean minutes, drops to 1 at the first timeout or 5xx.
Log: .cache/adlia/progress.log
"""
import gzip, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

HERE = Path(__file__).parent
D = HERE / '.cache' / 'adlia'
BASE = 'http://portali-huquqi.tj/publicadliya/view_qonunhoview.php?showdetail=&asosi_id={}&language={}'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) lexifina-law-archive'

lock = threading.RLock()
state = {'cap': 1, 'clean_since': time.time(), 'inflight': 0, 'done': 0, 'fail': 0, 'last': 0.0}


def log(msg):
    with lock:
        with open(D / 'progress.log', 'a', encoding='utf-8') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + msg + '\n')


def slot():
    while True:
        with lock:
            now = time.time()
            if state['cap'] < 5 and now - state['clean_since'] > 600:
                state['cap'] += 1
                state['clean_since'] = now
                log(f'step up to {state["cap"]} in flight')
            gap = 1.0 / state['cap']
            if state['inflight'] < state['cap'] and now - state['last'] >= gap:
                state['inflight'] += 1
                state['last'] = now
                return
        time.sleep(0.1)


def release(bad):
    with lock:
        state['inflight'] -= 1
        if bad:
            state['fail'] += 1
            if state['cap'] > 1:
                log(f'drop to 1 in flight')
            state['cap'] = 1
            state['clean_since'] = time.time()


def one(sess, lang, i):
    out = D / lang / f'{i}.html.gz'
    if out.exists():
        return
    for attempt in range(6):
        slot()
        bad = False
        try:
            r = sess.get(BASE.format(i, lang), timeout=60)
            if r.status_code >= 500 or r.status_code == 429:
                bad = True
                raise IOError(f'HTTP {r.status_code}')
            if r.status_code == 403:
                log(f'{i}: HTTP 403, stopping')
                os._exit(3)
            html = r.content.decode('utf-8', 'replace')
            a = html.find('<div class="tab-content">')
            b = html.find('</form>', a)
            if a < 0 or b < 0:
                bad = True
                raise IOError('no record content')
            tmp = out.with_suffix('.tmp')
            with gzip.open(tmp, 'wt', encoding='utf-8') as f:
                f.write(html[a:b])
            os.replace(tmp, out)
            release(False)
            if lang == 'tj' and '--with-ru' in sys.argv:
                # no Tajik text: the register holds the Russian one only
                a1, b1 = html.find('id="tab_view_qonunho1"'), html.find('id="tab_view_qonunho2"')
                h1 = html.find('<h1>', b1)
                body = re.sub(r'<[^>]+>', '', html[a1:b1])
                if h1 < 0 or len(body.strip()) < 300:
                    one(sess, 'ru', i)
            with lock:
                state['done'] += 1
                if state['done'] % 200 == 0:
                    log(f'{lang} done {state["done"]} (at id {i}), cap {state["cap"]}, failures {state["fail"]}')
            return
        except Exception as e:  # noqa: BLE001
            release(True)
            log(f'{i}: {type(e).__name__} {str(e)[:120]} (attempt {attempt + 1})')
            time.sleep(10 * (attempt + 1))
    log(f'{i}: gave up')


def main():
    only_at = sys.argv.index('--only') + 1 if '--only' in sys.argv else -1
    args = [a for k, a in enumerate(sys.argv) if k and k != only_at and not a.startswith('--')]
    lang = args[0] if args else 'tj'
    lo = int(args[1]) if len(args) > 1 else 1
    hi = int(args[2]) if len(args) > 2 else 28228
    (D / lang).mkdir(parents=True, exist_ok=True)
    (D / 'ru').mkdir(parents=True, exist_ok=True)
    if '--only' in sys.argv:
        ids = [int(x) for x in Path(sys.argv[sys.argv.index('--only') + 1]).read_text().split()]
    else:
        ids = list(range(lo, hi + 1))
    ids = [i for i in ids if not (D / lang / f'{i}.html.gz').exists()]
    log(f'start {lang}: {len(ids)} records to fetch')
    sess = requests.Session()
    sess.headers['User-Agent'] = UA
    with ThreadPoolExecutor(5) as ex:
        list(ex.map(lambda i: one(sess, lang, i), ids))
    log(f'finished {lang}: done {state["done"]}, failures {state["fail"]}')


if __name__ == '__main__':
    main()
