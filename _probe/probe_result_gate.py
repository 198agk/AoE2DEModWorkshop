# -*- coding: utf-8 -*-
r"""THE USER'S RESULT IS IN: villager 1000 (control PASSED), no Champi Scout (test FAILED).

Per the pre-committed reading that is "the mod loaded but the availability write does
not reach the menu".  BEFORE accepting that, rule out the gate I myself discovered in
Round 49 and may have walked straight into:

  the unit's own `Trigger Tech ID` must be REACHABLE in the layer that promises the
  unit.

The INCAS donor row for 2550 carries `Trigger Tech ID = 1350`.  If the panel's
Barracks `Techs` array does not contain 1350, then the panel promises a unit whose
enabling research it does not offer -- the exact "incomplete path" defect that made
the Jurchens subject unusable.  A negative result then says nothing about whether the
menu reads the tree.

Check:
  A  what is tech 1350?
  B  does the INCAS panel list 1350 at the Barracks?  (the donor's own environment)
  C  does the SMOKE6 panel list 1350 at the Britons' Barracks?
  D  and does the Britons' TREE (as written by smoke6) contain 1350?
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
SMOKE6 = os.path.join(HERE, "out_smoke6")
UNIT = 2550
TECH = 1350
BLDG = 12

LANG = {}
for loc in ("zh", "en"):
    d = os.path.join(GAME, "resources", loc, "strings", "key-value")
    LANG[loc] = {}
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".txt"):
                continue
            for line in open(os.path.join(d, fn), "rb").read().decode(
                    "utf-8-sig", "replace").splitlines():
                k, _, v = line.strip().partition("\t")
                if v.startswith('"') and v.endswith('"'):
                    LANG[loc][k.strip()] = v[1:-1]

tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
_techs = tk._tech_records()

print("A  what is tech %d?" % TECH)
t = _techs[TECH] if TECH < len(_techs) else None
if t:
    sid = t.get("LanguageDLLName")
    print("     internal name : %r" % t.get("name"))
    print("     civ           : %r" % t.get("civ"))
    print("     LanguageDLLName: %r -> en=%r zh=%r"
          % (sid, LANG["en"].get(str(sid)), LANG["zh"].get(str(sid))))
    print("     effect count  : %r" % t.get("effect_count"))
else:
    print("     no such .dat tech")

print()
print("B  the DONOR civilization's own panel: is %d at building %d?" % (TECH, BLDG))
panels = BP.load_all(GAME)
for label, root_, civ in (("INCAS (donor)", GAME, "Incas"),
                          ("BRITONS (shipped)", GAME, "Britons"),
                          ("BRITONS (smoke6 mod)", SMOKE6, "Britons")):
    try:
        p = BP.load_all(root_) if root_ != GAME else panels
        key = BP.civ_key_for(p, civ)
        obj = p[BP.panel_path_for(root_, civ)[1]]["obj"]
    except Exception as exc:
        print("     %-22s ERROR %s" % (label, exc))
        continue
    units, techs = set(), set()
    for blk in BP.buildings(obj, key):
        if blk.get("ID") == BLDG:
            units = {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])}
            techs = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
    print("     %-22s unit %s in Units=%s   tech %s in Techs=%s   Techs=%s"
          % (label, UNIT, UNIT in units, TECH, TECH in techs, sorted(techs)))

print()
print("C  the TREE: does the written BRITONS tree carry tech %d?" % TECH)
for label, root_ in (("shipped", GAME), ("smoke6 mod", SMOKE6)):
    trees = CT.load_trees(root_)
    b = trees.get("BRITONS")
    if b is None:
        print("     %-12s no BRITONS tree" % label)
        continue
    st = CT.node_status(b, TECH, CT.TECH_USE_TYPES)
    print("     %-12s BRITONS tree Tech-space row for %d: %r" % (label, TECH, st))
    # does ANY civ's tree carry it (to learn where it lives)
_any = sorted(s for s, tr in CT.load_trees(GAME).items()
              if CT.node_status(tr, TECH, CT.TECH_USE_TYPES) is not None)
print("     civs whose SHIPPED tree carries tech %d as a Tech row: %d %s"
      % (TECH, len(_any), _any[:10]))

print()
print("D  what the INCAS tree row for the unit actually says")
inc = CT.load_trees(GAME)["INCAS"]
r = CT.row_for(inc, UNIT, CT.UNIT_USE_TYPES)
print("     %s" % {k: r.get(k) for k in
                    ("Node ID", "Name", "Node Type", "Node Status", "Age ID",
                     "Building ID", "Trigger Tech ID")})
print("     -> Trigger Tech ID %r" % r.get("Trigger Tech ID"))

print()
print("E  VERDICT INPUT")
_ok_panel = None
_o = panels[BP.panel_path_for(GAME, "Incas")[1]]["obj"]
for blk in BP.buildings(_o, "Incas"):
    if blk.get("ID") == BLDG:
        _ok_panel = {e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])}
print("     INCAS panel Techs at the Barracks: %s" % sorted(_ok_panel or []))
print("     contains %d: %s" % (TECH, TECH in (_ok_panel or set())))
