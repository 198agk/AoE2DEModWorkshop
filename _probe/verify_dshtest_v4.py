# -*- coding: utf-8 -*-
r"""Verify `dsh test v4` from DISK -- both halves, and nothing else.

v4 is the first artifact that carries all three layers at once:

    .dat   (1) new effect 1500, (2) tech 263 -> it, (3) unit 2550's EnablingResearch
           = 263, (4) unit 8's EnablingResearch cleared, (5) villager family HP 1000
    JSON   (6) CivTechTrees/BRITONS.json gains a row for 2550
           (7) futuravailableunits.json gains the Britons Barracks entry

Everything is re-read from the emitted files with fresh parsers, so the check is
about what the GAME would see, not about the in-memory model that produced it.
"""
import contextlib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.dat.parser as P                             # noqa: E402
from aoe2mod.game import buildpanel as BP                  # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"
V4 = os.path.join(HERE, "out_dshtest_v4")
DAT = os.path.join(V4, "resources", "_common", "dat", "empires2_x2_p1.dat")
TREE = os.path.join(V4, "resources", "_common", "dat", "CivTechTrees",
                    "BRITONS.json")
PANEL = os.path.join(V4, "resources", "_common", "dat",
                     "futuravailableunits.json")
UNIT, LONGBOW, VILLAGER, TECH, NEW_EFFECT, BLDG = 2550, 8, 83, 263, 1500, 12
fails = []


def check(name, ok, detail=""):
    print("  %-70s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def enabling(raw, gv_, want):
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    stage = next(t for t in pr.stage_offsets if "TechTree" in t[0])
    r = P.Reader(raw, gv=gv_)
    r.pos = stage[1] + 7 * 4
    n_ages, n_bldg = r.u8(), r.u8()
    n_units = r.i16() if r.gv >= P.GV_C32 else r.u8()
    r.i16() if r.gv == P.GV_CCV2 else r.u8()
    r.i32()
    for _ in range(n_ages):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(10); r.skip(10); r.u8(); r.i32()
    for _ in range(n_bldg):
        r.i32(); r.u8()
        for _ in range(3):
            k = r.u8()
            if k:
                r.i32_array(k)
        r.i32(); r.i32_array(10); r.i32_array(10)
        r.u8(); r.skip(5); r.skip(5); r.i32(); r.i32()
    for _ in range(n_units):
        uid = r.i32(); r.u8()
        r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); r.i32()
        r.i32()
        en = r.i32()
        if uid == want:
            return en
    return None


print("A  the artifact is complete and internally consistent")
for p, label in ((DAT, ".dat"), (TREE, "CivTechTrees/BRITONS.json"),
                 (PANEL, "futuravailableunits.json")):
    exists = os.path.isfile(p)
    print("     %-34s %s  %s" % (label, "present" if exists else "MISSING",
                                 ("%d B" % os.path.getsize(p)) if exists else ""))
    check("%s is present" % label, exists)

print()
print("B  the .dat half")
raw, how = P.load_dat(DAT)
with contextlib.redirect_stdout(io.StringIO()):
    pr = P.Parser(raw)
    pr.parse()
print("     %d bytes, %s, consumed %d, clean EOF %s"
      % (len(raw), how, pr.r.pos, pr.r.pos == len(raw)))
check("the .dat parses to exactly its own length", pr.r.pos == len(raw))
gv = pr.r.gv
check("the new effect exists with both commands",
      [tuple(c) for c in pr.stats["effects"][NEW_EFFECT]["commands"]]
      == [(2, LONGBOW, 1, -1, 0.0), (2, UNIT, 1, -1, 0.0)],
      "%s" % pr.stats["effects"][NEW_EFFECT]["commands"])
check("British tech %d points at it" % TECH,
      pr.stats["techs"][TECH]["effect_id"] == NEW_EFFECT)
check("unit %d's EnablingResearch is %d" % (UNIT, TECH),
      enabling(raw, gv, UNIT) == TECH, "got %s" % enabling(raw, gv, UNIT))
check("unit %d's EnablingResearch was CLEARED (negative control)" % LONGBOW,
      enabling(raw, gv, LONGBOW) == -1, "got %s" % enabling(raw, gv, LONGBOW))
_hp = sorted({u.get("hit_points") for c in pr.stats["civs"]
              for u in (c.get("units") or []) if u.get("id") == VILLAGER})
check("villagers are 1000 hp %s" % _hp, _hp == [1000])

print()
print("C  the tree half")
# `CT.load_trees(root)` appends `resources/_common/dat/CivTechTrees` itself, so the
# argument is the MOD ROOT (V4), not a path with the prefix stripped.  Stripping it
# raised `KeyError: 'BRITONS'` on a first attempt.
t = CT.load_trees(V4)
row = CT.row_for(t["BRITONS"], UNIT, CT.UNIT_USE_TYPES)
print("     BRITONS row for %d: %s" % (UNIT, row))
check("the Britons now have a tree row for %d" % UNIT, row is not None)
check("and it says ResearchedCompleted",
      (row or {}).get("Node Status") == "ResearchedCompleted")
check("at the Barracks (Age 1)",
      (row or {}).get("Building ID") == BLDG and (row or {}).get("Age ID") == 1)
check("the shipped Longbowman row is still ResearchedCompleted",
      (CT.row_for(t["BRITONS"], LONGBOW, CT.UNIT_USE_TYPES) or {}).get(
          "Node Status") == "ResearchedCompleted")
# only ONE row added?
_orig = CT.load_trees(GAME)["BRITONS"]
print("     rows: shipped %d -> v4 %d" % (len(CT.rows_of(_orig)),
                                          len(CT.rows_of(t["BRITONS"]))))
check("exactly one row was added",
      len(CT.rows_of(t["BRITONS"])) == len(CT.rows_of(_orig)) + 1)

print()
print("D  the panel half")
panels = BP.load_all(V4)
key = BP.civ_key_for(panels, "Britons")
b, e = BP.find_entry(panels[BP.panel_path_for(V4, "Britons")[1]]["obj"],
                     key, UNIT, BP.UNITS_KEY)
print("     Britons panel entry for %d: building %s  %s" % (UNIT, b, e))
check("the Britons panel lists %d" % UNIT, e is not None)
check("under the Barracks (%d)" % BLDG, b == BLDG)
# the shipped copy must NOT list it
_g = BP.load_all(GAME)
_gk = BP.civ_key_for(_g, "Britons")
_gb, _ge = BP.find_entry(_g[BP.panel_path_for(GAME, "Britons")[1]]["obj"],
                         _gk, UNIT, BP.UNITS_KEY)
check("the SHIPPED panel does not list it (so this is a real change)",
      _ge is None, "shipped entry=%s" % (_ge,))

print()
print("V4 VERIFIED: one mod carrying the .dat enable, the tree row and the panel "
      "entry -- plus control A and the negative control B.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
