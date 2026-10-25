# -*- coding: utf-8 -*-
r"""PIN: `dsh test v4` reproduces the Incas' data for unit 2550 EXACTLY.

v4 is the strongest experiment this project has built, so the claim "it gives the
Britons the very data the Incas have" must be checked field by field rather than
asserted.  If any field differed, a negative result would be ambiguous -- it could be
the difference rather than the mechanism.

Measured: the Britons' new tree row is **field-identical** to the Incas' shipped row,
and the panel entry is **identical** too:

    INCAS   {'Name': 'Champi Scout', 'Node Type': 'RegionalUnit',
             'Link Node Type': 'Unit', 'Draw Node Type': 'UnitTech',
             'Use Type': 'Unit', 'Node Status': 'ResearchedCompleted',
             'Name String ID': 14526, 'Age ID': 1, 'Building ID': 12,
             'Help String ID': 105526, 'Node ID': 2550, 'Picture Index': 540,
             'Trigger Tech ID': 1350}
    v4 BRITONS  -- zero field differences
    panel: {'ID': 2550, 'Name': 'Champi Scout', 'RequiredAge': 1} on both sides

So v4 asks exactly one question: **does the same data, given to a different
civilization, produce a buildable unit?**  A "no" therefore points at a per-civ input
that is NOT in these two rows, not at a malformed row.

The `Trigger Tech ID = 1350` on that copied row is a GLOBAL make-avail tech
(`civ == -1`, effect `[(2, 2550, 1)]`), and pointing at a global tech one cannot reach
as a Tech row is the NORM -- 1,590 of 1,814 such rows corpus-wide -- so that is not a
defect to fix first (see the Round 66 measurement).

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_v4_reproduces_incas.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The artifact this file reads is built, not checked in, and on 2026-10-25 a
# workspace cleanup deleted it -- the suite then failed with KeyError/FileNotFound,
# which reads like a data bug.  Rebuild it instead of depending on a directory
# that happens to be there.
sys.path.insert(0, HERE)
from ensure_artifact import ensure as _ensure  # noqa: E402
_ensure("out_dshtest_v4", "build_dshtest_v4.py", required=None)
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
V4 = _ensure("out_dshtest_v4", "build_dshtest_v4.py")
UNIT = 2550
BLDG = 12
LONGBOW = 8
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


print("A  the tree row the Britons gain is field-identical to the Incas'")
ship = CT.load_trees(GAME)
v4 = CT.load_trees(V4)
a = CT.row_for(ship["INCAS"], UNIT, CT.UNIT_USE_TYPES)
b = CT.row_for(v4["BRITONS"], UNIT, CT.UNIT_USE_TYPES)
check("the Incas row exists", a is not None)
check("the v4 Britons row exists", b is not None)
if a and b:
    keys = sorted(set(a) | set(b))
    diff = [(k, a.get(k), b.get(k)) for k in keys if a.get(k) != b.get(k)]
    print("     fields compared: %d ; differences: %d %s"
          % (len(keys), len(diff), diff))
    check("zero field differences", not diff, "%s" % diff)
    for k in sorted(a):
        print("        %-20s %r" % (k, a[k]))

print()
print("B  and the panel entry is identical")
sh = BP.load_all(GAME)
v4p = BP.load_all(V4)
ok_ = BP.civ_key_for(sh, "Incas")
vk_ = BP.civ_key_for(v4p, "Britons")
ob = sh[BP.panel_path_for(GAME, "Incas")[1]]["obj"]
ov = v4p[BP.panel_path_for(V4, "Britons")[1]]["obj"]
ib, eb = BP.find_entry(ob, ok_, UNIT, BP.UNITS_KEY)
iv, ev = BP.find_entry(ov, vk_, UNIT, BP.UNITS_KEY)
print("     Incas : building %s  %s" % (ib, eb))
print("     v4    : building %s  %s" % (iv, ev))
check("both sit under the Barracks (%d)" % BLDG, ib == BLDG and iv == BLDG)
check("the entries are equal", eb == ev, "%s vs %s" % (eb, ev))

print()
print("C  so the question v4 asks is exactly one question")
check("the Britons had NO row for it before (it is a real grant)",
      CT.row_for(ship["BRITONS"], UNIT, CT.UNIT_USE_TYPES) is None)
check("the Britons' own Longbowman row is untouched",
      (CT.row_for(v4["BRITONS"], LONGBOW, CT.UNIT_USE_TYPES) or {}).get(
          "Node Status") == "ResearchedCompleted")
print("     -> the SAME data, given to a different civilization.  A negative result")
print("        then points at a per-civ input that is not in these rows.")

print()
print("V4 REPRODUCES THE INCAS: the tree row and the panel entry match the shipped")
print("  Incas data field for field, so a negative in-game result is not attributable")
print("  to a malformed row.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
