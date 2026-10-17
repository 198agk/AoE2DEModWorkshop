# -*- coding: utf-8 -*-
"""Print the current family table verbatim, for updating test expectations.

Exists because the expectations in test_families.py are written as literals and
a rule change must be reflected there by measurement, not by editing numbers
until the test goes green.
"""
import collections
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod import api as A            # noqa: E402
from aoe2mod.dat import families as F   # noqa: E402

tk = A.open_toolkit()
tk._ensure()
F.warm(tk._stats, tk.game_root)
fam = F.build_families(tk._civs)
fams = sorted({tuple(v) for v in fam.values()}, key=lambda v: (-len(v), v[0]))
print("families %d  ids %d" % (len(fams), sum(len(v) for v in fams)))
print("size histogram: %s" % dict(sorted(
    collections.Counter(len(v) for v in fams).items())))
print()
by_id = {}
for c in tk._civs:
    for u in c.get("units") or ():
        by_id.setdefault(u.get("id"), u)
for t in fams:
    names = sorted({(by_id[i].get("name") or "?") for i in t if i in by_id})
    if len(t) >= 4:
        print("%-4d %s" % (len(t), list(t)))
        print("       names: %s" % ", ".join(names[:6]))
print()
for uid in (83, 293, 444, 1808, 2172, 2556):
    print("%-6s -> %s" % (uid, F.family_of(fam, uid)))
