"""Tajikistan: add the Ministry of Justice public register (portali-huquqi.tj/publicadliya, "Адлия") to corpus.json.

Run after parse_andoz.py and parse_wipo.py. Input: .cache/adlia/<lang>/<id>.html.gz (fetch_adlia.py).
Each record gives the current edition's text and a reference card: number, adoption day, status, start of action,
the edition in force and the act that made it (with its in-force day), the day it lapsed. One version per act:
  - an act never amended: its text from the start-of-action day, credited to the act itself (as enacted);
  - an amended act: the current edition, from the day that edition took effect, "oldest version available";
  - a lapsed act: a second version on the day it lapsed, with no provisions, credited to the act that repealed it.
Skipped: amending acts and acts that only repeal (their changes are in the consolidated texts); Majlisi Oli
resolutions that only adopt or approve a law; international treaties (no Tajik in-force day on the card);
records with no text. Acts already held from andoz.tj / WIPO Lex: an Adlia edition is added only when it is newer
than every version held (older ones would need the published history rewritten).
Writes .cache/adlia/parsed.json (per-record status) and .cache/adlia/need_ru.txt (records with no Tajik text).
"""
import datetime as dt, gzip, hashlib, html as htmlmod, json, os, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from parse_andoz import reflow, units_of, slugify, LAT  # noqa: E402

HERE = Path(__file__).parent
D = HERE / '.cache' / 'adlia'
TODAY = '2026-11-27'
VIEW = 'http://portali-huquqi.tj/publicadliya/view_qonunhoview.php?showdetail=&asosi_id={}&language={}'
PUB = {'name': 'Вазорати адлияи Ҷумҳурии Тоҷикистон (Феҳристи санадҳои меъёрии ҳуқуқӣ, portali-huquqi.tj)',
       'email': 'publisher@adlia.invalid'}
SRC_ID = re.compile(r'(\d+)\.html\.gz$')


def card(h, label):
    m = re.search(re.escape(label) + r'\s*</td>\s*<td class="info-accent">\s*(.*?)</td>', h, re.S)
    return re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', ' ', m.group(1)))).strip() if m else None


def dmy(s):
    m = re.search(r'(\d\d)/(\d\d)/(\d{4})', s or '')
    if not m:
        return None
    try:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
    except ValueError:
        return None


def record(i, lang='tj'):
    f = D / lang / f'{i}.html.gz'
    if not f.exists():
        return None
    h = gzip.open(f, 'rt', encoding='utf-8').read()
    a, b = h.find('id="tab_view_qonunho1"'), h.find('id="tab_view_qonunho2"')
    body = h[a:b]
    m = re.search(r'<span class="qonun">(.*)</span>\s*</span>\s*</script>', body, re.S)
    body = m.group(1) if m else ''
    about = h[b:h.find('id="tab_view_qonunho3"')]
    t = re.search(r'<h1>(.*?)</h1>', about, re.S)
    r = {'id': i, 'lang': lang, 'raw': h, 'body': body,
         'heading': re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<br\s*/?>', ' ', t.group(1)))).strip() if t else '',
         'number': card(about, 'Номер документа:'), 'adopted': dmy(card(about, 'Дата принятия:')),
         'status': card(about, 'Состояние документа:'), 'start': dmy(card(about, 'Начало действия документа:')),
         'lapsed': dmy(card(about, 'Утратил силу с:')), 'org': card(about, 'Органы эмитенты:')}
    pub = re.search(r'<h2>Опубликование документа</h2>\s*(.*?)<h2>', about, re.S)
    r['published_in'] = re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', ' ', pub.group(1)))).strip() if pub else None
    ed = re.search(r'Текущая редакция принята:\s*([\d/]+)(.*?)</p>', about, re.S)
    r['ed_date'] = dmy(ed.group(1)) if ed else None
    r['ed_doc'] = None
    r['ed_inforce'] = None
    if ed:
        m = re.search(r'asosi_id=(\d+)', ed.group(2))
        r['ed_doc'] = int(m.group(1)) if m else None
        m = re.search(r'Вступила в силу с:\s*<b>([\d/]+)', ed.group(2))
        r['ed_inforce'] = dmy(m.group(1)) if m else None
        r['ed_label'] = re.sub(r'\s+', ' ', htmlmod.unescape(re.sub(r'<[^>]+>', ' ', ed.group(2)))).replace('документом', '').strip()
    # the act that repealed it: the link in the "lapsed" note at the top of the text
    m = re.search(r'class=imp-comment>(.*?)</SPAN>', body, re.S | re.I)
    r['lapse_doc'] = None
    if m and re.search(r'соқит|утратил|бекор', m.group(1), re.I):
        m2 = re.search(r'asosi_id=(\d+)', m.group(1))
        r['lapse_doc'] = int(m2.group(1)) if m2 else None
    return r


