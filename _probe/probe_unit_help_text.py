# -*- coding: utf-8 -*-
"""probe_unit_help_text.py -- is there unit prose to show at all?

A panel that explains a unit wants a sentence per unit.  `unit_names.json` holds
names only, so the only candidate source is `LanguageDLLHelp` on the unit record
(Unit.cpp:125).  It used to be read and thrown away; `aoe2mod/dat/locate.py` now
keeps it as `_dll_help`.

This probe measures whether those ids actually exist in the shipped string
tables.  The research note said the 107xxx ids are absent for TECH help; if that
also holds for units, the UI must say "this build ships no description" rather
than put an empty box on screen.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

    tables = {}
    for lang in ("en", "zh"):
        t = {}
        d = os.path.join(GAME, "resources", lang, "strings", "key-value")
        for name in S.KV_FILES:
            fp = os.path.join(d, name)
            if os.path.exists(fp):
                t.update(S.parse_kv_file(fp)[0])
        tables[lang] = t

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    has = [u for u in by_id.values() if (u.get("_dll_help") or 0) > 0]
    print("units: %d, with a nonzero LanguageDLLHelp: %d" % (len(by_id), len(has)))
    if not has:
        print("=> no unit carries a help id; a description panel has nothing to read")
        return 0

    ids = sorted({u["_dll_help"] for u in has})
    print("distinct help ids: %d; range %s..%s" % (len(ids), ids[0], ids[-1]))
    for lang in ("en", "zh"):
        t = tables[lang]
        hit = [i for i in ids if i in t]
        print("  %s: %d / %d resolve" % (lang, len(hit), len(ids)))
    print("\nsample:")
    for uid in sorted(by_id)[:0] or [83, 74, 4, 2550, 82, 12]:
        u = by_id.get(uid) or {}
        hid = u.get("_dll_help")
        name = tables["zh"].get(u.get("_dll_name")) or ""
        zh = tables["zh"].get(hid) if hid else None
        en = tables["en"].get(hid) if hid else None
        print("  unit %-5s %-12r help=%-8s zh=%r"
              % (uid, name[:12], hid, (zh or "")[:60]))
        print("        en=%r" % ((en or "")[:70],))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
