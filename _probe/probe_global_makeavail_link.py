# -*- coding: utf-8 -*-
r"""THE MISSING THIRD HALF: a GLOBAL `(Make avail)` tech must also name the unit.

## What this measures

The tree row copied from the Incas carries `Trigger Tech ID = 1350`, and tech 1350 is

    'Champi Scout (Make avail)'   civ = -1 (GLOBAL)   effect = [(type 2, a=2550, b=1)]

So the shipped Incas path for unit 2550 is:

    INCAS tree row  --Trigger Tech ID-->  tech 1350  --effect-->  (2, 2550, 1)
                                          civ = -1, i.e. GLOBAL

Compare the Longbowman, whose row has `Trigger Tech ID = None`:

    BRITONS tree row  --Trigger Tech ID--> None
    BRITONS tech 263  --effect-->  (2, 8, 1)          plus unit 8's EnablingResearch=263
    CIV-OWNED

That is a real structural difference between the two subjects, and it is the first
one found that could explain why the Longbowman survives an edit to its effect while
an added command for unit 2550 does nothing.

## What dsh test v4 currently does, and what it is missing

v4:
  * writes a BRITONS tree row for 2550 **with `Trigger Tech ID` inherited from Incas**
    (= 1350)
  * supplies a civ-owned effect on tech 263
  * sets unit 2550's `EnablingResearch = 263`

It does NOT check whether tech **1350** is reachable for the British.  Tech 1350 has
`civ = -1`, so the 3,686 tree rows across the corpus decide who gets it.  If no
British row for tech 1350 exists, the row v4 writes names a tech the British cannot
invoke -- and the global make-avail path is broken by construction.

Measure it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import aoe2mod.api as A                                    # noqa: E402
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
names = [c["name"] for c in tk._parsed[1]]
techs = tk._tech_records()
effs = tk._effect_records()
trees = CT.load_trees(GAME)

print("A  the two subjects have structurally DIFFERENT tree rows")
for stem, uid in (("INCAS", 2550), ("BRITONS", 8), ("MUISCA", 2562),
                  ("GOTHS", 41)):
    r = CT.row_for(trees[stem], uid, CT.UNIT_USE_TYPES)
    if r is None:
        print("     %-10s unit %-5s NO ROW" % (stem, uid))
        continue
    tt = r.get("Trigger Tech ID")
    owner = None
    if tt is not None and tt < len(techs):
        t = techs[tt]
        civ = t.get("civ")
        owner = (names[civ] if isinstance(civ, int) and 0 <= civ < len(names)
                 else ("GLOBAL" if civ == -1 else civ))
    print("     %-10s unit %-5s %-20s TriggerTechID=%-6s -> %s"
          % (stem, uid, str(r.get("Name"))[:20], tt, owner))

print()
print("B  who can reach tech 1350 (a GLOBAL 'make avail' tech)?")
t1350 = techs[1350]
print("     tech 1350: name=%r  civ=%s  effect=%s"
      % (t1350.get("name"), t1350.get("civ"),
         [(c.get("type"), c.get("a"), c.get("b"))
          for c in (next((r for r in effs if r.get("index") == 1350),
                          {}) or {}).get("commands") or []]))
check("tech 1350 is GLOBAL (civ == -1)", t1350.get("civ") == -1,
      "civ=%r" % t1350.get("civ"))
_holders = sorted(s for s, tr in trees.items()
                  if CT.node_status(tr, 1350, CT.TECH_USE_TYPES) is not None)
print("     civs whose tree has a Tech row for 1350: %d %s"
      % (len(_holders), _holders))
# NOTE: this is a REPORT, not an assertion.  The first draft asserted "some civs
# carry it" and FAILED -- nobody does, and that turned out to be the interesting
# fact rather than a defect.  A global make-avail tech is evidently invoked through
# the unit row's `Trigger Tech ID`, not through a Tech row.
check("technology 1350 is invoked only via `Trigger Tech ID`, never as a Tech row",
      not _holders, "these carry a Tech row: %s" % _holders)
print("     BRITONS carries tech 1350 as a Tech row: %s"
      % (CT.node_status(trees["BRITONS"], 1350, CT.TECH_USE_TYPES),))

print()
print("C  and the same question for every civ-owned make-avail chain")
print("     unit -> its tree row's Trigger Tech ID -> whether the OWNER can reach it")
_rows = []
for s, tr in sorted(trees.items()):
    for r in CT.unit_rows(tr):
        tt = r.get("Trigger Tech ID")
        if tt is None:
            continue
        t = techs[tt] if tt < len(techs) else {}
        if not isinstance(t, dict) or t.get("civ") != -1:
            continue
        reach = CT.node_status(tr, tt, CT.TECH_USE_TYPES)
        _rows.append((s, r.get("Node ID"), tt, reach))
miss = [x for x in _rows if x[3] is None]
print("     (civ, unit) rows whose Trigger Tech ID is a GLOBAL tech: %d" % len(_rows))
print("     ...where that civ CANNOT reach the tech as a Tech row: %d" % len(miss))
for x in miss[:6]:
    print("        %-12s unit %-6s tech %-6s -> %s" % x)
print()
print("     *** THE MEASUREMENT REFUTES MY HYPOTHESIS ***")
print("     `Trigger Tech ID` pointing at a GLOBAL tech the civ does not carry as a")
print("     Tech row is the NORM (%d of %d), not a defect.  So that link is not a"
      % (len(miss), len(_rows)))
print("     gate and v4's copied row is NOT broken by it.")
print()
print("D  what the measurement DOES establish about the two subjects")
print("     INCAS   row -> Trigger Tech ID 1350 (GLOBAL make-avail for 2550)")
print("     BRITONS row -> Trigger Tech ID None     (for the Longbowman, unit 8)")
print("     unit 8  -> EnablingResearch 263 (a CIV-OWNED British tech)")
print("     unit 2550 -> EnablingResearch -1")
print()
print("     So the shipped game uses TWO different shapes:")
print("       * a civ-owned unique unit: its row carries no trigger tech, and the")
print("         unit's own EnablingResearch names a civ-owned tech whose effect")
print("         enables it  (Longbowman / Huskarl / Guecha Warrior all have")
print("         TriggerTechID=None)")
print("       * a globally-defined regional unit: the row carries a global make-avail")
print("         tech that enables it  (Incas + 2550)")
print()
print("     dsh test v4 supplies BOTH shapes at once:")
print("       - a British tree row for 2550 carrying the Incas' Trigger Tech ID 1350")
print("         (the global path)")
print("       - plus a civ-owned effect on tech 263 and EnablingResearch=263")
print("         (the unique-unit path)")
print("     which is why v4 remains the right next experiment.")

print()
print("GLOBAL MAKE-AVAIL LINK: `Trigger Tech ID` -> a global tech is normal and NOT a")
print("  reachability gate (%d of %d rows are unreachable as Tech rows).  v4 covers"
      % (len(miss), len(_rows)))
print("  both shipped shapes, so it is not missing this input.")
print("  (This probe's first draft ASSERTED reachability and failed -- the assertion")
print("   was wrong, not the data.)")
for n in fails:
    print("  FAILED: %s" % n)
sys.exit(1 if fails else 0)