BLOCK = re.compile(r'</?(?:p|div|h[1-6]|tr|li|ul|ol|table|tbody|thead|br)\b[^>]*>', re.I)


def paragraphs(body):
    b = re.sub(r'(?is)<div class=doc-info-change>.*?</div>', '', body)
    b = re.sub(r'(?is)<span class=imp-comment>.*?</span>', '', b)
    b = re.sub(r'(?is)<script.*?</script>', '', b)
    b = re.sub(r'(?i)</t[dh]>\s*<t[dh][^>]*>', ' | ', b)
    b = BLOCK.sub('\n', b)
    b = re.sub(r'<[^>]+>', '', b)
    b = htmlmod.unescape(b).replace('\xa0', ' ').replace('​', '').replace('­', '')
    out = []
    for l in b.split('\n'):
        l = re.sub(r'\s+', ' ', l).strip().strip('|').strip()
        if l and not re.fullmatch(r'[|\s]*', l):
            out.append(l.replace('“', '"').replace('”', '"').replace('„', '"'))
    return out


RU_ART = re.compile(r'^Статья\s+(\d+)(?:[.\-](\d+)(?=\.))?\s*\.?\s*(.*)$')


def units_ru(paras):
    """Russian texts: the same split as units_of, on "Статья N"."""
    conv = []
    for p in paras:
        m = RU_ART.match(p)
        conv.append(('Моддаи ' + p[len('Статья '):]) if m else p)
    u = units_of(conv)
    for k, v in u.items():
        lines = v['text'].split('\n')
        v['text'] = '\n'.join(('Статья ' + l[len('Моддаи '):]) if l.startswith('Моддаи ') and RU_ART.match('Статья ' + l[len('Моддаи '):]) else l for l in lines)
        v['label'] = v['label'].replace('Моддаи', 'Статья').replace('Муқаддима', 'Преамбула')
    return u


