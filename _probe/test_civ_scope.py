"""A sentence that names a civilisation must not edit all 63 of them.

The failure this gate exists for was silent in every observable way: the server
returned 200, the intent looked right, the edit count was a plausible number --
and the player who typed 「不列颠村民血量改成100」 got a mod that changed every
civilisation's villager.  Nothing in `/api/parse`, `/api/stat` or the page said
so.  Only asking 「is the number in the file the number the sentence asked for」
exposes it, which is what this file does.

Every number here has a Python baseline measured through
`aoe2mod.ui.server.App().parse` / `.build`, so a change in the intent compiler
shows up as a disagreement rather than as a new truth.
"""
import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUNDLE = r'D:\Software\AI\AoE2ModWorkshop'
EXE = os.path.join(BUNDLE, 'aoe2-mod-workshop.exe')
PORT = 7817
BASE = 'http://127.0.0.1:%d' % PORT

fails = []


def check(name, got, want, why=''):
    ok = got == want
    print('  %-46s %-22s %s' % (name, repr(got), 'ok' if ok else 'WANT %r' % (want,)))
    if not ok:
        fails.append('%s: %r != %r %s' % (name, got, want, why))
    return ok


def post(path, body, timeout=600):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'},
    )
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def wait_ready():
    for _ in range(180):
        try:
            j = json.load(urllib.request.urlopen(BASE + '/api/progress', timeout=2))
            p = j.get('progress') or {}
            if p.get('ready') or p.get('error'):
                return p
        except Exception:
            pass
        time.sleep(1)
    return {}


def raw_of(built_dir):
    """The .dat the game will read, decompressed, as bytes.

    Searched rather than assumed: the build places it under
    `resources/_common/dat` relative to whichever root it chose, and the two
    implementations do not agree on whether that root is `out_dir` or
    `out_dir/<title>`.  Walking for the filename is the only version that does
    not bake one of their conventions into the gate.
    """
    for root, _dirs, files in os.walk(built_dir):
        if 'empires2_x2_p1.dat' in files:
            with open(os.path.join(root, 'empires2_x2_p1.dat'), 'rb') as f:
                return zlib.decompress(f.read(), -15)
    raise SystemExit('no .dat under %s' % built_dir)


def parse_intent(text):
    j = post('/api/parse', {'text': text})
    intents = j.get('intents') or []
    return (intents[0] if intents else None), j


def main():
    if not os.path.isfile(EXE):
        sys.exit('no shipped exe: %s' % EXE)
    proc = subprocess.Popen(
        [EXE, '--port', str(PORT)],
        cwd=BUNDLE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        p = wait_ready()
        if not p.get('ready'):
            sys.exit('never became ready: %r' % (p,))

        print('scope, read from the sentence')
        # The sentence layer must carry the civilisation, or nothing downstream
        # can scope.  The .dat spelling is the contract (`British`, not `BRITONS`).
        for text, want in [
            ('不列颠村民血量改成100', ['British']),
            ('不列颠和法兰克的村民血量改成1000', ['British', 'French']),
            ('中国城镇中心视野加2', ['Chinese']),
        ]:
            it, j = parse_intent(text)
            check('civs of 「%s」' % text, (it or {}).get('civs'), want)
            notes = [c.get('notes') for c in (j.get('clauses') or [])]
            check('  notes say not-all-civs', bool(notes and notes[0]), True)

        # An unscoped sentence must stay unscoped: adding a scope where the
        # player said nothing would be the same defect pointing the other way.
        it, _ = parse_intent('村民血量改成100')
        check('no civs when none named', 'civs' in (it or {}), False)

        # A civilisation name that is also a technology (「不列颠」 is tech 529)
        # must not turn 「不列颠兵营攻击力加5」 into an edit of the technology.
        it, _ = parse_intent('不列颠兵营攻击力加5')
        check('兵营 wins over tech 529', (it or {}).get('unit'), 12)
        it, _ = parse_intent('不列颠研究时间改成5')
        check('研究 hint keeps tech 529', (it or {}).get('tech'), 529)

        print('scope, measured in the file')
        # 27 villager records x 1 civilisation.  The baseline comes from Python.
        all63 = post('/api/stat', {'stat': 'hit_points', 'unit': 1810, 'value': 100})
        check('all 63 civilisations', all63.get('edit_count'), 1701)
        check('  spans 63 civ records', all63.get('civs'), 63)

        one = post('/api/stat', {'stat': 'hit_points', 'unit': 1810,
                                 'value': 100, 'civs': ['British']})
        check('British only', one.get('edit_count'), 27)
        check('  spans 1 civ record', one.get('civs'), 1)
        check('  bytes touched', one.get('bytes_changed'), 27)

        two = post('/api/stat', {'stat': 'hit_points', 'unit': 1810,
                                 'value': 100, 'civs': ['British', 'French']})
        check('British + French', two.get('edit_count'), 54)
        check('  spans 2 civ records', two.get('civs'), 2)

        # A stat stored twice (panel number + the row the damage maths reads)
        # must move BOTH in scope: 2 variants x 2 places x 1 civ.
        castle = post('/api/stat', {'stat': 'displayed_attack', 'unit': 82,
                                    'value': 20, 'civs': ['British']})
        check('castle attack, 1 civ', castle.get('edit_count'), 4)
        check('  one of those is a mirror', castle.get('mirror_count'), 2)

        # Naming a civilisation that does not exist is a refusal that names it.
        # Reporting "no unit has this stat" instead would send the player to
        # look for the wrong problem.
        bad = post('/api/stat', {'stat': 'hit_points', 'unit': 1810,
                                 'value': 100, 'civs': ['Atlantis']})
        check('unknown civ refused', bad.get('ok'), False)
        check('  name in the reason', 'Atlantis' in (bad.get('error') or ''), True)

        print('scope, proven byte for byte against Python')
        # The only claim that cannot be faked by counting: the same sentence in
        # both implementations produces the same 93 MB of bytes.
        rust = post('/api/build', {'intent': 'unit.stat', 'unit': 1810,
                                   'stat': 'hit_points', 'value': 100,
                                   'civs': ['British'], 'title': 'civscope_gate'})
        rust_raw = hashlib.sha256(raw_of(rust['built'])).hexdigest()

        sys.path.insert(0, ROOT)
        import tempfile
        import aoe2mod.api as A
        tk = A.open_toolkit()
        tk._ensure()
        out = os.path.join(tempfile.gettempdir(), 'civscope_gate_py_%d' % int(time.time()))
        tk.build({'intent': 'unit.stat', 'unit': 1810, 'stat': 'hit_points',
                  'value': 100, 'civs': ['British']},
                 title='civscope_gate_py', author='aoe2mod', out_dir=out,
                 overwrite=True)
        py_raw = hashlib.sha256(raw_of(out)).hexdigest()
        check('Rust == Python bytes', rust_raw == py_raw, True,
              'rust %s py %s' % (rust_raw[:16], py_raw[:16]))
        print('  %s' % rust_raw)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    print()
    if fails:
        print('VERDICT %d FAILED' % len(fails))
        for f in fails:
            print('  - %s' % f)
        sys.exit(1)
    print('VERDICT all scoped correctly')


if __name__ == '__main__':
    main()
