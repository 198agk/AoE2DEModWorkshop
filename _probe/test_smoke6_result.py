# -*- coding: utf-8 -*-
r"""PIN: the smoke6 result, and the one mechanism the `.dat` still offers.

## The result (user, m24260)

    「村民血量1000没问题，黑暗时代兵营没有蔷琵侦察兵」

  * **control PASSED** -- the mod loaded and the `.dat` edit rendered (villager 1000)
  * **test FAILED**    -- the Britons' Barracks offers no Champi Scout in the Dark Age

Per the pre-committed reading that is "the write does not reach the menu".  But
before accepting it, the gate I myself found in Round 49 had to be ruled out: does
the panel promise a unit whose enabling research it does not offer?

    INCAS (can build it)  panel Units: 2550 PRESENT ; panel Techs: 1350 ABSENT
    BRITONS (after write) panel Units: 2550 PRESENT ; panel Techs: 1350 ABSENT

**Identical shapes -- one works in game, one does not.**  So the gate is neither the
panel's `Techs` channel nor the tree's `Trigger Tech ID` row.

## The mechanism the `.dat` still offers

`TechTree.UnitConnection.EnablingResearch` is a per-civilization mechanism inside the
`.dat` (46 of 47 civ-owned enabling researches name exactly the civ the tree says can
build the unit).  It is read and discarded by the parser.

For the American regional units it is **-1**:

    unit 2550 Champi Scout   enabling=-1
    unit 2552                enabling=-1
    unit 2562/2566/2579      enabling=-1
    unit 8  Longbowman       enabling=263 -> British
    unit 41 Huskarl          enabling=270 -> Goths
    unit 5  Hand Cannoneer   enabling=85  -> GLOBAL

So enabling research does **not** gate 2550 either.

## What that leaves

The Britons' `.dat` record for 2550 and the Incas' are byte-for-byte the same except
for the `civ` field and offsets; the tree row written is field-identical to the
Incas' row; the panel entry is identical.  Three layers say yes for the Britons and
the game says no.  The remaining candidates, in order:

  1. a forth layer this project has not identified (a per-civ unit-line table);
  2. **caching** -- the tree may be read once at a point the mod cannot influence;
  3. the menu reads the SHIPPED `futuravailableunits.json` from the game directory
     and the mod's copy is never consulted for this path.

This pin records the measurement so a later round does not re-derive it, and marks
the honest boundary: **the availability write has now been tested in game and did
not take effect on the menu.**

Run:  $env:PYTHONPATH='D:\\Software\\AI\\帝国项目'; python _probe\test_smoke6_result.py
"""
import json
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
UNIT, TECH, BLDG = 2550, 1350, 12


def _find_installed(pattern):
    """Locate an installed mod folder whose name contains `pattern`.

    The earlier version hard-coded the folder name, so replacing smoke6 with smoke7
    made this pin fail for a reason that has nothing to do with what it pins: the
    artifact under test moved on.  Deriving the path keeps the measurement about the
    JSON write, which is what the file is for.
    """
    root = (r"C:\Users\26913\Games\Age of Empires 2 DE"
            r"\76561198406248391\mods\local")
    if not os.path.isdir(root):
        return None
    for d in sorted(os.listdir(root)):
        if pattern.lower() in d.lower():
            return os.path.join(root, d)
    return None


INSTALLED = _find_installed("Smoke6")
SMOKE7 = _find_installed("Smoke7")
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


print("A  the control worked, so the mod really loaded")
# The villager .dat edit is present in the installed artifact; the user saw 1000.
_tree = CT.load_trees(SMOKE6)
_ship = CT.load_trees(GAME)
# The measurement is about the ARTIFACT this project built and the user installed.
# smoke6 (JSON layers) has since been replaced by smoke7 (dat-only), so the
# installed-folder assertions are reported for whichever of them is present, and
# the JSON-layer content is asserted against the BUILT artifact, which still exists.
if INSTALLED:
    print("     [note] the smoke6 artifact is still installed at %s" % INSTALLED)
    _dat = os.path.join(INSTALLED, "resources", "_common", "dat",
                        "empires2_x2_p1.dat")
    check("it carries the .dat (11.98 MB)", os.path.exists(_dat) and
          os.path.getsize(_dat) > 10_000_000)
else:
    # Do NOT name a specific successor: the mod installed today may itself be
    # replaced next round (it already was, several times, and the naming scheme
    # changed to `dsh test vN` as well).  What matters is that SOME later experiment
    # is installed, so the replacement is a deliberate progression rather than an
    # accidental deletion.  Match ANY `dsh test` mod, and keep the old smoke names
    # for historical readability.
    _root = (r"C:\Users\26913\Games\Age of Empires 2 DE"
             r"\76561198406248391\mods\local")
    _later = []
    if os.path.isdir(_root):
        for d in sorted(os.listdir(_root)):
            if (d.startswith("dsh test ") or
                    any(k in d for k in ("Smoke7", "Smoke8", "Smoke9"))):
                _later.append(d)
    check("smoke6 was replaced on disk by a later test mod%s"
          % ((" (%s)" % ", ".join(_later)) if _later else ""),
          bool(_later))
    print("     the BUILT smoke6 artifact is still asserted below -- what this pin")
    print("     records is the CONTENT of the JSON-layer write, not its presence on")
    print("     the machine today")
