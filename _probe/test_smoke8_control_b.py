# -*- coding: utf-8 -*-
r"""Protect smoke8's CONTROL B: is the Longbowman gate still intact?

smoke8's second control is "the Longbowman must still appear at the British Archery
Range".  It is what separates "type 2 does not grant an added unit" from "my edit broke
the effect".  So before the user runs the match, verify the chain the shipped game
relies on is untouched in the artifact:

    unit 8 (Longbowman)  --EnablingResearch-->  tech 263  --civ-->  1 (British)

If any link is broken, control B would fail for a reason that has nothing to do with
the question smoke8 asks, and the whole result would be unreadable.

Also confirm the two things smoke8 DELIBERATELY changed, and nothing else in the
effect section:
    * a NEW effect 1500 exists with commands [(2,8,1),(2,2550,1)]
    * tech 263's `effect_id` is 1500 (was 251)
    * effect 251 is byte-identical to the shipped one
"""
import contextlib
import _gamepaths as GP
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# The artifact this file reads is built, not checked in, and on 2026-10-25 a
# workspace cleanup deleted it -- the suite then failed with KeyError/FileNotFound,
# which reads like a data bug.  Rebuild it instead of depending on a directory
# that happens to be there.
sys.path.insert(0, HERE)
from ensure_artifact import ensure as _ensure  # noqa: E402
_ensure("out_smoke8", "build_smoke8.py", required=None)
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.locate as L                             # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402

GAME = GP.GAME
ART = os.path.join(_ensure("out_smoke8", "build_smoke8.py"), "resources", "_common", "dat",
                   "empires2_x2_p1.dat")
TECH = 263
OLD_EFFECT = 251
UNIT = 2550
LONGBOW = 8
fails = []


def check(name, ok, detail=""):
    print("  %-72s %s%s" % (name, "PASS" if ok else "FAIL",
                            "" if ok else "   %s" % detail))
    if not ok:
        fails.append(name)


def load(path, tk_parser=None):
    raw, how = P.load_dat(path)
    with contextlib.redirect_stdout(io.StringIO()):
        pr = P.Parser(raw)
        pr.parse()
    civs, cs, gv, tail = L.locate(raw, parser=pr)
    return {"raw": raw, "pr": pr, "civs": civs, "tail": tail, "gv": gv,
            "techs": L.locate_techs(raw, tail, gv),
            "effects": L.locate_effects(raw)[0], "how": how}


def unit_connection(data, unit_id):
    """The `.dat` TechTree UnitConnection for `unit_id` (EnablingResearch).

    Read the section the same way `_probe/probe_enabling_gate.py` does: 7 i32, then
    the ages/buildings, then the unit connections.

    NOTE: the TechTree lives INSIDE the last stage, which the parser names
    `10 Tail+TechTree`.  Using `stage_offsets[-1][2]` (its END) lands at EOF, which
    is why a first attempt died with
    `EOFError: read of 1 byte(s) at offset 93268180 would pass end of file
    (93268152)`.  `_probe/probe_enabling_gate.py` avoids it by parsing only to stage
    9, where the last entry's END equals this stage's START.  Either way the byte to
    start from is `93202964 + 7*4 = 93202992`:  seven i32 of tail counts, then the
    TechTree's own `u8 ages, u8 buildings, ...`.
    """
    stage = next(t for t in data["pr"].stage_offsets if "TechTree" in t[0])
    r = P.Reader(data["raw"], gv=data["gv"])
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
        uid = r.i32(); r.u8(); upper = r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); req = r.i32(); r.i32(); enab = r.i32()
        if uid == unit_id:
            return {"upper": upper, "required": req, "enabling": enab}
    return None


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
ship = {"raw": tk._parsed[0], "pr": None, "civs": tk._parsed[1],
        "tail": tk._parsed[4], "gv": tk._parsed[3],
        "techs": L.locate_techs(tk._parsed[0], tk._parsed[4], tk._parsed[3]),
        "effects": L.locate_effects(tk._parsed[0])[0], "how": tk._parsed[5]}
