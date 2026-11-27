"""Detached runner: every ~30 min while fetch_adlia.py runs (and once after it ends), rebuild from the cache and push.

One wave: parse_adlia.py -> builder/build.py (scratch .tmp-build) -> graft_fast.py onto work/repo -> check the
non-doc tree equals the build -> readme_adlia.py -> docs_commit.py -> push (fast-forward, retried) -> ls-remote.
After the Tajik sweep ends, the records with no Tajik text fetched before the Russian fallback existed are fetched
in Russian (fetch_adlia.py ru --only need_ru.txt), then a last wave. Log: .cache/adlia/waves.log
"""
import subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).parent.resolve()
LIVE = HERE / 'work' / 'repo'
SCR = HERE / '.tmp-build'
LOG = HERE / '.cache' / 'adlia' / 'waves.log'
PY = [sys.executable, '-X', 'utf8']
NOWIN = 0x08000000


def log(m):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + m + '\n')


def run(cmd, cwd=HERE, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, creationflags=NOWIN)
    out = (r.stdout + r.stderr).decode('utf-8', 'replace')
    if check and r.returncode:
        log(f'FAILED {cmd[-3:]}: {out[-1500:]}')
        raise RuntimeError(out)
    return out


def fetcher_alive():
    out = run(['powershell', '-NoProfile', '-Command',
               "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | ? { $_.CommandLine -match 'fetch_adlia' } | % ProcessId"], check=False)
    return bool(out.strip())


def wave(n):
    out = run(PY + ['parse_adlia.py'])
    log('parse: ' + out.splitlines()[0])
    run(PY + ['builder/build.py', '.', '--repo', str(SCR), '--docs-date', '2026-11-27'])
    log('graft: ' + run(PY + ['graft_fast.py', str(SCR), str(LIVE)]).strip())
    d = run(['git', 'diff', '--name-only', 'refs/build/main', 'HEAD', '--', '.', ':(exclude)*README*', ':(exclude)data',
             ':(exclude)tools', ':(exclude)REPRODUCE.md', ':(exclude)LICENSE'], cwd=LIVE)
    if d.strip() and len(d.splitlines()) <= 300:
        # an earlier record read later (its Russian text arrived) took a folder name first: move the folders
        log('correction: ' + run(PY + ['correct.py', str(SCR), str(LIVE),
                                       'Ministry of Justice register: folder names of acts sharing a name',
                                       'Records of the register read later took the folder name of an act with the same number and name; '
                                       'the folders are renamed to match the build (record number added to the later one). No word changed.',
                                       'the register commits before it']).strip())
        d = run(['git', 'diff', '--name-only', 'refs/build/main', 'HEAD', '--', '.', ':(exclude)*README*', ':(exclude)data',
                 ':(exclude)tools', ':(exclude)REPRODUCE.md', ':(exclude)LICENSE'], cwd=LIVE)
    if d.strip():
        log('STOP: live tree differs from the build outside docs:\n' + d[:2000])
        raise SystemExit(2)
    log('readme: ' + run(PY + ['readme_adlia.py', str(LIVE)]).strip())
    log('docs: ' + run(PY + ['docs_commit.py', str(SCR), str(LIVE),
                             'README (Tajik and English), LICENSE, REPRODUCE, act tables and data: Ministry of Justice register',
                             f'More acts from the public register of normative legal acts of the Ministry of Justice (portali-huquqi.tj/publicadliya), part {n}.']).strip())
    head = run(['git', 'rev-parse', 'HEAD'], cwd=LIVE).strip()
    for attempt in range(6):
        run(['git', 'push', 'origin', 'main'], cwd=LIVE, check=False)
        remote = run(['git', 'ls-remote', 'origin', 'main'], cwd=LIVE, check=False).split()
        if remote and remote[0] == head:
            log(f'pushed {head}')
            return
        time.sleep(60 * (attempt + 1))
    log(f'PUSH NOT VERIFIED for {head}')


def main():
    n = 2
    ru_done = False
    while True:
        alive = fetcher_alive()
        if not alive and not ru_done:
            run(PY + ['parse_adlia.py'])
            log('ru pass: ' + run(PY + ['fetch_adlia.py', 'ru', '--only', str(HERE / '.cache' / 'adlia' / 'need_ru.txt')], check=False)[-300:])
            ru_done = True
        try:
            wave(n)
        except RuntimeError:
            log('wave failed; next try in 30 min')
        n += 1
        if not alive and ru_done:
            log('done')
            return
        for _ in range(30):
            time.sleep(60)
            if not fetcher_alive():
                break


if __name__ == '__main__':
    main()
