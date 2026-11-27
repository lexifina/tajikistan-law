"""Append one Kind: correction commit that sets every non-doc path where live main differs from the scratch build
to the build's content (after graft_fast.py). usage: python correct.py <scratch> <live> <subject> <body> <corrects>"""
import os, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from docs_commit import git, is_doc  # noqa: E402


def main(scratch, live, subject, body, corrects):
    scratch, live = Path(scratch).resolve(), Path(live).resolve()
    git(live, 'fetch', '-q', str(scratch), '+main:refs/build/main')
    diff = [l.split('\t', 1) for l in git(live, 'diff', '--name-status', '--no-renames', 'HEAD', 'refs/build/main').splitlines()]
    diff = [(s, p) for s, p in diff if not is_doc(p)]
    if not diff:
        print('nothing to correct')
        return
    tree_of = {}
    for row in git(live, 'ls-tree', '-r', 'refs/build/main').splitlines():
        meta, p = row.split('\t', 1)
        tree_of[p] = meta.split()
    idx = live / '.git' / 'index.corr'
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    git(live, 'read-tree', 'HEAD', env=env)
    info = [f'0 {"0" * 40}\t{p}' if s == 'D' else f'{tree_of[p][0]} {tree_of[p][2]}\t{p}' for s, p in diff]
    git(live, 'update-index', '--index-info', env=env, inp=('\n'.join(info) + '\n').encode('utf-8'))
    tree = git(live, 'write-tree', env=env).strip()
    idx.unlink()
    cenv = dict(os.environ, GIT_AUTHOR_NAME='Lexifina', GIT_AUTHOR_EMAIL='tajikistan-law@lexifina.com',
                GIT_COMMITTER_NAME='Lexifina', GIT_COMMITTER_EMAIL='tajikistan-law@lexifina.com')
    msg = f'{subject}\n\n{body}\n\nKind: correction\nCorrects: {corrects}\n'
    head = git(live, 'commit-tree', tree, '-p', 'HEAD', env=cenv, inp=msg.encode('utf-8')).strip()
    git(live, 'update-ref', 'refs/heads/main', head)
    git(live, 'reset', '-q', '--hard', 'main')
    print('correction', head, len(diff), 'paths')


if __name__ == '__main__':
    main(*sys.argv[1:])
