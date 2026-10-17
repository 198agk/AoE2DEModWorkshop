"""Can these two cache files be written back byte-for-byte?

Nothing may edit them until this says yes.  The CivTechTrees writer taught the
lesson the hard way: `json.dumps(..., indent=2)` reproduced 60 of 62 files, and
the two that failed differed by 5 bytes because the game escapes an apostrophe as
a literal `\\u0027` while Python leaves `'`.  A near-match is the dangerous case --
it parses identically and differs in bytes nobody asked to change.

So: try the naive writer, then the candidate rule set, and report which one
reproduces ALL of it.  Report the first differing byte when it fails.

Run:  python _probe/probe_fu_serialize.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A  # noqa: E402
from aoe2mod.game import civtechtrees as CT  # noqa: E402

DAT_REL = os.path.join("resources", "_common", "dat")
FILES = ("futuravailableunits.json", "paphosfutureavailableunits.json")


def _strip_bom(raw):
    return raw[3:] if raw[:3] == b"\xef\xbb\xbf" else raw


def first_diff(a, b):
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i, a[max(0, i - 30):i + 30], b[max(0, i - 30):i + 30]
    if len(a) != len(b):
        return n, a[max(0, n - 30):n + 30], b[max(0, n - 30):n + 30]
    return None, b"", b""


def main():
    tk = A.open_toolkit()
    d = os.path.join(tk.game_root, DAT_REL)
    for name in FILES:
        path = os.path.join(d, name)
        raw = open(path, "rb").read()
        text = raw.decode("utf-8-sig")
        obj = json.loads(text)
        print("== %s" % name)
        print("   bytes %d  bom %s  crlf %d  lf-only %d  trailing-newline %s"
              % (len(raw), raw[:3] == b"\xef\xbb\xbf",
                 raw.count(b"\r\n"), raw.count(b"\n") - raw.count(b"\r\n"),
                 raw.endswith(b"\n")))
        print("   apostrophes in source: %d" % text.count("'"))
        print("   \\u0027 sequences    : %d" % text.count("\\u0027"))
        print("   other backslash-esc  : %s"
              % sorted({text[i:i + 6] for i in range(len(text))
                        if text[i] == "\\"} - {"\\u0027"})[:6])

        cands = {}
        base = json.dumps(obj, ensure_ascii=False, indent=2)
        cands["naive"] = base
        cands["naive+crlf"] = base.replace("\n", "\r\n")
        esc = base.replace("'", "\\u0027")
        cands["apos"] = esc
        cands["apos+crlf"] = esc.replace("\n", "\r\n")
        for label, s in cands.items():
            got = s.encode("utf-8")
            if got == raw:
                print("   MATCH (exact): %s" % label)
                break
            if got == _strip_bom(raw):
                print("   MATCH (modulo BOM): %s" % label)
                break
        else:
            label = "apos+crlf"
            off, ga, gb = first_diff(cands[label].encode("utf-8"), raw)
            print("   NO MATCH. first diff at %s for %r" % (off, label))
            print("     produced %r" % ga)
            print("     on disk  %r" % gb)

        # indent / key-order sanity
        print("   indent guess: first line %r" % text.split("\r\n")[0][:40])
        print()

    # ---- coverage: who is in NEITHER file -------------------------------
    fu = json.loads(open(os.path.join(d, FILES[0]), "rb")
                    .read().decode("utf-8-sig"))
    pap = json.loads(open(os.path.join(d, FILES[1]), "rb")
                     .read().decode("utf-8-sig"))
    trees = CT.load_trees(tk.game_root)
    stems = {CT.civ_file_stem(k): k for k in list(fu) + list(pap)}
    print("coverage of the 62 tree files by the two cache files:")
    missing = sorted(k for k in trees if k not in stems)
    print("  tree files with NO cache entry: %s" % missing)
    for m in missing:
        print("    %s -> futuravailableunits %s / paphos %s"
              % (m, m in {CT.civ_file_stem(k) for k in fu},
                 m in {CT.civ_file_stem(k) for k in pap}))
    print("  cache keys with no tree file: %s"
          % sorted(set(stems) - set(trees)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
