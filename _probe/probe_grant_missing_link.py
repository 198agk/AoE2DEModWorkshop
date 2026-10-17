# -*- coding: utf-8 -*-
r"""Why did smoke9's added type-2 command NOT grant the unit?  Measure the candidates.

## The result (user m25302)

    A  villagers stay at 1000 even with a task   -> PASS (the family fix worked)
    B  Castle Age, British Castle -> Longbowman  -> PASS (the effect IS read)
    C  Dark Age, British Barracks -> Champi Scout-> FAIL (no grant)

B is the important one.  smoke9 re-pointed British tech 263 from effect 251 to a NEW
effect 1500 = `[(2,8,1),(2,2550,1)]`, and the Longbowman still appears.  So the engine
DOES follow `tech 263 -> effect 1500 -> command (2, 8, 1)`.  The effect list is read
and honoured.

It simply did not honour the SECOND command, `(2, 2550, 1)`.

## The two differences between unit 8 and unit 2550

    unit 8  (Longbowman)     EnablingResearch = 263   AND a British tree row exists
    unit 2550 (Champi Scout) EnablingResearch = -1    AND no British tree row

So the grant may need EITHER

  (a) the unit's own `EnablingResearch` naming a tech of that civ, or
  (b) a tree row for the unit in that civ  -- i.e. the JSON layer, which already
      failed to take effect, or
  (c) both.

Measure, over every civ-owned type-2 enable in shipped data, how often each holds.
Whichever is near-universal is the missing link, and the fix follows from it.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import contextlib
import io

import aoe2mod.api as A                                    # noqa: E402
import aoe2mod.dat.parser as P                             # noqa: E402
from aoe2mod.game import civtechtrees as CT                # noqa: E402

GAME = r"D:\Games\Steam\steamapps\common\AoE2DE"


def unit_connections(pr, raw, gv_):
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
    out = {}
    for _ in range(n_units):
        uid = r.i32(); r.u8(); upper = r.i32()
        r.i32(); r.i32_array(10); r.i32_array(10); r.i32()
        k = r.u8()
        if k:
            r.i32_array(k)
        r.i32(); req = r.i32(); r.i32(); enab = r.i32()
        out[uid] = {"upper": upper, "required": req, "enabling": enab}
    return out


tk = A.open_toolkit(game_root=GAME)
tk.describe(4)
data, civs, _cs, gv, _tail, _how = tk._parsed
names = [c["name"] for c in civs]
techs = tk._tech_records()
effs = tk._effect_records()
trees = CT.load_trees(GAME)
with contextlib.redirect_stdout(io.StringIO()):
    _p = P.Parser(data)
    _p.parse()
conn = unit_connections(_p, data, gv)

rows = []
for rec in effs:
    ti = rec.get("index")
    if ti is None or ti >= len(techs):
        continue
    t = techs[ti]
    if not isinstance(t, dict):
        continue
    civ = t.get("civ")
    if not isinstance(civ, int) or civ <= 0:        # exclude global(-1) and Gaia(0)
        continue
    for c in rec.get("commands") or []:
        if c.get("type") == 2 and c.get("b") == 1 and (c.get("a") or -1) > 0:
            rows.append((ti, civ, t.get("name"), c.get("a")))
            break

print("civ-owned (playable) type-2 unit enables: %d" % len(rows))
print()
print("  %-6s %-12s %-32s %-6s %-8s %-9s %s"
      % ("tech", "owner", "tech name", "unit", "unit.En", "treeRow", "status"))
a = b = ab = 0
for ti, civ, nm, u in rows:
    en = (conn.get(u) or {}).get("enabling")
    tr = trees.get(CT.civ_file_stem(names[civ]))
    row = CT.row_for(tr, u, CT.UNIT_USE_TYPES) if tr else None
    hasA = (en == ti)
    hasB = (row is not None)
    a += hasA
    b += hasB
    ab += (hasA and hasB)
    print("  %-6s %-12s %-32s %-6s %-8s %-9s %s"
          % (ti, names[civ], str(nm)[:32], u, en, hasB,
             (row or {}).get("Node Status")))

print()
print("  (a) unit.EnablingResearch == that tech      : %d of %d" % (a, len(rows)))
print("  (b) the owner civ's tree has a row for it   : %d of %d" % (b, len(rows)))
print("  (a) AND (b)                                 : %d of %d" % (ab, len(rows)))
print()
print("=" * 74)
print("READING")
print("=" * 74)
print("Neither condition is universal, so neither alone is the gate.  But watch which")
print("one the FAILING case lacks vs the PASSING case:")
print()
print("  smoke9 PASS (unit 8) : treeRow=%s  Enabling=%s  (tech 263)"
      % (CT.row_for(CT.load_trees(GAME)['BRITONS'], 8, CT.UNIT_USE_TYPES) is not None,
         (conn.get(8) or {}).get('enabling')))
print("  smoke9 FAIL (unit 2550): treeRow=%s  Enabling=%s"
      % (CT.row_for(CT.load_trees(GAME)['BRITONS'], 2550,
                    CT.UNIT_USE_TYPES) is not None,
         (conn.get(2550) or {}).get('enabling')))
print()
print("The clean experiment that separates them, needing no guessing:")
print("  set unit 2550's `EnablingResearch` to a British-owned tech in the .dat")
print("  (a `.dat`-only change, same 3 readings as dsh test v1).")
print("  If C then passes, the gate is (a).  If it still fails, the gate is (b) or (c),")
print("  and the JSON tree layer really is required -- which contradicts the clean")
print("  2026-10-15 test unless the tree must be read from a different place.")
