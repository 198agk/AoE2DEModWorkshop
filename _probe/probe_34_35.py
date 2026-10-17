# -*- coding: utf-8 -*-
r"""Why do techs 34 and 35 appear as tree Tech rows when 134 other unit-upgrade
technologies do not?

`test_trigtech_space.py` asserted "no unit-upgrade technology is ever a tree Tech
row" and it FAILED on exactly two ids: 34 and 35.  Two explanations:

  (a) the ship-upgrade line really is represented as researchable techs in the tree
      (unlike the land-unit lines), or
  (b) ids 34/35 in the tree's Tech space are DIFFERENT technologies than .dat techs
      34/35 (War Galley / Galleon), i.e. the same "two id spaces share an integer"
      trap that has bitten this project before.

Decide by identity, not by counting.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
LANG = {}
kd = os.path.join(GAME, "resources", "en", "strings", "key-value")
for fn in sorted(os.listdir(kd)):
    if fn.endswith(".txt"):
        for line in open(os.path.join(kd, fn), "rb").read().decode(
                "utf-8-sig", "replace").splitlines():
            k, _, v = line.strip().partition("\t")
            if k.strip().isdigit() and v.startswith('"') and v.endswith('"'):
                LANG.setdefault(int(k.strip()), v[1:-1])

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
_techs = tk._tech_records()
trees = CT.load_trees(GAME)


def dat_tech(tid):
    t = _techs[tid] if tid < len(_techs) else None
    if not t:
        return None, None
    sid = t.get("LanguageDLLName")
    return t.get("name"), (LANG.get(sid) if sid else None)


print("A  what .dat techs 34 and 35 are")
for tid in (34, 35):
    print("   .dat tech %-4s internal=%r name=%r" % (tid, *dat_tech(tid)))

print()
print("B  which trees carry a Tech row for 34 / 35, and what does that row say?")
for tid in (34, 35):
    civs = []
    for s, t in sorted(trees.items()):
        r = CT.row_for(t, tid, CT.TECH_USE_TYPES)
        if r is not None:
            civs.append((s, r.get("Node Status"), r.get("Age ID"),
                         r.get("Building ID"), r.get("Name"),
                         r.get("Name String ID")))
    print("   tech %-4s appears in %d tree(s)" % (tid, len(civs)))
    for s, st, age, bid, nm, sid in civs:
        loc = LANG.get(sid) if sid else None
        print("      %-12s status=%-18s age=%s bldg=%-5s Name=%-22r localized=%r"
              % (s, st, age, bid, nm, loc))

print()
print("C  the decisive comparison: does the tree's row for 34 describe the SAME")
print("   thing as .dat tech 34?  Compare its Name String ID to the .dat's")
print("   LanguageDLLName and to the +10000 localized block.")
for tid in (34, 35):
    dt_name, dt_loc = dat_tech(tid)
    t = _techs[tid]
    dll = t.get("LanguageDLLName")
    print("   tech %-4s .dat LanguageDLLName=%s (localized=%r)  +10000=%r"
          % (tid, dll, dt_loc, LANG.get(dll + 10000) if dll else None))
    for s, _st, _a, _b, nm, sid in [(c[0], c[1], c[2], c[3], c[4], c[5])
                                    for c in [(s, r.get("Node Status"),
                                               r.get("Age ID"), r.get("Building ID"),
                                               r.get("Name"), r.get("Name String ID"))
                                              for s, t2 in sorted(trees.items())
                                              for r in [CT.row_for(t2, tid,
                                                                   CT.TECH_USE_TYPES)]
                                              if r is not None]]:
        print("      tree %-12s Node ID=%s Name String ID=%s  == dat DLL? %s"
              % (s, tid, sid, sid == dll))

print()
print("D  how many unit-upgrade techs appear as tree Tech rows, by building")
trigger = set()
for t in trees.values():
    for r in CT.unit_rows(t):
        tt = r.get("Trigger Tech ID")
        if tt is not None:
            trigger.add(tt)
withrow = sorted(x for x in trigger
                 if any(CT.node_status(t, x, CT.TECH_USE_TYPES) is not None
                        for t in trees.values()))
print("   distinct unit-upgrade tech ids referenced by unit rows : %d" % len(trigger))
print("   of those, ids that also exist as a tree Tech row       : %d %s"
      % (len(withrow), withrow))
print()
print("E  are 34/35 the ONLY exceptions?  And is the rule instead:")
print("   'a unit-upgrade tech is a tree Tech row only when it ALSO upgrades a")
print("    unit that is NOT itself in the tree's unit rows' chain'?")
print("   Check: which units does .dat tech 34/35 upgrade?")
for tid in (34, 35):
    t = _techs[tid]
    print("      tech %-4s civ=%s  (see also unit rows referencing it)"
          % (tid, t.get("civ")))
    owners = [s for s, tr in trees.items()
              if any((r.get("Trigger Tech ID") == tid) for r in CT.unit_rows(tr))]
    print("         unit rows referencing it as Trigger Tech ID: %d civs" % len(owners))
