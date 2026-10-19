# -*- coding: utf-8 -*-
"""probe_unit_help_pattern.py -- is the help id just name id + 100000?

probe_unit_help_text.py measured: 2,690 units carry a LanguageDLLHelp id, and
1 of 684 distinct ids resolves in either shipped string table.  The samples look
arithmetic -- name 5121 (Villager) -> help 105121, name 5079 (Militia) -> 105079.

If help == name + 100000 for every unit, then the id is DERIVED, and the absence
of the text is a fact about this build rather than a parsing mistake.  A panel
must then show the shipped stats and say it has no prose, instead of printing an
id or an empty box.
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

    zh = {}
    d = os.path.join(GAME, "resources", "zh", "strings", "key-value")
    for name in S.KV_FILES:
        fp = os.path.join(d, name)
        if os.path.exists(fp):
            zh.update(S.parse_kv_file(fp)[0])

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)

    same = diff = zero = 0
    examples = []
    for uid, u in by_id.items():
        h = u.get("_dll_help") or 0
        n = u.get("_dll_name") or 0
        if h == 0:
            zero += 1
            continue
        if h == n + 100000:
            same += 1
        else:
            diff += 1
            if len(examples) < 12:
                examples.append((uid, n, h, h - n))

    print("units %d: help == name+100000 for %d, differs for %d, none for %d"
          % (len(by_id), same, diff, zero))
    print("\nwhere it differs (unit, name, help, help-name):")
    for e in examples:
        print("  %-6s name=%-8s help=%-9s delta=%s   name_zh=%r"
              % (e[0], e[1], e[2], e[3], (zh.get(e[1]) or "")[:20]))

    resolved = sorted(i for i in zh if isinstance(i, int) and i in
                      {u.get("_dll_help") for u in by_id.values() if u.get("_dll_help")})
    print("\nhelp ids that DO resolve: %s" % resolved[:5])
    for i in resolved[:5]:
        print("   %s -> %r" % (i, zh[i]))

    band = [i for i in zh if isinstance(i, int) and 105000 <= i < 106000]
    print("\nstrings in the 105xxx band: %d" % len(band))
    band2 = [i for i in zh if isinstance(i, int) and 100000 <= i < 200000]
    print("strings anywhere in 100xxx..199999: %d" % len(band2))
    print("lowest 5 in that band: %s" % sorted(band2)[:5])
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