_dat6 = os.path.join(SMOKE6, "resources", "_common", "dat", "empires2_x2_p1.dat")
check("the built smoke6 artifact still carries its .dat",
      os.path.exists(_dat6) and os.path.getsize(_dat6) > 10_000_000)
print("     the user saw villager hit points 1000 -> the .dat edit rendered in game")

print()
print("B  the availability write landed in BOTH layers of the artifact")
_r = CT.row_for(_tree["BRITONS"], UNIT, CT.UNIT_USE_TYPES)
check("the emitted BRITONS tree has a row for 2550", _r is not None)
if _r:
    print("     %s" % {k: _r.get(k) for k in
                       ("Node ID", "Name", "Node Status", "Age ID",
                        "Building ID", "Trigger Tech ID")})
check("and it is ResearchedCompleted at Age 1",
      (_r or {}).get("Node Status") == "ResearchedCompleted"
      and (_r or {}).get("Age ID") == 1)
_p = BP.load_all(SMOKE6)
_key = BP.civ_key_for(_p, "Britons")
_b, _e = BP.find_entry(_p[BP.panel_path_for(SMOKE6, "Britons")[1]]["obj"],
                       _key, UNIT, BP.UNITS_KEY)
check("the emitted panel lists 2550 at the Barracks",
      _e is not None and _b == BLDG, "bldg=%r entry=%r" % (_b, _e))
print("     -> both layers were written correctly, and the game did not show it")

print()
print("C  the INCAS have the SAME shape and the unit works for them there")
_inc = CT.row_for(CT.load_trees(GAME)["INCAS"], UNIT, CT.UNIT_USE_TYPES)
check("the donor row is field-identical to what was written",
      _inc is not None and all(_r.get(k) == _inc.get(k)
                               for k in ("Name", "Node Type", "Node Status",
                                         "Age ID", "Building ID",
                                         "Trigger Tech ID")))
print("     donor  : %s" % {k: _inc.get(k) for k in
                           ("Node Status", "Age ID", "Building ID",
                            "Trigger Tech ID")})
print("     written: %s" % {k: _r.get(k) for k in
                           ("Node Status", "Age ID", "Building ID",
                            "Trigger Tech ID")})


def _panel_techs(root, civ):
    p = BP.load_all(root)
    k = BP.civ_key_for(p, civ)
    o = p[BP.panel_path_for(root, civ)[1]]["obj"]
    for blk in BP.buildings(o, k):
        if blk.get("ID") == BLDG:
            return ({e.get("ID") for e in (blk.get(BP.TECHS_KEY) or [])},
                    {e.get("ID") for e in (blk.get(BP.UNITS_KEY) or [])})
    return set(), set()


print()
print("D  the panel's Techs channel is NOT the difference")
_it, _iu = _panel_techs(GAME, "Incas")
_bt, _bu = _panel_techs(SMOKE6, "Britons")
print("     INCAS   Units has 2550: %s   Techs has 1350: %s" % (UNIT in _iu,
                                                                TECH in _it))
print("     BRITONS Units has 2550: %s   Techs has 1350: %s" % (UNIT in _bu,
                                                                TECH in _bt))
check("the donor civ ALSO lacks tech 1350 in its panel Techs (so that is not the "
      "gate)", TECH not in _it)
check("and the written Britons panel matches that shape", TECH not in _bt)
print("     -> two civilizations with identical data shapes; one works, one does not")

print()
print("E  `EnablingResearch` is not the gate for this unit either")
# Measured by walking the .dat TechTree connections (see probe_enabling_gate.py for
# the reader).  Recorded here so the number is not re-derived by hand.
print("     unit 2550 connection: enabling=-1, required=-1, upper=-1")
print("     unit 8 Longbowman  : enabling=263 -> British   (civ-owned)")
print("     unit 41 Huskarl    : enabling=270 -> Goths      (civ-owned)")
print("     unit 5  Hand Cann : enabling=85  -> GLOBAL")
print("     [note] unit 2550 carries no enabling research (recorded fact; the "
      "reader lives in _probe/probe_enabling_gate.py)")

print()
print("SMOKE6 RESULT: the mod loaded (control passed) and the availability write did")
print("  NOT reach the menu.  Three layers agree for the Britons, the game says no.")
print("  Remaining candidates: an unidentified fourth layer; engine caching of the")
print("  tree; or the menu reading only the SHIPPED panel file.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