KINDS = [  # heading prefix -> (folder, law kind, short prefix)
    (r'^Постановление\s+[Пп]ленума\s+Верховного|^Қарори\s+Пленуми\s+Суди\s+Олӣ', 'qarorhoi-plenumi-sudi-oli', 'court', None),
    (r'^Постановление\s+Пленума\s+Высшего\s+экономического|^Қарори\s+Пленуми\s+Суди\s+Олии\s+иқтисодӣ', 'qarorhoi-plenumi-sudi-oli-iqtisodi', 'court', None),
    (r'^Қарори\s+Девони\s+Вазирон', 'qarorhoi-hukumat', 'decree', 'Қарори Девони Вазирони ҶТ'),
    (r'^Постановление\s+(?:Кабинета?\s+Министров|Совета?\s+Министров)', 'qarorhoi-shuroi-vaziron', 'decree', None),
    (r'^Постановление\s+Правительств', 'qarorhoi-hukumat', 'decree', 'Постановление Правительства РТ'),
    (r'^[ҚК][аa][рp][оo][рp]и?\s+Ҳукумат', 'qarorhoi-hukumat', 'decree', 'Қарори Ҳукумати ҶТ'),
    (r'^(?:Постановление|Қарори)\s+Совета?\s+(?:Маджлиси|Мажлиси|Маҷлиси)', 'qarorhoi-majlisi-oli', 'decree', None),
    (r'^Приказ\s+[Гг]енерального\s+[Пп]рокурора|^Фармоиши\s+Прокурори\s+генералӣ', 'farmoishhoi-prokurori-generali', 'decree', None),
    (r'^(?:Постановление|Қарори|Указ)\s+(?:Совета\s+|Президиума\s+|президиума\s+)?(?:Маджлиси|Маҷлиси|Верховного|Шӯрои\s+Маҷлиси)', 'qarorhoi-majlisi-oli', 'decree', None),
    (r'^\S+\s+[Кк]одекс\b', None, 'law', ''),
    (r'^Кодекси ', None, 'law', ''),
    (r'^Қонуни конститутсионии ', None, 'law', 'Қонуни конститутсионии ҶТ'),
    (r'^Қонуни+ Ҷумҳурии Тоҷикистон', 'qonunho', 'law', 'Қонуни ҶТ'),
    (r'^Қонун', 'qonunho', 'law', 'Қонуни ҶТ'),
    (r'^Фармони Президенти', 'farmonhoi-prezident', 'decree', 'Фармони Президенти ҶТ'),
    (r'^Фармоиши Президенти', 'farmoishhoi-prezident', 'decree', 'Фармоиши Президенти ҶТ'),
    (r'^Қарори Ҳукумати', 'qarorhoi-hukumat', 'decree', 'Қарори Ҳукумати ҶТ'),
    (r'^Қарори Маҷлиси (?:намояндагони|миллии|Олии)', 'qarorhoi-majlisi-oli', 'decree', None),
    (r'^Қарори Шӯрои Вазирон', 'qarorhoi-shuroi-vaziron', 'decree', 'Қарори Шӯрои Вазирони ҶТ'),
    (r'^Кодекс ', None, 'law', ''),
    (r'^Конституционный [Зз]акон', None, 'law', 'Конституционный Закон РТ'),
    (r'^Закон ', 'qonunho', 'law', 'Закон РТ'),
    (r'^Указ\s+Президент', 'farmonhoi-prezident', 'decree', 'Указ Президента РТ'),
    (r'^Распоряжение Президента', 'farmoishhoi-prezident', 'decree', 'Распоряжение Президента РТ'),
    (r'^Постановление Правительства', 'qarorhoi-hukumat', 'decree', 'Постановление Правительства РТ'),
    (r'^Постановление (?:Маджлиси|Верховного Совета|Президиума)', 'qarorhoi-majlisi-oli', 'decree', None),
    (r'^Постановление Совета Министров', 'qarorhoi-shuroi-vaziron', 'decree', 'Постановление Совета Министров РТ'),
]
AMEND = re.compile(r'^(?:Изменения|Изменение|Дополнения|Дополнение)\s+(?:и\s+)?|(?:ворид|дохил|даровардан|даровард)\w*\s+(?:\w+\s+)?тағйир|^О(?:б)?\s+(?:внесени|изменени|дополнени)'
                   r'|^(?:Оиди|Оид ба|Дар бораи|Дар хусуси)\s+(?:аз\s+эътибор\s+соқит|беэътибор)', re.I)
SKIP_NAME = re.compile(r'^(?:Оид ба|Оиди|Дар бораи|Дар хусуси)\s+(?:ворид\s+(?:намудани|кардани)\s+(?:тағйир|илова)|'
                       r'тағйиру\s+илова|аз\s+эътибор\s+соқит|беэътибор\s+донистани|қабул\s+(?:кардани|намудани)\s+Қонун|'
                       r'Қонуни\s+Ҷумҳурии\s+Тоҷикистон|Қонуни\s+ҶТ|ҷонибдорӣ)|^О\s+(?:внесении\s+(?:изменени|дополнени)|признании\s+утратившим|принятии\s+(?:Закона|Кодекса|Конституционного)|Законе\s+Республики|Кодексе\s+Республики|Конституционном\s+Законе|порядке\s+введения\s+в\s+действие)|^Об\s+отмене', re.I)
