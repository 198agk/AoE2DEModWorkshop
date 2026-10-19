# -*- coding: utf-8 -*-
"""probe_icon_cases.py -- what icon_id do the entities I am LOOKING at actually have?

probe_icon_look.py took icon_id == unit id as a shortcut.  That assumption is
exactly the kind of thing this project keeps getting burned by, so measure it:
print id / type / name / icon_id for the handful of entities under discussion.
"""
from __future__ import print_function

import codecs
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(HERE, "semantic"))

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")

WANT = [12, 70, 71, 50, 82, 83, 74, 4, 42, 263, 682, 109, 234, 889, 1193, 182]


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L
    import strings_db as S

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    zh = {}
    base = os.path.join(GAME, "resources", "zh", "strings", "key-value")
    for name in S.KV_FILES:
        fp = os.path.join(base, name)
        if os.path.exists(fp):
            zh.update(S.parse_kv_file(fp)[0])

    by_id = {}
    for civ in civs:
        for u in civ.get("units") or []:
            by_id.setdefault(u.get("id"), u)
    print("records: %d" % len(by_id))
    for i in WANT:
        u = by_id.get(i)
        if not u:
            print("  %-5d <missing>" % i)
            continue
        print("  id=%-5d type=%-3s icon_id=%-5s name=%-20r zh=%r"
              % (i, u.get("type"), u.get("icon_id"), u.get("name"),
                 zh.get(u.get("_dll_name"))))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
