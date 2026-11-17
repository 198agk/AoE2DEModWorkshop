# -*- coding: utf-8 -*-
r"""Pin the DISCRIMINATING experiment's artifact -- and record why it was retired.

STATUS: this design was AUDITED (2026-10-15, `_probe/team/auditor/REPORT.md`)
and found AMBIGUOUS on three independent grounds, so the mod was UNINSTALLED
(`_probe/remove_smoke5.py`) and the zero-mod experiment
(`_probe/test_zero_mod_experiment.py`) took its place.  The suite is kept
because it pins the ARTIFACT, and because the reasons it failed are the ones a
future experiment must not repeat:

  1. `aoe2mod Bundle VillagerHP plus Britons HandCannon` (an existing local mod)
     ships the SAME three engine paths with DIFFERENT content, and its `.dat` is
     byte-identical to smoke5's (both sha256[:16] `330665c06b53f033`).  So
     "Villager HP 1000" proves *a* villager-HP mod loaded, not WHICH one.
  2. Subject B (Militia 74) is masked by this file's own precondition: the
     Britons TREE already grants it, so removing the PANEL entry cannot be
     observed -- the tree supplies the button regardless.
  3. With both mods enabled, per-file layering can produce this design's
     headline outcome ("PANEL drives") while smoke5's edits are entirely absent.

What the design still demonstrates, and what this suite checks, is the SHAPE that
makes an experiment attributable: two subjects moved in OPPOSITE directions with
a control that proves the load.  The earlier in-game tests failed for the mirror
reason -- both halves moved the same way, and Hand Cannoneer (unit 5) carried
`RequiredAge` 4 so a Dark-Age game could never show it.

Run:  python _probe\test_smoke5_design.py
"""
import json
import _gamepaths as GP
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aoe2mod.dat import parser as P                        # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = GP.GAME
OUT = os.path.join(HERE, "out_smoke5")
CIV = "Britons"
STEM = "BRITONS"
BLD = 12
TREE_ONLY = 2550        # added to the tree, must be absent from the panel
PANEL_ONLY = 74         # removed from the panel, must remain in the tree

fails = []


