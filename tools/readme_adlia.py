"""Update README.md, README.en.md and LICENSE of the live repo in place for the Ministry of Justice register texts.
Counts come from corpus.json. Idempotent: replaces the sentences it wrote before.
usage: python readme_adlia.py <live repo>
"""
import json, re, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
live = Path(sys.argv[1])
c = json.loads((HERE / 'corpus.json').read_text(encoding='utf-8'))
ad = [a for a in c['acts'] if a.get('_adlia')]
fold = Counter((a.get('dir') or 'root').split('/')[0] for a in ad)
ru = sum(1 for a in ad if '&language=ru' in a['versions'][0]['source_url'])
lapsed = sum(1 for a in ad if len(a['versions']) > 1 and a['versions'][-1]['units'] == {})
newer = sum(1 for a in c['acts'] if not a.get('_adlia') for v in a['versions'] if 'portali-huquqi.tj' in (v.get('source_url') or ''))
n_laws = fold['qonunho']
n_codes = sum(1 for a in ad if not a.get('dir'))
n_gov = fold['qarorhoi-hukumat'] + fold['qarorhoi-shuroi-vaziron']
n_pres = fold['farmonhoi-prezident'] + fold['farmoishhoi-prezident']
n_mo = fold['qarorhoi-majlisi-oli']
n_other = fold['sanadhoi-digar']

EN = (f'<!-- adlia -->**From the Ministry of Justice register** (portali-huquqi.tj/publicadliya, the public "Адлия" register of '
      f'normative legal acts): {len(ad)} more acts in their current editions: {n_codes} codes and constitutional laws, '
      f'{n_laws} laws in `qonunho/<year>/`, {n_gov} government resolutions in `qarorhoi-hukumat/<year>/` and '
      f'`qarorhoi-shuroi-vaziron/<year>/`, {n_pres} presidential decrees and orders in `farmonhoi-prezident/<year>/` and '
      f'`farmoishhoi-prezident/<year>/`, {n_mo} Majlisi Oli resolutions in `qarorhoi-majlisi-oli/<year>/` and {n_other} other acts '
      f'in `sanadhoi-digar/<year>/` (the year is the year of adoption), plus {newer} newer editions of acts already held. '
      f'Each is dated by the in-force day the register gives for its edition; {lapsed} acts the register marks as no longer '
      f'in force are removed on that day. {ru} acts for which the register has no Tajik text are in Russian. '
      f'Amending acts are not folders of their own: their changes are in the consolidated texts.<!-- /adlia -->')
TG = (f'<!-- adlia -->**Аз Феҳристи Вазорати адлия** (portali-huquqi.tj/publicadliya, феҳристи ошкорои санадҳои меъёрии ҳуқуқии «Адлия»): '
      f'боз {len(ad)} санад дар таҳрири ҷорӣ: {n_codes} кодекс ва қонуни конститутсионӣ, {n_laws} қонун дар `qonunho/<сол>/`, '
      f'{n_gov} қарори Ҳукумат дар `qarorhoi-hukumat/<сол>/` ва `qarorhoi-shuroi-vaziron/<сол>/`, {n_pres} фармон ва фармоиши '
      f'Президент дар `farmonhoi-prezident/<сол>/` ва `farmoishhoi-prezident/<сол>/`, {n_mo} қарори Маҷлиси Олӣ дар '
      f'`qarorhoi-majlisi-oli/<сол>/` ва {n_other} санади дигар дар `sanadhoi-digar/<сол>/` (сол — соли қабул), инчунин {newer} таҳрири '
      f'навтари санадҳое, ки аллакай ҳастанд. Ҳар яке бо рӯзи эътибор пайдо кардани таҳрираш, ки феҳрист медиҳад, сана гузошта '
      f'шудааст; {lapsed} санаде, ки феҳрист эътибор надошташон медонад, дар он рӯз хориҷ карда мешаванд. {ru} санад, ки дар '
      f'феҳрист матни тоҷикӣ надоранд, бо забони русӣ оварда шудаанд. Санадҳои тағйирдиҳанда ҷузвдони алоҳида надоранд: '
      f'тағйироташон дар матнҳои мураттаб аст.<!-- /adlia -->')
SRC_EN = ('| [Ministry of Justice register of normative legal acts](http://portali-huquqi.tj/publicadliya/) (portali-huquqi.tj, "Адлия") '
          '| Current editions of codes, laws, decrees and resolutions, with reference cards (adoption, start of action, edition, lapse) '
          '| no, the current edition of each act | Read on 27 November 2026; Tajik, Russian where no Tajik text |')
SRC_TG = ('| [Феҳристи санадҳои меъёрии ҳуқуқии Вазорати адлия](http://portali-huquqi.tj/publicadliya/) (portali-huquqi.tj, «Адлия») '
          '| Таҳрири ҷории кодексҳо, қонунҳо, фармонҳо ва қарорҳо бо маълумотнома (қабул, оғози амал, таҳрир, аз эътибор соқит шудан) '
          '| не, таҳрири ҷории ҳар санад | 27 ноябри соли 2026 хонда шуд; тоҷикӣ, русӣ дар ҷое, ки матни тоҷикӣ нест |')
