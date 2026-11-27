"""Replay a scratch build's commits onto the live branch (fast-forward append).

usage: python graft.py <scratch repo> <live repo>
Every scratch commit on main whose Source/Consolidated trailer set is not yet in the live history (matched by
subject + author date) and that is not the final documentation commit is re-created on top of live HEAD: same
author, dates and message; its tree change (diff against its scratch parent) applied to the live tree.
Documentation paths (README*, REPRODUCE.md, data/, tools/, LICENSE) are skipped; they go in the docs commit.
"""
import os, subprocess, sys, tempfile
from pathlib import Path

SKIP = ('README.md', 'README.en.md', 'REPRODUCE.md', 'LICENSE', 'jurisdiction.json')
SKIP_DIRS = ('data/', 'tools/', 'visualisations/', 'vulnerabilities/')


def git(repo, *a, env=None, inp=None):
    r = subprocess.run(['git', '-C', str(repo), *a], capture_output=True, env=env, input=inp)
    if r.returncode:
        raise SystemExit(f'git {a}: {r.stderr.decode()}')
    return r.stdout.decode('utf-8')


def main(scratch, live):
    scratch, live = Path(scratch), Path(live)
    have = set(git(live, 'log', '--format=%ad|%s', '--date=raw').splitlines())
    revs = git(scratch, 'rev-list', '--reverse', 'main').split()
    git(live, 'fetch', '-q', str(scratch), '+main:refs/build/main')
    idx = Path(tempfile.mkdtemp()) / 'index'
    env = dict(os.environ, GIT_INDEX_FILE=str(idx))
    head = git(live, 'rev-parse', 'HEAD').strip()
    git(live, 'read-tree', head, env=env)
    n = 0
    for r in revs:
        key = git(scratch, 'log', '-1', '--format=%ad|%s', '--date=raw', r).strip()
        parents = git(scratch, 'log', '-1', '--format=%P', r).split()
        if key in have or not parents:
            continue
        diff = git(scratch, 'diff-tree', '-r', '--no-renames', parents[0], r).splitlines()
        changed = False
        info = []
        for line in diff:
            meta, path = line.split(chr(9), 1)
            _, mode, _, sha, st = meta.split()
            if path in SKIP or path.startswith(SKIP_DIRS) or path.endswith('/README.md'):
                continue
            info.append(f'0 {"0" * 40}{chr(9)}{path}' if st == 'D' else f'{mode} {sha}{chr(9)}{path}')
            changed = True
        if info:
            git(live, 'update-index', '--index-info', env=env, inp=(chr(10).join(info) + chr(10)).encode('utf-8'))
        if not changed:
            continue
        tree = git(live, 'write-tree', env=env).strip()
        fmt = git(scratch, 'log', '-1', '--format=%an%x00%ae%x00%ad%x00%cn%x00%ce%x00%cd', '--date=raw', r).split('\x00')
        msg = git(scratch, 'log', '-1', '--format=%B', r)
        cenv = dict(os.environ, GIT_AUTHOR_NAME=fmt[0], GIT_AUTHOR_EMAIL=fmt[1], GIT_AUTHOR_DATE='@' + fmt[2],
                    GIT_COMMITTER_NAME=fmt[3], GIT_COMMITTER_EMAIL=fmt[4], GIT_COMMITTER_DATE='@' + fmt[5].strip())
        head = git(live, 'commit-tree', tree, '-p', head, env=cenv, inp=msg.encode('utf-8')).strip()
        n += 1
    git(live, 'update-ref', 'refs/heads/main', head)
    git(live, 'reset', '-q', '--hard', 'main')
    print('grafted', n, 'commits; head', head)


if __name__ == '__main__':
    main(*sys.argv[1:])
