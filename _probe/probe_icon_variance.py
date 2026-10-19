# -*- coding: utf-8 -*-
"""probe_icon_variance.py -- does icon_id vary across civilizations?

The semantic layer keys entities by `id` and keeps per-civilization variants in
`civ_variants`.  An icon is only storable on that key if every civilization's
record for that id agrees on it.  This probe measures that before the icon layer
is designed, because discovering it later means the schema is wrong.
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

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
DAT = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")


def main():
    from aoe2mod.dat import parser as P
    from aoe2mod.dat import locate as L

    data, how = P.load_dat(DAT)
    p = P.Parser(data)
    with contextlib.redirect_stdout(io.StringIO()):
        p.parse()
    civs, start, gv, tail = L.locate(data, parser=p)

    icon = {}
    types = {}
    civson = {}
    for civ in civs:
        idx = civ.get("civ")
        for u in civ.get("units") or []:
            uid = u.get("id")
            icon.setdefault(uid, {})[idx] = u.get("icon_id")
            types.setdefault(uid, {})[idx] = u.get("type")
            civson.setdefault(uid, set()).add(idx)

    multi = {k: v for k, v in icon.items() if len(set(v.values())) > 1}
    print("unit ids seen: %d" % len(icon))
    print("ids whose icon_id differs between civilizations: %d" % len(multi))
    for k in sorted(multi)[:15]:
        vals = multi[k]
        pairs = sorted(set(vals.values()))
        print("  unit %-5s icon values %s (%d civs)"
              % (k, pairs, len(vals)))
    multi_t = {k: v for k, v in types.items() if len(set(v.values())) > 1}
    print("ids whose TYPE differs between civilizations: %d" % len(multi_t))

    per_civ = {}
    for uid, s in civson.items():
        per_civ[len(s)] = per_civ.get(len(s), 0) + 1
    print("how many civilizations declare each unit id: %s"
          % sorted(per_civ.items())[:8])

    # do tech records carry an icon id per civ too?
    from aoe2mod.semantic import index as SI
    ix = SI.index()
    t = ix.techs.get(22)
    print("\ntech 22 (%r) _extra keys: %s"
          % (t.en if t else None, sorted((t._extra or {}).keys()) if t else None))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    except Exception:
        pass
    sys.exit(main())
