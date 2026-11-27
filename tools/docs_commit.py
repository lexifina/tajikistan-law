"""After graft_fast.py: one documentation commit on live main that brings in the scratch build's generated docs
(REPRODUCE.md, data/, tools/, every act's README.md) and the hand-kept README.md / README.en.md / LICENSE from the
working tree of the live repo (edit those in place first).

usage: python docs_commit.py <scratch repo> <live repo> "<subject>" "<body>"
Non-doc paths must already be identical (the graft); the script stops if they are not.
"""
import os, subprocess, sys
from pathlib import Path

DOC = ('REPRODUCE.md', 'data/', 'tools/')


def git(repo, *a, env=None, inp=None):
    r = subprocess.run(['git', '-C', str(repo), *a], capture_output=True, env=env, input=inp)
    if r.returncode:
        raise SystemExit(f'git {a}: {r.stderr.decode()}')
    return r.stdout.decode('utf-8')


def is_doc(p):
    return p.startswith(DOC) or p.endswith('README.md') or p in ('README.en.md', 'LICENSE', 'jurisdiction.json') \
        or p.startswith(('visualisations/', 'vulnerabilities/'))


def main(scratch, live, subject, body=''):
    scratch, live = Path(scratch).resolve(), Path(live).resolve()
    git(live, 'fetch', '-q', str(scratch), '+main:refs/build/main')
    diff = git(live, 'diff', '--name-status', '--no-renames', 'HEAD', 'refs/build/main').splitlines()
    bad = [l for l in diff if not is_doc(l.split('\t', 1)[1])]
    if bad:
        raise SystemExit('non-doc paths differ from the build:\n' + '\n'.join(bad[:20]))
    idx = live / '.git' / 'index.docs'
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    git(live, 'read-tree', 'HEAD', env=env)
    info = []
    for l in diff:
        st, p = l.split('\t', 1)
        if p in ('README.md', 'README.en.md', 'LICENSE') or p.startswith(('visualisations/', 'vulnerabilities/')):
            continue  # hand-kept files: taken from the working tree below
        if st == 'D':
            info.append(f'0 {"0" * 40}\t{p}')
        else:
            mode_sha = git(live, 'ls-tree', 'refs/build/main', '--', p).split('\t')[0].split()
            info.append(f'{mode_sha[0]} {mode_sha[2]}\t{p}')
    for p in ('README.md', 'README.en.md', 'LICENSE'):
        sha = git(live, 'hash-object', '-w', str(live / p)).strip()
        info.append(f'100644 {sha}\t{p}')
    git(live, 'update-index', '--index-info', env=env, inp=('\n'.join(info) + '\n').encode('utf-8'))
    tree = git(live, 'write-tree', env=env).strip()
    idx.unlink()
    if tree == git(live, 'rev-parse', 'HEAD^{tree}').strip():
        print('no doc change')
        return
    cenv = dict(os.environ, GIT_AUTHOR_NAME='Lexifina', GIT_AUTHOR_EMAIL='tajikistan-law@lexifina.com',
                GIT_COMMITTER_NAME='Lexifina', GIT_COMMITTER_EMAIL='tajikistan-law@lexifina.com')
    msg = subject + ('\n\n' + body if body else '') + '\n'
    head = git(live, 'commit-tree', tree, '-p', 'HEAD', env=cenv, inp=msg.encode('utf-8')).strip()
    git(live, 'update-ref', 'refs/heads/main', head)
    git(live, 'reset', '-q', '--hard', 'main')
    print('docs commit', head)


if __name__ == '__main__':
    main(*sys.argv[1:])