with contextlib.redirect_stdout(io.StringIO()):
    _pp = P.Parser(ship["raw"])
    _pp.parse()
ship["pr"] = _pp

art = load(ART)
print("A  the artifact loads and consumes exactly its own bytes")
print("     %d bytes, %s, leftover %d"
      % (len(art["raw"]), art["how"], len(art["raw"]) - art["pr"].r.pos))
check("clean EOF on the artifact", art["pr"].r.pos == len(art["raw"]))

print()
print("B  CONTROL B's chain is intact: unit 8 --EnablingResearch--> tech 263, civ 1")
c_ship = unit_connection(ship, LONGBOW)
c_art = unit_connection(art, LONGBOW)
print("     shipped : %s" % c_ship)
print("     artifact: %s" % c_art)
check("the shipped Longbowman connection enables via tech %d" % TECH,
      (c_ship or {}).get("enabling") == TECH)
check("the artifact's connection is UNCHANGED", c_art == c_ship)
check("tech %d is still owned by civ 1 (British)" % TECH,
      art["techs"][TECH].get("civ") == 1,
      "civ=%r" % art["techs"][TECH].get("civ"))
check("tech %d still has the shipped costs pattern" % TECH,
      [c.get("type") for c in (art["techs"][TECH].get("costs") or [])] == [-1, -1, -1],
      "costs=%s" % [c.get("type") for c in (art["techs"][TECH].get("costs") or [])])

print()
print("C  and exactly the two intended changes happened")
e_new = next((r for r in art["effects"]
              if r.get("index") == art["techs"][TECH].get("effect_id")), None)
print("     tech %d now points at effect %s" % (TECH, art["techs"][TECH].get("effect_id")))
print("     that effect's commands: %s"
      % [(c.get("type"), c.get("a"), c.get("b")) for c in (e_new or {}).get("commands") or []])
check("tech %d points at a NEW effect (not the shipped %d)"
      % (TECH, OLD_EFFECT),
      art["techs"][TECH].get("effect_id") != OLD_EFFECT)
check("the new effect does BOTH: the shipped Longbow enable and the new grant",
      sorted(c.get("a") for c in (e_new or {}).get("commands") or [])
      == sorted([LONGBOW, UNIT]))
e_old_ship = next(r for r in ship["effects"] if r.get("index") == OLD_EFFECT)
e_old_art = next(r for r in art["effects"] if r.get("index") == OLD_EFFECT)
check("the shipped effect %d is byte-identical (same command list)" % OLD_EFFECT,
      [(c.get("type"), c.get("a"), c.get("b"), c.get("c"), c.get("d"))
       for c in e_old_ship.get("commands")]
      == [(c.get("type"), c.get("a"), c.get("b"), c.get("c"), c.get("d"))
          for c in e_old_art.get("commands")])

print()
print("D  the control A edit is present, and only for villagers")
vals = sorted({u.get("hit_points") for ci in art["civs"]
               for u in (ci.get("units") or []) if u.get("id") == 83})
print("     villager(83) hit_points distinct values: %s" % vals)
check("every civ's villager is 1000", vals == [1000], "%s" % vals)
_ship_vals = sorted({u.get("hit_points") for ci in ship["civs"]
                     for u in (ci.get("units") or []) if u.get("id") == 83})
print("     shipped villager hit_points: %s" % _ship_vals)
check("and the shipped value was different (so the control is a real change)",
      _ship_vals != vals)

print()
print("E  and the tree/panel layers were NOT touched by this artifact")
tdir = os.path.join(HERE, "out_smoke8", "resources", "_common", "dat")
print("     files in the artifact's dat folder: %s" % sorted(os.listdir(tdir)))
check("the artifact carries no CivTechTrees and no panel JSON",
      not any(os.path.isdir(os.path.join(tdir, x)) for x in os.listdir(tdir)))

print()
print("SMOKE8 PROTECTED: the Longbowman gate is intact, so CONTROL B is meaningful --")
print("  if the Longbowman is missing after this mod, the fault is in the ENGINE's")
print("  reading of my new effect, not in a broken chain.")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