MISS_EN = ('- **Earlier editions and the newest acts.** The Ministry of Justice register gives only the current edition of each act, '
           'and its public copy ends in late 2023; the official database ncz.tj and parlament.tj / majmilli.tj time out from here. '
           'The Labour and Forest Codes are here only if the register holds them.')
MISS_TG = ('- **Таҳрирҳои пештара ва санадҳои навтарин.** Феҳристи Вазорати адлия танҳо таҳрири ҷории ҳар санадро медиҳад ва нусхаи '
           'ошкорои он охири соли 2023 ба охир мерасад; махзани расмии ncz.tj ва parlament.tj / majmilli.tj аз ин ҷо ҷавоб намедиҳанд.')


def put(text, block, anchor_re):
    if '<!-- adlia -->' in text:
        return re.sub(r'<!-- adlia -->.*?<!-- /adlia -->', lambda m: block, text, flags=re.S)
    m = re.search(anchor_re, text, re.M)
    return text[:m.end()] + '\n\n' + block + text[m.end():]


for name, block, src, miss, old_miss, old_any, any_new in (
        ('README.en.md', EN, SRC_EN, MISS_EN, r'^- \*\*Codes and statutes\.\*\*.*$',
         r'^- \*\*Any other law\*\*.*$', '- **Any other law**: case law (the Constitutional Court decisions are in the separate tajikistan-caselaw repository), local acts and treaties are not here.'),
        ('README.md', TG, SRC_TG, MISS_TG, r'^- \*\*Кодексҳо ва қонунҳо\.\*\*.*$',
         r'^- \*\*Ягон қонуни дигар\*\*.*$', '- **Ягон қонуни дигар**: таҷрибаи судӣ, санадҳои маҳаллӣ ва шартномаҳои байналмилалӣ дар ин ҷо нестанд.')):
    p = live / name
    t = p.read_text(encoding='utf-8')
    t = put(t, block, r'^\*\*(?:What is in it now|Ҳоло дар он чӣ ҳаст):\*\*.*$')
    t = re.sub(old_miss, miss.replace('\\', r'\\'), t, count=1, flags=re.M)
    t = re.sub(old_any, any_new.replace('\\', r'\\'), t, count=1, flags=re.M)
    if 'portali-huquqi.tj/publicadliya/) (portali' not in t:
        t = re.sub(r'(^\| \[(?:Tax Committee|Кумитаи андози)[^\n]*$)', lambda m: m.group(1) + '\n' + src, t, count=1, flags=re.M)
    if name == 'README.en.md':
        t = t.replace('The Russian text and any English translation are not part of this record.',
                      'The Russian text is used only for acts the Ministry of Justice register holds in Russian alone; English translations are not part of this record.')
        t = re.sub(r'^- \*\*The Russian text\*\*, the language of interethnic communication \(Article 2\)\.$',
                   '- **The Russian text** of acts that have a Tajik text (Russian is the language of interethnic communication, Article 2).', t, flags=re.M)
    else:
        t = t.replace('Матни русӣ ва ҳар гуна тарҷумаи англисӣ ба ин сабт дохил намешаванд.',
                      'Матни русӣ танҳо барои санадҳое оварда мешавад, ки дар феҳристи Вазорати адлия танҳо бо русӣ ҳастанд; тарҷумаи англисӣ ба ин сабт дохил намешавад.')
        t = re.sub(r'^- \*\*Матни русӣ\*\*, ки забони муоширати байни миллатҳост \(моддаи 2\)\.$',
                   '- **Матни русии** санадҳое, ки матни тоҷикӣ доранд (забони муоширати байни миллатҳо, моддаи 2).', t, flags=re.M)
    p.write_text(t, encoding='utf-8', newline='\n')

lic = live / 'LICENSE'
t = lic.read_text(encoding='utf-8')
if 'portali-huquqi.tj' not in t:
    para = ('Ministry of Justice register: most acts are the texts of the public register of normative legal acts of the\n'
            'Ministry of Justice of the Republic of Tajikistan (http://portali-huquqi.tj/publicadliya/), official documents\n'
            'not protected by copyright (Law on Copyright, art. 7, above). The register\'s own footer notice covers its site;\n'
            'its HTML was converted to one Markdown file per article, one paragraph per line, with the wording unchanged.\n'
            'The Ministry does not endorse this repository.\n\n')
    t = t.replace("Lexifina's own contributions", para + "Lexifina's own contributions")
    lic.write_text(t, encoding='utf-8', newline='\n')
print(len(ad), dict(fold), 'ru', ru, 'lapsed', lapsed, 'newer', newer)
