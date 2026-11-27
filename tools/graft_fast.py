"""Like graft.py, but one git fast-import stream instead of several git calls per commit (for thousands of commits).

usage: python graft_fast.py <scratch repo> <live repo>
Every scratch commit on main whose (author date, subject) is not yet in the live history, and that changes a non-doc
path, is re-created on top of live main with the same author, dates and message; its tree change (diff against its
scratch parent, doc paths skipped) is applied to the live tree. Blobs come from the scratch repo (fetched first).
"""
import os, subprocess, sys
from pathlib import Path

SKIP = ('README.md', 'README.en.md', 'REPRODUCE.md', 'LICENSE', 'jurisdiction.json')
SKIP_DIRS = ('data/', 'tools/', 'visualisations/', 'vulnerabilities/')


def git(repo, *a, inp=None):
    r = subprocess.run(['git', '-C', str(repo), *a], capture_output=True, input=inp)
    if r.returncode:
        raise SystemExit(f'git {a}: {r.stderr.decode()}')
    return r.stdout.decode('utf-8')


def main(scratch, live):
    scratch, live = Path(scratch).resolve(), Path(live).resolve()
    have = set(git(live, 'log', '--format=%ad|%s', '--date=raw').splitlines())
    git(live, 'fetch', '-q', str(scratch), '+main:refs/build/main')
    # one log over the scratch history: header + raw diff per commit
    out = subprocess.run(['git', '-C', str(scratch), 'log', '--reverse', '--no-renames', '-r', '--raw', '--no-abbrev',
                          '--format=%x1e%H%x1f%P%x1f%an%x1f%ae%x1f%ad%x1f%cn%x1f%ce%x1f%cd%x1f%s%x1f%B%x1d',
                          '--date=raw', 'main'], capture_output=True).stdout.decode('utf-8')
    head = git(live, 'rev-parse', 'refs/heads/main').strip()
    stream = []
    n = 0
    for rec in out.split('\x1e')[1:]:
        hdr, _, diff = rec.partition('\x1d')
        h, parents, an, ae, ad, cn, ce, cd, subj, body = hdr.split('\x1f')
        if not parents or f'{ad}|{subj}' in have:
            continue
        ops = []
        for line in diff.strip('\n').splitlines():
            if not line.startswith(':'):
                continue
            meta, path = line.split('\t', 1)
            _, mode, _, sha, st = meta.split()
            if path in SKIP or path.startswith(SKIP_DIRS) or path.endswith('/README.md'):
                continue
            ops.append(f'D {path}' if st == 'D' else f'M {mode} {sha} {path}')
        if not ops:
            continue
        msg = body.encode('utf-8')
        stream.append(f'commit refs/heads/main\nauthor {an} <{ae}> {ad}\ncommitter {cn} <{ce}> {cd}\n'
                      f'data {len(msg)}\n'.encode('utf-8') + msg + b'\n')
        if n == 0:
            stream.append(f'from {head}\n'.encode())
        stream.append(('\n'.join(ops) + '\n\n').encode('utf-8'))
        n += 1
    if n:
        r = subprocess.run(['git', '-C', str(live), 'fast-import', '--quiet'], input=b''.join(stream),
                           capture_output=True)
        if r.returncode:
            raise SystemExit('fast-import: ' + r.stderr.decode())
        git(live, 'reset', '-q', '--hard', 'main')
    print('grafted', n, 'commits; head', git(live, 'rev-parse', 'HEAD').strip())


if __name__ == '__main__':
    main(*sys.argv[1:])