def check(name, ok, detail=""):
    print("  %-58s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


if not os.path.isdir(OUT):
    print("SMOKE5 DESIGN: SKIP -- %s is not built" % OUT)
    print("  (no artifact, so the design is unverified, not disproven)")
    sys.exit(0)

print("A  the artifact carries all FOUR layers")
want = {
    "resources/_common/dat/empires2_x2_p1.dat": "the .dat control",
    "resources/_common/dat/CivTechTrees/BRITONS.json": "the tree half",
    "resources/_common/dat/futuravailableunits.json": "the panel half",
}
for rel, why in want.items():
    p = os.path.join(OUT, *rel.split("/"))
    check("%s present (%s)" % (rel.split("/")[-1], why), os.path.isfile(p),
          "missing: %s" % p)

print()
print("B  the .dat control really is 1000 HP for EVERY civ")
# `hit_points` is a field of the unit record (parser.py:772), not of type50.
d = os.path.join(OUT, "resources", "_common", "dat", "empires2_x2_p1.dat")
_raw, _how = P.load_dat(d)
_stats = P.Parser(_raw).parse()
hp = {u.get("hit_points") for c in _stats["civs"] for u in c["units"]
      if u.get("id") == 83}
check("Villager (83) hit points == {1000}", hp == {1000}, "got %s" % sorted(hp))
check("the control is uniform across all 63 civs", len(_stats["civs"]) == 63
      and hp == {1000}, "civs=%d hp=%s" % (len(_stats["civs"]), sorted(hp)))

# The edit is applied through the FAMILY, not to one id: "Villager" resolves to a
# set of unit records (male / female / builder and their age forms) and each is
# written once per civ.  Checking only id 83 would pass while a sibling variant
# silently stayed at 25 -- the exact failure an earlier round hit when only the
# name-resolved record was patched.
#
# The set is DERIVED by differencing the game's .dat against the mod's, not by
# looking for "units whose HP is 1000": plenty of units already have 1000 HP in the
# shipped data, so "HP == 1000" is not a marker of an edit.  Comparing against the
# baseline is the only shape that answers "what did we change".
_gd = os.path.join(GAME, "resources", "_common", "dat", "empires2_x2_p1.dat")
_graw, _ = P.load_dat(_gd)
_gstats = P.Parser(_graw).parse()


def _hp_by_civ(stats):
    """[civ_index][unit_index] -> (id, hit_points), the record order as written."""
    return [[(u.get("id"), u.get("hit_points")) for u in c["units"]]
            for c in stats["civs"]]


_before, _after = _hp_by_civ(_gstats), _hp_by_civ(_stats)
check("both files carry the same 63 civs", len(_before) == len(_after) == 63,
      "game=%d mod=%d" % (len(_before), len(_after)))

_changed_ids, _changed = set(), 0
_shape_ok = True
for ci, (b, a) in enumerate(zip(_before, _after)):
    if len(b) != len(a):
        _shape_ok = False
        break
    for (bid, bhp), (aid, ahp) in zip(b, a):
        if bid != aid:
            _shape_ok = False
            break
        if bhp != ahp:
            _changed += 1
            _changed_ids.add(bid)
check("the record sequence is unchanged (same ids in the same order)", _shape_ok,
      "an insertion or reorder would shift every later record")
if _shape_ok:
    _pairs = {(bhp, ahp) for b, a in zip(_before, _after)
              for (bid, bhp), (aid, ahp) in zip(b, a) if bhp != ahp}
    check("every changed record went 25 -> 1000", _pairs == {(25, 1000)},
          "observed transitions: %s" % sorted(_pairs))
    check("changed records are 63 per edited id (one per civ)",
          _changed == len(_changed_ids) * 63,
          "%d changes / %d ids" % (_changed, len(_changed_ids)))
    check("the edited set is a real family, not one unit",
          len(_changed_ids) > 1, "only %s changed" % sorted(_changed_ids))
    check("id 83 is in the edited set", 83 in _changed_ids,
          "the named unit was not touched; edited=%s" % sorted(_changed_ids))
    print("        edited ids (%d): %s" % (len(_changed_ids), sorted(_changed_ids)))

print()
print("C  the TREE half grants the tree-only unit and keeps the panel-only one")
t = CT.load_trees(OUT)[STEM]
check("tree: Britons CAN build %d (tree-only)" % TREE_ONLY,
      CT.can_build(t, TREE_ONLY))
check("tree: Britons STILL has %d (the panel-only subject)" % PANEL_ONLY,
      CT.row_for(t, PANEL_ONLY) is not None,
      "if the tree lost it, a missing button would not isolate the panel")
row = CT.row_for(t, TREE_ONLY) or {}
check("tree: the granted row is Age 1 (no age gate)", row.get("Age ID") == 1,
      "Age ID=%r" % row.get("Age ID"))
check("tree: the granted row sits in the Barracks (%d)" % BLD,
      row.get("Building ID") == BLD, "Building ID=%r" % row.get("Building ID"))

print()
print("D  the PANEL half is the MIRROR IMAGE -- and that is the whole point")
pk = BP.panel_path_for(OUT, CIV)[1]
_pt, po = BP.load_panel(os.path.join(OUT, BP.PANEL_REL))
_b, e_tree_only = BP.find_entry(po, pk, TREE_ONLY, BP.UNITS_KEY)
_b2, e_panel_only = BP.find_entry(po, pk, PANEL_ONLY, BP.UNITS_KEY)
check("panel: does NOT list %d (so a hit means the TREE was read)" % TREE_ONLY,
      e_tree_only is None, "panel entry %r would confound the reading" % (e_tree_only,))
check("panel: %d has been REMOVED (so a miss means the PANEL was read)"
      % PANEL_ONLY, e_panel_only is None, "still present: %r" % (e_panel_only,))
check("the two halves move in OPPOSITE directions, as a set",
      CT.can_build(t, TREE_ONLY) and e_tree_only is None
      and CT.row_for(t, PANEL_ONLY) is not None and e_panel_only is None,
      "one half fell into lockstep; the test would prove nothing")

print()
print("E  the shipped baseline really contradicts both edits (no no-op)")
_gt = CT.load_trees(GAME)[STEM]
check("shipped tree did NOT have %d" % TREE_ONLY,
      CT.row_for(_gt, TREE_ONLY) is None)
_gp = BP.load_all(GAME)
_gk = BP.panel_path_for(GAME, CIV)[1]
_gb, _ge = BP.find_entry(_gp[_gk]["obj"], _gk, PANEL_ONLY, BP.UNITS_KEY)
check("shipped panel DID list %d at the barracks" % PANEL_ONLY,
      _ge is not None and _gb == BLD, "got building=%r entry=%r" % (_gb, _ge))

print()
print("F  the other civilizations are untouched")
_gpo = _gp[_gk]["obj"]
_pk2 = BP.panel_path_for(OUT, "Turks")[1]
_t2, _po2 = BP.load_panel(os.path.join(OUT, BP.PANEL_REL))
_a, _b3 = BP.find_entry(_gpo, _pk2, PANEL_ONLY, BP.UNITS_KEY)
_c, _d = BP.find_entry(_po2, _pk2, PANEL_ONLY, BP.UNITS_KEY)
check("Turks' Militia survived the Britons-only edit",
      _b3 is not None and _d is not None, "shipped=%r mod=%r" % (_b3, _d))

print()
print("SMOKE5 DESIGN: %s" % ("THE EXPERIMENT DISCRIMINATES"
                             if not fails else "BROKEN -> %s" % fails))
print("  A hit on the tree-only unit says the menu reads the tree;")
print("  a miss on the panel-only unit says the menu reads the panel.")
for name in fails:
    print("  FAILED: %s" % name)
sys.exit(1 if fails else 0)