TREATY = re.compile(r'^(?:\S+ое Соглашение|Инструкция к|Общая Инструкция|Меморандум|Заключительный Акт|Оглашение|Постановление Межпарламентской|Решение|Заявление|Рекомендация|Минимальные|Международн|Исполнительный Регламент|Служебная Инструкция|Конвесия|\S+ское Соглашение|\S+ская Декларация|\S+ дополнительный протокол|Базовое Соглашение|Конвенсия|Созишнома|Паймон|Протокол|Шартнома|Эъломия|Аҳднома|Хартия|Оинномаи СММ|Конвенция|Соглашение|Пакт|Договор|Декларация|Устав)', re.I)


def norm(t):
    t = t.lower().replace('ё', 'е')
    m = re.search(r'["«](.+)["»]', t)
    if m:
        kind = 'k' if 'конститутсион' in t[:m.start()] else 'q' if re.match(r'қонун', t) else t.split()[0]
        return kind + ' ' + re.sub(r'\s+', ' ', re.sub(r'["«»“”„\'(),.]', ' ', m.group(1))).strip()
    t = re.sub(r'\s+аз\s+\d.*$', '', t)
    t = re.sub(r'\s+аз\s+\d{1,2}\s+\S+\s+(?:соли\s+)?\d{4}\s*(?:с\.|сол)?\s*,?\s*(?:№\s*[\w\-/]+)?', ' ', t)
    t = re.sub(r'ҷумҳурии тоҷикистон|\bҷт\b|қонуни|қонун|конститутсионии|["«»“”„\'(),.]', ' ', t)
    return re.sub(r'\s+', ' ', t).strip()


