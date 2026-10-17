# -*- coding: utf-8 -*-
"""Inspect existing Effect command shapes so the append demo can mirror a real
resource-adding effect instead of guessing the command-type enum.
"""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import contextlib
import io
import sys
from collections import Counter

sys.path.insert(0, _HERE_PATH("_probe", "datparse"))
sys.path.insert(0, _HERE_PATH("_probe", "serializer"))

import parse_dat
import write_dat

BASE = (r"D:\Games\Steam\steamapps\common\AoE2DE\resources\_common\dat"
        r"\empires2_x2_p1.dat")

def main():
    raw, how = write_dat.load_dat(BASE)
    p = parse_dat.Parser(raw)
    with contextlib.redirect_stdout(io.StringIO()):
        st = p.parse()

    effs = st["effects"]
    print("effects: %d" % len(effs))
    types = Counter()
    for e in effs:
        for c in e["commands"]:
            types[c[0]] += 1
    print("command type histogram (type -> count):")
    for t, n in sorted(types.items()):
        print("   type %-4d %8d" % (t, n))
    print()

    # effects whose commands look like 4 resource entries (A in 0..3, D = amount)
    print("candidate resource-adding effects (all cmds type 1, A in 0..3):")
    shown = 0
    for i, e in enumerate(effs):
        cs = e["commands"]
        if not cs or len(cs) > 6:
            continue
        if all(c[0] == 1 and 0 <= c[1] <= 3 for c in cs):
            print("   effect[%d] name=%r" % (i, e["name"]))
            for c in cs:
                print("      type=%d A=%d B=%d C=%d D=%s" % c)
            shown += 1
            if shown >= 4:
                break
    if shown == 0:
        print("   none found; dumping 3 arbitrary effects")
        for i, e in enumerate(effs[:3]):
            print("   effect[%d] name=%r" % (i, e["name"]))
            for c in e["commands"]:
                print("      type=%d A=%d B=%d C=%d D=%s" % c)
    print()

    # what do techs look like?
    print("first 3 techs:")
    for i, t in enumerate(st["techs"][:3]):
        print("   tech[%d] civ=%s effect_id=%s type=%s icon=%s name=%r locs=%s"
              % (i, t["civ"], t["effect_id"], t["type"], t["icon_id"],
                 t["name"], t["research_locations"]))
    print()
    print("last tech: %r" % (st["techs"][-1],))
    print("counts: effects stored=%s effect_count=%s techs stored=%s tech_count=%s"
          % (len(st["effects"]), st.get("effect_count"),
             len(st["techs"]), st.get("tech_count")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
