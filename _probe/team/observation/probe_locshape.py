"""Introspect locate()'s civ record shape, then run the barracks-unit census."""

import os as _os
_HERE_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
_ROOT_PATH = lambda *p: _os.path.join(
    _os.path.dirname(_os.path.abspath(__file__)), *p)
import json
import os
import sys

sys.path.insert(0, _HERE_PATH("..", "..", ".."))
ROOT = r"D:\Games\Steam\steamapps\common\AoE2DE"
from aoe2mod.dat import parser as P, locate

data, how = P.load_dat(os.path.join(ROOT, "resources", "_common", "dat", "empires2_x2_p1.dat"))
p = P.Parser(data)
p.parse()
loc = locate.locate(data, parser=p)
print("locate() returns a %d-tuple" % len(loc))
civs = loc[0]
print("civs type=%s len=%s" % (type(civs).__name__, len(civs)))
c0 = civs[0]
print("civs[0] type=%s" % type(c0).__name__)
if isinstance(c0, dict):
    print("  keys:", sorted(c0.keys())[:20])
    for k, v in c0.items():
        if isinstance(v, list):
            print("  %-20s list[%d]" % (k, len(v)))
        else:
            print("  %-20s %r" % (k, v))
else:
    print("  value: %r" % (c0,))
    print("  len:", len(c0))

# figure out how to iterate units
units = None
if isinstance(c0, dict):
    for k in ("units", "unit_list", "objects"):
        if k in c0:
            units = c0[k]
            break
print("\nunits container:", type(units).__name__, len(units) if units is not None else None)
if units:
    u = units[0]
    print("unit keys:", sorted(u.keys()))
    print("sample unit:", {k: u[k] for k in ("id", "name") if k in u})
    print("train_locations sample:", u.get("train_locations"))