def main():
    cp = HERE / 'corpus.json'
    c = json.loads(cp.read_text(encoding='utf-8'))
    for a in c['acts']:
        a['versions'] = [v for v in a['versions'] if 'portali-huquqi.tj' not in (v.get('source_url') or '')]
    c['acts'] = [a for a in c['acts'] if a['versions'] and not a.get('_adlia')]
    for k in [k for k in c['laws'] if k.startswith('adlia-')]:
        del c['laws'][k]
    held = {a['slug']: a for a in c['acts']}
    by_norm = {norm(a['title']): a['slug'] for a in c['acts']}
    by_norm.setdefault(norm('Конститутсияи Ҷумҳурии Тоҷикистон'), 'konstitutsiya')
    ids = sorted(int(SRC_ID.search(p.name).group(1)) for p in (D / 'tj').glob('*.html.gz'))
    recs = {}
    for i in ids:
        r = record(i, 'tj')
        if r is not None and (not r['heading'] or len(re.sub(r'<[^>]+>', '', r['body']).strip()) < 40) and (D / 'ru' / f'{i}.html.gz').exists():
            r2 = record(i, 'ru')
            if r2 and len(re.sub(r'<[^>]+>', '', r2['body']).strip()) >= 40:
                r2['heading_tj'] = r['heading']
                r = r2
        recs[i] = r
    laws, status, new, need_ru = {}, [], {}, []
    used_slugs = set(held)

    def law_of(j):
        """law key for record j (an act named in a card), with its label; None if we do not hold the record."""
        rj = recs.get(j)
        if not rj or not rj['heading']:
            return None
        k = f'adlia-{j}'
        if k not in laws:
            hd = rj['heading']
            pre = re.split(r'\s+(?:аз|от)\s+\d|\s*["«]', hd)[0].strip() or hd[:60]
            pre = re.sub(r'Ҷумҳурии Тоҷикистон', 'ҶТ', pre).replace('Республики Таджикистан', 'РТ')
            ru = rj['lang'] == 'ru'
            label = pre
            if rj['adopted']:
                y, mo, d = rj['adopted'].split('-')
                label += f' {"от" if ru else "аз"} {d}.{mo}.{y}'
            if rj['number']:
                label += f' №{rj["number"]}'
            title = re.search(r'["«](.+)["»]\s*$', hd)
            laws[k] = {'label': label[:120], 'title': (title.group(1) if title else hd)[:300],
                       'kind': 'decree' if re.match(r'^(?:Қарор|Фармо|Постановление|Указ|Распоряжение)', hd) else 'law',
                       'enacted': rj['adopted'], 'published': None, 'url': VIEW.format(j, 'tj'),
                       'temporary_until': None, 'restores': None, 'note': None}
        return k

    for i in ids:
        r = recs[i]
        st = {'id': i}
        status.append(st)
        hd = r['heading'] if r else ''
        st['heading'] = hd[:160]
        body_text = len(re.sub(r'<[^>]+>', '', r['body']).strip()) if r else 0
        if not hd:
            st['status'] = 'skipped: empty record'
            if r and r['lang'] == 'tj':
                need_ru.append(i)
            continue
        if body_text < 40:
            st['status'] = 'held: no text in the register'
            if r['lang'] == 'tj':
                need_ru.append(i)
            continue
        m = re.search(r'["«](.+)["»]\s*$', hd)
        name = (m.group(1) if m else '').strip()
        heading_tj = r.get('heading_tj') or hd
        kind = next((k for k in KINDS if re.match(k[0], heading_tj, re.I)), None)
        if TREATY.match(heading_tj):
            st['status'] = 'skipped: international instrument (no Tajik in-force day on the card)'
            continue
        if name and (SKIP_NAME.match(name) or AMEND.search(name)) or AMEND.match(heading_tj) or re.match(r'^Оид ба ворид|^Дар бораи ворид намудани', heading_tj):
            st['status'] = 'skipped: amending, repealing or adopting act'
            continue
        if kind and kind[1] == 'qarorhoi-majlisi-oli' and re.search(r'Қонуни|Кодекси|Қонун|Закон|Кодекс', name or ''):
            st['status'] = 'skipped: Majlisi Oli resolution on a law'
            continue
        if not r['adopted'] and not r['start']:
            st['status'] = 'held: no date on the card'
            continue
        # the day the text took effect
        if r['ed_date'] and r['adopted'] and r['ed_date'] > r['adopted']:
            eid = r['ed_doc']
            er = recs.get(eid) if eid else None
            if r['ed_inforce']:
                day, basis = r['ed_inforce'], 'in-force day the Ministry of Justice register gives for this edition'
            elif er and er['start']:
                day = er['start']
                basis = f'start-of-action day the register gives for the act that made this edition (record {eid})'
            else:
                day = r['ed_date']
                basis = 'adoption day of the act that made this edition (the register gives no in-force day for it)'
            amended = True
        else:
            day = r['start'] or r['adopted']
            basis = ('start-of-action day the Ministry of Justice register gives for this act' if r['start']
                     else 'adoption day the register gives (no start-of-action day stated)')
            amended = False
        if day < '1991-01-01' and not re.match(r'^Қонуни|^Кодекси', heading_tj):
            pass
        paras = paragraphs(r['body'])
        units = units_ru(paras) if r['lang'] == 'ru' else units_of(paras)  # HTML paragraphs are paragraphs: no PDF reflow
        arts = [k for k in units if k.startswith('art-')]
        if not arts:
            units = {'matn': {'label': 'Матн' if r['lang'] == 'tj' else 'Текст', 'kind': 'text',
                              'text': '\n'.join(paras) + '\n'}}
        own = law_of(i)
        src = VIEW.format(i, r['lang'])
        v = {'from': day, 'source_url': src, 'sha256': hashlib.sha256(r['body'].encode('utf-8')).hexdigest(),
             'units': units, 'in_force_basis': basis}
        if r['lang'] == 'ru':
            v['note'] = 'Russian text: the register holds no Tajik text for this act.'
        lapse = None
        if r['lapsed'] and r['lapsed'] > day:
            lapse = {'from': r['lapsed'], 'source_url': src, 'sha256': v['sha256'], 'units': {},
                     'in_force_basis': 'day the register gives for the act losing force ("Утратил силу с")',
                     'note': 'The Ministry of Justice register records this act as no longer in force from this day.'}
            lk = law_of(r['lapse_doc']) if r['lapse_doc'] else None
            if lk:
                lapse['credits'] = {k: [lk] for k in units}
        elif r['status'] and 'Утратил' in r['status'] and not r['lapsed']:
            st['status'] = 'held: lapsed, with no lapse day on the card'
            continue
        nk = norm(heading_tj)
        slug = by_norm.get(nk)
        if slug in held:
            have = [x['from'] for x in held[slug]['versions']]
            st['slug'] = slug
            if day in have or day <= max(have):
                st['status'] = (f'skipped: {slug} holds a version on {day}' if day in have else
                                f'held: older than the latest version held ({max(have)}); adding it needs a history rewrite')
                continue
            vv = dict(v, publisher=PUB)
            held[slug].setdefault('_new', []).append(vv)
            if lapse:
                held[slug]['_new'].append(dict(lapse, publisher=PUB))
            st['status'] = 'ok (newer edition of a held act)'
            st['day'] = day
            continue
        # a new act
        fold = kind[1] if kind else 'sanadhoi-digar'
        year = (r['adopted'] or day)[:4]
        no = re.sub(r'[^0-9a-z]+', '-', (r['number'] or '').lower().translate(LAT)).strip('-')
        base = slugify(name or heading_tj) or f'sanad-{i}'
        if kind and kind[1] is None:  # codes and constitutional laws: at the root, like the codes already held
            head0 = re.split(r'\s+(?:аз|от)\s+\d|\s*["«]', heading_tj)[0]
            if name:  # constitutional laws: kind + name, like the folders already held
                head0 = re.sub(r'\s+(?:Ҷумҳурии Тоҷикистон|Республики Таджикистан)$', '', head0) + ' ' + name
            base = slugify(head0).replace('-jumhurii-tojikiston', '').replace('-respubliki-tadzhikistan', '')
            slug = base
            d_ = None
        else:
            slug = (f'{no}-{base}' if no else base)[:80].rstrip('-')
            d_ = f'{fold}/{year}'
        pth = (lambda s: f'{d_}/{s}' if d_ else s)
        if pth(slug) in used_slugs:  # unique per folder path
            slug = f'{slug}-{year}' if not d_ and pth(f'{slug}-{year}') not in used_slugs else f'{slug[:72]}-{i}'
        used_slugs.add(pth(slug))
        pre = kind[3] if kind else None
        if r['lang'] == 'ru':
            short = re.sub(r'\s+от\s+\d.*?(?=["«]|$)', ' ', hd).replace('Республики Таджикистан', 'РТ').strip()
        elif name and pre:
            short = f'{pre} "{name}"'
        elif kind and kind[1] is None:
            short = re.sub(r'\s+аз\s+\d.*$', '', heading_tj).replace('Ҷумҳурии Тоҷикистон', 'ҶТ').strip()
        else:
            short = re.sub(r'Ҷумҳурии Тоҷикистон', 'ҶТ', hd)
        if len(short) > 70:
            short = short[:67].rstrip() + '...'
        title = re.sub(r'\s+', ' ', hd).strip()
        a = {'slug': slug, 'short': short, 'title': title, 'url': src,
             'first_law': None if amended else own, 'earlier_laws': [own] if amended else [],
             'publisher': PUB, 'versions': [v] + ([lapse] if lapse else []), '_adlia': i}
        if d_:
            a['dir'] = d_
        if amended and r['ed_doc'] and law_of(r['ed_doc']):
            a['earlier_laws'].append(law_of(r['ed_doc']))
        new[slug] = a
        st.update(status='ok (new act)', slug=(d_ + '/' if d_ else '') + slug, day=day, units=len(units),
                  articles=len(arts), lang=r['lang'])
    added = 0
    for a in held.values():
        for v in sorted(a.pop('_new', []), key=lambda v: v['from']):
            a['versions'].append(v)
            added += 1
    added += sum(len(a['versions']) for a in new.values())
    # laws: only those named by an act we build
    usedk = set()
    for a in list(held.values()) + list(new.values()):
        usedk.update(x for x in [a.get('first_law')] + a.get('earlier_laws', []) if x)
        for v in a['versions']:
            for ls in (v.get('credits') or {}).values():
                usedk.update(ls)
    for k in usedk:
        if k.startswith('adlia-'):
            c['laws'][k] = laws[k]
    folders = Counter(a.get('dir') for a in new.values())
    c['acts'] = sorted(list(held.values()) + list(new.values()), key=lambda a: (a['slug'] != 'konstitutsiya', a.get('dir') or '', a['slug']))
    c['sources'] = [s for s in c['sources'] if 'portali-huquqi.tj' not in s['url']]
    c['sources'].append({'name': 'Вазорати адлияи Ҷумҳурии Тоҷикистон: Феҳристи санадҳои меъёрии ҳуқуқӣ (Ministry of Justice public register, "Адлия")',
                         'url': 'http://portali-huquqi.tj/publicadliya/', 'retrieved': TODAY,
                         'requests': len(ids) + len(list((D / 'ru').glob('*.html.gz'))) + 8,
                         'licence': 'Official texts (not objects of copyright, Law on Copyright of 13.11.1998, art. 7)',
                         'notes': 'current editions of laws, codes, decrees and resolutions with reference cards (adoption, start of action, edition, lapse); Tajik, Russian where no Tajik text'})
    dec = [x for x in c['decisions'] if 'Ministry of Justice register' not in x]
    dec += ['Ministry of Justice register (portali-huquqi.tj/publicadliya): one version per act, the current edition. '
            'An act never amended is dated by the start-of-action day on its card and credited to itself; an amended '
            'act is dated by the in-force day the card gives for its edition (or the start-of-action day of the act '
            'that made it) and committed as "oldest version available"; an act that lapsed gets a second version on '
            'its lapse day with no provisions, credited to the repealing act when the register links it. '
            'Amending, repealing and adopting acts are not acts of their own here; international instruments and '
            'records with no date or no text are held. Editions older than a version already published are held.',
            'Ministry of Justice register: new laws go in qonunho/<year of adoption>/<number>-<name>/, government '
            'resolutions in qarorhoi-hukumat/<year>/, presidential decrees in farmonhoi-prezident/<year>/, '
            'presidential orders in farmoishhoi-prezident/<year>/, Majlisi Oli resolutions in qarorhoi-majlisi-oli/<year>/, '
            'Supreme Court and Supreme Economic Court plenum resolutions in qarorhoi-plenumi-sudi-oli(-iqtisodi)/<year>/, '
            'Prosecutor General orders in farmoishhoi-prokurori-generali/<year>/, Council/Cabinet of Ministers resolutions in qarorhoi-shuroi-vaziron/<year>/, '
            'other acts in sanadhoi-digar/<year>/; new codes and constitutional laws at the root beside the codes '
            'already held. Where the register holds no Tajik text the Russian text is used (marked in the version note).']
    c['decisions'] = dec
    (D / 'parsed.json').write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding='utf-8')
    (D / 'need_ru.txt').write_text('\n'.join(map(str, need_ru)) + '\n', encoding='utf-8')
    tmp = cp.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + '\n', encoding='utf-8', newline='\n')
    os.replace(tmp, cp)
    print(Counter(s.get('status', '?').split(':')[0].split(' (')[0] for s in status), 'versions added', added)
    print(Counter(s.get('status') for s in status if not s.get('status', '').startswith('ok')).most_common(12))
    print('largest folders', folders.most_common(5))


if __name__ == '__main__':
    main()
