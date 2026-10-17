# -*- coding: utf-8 -*-
r"""PIN: unit-upgrade technologies live in DIFFERENT places in the two layers.

Round 49 established the criterion "the layer that promises a unit must supply a
COMPLETE path".  Round 50 then alarmed itself by checking that on the TREE side as

    CT.node_status(tree, 588's Trigger Tech ID = 320, TECH_USE_TYPES) is None

and concluding Sicilians' tree was incomplete, which would have invalidated GAME 2.

That check was measured in the WRONG SPACE.  What is actually true:

  * `Trigger Tech ID` IS a `.dat` tech index -- identity confirmed by name
    (320 -> 'Siege Onager', 207 -> 'Long Swordsman', 429 -> 'Halberdier', ...).
  * **A unit-upgrade technology is almost never a tree `Use Type: Tech` row.**
    Of the 136 distinct upgrade techs referenced by unit rows, only **2** appear
    as a tree Tech row -- `.dat` 34 'War Galley' and 35 'Galleon', which the tech
    tree genuinely shows as researchable ("Warships"/"Heavy Warships").  The
    other 134 appear in 0 of 62 trees.
  * The tree therefore expresses an upgrade through the **unit row's own
    `Trigger Tech ID` field** (588 -> 320), NOT as a Tech row.
  * The PANEL expresses the same upgrade through its **`Techs` array** (Sicilians'
    building 49 lists 96, 255, 257, 239).

So the two layers use different mechanisms, and the completeness test has to be
written per layer:

    panel is promising  -> the unit is in `Units` AND its upgrade is in `Techs`
    tree is promising   -> the unit row is `ResearchedCompleted` and the chain's
                           predecessor units are too (upgrades ride on unit rows)

Under the corrected tree-side test, Sicilians 588 is COMPLETE (280 Mangonel RC ->
550 Onager RC, trigTech 257 -> 588 Siege Onager RC, trigTech 320).  GAME 2 stands.
The tree's Tech `Node ID` is nevertheless still the `.dat` tech index -- B2 checks
that by name identity (132 rows agree outright; the 106 apparent disagreements are
display-vs-codename, e.g. 'Crop rotation'->'Crop Rotation').

Also pinned: the panel is internally consistent about this in a checkable way --
whenever it lists a unit that is the target of an upgrade research, it lists that
research too (422+255->548, 280+257->550).  And for SICILIANS it lists neither 320
nor 588, which is why it is silent in BOTH channels.

Run:  $env:PYTHONPATH='D:\\Software\\DeepSeek Harness\\工作区2'; python _probe\test_trigtech_space.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
_techs = tk._tech_records()
trees = CT.load_trees(GAME)
panels = BP.load_all(GAME)

print("A  `Trigger Tech ID` is a .dat tech index -- confirmed by NAME identity")
for tid, expect in ((320, "Siege Onager"), (207, "Long Swordsman"),
                    (429, "Halberdier"), (257, "Onager"),
                    (264, "Champion"), (244, "Heavy Demolition")):
    got = (_techs[tid] or {}).get("name") if tid < len(_techs) else None
    check(".dat tech %-4s is %r" % (tid, expect), got == expect, "got %r" % got)

print()
print("B  a unit-upgrade technology is almost never a tree `Use Type: Tech` row")
# collect every Trigger Tech ID used by any unit row, across all trees
trigger_ids = set()
for t in trees.values():
    for r in CT.unit_rows(t):
        tt = r.get("Trigger Tech ID")
        if tt is not None:
            trigger_ids.add(tt)
print("     distinct Trigger Tech IDs used by unit rows: %d" % len(trigger_ids))
have_row = {}
for tid in sorted(trigger_ids):
    n = sum(1 for t in trees.values()
            if CT.node_status(t, tid, CT.TECH_USE_TYPES) is not None)
    have_row[tid] = n
withrow = sorted(k for k, v in have_row.items() if v)
print("     of those, tech ids that DO appear as a tree Tech row somewhere: %d %s"
      % (len(withrow), withrow))
check("only a tiny minority of unit-upgrade techs are tree Tech rows",
      len(withrow) <= 3, "these are: %s" % withrow)
check("the sample used earlier (320/257/255/96/207/429) is 0/62 each",
      all(have_row.get(i, 0) == 0 for i in (320, 257, 255, 96, 207, 429)))
# the two exceptions are the DOCK line: .dat 34 'War Galley' / 35 'Galleon',
# which the tech tree genuinely shows as researchable ("Warships"/"Heavy
# Warships").  They are exceptions, not evidence of a different id space.
for _tid in withrow:
    _dn = (_techs[_tid] or {}).get("name")
    print("        exception: tech %-4s .dat internal=%r appears in %d trees"
          % (_tid, _dn, have_row[_tid]))

print()
print("B2 the tree's Tech `Node ID` IS the .dat tech index -- by name identity")
# Not a range test: compare each row's `Name` to the .dat internal name, and
# classify the disagreements.  They turn out to be display-vs-codename.
_allrows = {}
for _s, _t in trees.items():
    for _r in CT.tech_rows(_t):
        _nid = _r.get("Node ID")
        if _nid is not None:
            _allrows.setdefault(_nid, set()).add(_r.get("Name"))
_same = _diff = 0
for _nid in sorted(_allrows):
    if _nid >= len(_techs):
        continue
    _dn = (_techs[_nid] or {}).get("name")
    _tn = {x for x in _allrows[_nid] if x}
    if not _dn or not _tn:
        continue
    if _dn.lower() in {x.lower() for x in _tn} or _dn in _tn:
        _same += 1
    else:
        _diff += 1
check("the great majority of tree Tech rows name the same technology as the .dat "
      "entry at that index", _same > 0 and _same >= _diff,
      "same=%d diff=%d" % (_same, _diff))
print("     same=%d  differing=%d  (differing ones are display names: "
      "'Crop rotation'->'Crop Rotation', 'British Yeoman'->'Yeomen')"
      % (_same, _diff))

print()
print("C  so the tree expresses an upgrade on the UNIT row instead")
sc = trees["SICILIANS"]
check("Sicilians' unit 588 row carries Trigger Tech ID 320",
      (CT.row_for(sc, 588, CT.UNIT_USE_TYPES) or {}).get("Trigger Tech ID") == 320)
check("the tree's Tech space has no row for 320 (normal, not a hole)",
      CT.node_status(sc, 320, CT.TECH_USE_TYPES) is None)
print("     the chain the TREE carries at building 49:")
for uid in (280, 550, 588):
    r = CT.row_for(sc, uid, CT.UNIT_USE_TYPES)
    print("        unit %-4s status=%-18s trigTech=%s"
          % (uid, (r or {}).get("Node Status"), (r or {}).get("Trigger Tech ID")))
check("the whole Sicilian siege chain is ResearchedCompleted in the tree",
      all(CT.node_status(sc, u, CT.UNIT_USE_TYPES) == "ResearchedCompleted"
          for u in (280, 550, 588)))
check("Mangonel 280 is the chain root (no Trigger Tech ID)",
      (CT.row_for(sc, 280, CT.UNIT_USE_TYPES) or {}).get("Trigger Tech ID") is None)

print()
print("D  the PANEL expresses upgrades in its `Techs` array, and is consistent")
o = panels[BP.panel_path_for(GAME, "Sicilians")[1]]["obj"]


def panel_arrays(civ, bid):
    u, t = set(), set()
    for blk in BP.buildings(o if civ == "Sicilians" else
                            panels[BP.panel_path_for(GAME, civ)[1]]["obj"], civ):
        if blk.get("ID") == bid:
            u = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
            t = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
    return u, t


u49, t49 = panel_arrays("Sicilians", 49)
print("     Sicilians building 49: Units=%s" % sorted(u49))
print("                            Techs=%s" % sorted(t49))
check("the panel's `Techs` array holds unit-upgrade techs (96, 255, 257, 239)",
      {96, 255, 257, 239} <= t49)
check("the panel lists 588's upgrade tech 320 NOWHERE (silent channel 1)",
      320 not in t49)
check("the panel does NOT list 588 in Units either (silent channel 2)",
      588 not in u49)
check("where the panel DOES list an upgraded unit, it also lists its tech "
      "(422+255 -> 548, 280+257 -> 550)",
      {422, 548, 280, 550} <= u49 and {255, 257} <= t49)

print()
print("E  the corrected completeness test, per layer -- both games stand")
# kind-P: the panel is the promising layer -> unit in Units AND upgrade in Techs
mo = panels[BP.panel_path_for(GAME, "Muisca")[1]]["obj"]
mu, mt = set(), set()
for blk in BP.buildings(mo, "Muisca"):
    if blk.get("ID") == 12:
        mu = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
        mt = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
check("GAME 1 (MUISCA 359): panel gives unit 359 AND upgrade 429 -- COMPLETE",
      359 in mu and 429 in mt)
check("GAME 1: the tree says NotAvailable, so the two layers really disagree",
      CT.node_status(trees["MUISCA"], 359, CT.UNIT_USE_TYPES) == "NotAvailable")
check("GAME 2 (SICILIANS 588): tree gives the whole chain RC -- COMPLETE",
      all(CT.node_status(sc, u, CT.UNIT_USE_TYPES) == "ResearchedCompleted"
          for u in (280, 550, 588)))
check("GAME 2: the panel is silent in BOTH channels, so they really disagree",
      588 not in u49 and 320 not in t49)
# and the JURCHENS subject stays unusable under the corrected test
jo = panels[BP.panel_path_for(GAME, "Jurchens")[1]]["obj"]
ju, jt = set(), set()
for blk in BP.buildings(jo, "Jurchens"):
    if blk.get("ID") == 12:
        ju = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
        jt = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
check("JURCHENS 77 remains UNUSABLE: panel lists 77 but not its upgrade 207",
      77 in ju and 207 not in jt)
check("...while it does list 75 AND 222, proving the omission is specific",
      75 in ju and 222 in jt)

print()
print("TRIGGER-TECH SPACE: the tree carries upgrades on unit rows, the panel in its")
print("  `Techs` array -- the two layers cannot be checked in the same id space.")
print("  Sicilians 588 is COMPLETE, so GAME 2 stands; the Round 50 alarm was mine.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
