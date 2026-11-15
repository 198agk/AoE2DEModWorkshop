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
import _paths as P

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLE = P.BUNDLE
EXE = os.path.join(BUNDLE, 'aoe2-mod-workshop.exe')
PORT = 7824
BASE = 'http://127.0.0.1:%d' % PORT
TITLE = 'gate rebuild'
STALE_SHA = hashlib.sha256(b'stale').hexdigest()

# A GATE MUST NOT LEAVE ANYTHING IN THE PLAYER'S MOD LIST.
#
# This suite POSTs /api/build with install:true, which writes a real entry into
# mod-status.json.  Its `finally` only removed the folder, so every full-suite
# run left a "gate rebuild" row behind -- measured 2026-11-12: the run put it
# back at Priority 1, Enabled=true, beside a real player mod that had to share
# the list with it.  Point the whole server at a THROWAWAY profile instead: the
# install then lands there and dies with the temp dir.
TMP = os.path.join(os.environ.get("TEMP", "."), "aoe2mod-rebuild-installs")


def _sandbox():
    """A throwaway profile + state, both deleted by the caller."""
    if os.path.isdir(TMP):
        shutil.rmtree(TMP, ignore_errors=True)
    state = os.path.join(TMP, "_state")
    os.makedirs(state)
    with open(os.path.join(state, "builds.json"), "w", encoding="utf-8") as fh:
        fh.write('{"builds":{}}')
    # AN EMPTY PROFILE, NOT A COPY.  The player's mods folder is 2.5 GB
    # (161 MB local + 2.3 GB subscribed, measured 2026-11-12) and this suite
    # does not read a single one of those mods -- it only needs somewhere for
    # `install_mod` to write.  `find_profile_root` accepts any directory that
    # holds `mods/mod-status.json`, so an empty one is a complete profile and
    # the copy cost drops from minutes to nothing.
    app = os.path.join(TMP, "app")
    os.makedirs(os.path.join(app, "mods"))
    with open(os.path.join(app, "mods", "mod-status.json"), "w",
              encoding="utf-8") as fh:
        fh.write('{"Mods":[],"Unsub":[]}')
    env = dict(os.environ)
    env["AOE2MOD_PROFILE"] = app
    env["AOE2MOD_STATE"] = state
    env["AOE2MOD_BUILD_OUT"] = os.path.join(TMP, "out")
    env["AOE2MOD_STAT_OFFSETS"] = os.path.join(ROOT, "_golden", "stat_offsets.json")
    env["AOE2MOD_ENTITY_NAMES"] = os.path.join(ROOT, "_golden", "entity_names.json")
    return env

fails = []


def check(name, got, want, why=''):
    ok = got == want
    print('  %-46s %-22s %s' % (name, repr(got), 'ok' if ok else 'WANT %r' % (want,)))
    if not ok:
        fails.append('%s: %r != %r %s' % (name, got, want, why))


def post(path, body, timeout=900):
    # RETRY A RESET, ONCE.  Measured 2026-11-02: a full-suite run got
    # `ConnectionResetError [WinError 10054]` on one POST while the same file
    # passed on its own.  A reset means no answer was read, so a retry cannot
    # double-install (the build is keyed by TITLE and replaces its own folder) --
    # and after two failures this still raises, because a silent retry loop would
    # turn a broken server into a green suite.
    last = None
    for attempt in (1, 2):
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json'},
        )
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except ConnectionResetError as exc:            # noqa: PERF203
            last = exc
            if attempt == 1:
                print('  [retry] POST %s was reset, asking again' % (path,))
                time.sleep(2.0)
    raise last


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    if not os.path.isfile(EXE):
        sys.exit('no shipped exe: %s' % EXE)
    env = _sandbox()
    proc = subprocess.Popen(
        [EXE, '--port', str(PORT)],
        cwd=BUNDLE, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
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
        # The whole sandbox goes, not just the folder: the mod-status entry it
        # wrote lives inside TMP too, so the player's list is untouched.
        if TMP and os.path.isdir(TMP):
            shutil.rmtree(TMP, ignore_errors=True)

    print()
    if fails:
        print('VERDICT %d FAILED' % len(fails))
        for f in fails:
            print('  - %s' % f)
        sys.exit(1)
    print('VERDICT rebuild reaches the disk')


if __name__ == '__main__':
    main()
