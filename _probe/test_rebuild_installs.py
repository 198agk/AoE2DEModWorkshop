"""Rebuilding a mod must put the rebuilt bytes back where the mod lives.

`/api/rebuild` exists to fix a mod that went stale after a game update.  It
answered `ok: true` with a fresh `edit_count` while never touching the installed
file: `replay` did not pass `install`, so the build landed in a temp folder, and
it built under `"<stat> <unit>"` rather than the record's title, so even an
install would have created a second folder beside the stale one.

Both defects were invisible from the response.  This gate looks at the file.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLE = r'D:\Software\AI\AoE2ModWorkshop'
EXE = os.path.join(BUNDLE, 'aoe2-mod-workshop.exe')
PORT = 7824
BASE = 'http://127.0.0.1:%d' % PORT
TITLE = 'gate rebuild'
STALE_SHA = hashlib.sha256(b'stale').hexdigest()

fails = []


def check(name, got, want, why=''):
    ok = got == want
    print('  %-46s %-22s %s' % (name, repr(got), 'ok' if ok else 'WANT %r' % (want,)))
    if not ok:
        fails.append('%s: %r != %r %s' % (name, got, want, why))


def post(path, body, timeout=900):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'},
    )
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    if not os.path.isfile(EXE):
        sys.exit('no shipped exe: %s' % EXE)
    proc = subprocess.Popen(
        [EXE, '--port', str(PORT)],
        cwd=BUNDLE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    installed = None
    try:
        for _ in range(180):
            try:
                p = (json.load(urllib.request.urlopen(BASE + '/api/progress', timeout=2))
                     .get('progress') or {})
                if p.get('ready') or p.get('error'):
                    break
            except Exception:
                pass
            time.sleep(1)
        if not p.get('ready'):
            sys.exit('never became ready: %r' % (p,))

        # A scoped edit, because the scope is part of what a replay must preserve.
        built = post('/api/build', {
            'intent': 'unit.stat', 'unit': 1810, 'stat': 'hit_points',
            'value': 120, 'civs': ['British'], 'title': TITLE, 'install': True,
        })
        installed = built.get('installed') or ''
        check('build installed somewhere', bool(installed), True)
        if not installed or not os.path.isdir(installed):
            sys.exit('build did not install: %r' % (built,))
        dat = os.path.join(installed, 'resources', '_common', 'dat', 'empires2_x2_p1.dat')
        check('  .dat on disk', os.path.isfile(dat), True)
        original = sha(dat)
        check('  scoped to one civ', built.get('civs'), 1)
        check('  edit count', built.get('edit_count'), 27)

        # Make it stale the way a game update would: the file is no longer ours.
        with open(dat, 'wb') as f:
            f.write(b'stale')
        check('the file was replaced', sha(dat) != original, True)

        out = post('/api/rebuild', {'title': TITLE})
        rebuilt = out.get('rebuilt') or {}
        check('rebuild reported ok', out.get('ok'), True)
        check('  edit count', rebuilt.get('edit_count'), 27)
        check('  still scoped to one civ', rebuilt.get('civs'), 1)

        # The claim under test: the file the game reads is the rebuilt one.
        after = sha(dat)
        check('the installed file was rewritten', after != STALE_SHA, True)
        check('  byte-identical to the first build', after, original)
        check('  no second folder beside it',
              os.path.isdir(os.path.dirname(installed)), True)
        siblings = [d for d in os.listdir(os.path.dirname(installed))
                    if d.startswith('hit_points') or d.startswith('unit.stat')]
        check('  no "<stat> <unit>" leftover', siblings, [])
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
        if installed and os.path.isdir(installed):
            shutil.rmtree(installed, ignore_errors=True)

    print()
    if fails:
        print('VERDICT %d FAILED' % len(fails))
        for f in fails:
            print('  - %s' % f)
        sys.exit(1)
    print('VERDICT rebuild reaches the disk')


if __name__ == '__main__':
    main()
