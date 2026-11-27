"""Build tajikistan-caselaw from constcourt.tj's decisions (WordPress API cache .cache/cc/qarorho_.json).

One file and one commit per decision text, dated 12:00 Asia/Dushanbe on the decision day, authored by the court.
Usage: python build_caselaw.py <repo dir>   (an initialised git repo; appends commits)
"""
import html, json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
SRCS = [(HERE / '.cache' / 'cc' / 'qarorho_.json', 'qarorho', 'postanovleniya'),
        (HERE / '.cache' / 'cc' / 'tainotho_.json', 'tainotho', 'opredeleniya')]
# protected subjects (family, children, sexual offences) are not published here
PROTECTED = re.compile(r'(?i)кодекси оила|семейн|ноболиғ|несовершеннолет|ҷиноятҳои ҷинсӣ|половой неприкосн|половых преступл|таҷовуз ба номус|изнасилов')
MONTHS = {  # Tajik genitive-ish forms and Russian genitive
    'январи': 1, 'феврали': 2, 'марти': 3, 'апрели': 4, 'майи': 5, 'июни': 6, 'июли': 7, 'августи': 8,
    'сентябри': 9, 'октябри': 10, 'ноябри': 11, 'декабри': 12,
    'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4, 'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
    'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12}
LEGACY = str.maketrans({'Њ': 'Ҳ', 'њ': 'ҳ', 'Ќ': 'Қ', 'ќ': 'қ', 'Ѓ': 'Ғ', 'ѓ': 'ғ', 'Ў': 'Ӯ', 'ў': 'ӯ',
                        'Ї': 'Ӣ', 'ї': 'ӣ', 'Љ': 'Ҷ', 'љ': 'ҷ'})


def text_of(h):
    h = re.sub(r'(?i)<br\s*/?>|</p>|</h\d>|</li>|</tr>|</div>', '\n', h)
    h = re.sub(r'<[^>]+>', '', h)
    h = html.unescape(h).replace('\xa0', ' ').replace('­', '')
    lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in h.split('\n')]
    out = '\n'.join(l for l in lines if l)
    return out


def decided(t):
    flat = ' '.join(t.split())
    flat = flat.replace('«', '').replace('»', '').replace('"', '')
    m = re.search(r'(?:Душанбе|г\. ?Душанбе|ш\. ?Душанбе)\s*,?\s+(\d{1,2})\s+([а-яӣӯ]+)\s+(?:соли\s+)?(\d{4})', flat)
    if not m:
        return None
    mo = MONTHS.get(m.group(2).lower())
    return f'{int(m.group(3)):04d}-{mo:02d}-{int(m.group(1)):02d}' if mo else None


def run(repo, *a, env=None, inp=None):
    return subprocess.run(['git', '-C', str(repo), *a], check=True, capture_output=True, text=True, env=env,
                          input=inp, encoding='utf-8').stdout


def main(repo):
    repo = Path(repo)
    items = []
    skipped = 0
    for src, tg_dir, ru_dir in SRCS:
      if not src.exists():
        continue
      for p in json.loads(src.read_text(encoding='utf-8')):
        t = text_of(p['content']['rendered'])
        title = ' '.join(html.unescape(re.sub(r'<[^>]+>', '', p['title']['rendered'])).split())
        lang = 'ru' if re.search(r'Постановлени|КОНСТИТУЦИОННОГО|ОПРЕДЕЛЕНИЕ|Определение', t[:600] + title) else 'tg'
        if lang == 'tg':
            t, title = t.translate(LEGACY), title.translate(LEGACY)
        if PROTECTED.search(t):
            skipped += 1
            continue
        d = decided(t)
        items.append({'id': p['id'], 'link': p['link'], 'title': title, 'lang': lang, 'date': d, 'text': t,
                      'dir': tg_dir if lang == 'tg' else ru_dir})
    print('protected subjects skipped', skipped)
    bad = [i for i in items if not i['date']]
    for i in bad:
        print('NO DATE', i['id'], i['title'][:80], file=sys.stderr)
    items = [i for i in items if i['date']]
    items.sort(key=lambda i: (i['date'], i['lang'] != 'tg', i['id']))
    done = set()
    if run(repo, 'rev-parse', '--verify', '-q', 'HEAD') if subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '-q', 'HEAD'], capture_output=True).returncode == 0 else '':
        done = set(run(repo, 'log', '--format=%(trailers:key=Source-id,valueonly)').split())
    n = 0
    for i in items:
        if str(i['id']) in done:
            continue
        y = i['date'][:4]
        kind = i['dir']
        rel = Path('sudi-konstitutsioni') / kind / y / f'{i["date"]}-{i["id"]}.md'
        f = repo / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        body = f'# {i["title"]}\n\n{i["text"]}\n'
        f.write_bytes(body.encode('utf-8'))
        run(repo, 'add', str(rel).replace('\\', '/'))
        when = f'{i["date"]}T12:00:00+05:00'
        env = dict(os.environ, GIT_AUTHOR_NAME='Суди конститутсионии Ҷумҳурии Тоҷикистон',
                   GIT_AUTHOR_EMAIL='sudi-konstitutsioni@constcourt.invalid', GIT_AUTHOR_DATE=when,
                   GIT_COMMITTER_NAME='Lexifina', GIT_COMMITTER_EMAIL='tajikistan-caselaw@lexifina.com',
                   GIT_COMMITTER_DATE=when)
        subj = i['title'] if len(i['title']) <= 120 else i['title'][:117] + '...'
        msg = (f'{subj}\n\nConstitutional Court of the Republic of Tajikistan, decision of {i["date"]} '
               f'({"Tajik" if i["lang"] == "tg" else "Russian"} text as the court publishes it).\n\n'
               f'Court: Суди конститутсионии Ҷумҳурии Тоҷикистон\nDecided: {i["date"]}\nIn-force: {i["date"]}\n'
               f'In-force-basis: decision day stated in the decision ("шаҳри Душанбе" / "город Душанбе" line)\n'
               f'Language: {i["lang"]}\nSource: {urllib_unquote(i["link"])}\nSource-id: {i["id"]}\n')
        run(repo, '-c', 'commit.gpgsign=false', 'commit', '-q', '-F', '-', env=env, inp=msg)
        n += 1
    print('committed', n, 'of', len(items), 'undated', len(bad))


def urllib_unquote(u):
    import urllib.parse
    return urllib.parse.unquote(u)


if __name__ == '__main__':
    main(sys.argv[1])
